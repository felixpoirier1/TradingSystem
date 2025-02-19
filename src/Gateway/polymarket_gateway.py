import dotenv
import os

from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

import json
import time
from datetime import datetime, timedelta
from threading import Lock, Thread, Event
from websocket import WebSocketApp, WebSocketConnectionClosedException

from .base_gateway import Gateway
from trading.order_types import Side
from typing import List, Dict
import logging

class PolymarketGateway(Gateway):
    NAME = "PolymarketGateway"
    dotenv.load_dotenv(".config/.env")
    _api_key = os.environ["POLYMARKET_API_KEY"]
    _rest_host = "https://clob.polymarket.com"
    _stream_host = "wss://ws-subscriptions-clob.polymarket.com"
    _markets_dir = "data/polymarket_markets.json"
    _chain_id = POLYGON
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

    def _process_pm_book_msg(self, msg: dict):
        bids = msg["bids"]
        asks = msg['asks']
        midpoint = (int(1000*float(asks[-1]["price"])) + int(1000*float(bids[-1]["price"])))/2

    def attachFeed(self, feed):
        self.feed = feed

    def runMarketStream(self):
        try:
            self.__market_th.run()
        except KeyboardInterrupt:
            self.__market_th.join()

    def __connect(self):
        chain_id: int = POLYGON
        self.client = ClobClient(self._rest_host, key=self._api_key, chain_id=chain_id)
        self.client.set_api_creds(self.client.create_or_derive_api_creds())

    def ping(self, ws):
        while not self.ping_thread_stop_event.is_set():
            try:
                time.sleep(5)
                ws.send("PING")
            except WebSocketConnectionClosedException:
                logging.debug("Ping thread detected closed connection, exiting.")
                break
            except Exception as e:
                logging.error(f"Error in ping thread: {e}")
                break
    
    def __stream_market_on_open(self, ws: WebSocketApp):
        logging.debug("Polymarket stream connection opened")
        ws.send(json.dumps(self.market_subscription_message))
        self.ping_thread_stop_event = Event() 
        self.ping_thread = Thread(target=self.ping, args=(ws,))
        self.ping_thread.start()

    def __stream_market_on_message(self, ws, message):
        try:
            if (isinstance(message, list) and len(message) == 0) or (isinstance(message, str) and message == "PONG"):
                return
            resp_l = json.loads(message)
            for resp in resp_l:
                if isinstance(resp, dict) and resp["event_type"] in ["book", "price_change"]:
                    filename = f"data/polymarket_ws_markets/{resp["asset_id"]}.log"
                    if not os.path.exists(filename):
                        open(filename, "x")
                    with open(filename, "a") as f:
                        f.write(json.dumps(resp) + "\n")
        except Exception as e:
            print(e)
            
    def __stream_market_on_error(self, ws, error):
        logging.error("Error was sent")

    def __stream_market_on_close(self, ws, close_status_code, close_msg):
        logging.info(f"WebSocket closed: {close_status_code}, {close_msg}. Reconnecting...")
        # ensure ping thread is stopped
        self.ping_thread_stop_event.set()
        if self.ping_thread:
            self.ping_thread.join()
            self.ping_thread = None

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
        ws = WebSocketApp(f"{self._stream_host}/ws/market",
            on_open = self.__stream_market_on_open,
            on_message = self.__stream_market_on_message,
            on_error = self.__stream_market_on_error,
            on_close = self.__stream_market_on_close)
        self.market_subscription_message = {
            "auth": None,
            "type": "market",
            "assets_ids": self.subscribed_markets
        }
        ws.run_forever()

    def beginStream(self):
        self.__connect()
        self.__market_th = Thread(target=self.__stream_market)
        self.__market_th.start()

    def endStream(self):
        pass
    
    def _download_markets(self, obj_vector, evt: Event):
        # download from polymarket
        next_cursor = ""
        while True:
            resp = self.client.get_markets(next_cursor)
            obj_vector += resp['data']
            next_cursor = resp['next_cursor']
            logging.debug(f"Fetched markets, received next cursor {next_cursor}")
            if resp['next_cursor'] == "LTE=":
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
