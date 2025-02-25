import dotenv
import os

from py_clob_client.client import ClobClient
from py_clob_client.constants import POLYGON

import json
import time
from datetime import datetime, timedelta
from threading import Lock, Thread, Event
import websockets
from websockets.exceptions import ConnectionClosed
import asyncio
import requests
from typing import List, Dict
import logging

from .base_gateway import Gateway

class PolymarketGateway(Gateway):
    NAME = "PolymarketGateway"
    dotenv.load_dotenv(".config/.env")
    _api_key = os.environ["POLYMARKET_API_KEY"]
    _rest_host = "https://clob.polymarket.com"
    _gamma_host = "https://gamma-api.polymarket.com"
    _stream_host = "wss://ws-subscriptions-clob.polymarket.com"
    _markets_dir = "data/polymarket_markets.json"
    _chain_id = POLYGON
    def __init__(self, subscribed_markets: List[str]):
        websockets_logger = logging.getLogger('websockets')
        websockets_logger.setLevel(logging.INFO) # Set websockets logger to INFO
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

    async def ping(self, ws):
        try:
            while True:
                await ws.send("PING")
                await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Error in ping thread: {e}")
            raise e

    async def __stream_market_on_open(self, ws: websockets.WebSocketClientProtocol):
        await ws.send(json.dumps(self.market_subscription_message))
        self.ping_task = asyncio.create_task(self.ping(ws)) 

    async def __stream_market_on_message(self, message):
        try:
            if (isinstance(message, list) and len(message) == 0) or (isinstance(message, str) and message == "PONG"):
                return
            resp_l = json.loads(message)
            for resp in resp_l:
                if isinstance(resp, dict) and resp["event_type"] in ["book", "price_change"]:
                    filename = f"data/polymarket_ws_markets/{resp['asset_id']}.log"
                    if not os.path.exists(filename):
                        open(filename, "x")
                    with open(filename, "a") as f:
                        f.write(json.dumps(resp) + "\n")
        except Exception as e:
            logging.error(f"Error in stream market on message: {e}")
            
    async def __stream_market_on_error(self, ws, error):
        logging.error("Error was sent from the server")

    async def __stream_market_on_close(self, ws, close_status_code, close_msg):
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
            self.market_subscription_message = {
                "auth": None,
                "type": "market",
                "assets_ids": self.subscribed_markets
            }
            async with websockets.connect(f"{self._stream_host}/ws/market") as ws:
                await self.__stream_market_on_open(ws)
                async for message in ws:
                    await self.__stream_market_on_message(message)
        except websockets.ConnectionClosed as e:
            logging.error(f"WebSocket connection closed: {e.code}, {e.reason}")
            await self.__stream_market_on_close(ws, e.code, e.reason)
        except Exception as e:
            logging.error(f"WebSocket error: {e}")
            await self.__stream_market_on_error(ws, e)

    async def beginStream(self):
        self.__connect()
        await self.__stream_market()

    async def endStream(self):
        if hasattr(self, 'ping_task') and self.ping_task:
            self.ping_task.cancel()
            try:
                await self.ping_task
            except asyncio.CancelledError:
                logging.info("Ping task cancelled")
        if hasattr(self, 'ws') and self.ws:
            await self.ws.close()
            logging.info("Websocket closed by endStream")
    
    def _download_markets(self, obj_vector, evt: Event):
        # download from polymarket
        limit = 100  # Set the number of items to fetch per request
        offset = 0

        while True:
            params = {
                "order": "createdAt",
                "ascending": "True",
                "archived": "false",
                "active": "true",
                "closed": "false",
                "limit": limit,
                "offset": offset
            }

            response = requests.get(self._gamma_host + "/markets", params=params)
            response_data = response.json()  # Convert the response to JSON
            
            # Check if there's data in the response
            if isinstance(response_data, list) and response_data:
                obj_vector.extend(response_data)  # Add the current page of markets to the list
                offset += limit  # Move to the next set of data
            else:
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
