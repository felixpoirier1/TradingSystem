import dotenv
import os

import json
import time
from datetime import datetime, timedelta
from threading import Thread, Event
import websockets
import logging
import requests as r

from typing import List, Dict
from enum import Enum

import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.exceptions import InvalidSignature

from .base_gateway import Gateway

class Environment(Enum):
    DEMO = "demo"
    PROD = "prod"

class KalshiGateway(Gateway):
    NAME = "KalshiGateway"
    dotenv.load_dotenv(".config/.env")

    def __init__(self, subscribed_markets: List[str], environment: str = "demo"):
        websockets_logger = logging.getLogger('websockets')
        websockets_logger.setLevel(logging.INFO)
        logging.debug(f"environment: {environment}")
        environment = Environment(environment)
        self._api_key_id = os.environ["KALSHI_DEMO_KEYID"] if environment == Environment.DEMO else os.environ["KALSHI_PROD_KEYID"]
        self._api_key_filepath = os.environ["KALSHI_DEMO_KEYFILE"] if environment == Environment.DEMO else os.environ["KALSHI_PROD_KEYFILE"]
        self._api_key = self.load_private_key_from_file(self._api_key_filepath)
        self._rest_host = "https://api.elections.kalshi.com" if environment == Environment.PROD else "https://demo-api.kalshi.co"
        self._stream_host = "wss://api.elections.kalshi.com" if environment == Environment.PROD else "wss://demo-api.kalshi.co"
        self._markets_dir = "data/kalshi_markets.json"

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

        sig = self.__sign_pss_text(msg_string)

        headers = {
            'Content-Type': 'application/json',  # Important for POST requests with JSON body
            'KALSHI-ACCESS-KEY': self._api_key_id,
            'KALSHI-ACCESS-SIGNATURE': sig,
            'KALSHI-ACCESS-TIMESTAMP': timestamp_str
        }
        return headers
    
    def load_private_key_from_file(self, file_path):
        with open(file_path, "rb") as key_file:
            private_key = serialization.load_pem_private_key(
                key_file.read(),
                password=None,  # Or your password if the key is encrypted
            )
        return private_key
    
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
    
    async def __stream_market_on_open(self, ws: websockets.WebSocketClientProtocol):
        logging.debug("Kalshi stream connection opened")
        await ws.send(json.dumps(self.market_subscription_message))
        self.msg_id += 1

    async def __stream_market_on_message(self, message):
        try:
            logging.debug(json.dumps(message))
        except Exception as e:
            logging.error(f"Error in stream market on message: {e}")

    async def __stream_market_on_error(self, error):
        logging.error(f"Error was sent:\n{error}")

    async def __stream_market_on_close(self, close_status_code, close_msg):
        logging.info(f"WebSocket closed: {close_status_code}, {close_msg}. Reconnecting...")
        # ensure ping thread is stopped
        self.ping_task.cancel()

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
            await self.__stream_market()

    async def __stream_market(self):
        try:
            headers = self.__header("GET", "/trade-api/ws/v2")
            url_suffix = "/trade-api/ws/v2"
            self.market_subscription_message = {
                "id": self.msg_id,
                "cmd": "subscribe",
                "params": {
                    'channels': ['orderbook_delta'],
                    'market_tickers': self.subscribed_markets
                }
            }
            async with websockets.connect(f"{self._stream_host}{url_suffix}", additional_headers=headers) as ws:
                await self.__stream_market_on_open(ws)
                async for message in ws:
                    await self.__stream_market_on_message(message)
        except websockets.ConnectionClosed as e:
            logging.error(f"WebSocket connection closed: {e.code}, {e.reason}")
            await self.__stream_market_on_close(e.code, e.reason)
        except Exception as e:
            logging.error(f"WebSocket error: {e}")
            await self.__stream_market_on_error(e)

    async def beginStream(self):
        await self.__stream_market()

    def endStream(self):
        pass