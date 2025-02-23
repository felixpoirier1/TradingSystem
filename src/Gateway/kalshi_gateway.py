import dotenv
import os

from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

import json
import time
from datetime import datetime, timedelta
from threading import Lock, Thread, Event
from websocket import WebSocketApp, WebSocketConnectionClosedException
import asyncio

from .base_gateway import Gateway
from trading.order_types import Side
from typing import List, Dict
import logging
from utils.kalshi_api_key_decryption import load_private_key_from_file
import requests as r
import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.exceptions import InvalidSignature


class KalshiGateway(Gateway):
    NAME = "KalshiGateway"
    dotenv.load_dotenv(".config/.env")
    _api_key_filepath = ".config/kalshi-api-key.key"
    _api_key = load_private_key_from_file(_api_key_filepath)
    _api_key_id = os.environ["KALSHI_API_KEY_ID"]
    _rest_host = "https://api.elections.kalshi.com"
    _stream_host = "wss://api.elections.kalshi.com"
    _markets_dir = "data/kalshi_markets.json"

    def __init__(self, subscribed_markets: List[str]):
        self.markets = None
        self.markets_last_updated = datetime.min
        if os.path.isfile(self._markets_dir):
            with open(self._markets_dir, "r") as markets_file:
                try:
                    markets_dict = json.load(markets_file)
                    self.markets = markets_dict["markets"]
                    self.markets_last_updated = markets_dict["last_update"]
                except:
                    logging.error(f"Error reading markets file stored at {self._markets_dir}")
        else:
            logging.debug(f"File {self._markets_dir} does not exist.")

        self.subscribed_markets = subscribed_markets
        self.market_msgs: Dict[str, List] = {id: [] for id in self.subscribed_markets}
        self.msg_id = 1

    def __header(self, method, path):
        current_time_milliseconds = int(time.time() * 1000)
        timestamp_str = str(current_time_milliseconds)
        msg_string = timestamp_str + method + path  # String to be signed
        logging.info(f"msg_string: {msg_string}")  # Print for inspection

        sig = self.__sign_pss_text(msg_string)

        headers = {
            'Content-Type': 'application/json',  # Important for POST requests with JSON body
            'KALSHI-ACCESS-KEY': self._api_key_id,
            'KALSHI-ACCESS-SIGNATURE': sig,
            'KALSHI-ACCESS-TIMESTAMP': timestamp_str
        }
        logging.info(str(headers))
        return headers

    def __sign_pss_text(self, text: str) -> str:
        """Signs the text using RSA-PSS and returns the base64 encoded signature."""
        message = text.encode('utf-8')
        try:
            signature = self._api_key.sign(
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH
                ),
                hashes.SHA256()
            )
            return base64.b64encode(signature).decode('utf-8')
        except InvalidSignature as e:
            raise ValueError("RSA sign PSS failed") from e
        
    def __get(self, endpoint, params, headers = None, ret_type="json"):
        path = KalshiGateway._rest_host + endpoint
        if headers is None:
            headers = self.__header("GET", path)
        resp = r.get(path, params=params, headers=headers)
        if ret_type == "json":
            return resp.json()
        else:
            return resp

    def _download_markets(self, obj_vector, evt: Event):
        # download from polymarket
        next_cursor = ""
        params = {
            'status': ['open'],
            'limit': 1000
        }
        while True:
            resp = self.__get("/trade-api/v2/markets", params)
            obj_vector += resp['markets']
            next_cursor = resp['cursor']
            logging.debug(f"Fetched markets, received next cursor {next_cursor}")
            if resp['cursor'] == "":
                break
        # set event flag to false
        evt.set()
        # save to class & file
        self.markets = obj_vector
        with open(self._markets_dir, "w") as markets_file:
            try:
                obj_dict = {"last_update": datetime.now().strftime("%d/%m/%Y, %H:%M:%S"), "markets": obj_vector}
                json.dump(obj_dict, markets_file, indent=4)
            except Exception as e:
                logging.error(f"Error reading markets file stored at {self._markets_dir}:\n{e}")

    def getMarkets(self, download):
        if (download or self.markets is None) or \
           (download is None and self.markets_last_updated < datetime.now() - timedelta(1)):
            logging.info("Downloading markets data")
            evt = Event()
            markets = []
            evt.clear()
            t = Thread(target=self._download_markets, args=(markets, evt))
            t.start()
            # returns an Event object for market download & the datastructure itself
            return (evt, markets)

        else:
            return self.markets
        
    def attachFeed(self, feed):
        self.feed = feed

    def runMarketStream(self):
        try:
            self.__market_th.run()
        except KeyboardInterrupt:
            self.__market_th.join()
    
    def __stream_market_on_open(self, ws: WebSocketApp):
        logging.debug("Kalshi stream connection opened")
        ws.send(json.dumps(self.market_subscription_message))

    def __stream_market_on_message(self, ws, message):
        # try:
        #     if (isinstance(message, list) and len(message) == 0) or (isinstance(message, str) and message == "PONG"):
        #         return
        #     resp_l = json.loads(message)
        #     for resp in resp_l:
        #         if isinstance(resp, dict) and resp["event_type"] in ["book", "price_change"]:
        #             filename = f"data/polymarket_ws_markets/{resp["asset_id"]}.log"
        #             if not os.path.exists(filename):
        #                 open(filename, "x")
        #             with open(filename, "a") as f:
        #                 f.write(json.dumps(resp) + "\n")
        # except Exception as e:
        #     print(e)
        logging.debug(str(message))
            
    def __stream_market_on_error(self, ws, error):
        logging.error(f"Error was sent:\n{error}")

    def __stream_market_on_close(self, ws, close_status_code, close_msg):
        logging.info(f"WebSocket closed: {close_status_code}, {close_msg}. Reconnecting...")

        self.last_retry = getattr(self, "last_retry", datetime.min)

        # if last retry was more than 1h ago, restart retry counter
        if (datetime.now() - self.last_retry).seconds/60/60 > 1:
            self.retry_count = 1
        else:
            self.retry_count = getattr(self, "retry_count", 0) + 1
        self.last_retry = datetime.now()

        # if more than 10 retries within last hour, stop trying to connect
        if self.retry_count > 10:
            logging.error("Did not manage to re-establish connection with Polymarket socket API.")
        # try to connect otherwise, using exponential wait times
        else:
            time.sleep(min(2**(self.retry_count), 60))
            self.__stream_market()

    def __stream_market(self):
        url_suffix = "/trade-api/ws/v2"
        logging.info(f"{self._stream_host}{url_suffix}")
        ws = WebSocketApp(f"{self._stream_host}{url_suffix}",
            header = self.__header("GET", url_suffix),
            on_open = self.__stream_market_on_open,
            on_message = self.__stream_market_on_message,
            on_error = self.__stream_market_on_error,
            on_close = self.__stream_market_on_close)
        logging.debug(self.subscribed_markets)
        self.market_subscription_message = {
            "id": self.msg_id,
            "cmd": "subscribe",
            "params": {
                'channels': ['orderbook_delta'],
                'market_tickers': self.subscribed_markets
            }
        }
        logging.debug("Launching websocket")
        ws.run_forever()

    def beginStream(self):
        self.__market_th = Thread(target=self.__stream_market)
        self.__market_th.start()

    def endStream(self):
        pass