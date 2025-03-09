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
import logging
import traceback
import inspect
from typing import List, Dict, Union, Tuple

from trading.orderbooks import PredictionMarketOrderBook, Side, Action
from .base_gateway import Gateway
from utils.conventions import price_adapter, size_adapter
from utils.callback_manager import CallbackManager
from utils.polymarket_callbacks import callback_sig_table
from ml.theo.agent import TheoAgent

class PolymarketGateway(Gateway):
    """
    Gateway for interacting with the Polymarket platform, including fetching market data and streaming updates.
    """
    NAME = "PolymarketGateway"
    dotenv.load_dotenv(".config/.env")
    _api_key = os.environ["POLYMARKET_API_KEY"]
    _fund_addr = os.environ["POLYMARKET_PROXY_ADDRESS"]
    _rest_host = "https://clob.polymarket.com"
    _gamma_host = "https://gamma-api.polymarket.com"
    _stream_host = "wss://ws-subscriptions-clob.polymarket.com"
    _markets_dir = "data/polymarket_markets.json"
    _chain_id = POLYGON

    def __init__(self, subscribed_markets: List[str]):
        """
        Initializes the PolymarketGateway with subscribed markets and sets up WebSocket connections.

        Args:
            subscribed_markets (List[str]): A list of market IDs to subscribe to.
        """
        # logger dedicated to the websocket
        websockets_logger = logging.getLogger('websockets')
        websockets_logger.setLevel(logging.DEBUG) # Set websockets logger to INFO
        self.ws = None
        self.markets = None
        # last time when a market query was performed
        self.markets_last_updated = datetime.min
        # open reference file with last market query
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

        # list of market ids that websocket connects to
        self.subscribed_markets = subscribed_markets

        self.__theo_agent = TheoAgent()

        # self.market_msgs: Dict[str, List] = {id: [] for id in self.subscribed_markets}
        # dictionary of every order book for each subscribed market
        self.order_books: Dict[str, PredictionMarketOrderBook] = {id: PredictionMarketOrderBook(id, 1, msg_processor=PolymarketGateway._process_pm_book_msg) for id in self.subscribed_markets}
        self.callback_sigs = callback_sig_table
        self.callback_mgr = CallbackManager()
        self.initialize_callbacks()

    def _process_pm_book_msg(message: dict):
        """
        Processes Polymarket book messages and returns a list of actions to be performed.

        Args:
            message (dict): The message received from the Polymarket WebSocket.

        Returns:
            List[Tuple[Action, Dict]]: A list of actions and their corresponding arguments.
        """
        try:
            if message["event_type"] == "book":
                return [(Action.REINIT, {"bids": [(price_adapter(pl['price']), size_adapter(pl['size'])) for pl in message["bids"]], "asks": [(price_adapter(pl['price']), size_adapter(pl['size'])) for pl in message["asks"]]})]
            elif message["event_type"] == "price_change":
                return [(Action.MODIFY, {"price": price_adapter(msg['price']), "side": Side.ASK if msg["side"] == "SELL" else Side.BID, "size": size_adapter(msg['size'])}) for msg in message["changes"]]
            elif message["event_type"] == "tick_size_change":
                return [(Action.TICK, {"tick_size": price_adapter(message["new_tick_size"])})]

            else:
                return []
            
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__) 
            logging.error(f"Error processing polymarket book message: {[t for t in tb]}")
            logging.error(f"Message: {message}")
            return []
    
    def initialize_callbacks(self):
        logging.debug(f"Initializing callbacks {self.callback_sigs}")
        for func_name, sig in self.callback_sigs.items():
            self.callback_mgr.define_callback(func_name, sig)
        logging.debug("Callbacks initialized successfully")

    def attachFeed(self, feed):
        """
        Attaches a feed to the gateway.

        Args:
            feed: The feed to attach.
        """
        self.feed = feed

    def runMarketStream(self):
        """
        Runs the market stream.
        """
        try:
            self.__market_th.run()
        except KeyboardInterrupt:
            self.__market_th.join()

    def __connect(self):
        """
        Connects to the Polymarket API.
        """
        self.client = ClobClient(self._rest_host, key=self._api_key, chain_id=self._chain_id)
        self.creds = self.client.create_or_derive_api_creds()
        self.client.set_api_creds(self.creds)

    async def ping(self, ws):
        """
        Sends a ping message to the WebSocket every 5 seconds.

        Args:
            ws (websockets.WebSocketClientProtocol): The WebSocket connection.
        """
        try:
            while True:
                await ws.send("PING")
                await asyncio.sleep(5)
        except Exception as e:
            logging.error(f"Error in ping thread: {e}")
            raise e

    async def __stream_market_on_open(self, ws):
        """
        Sends the market & user subscription messages when the WebSocket connection is opened.

        Args:
            ws (websockets.WebSocketClientProtocol): The WebSocket connection.
        """
        # send market subscription message to receive order book data
        await ws.send(json.dumps(self.market_subscription_message))
        # send user subscription message to receive user data
        await ws.send(json.dumps(self.user_subscription_message))
        self.ping_task = asyncio.create_task(self.ping(ws)) 

    async def __stream_market_on_message(self, message):
        """
        Processes messages received from the market stream.

        Args:
            message: The message received from the WebSocket.
        """
        try:
            if (isinstance(message, list) and len(message) == 0) or (isinstance(message, str) and message == "PONG"):
                return
            resp_l = json.loads(message)
            for resp in resp_l:
                if isinstance(resp, dict) and resp["event_type"] in ["book", "price_change", "tick"]:
                    # process message in order book
                    asset_id = resp["asset_id"]
                    self.order_books[asset_id].process_message(resp)
                    # logging.debug(self.order_books[asset_id].to_json(indent=4))
                    # callbacks
                    await self.callback_mgr.trigger_callbacks("market_ws_msg", resp)
        except Exception as e:
            tb = traceback.extract_tb(e.__traceback__) 
            filename, line_number, function_name, text = tb[-1] # Extract the last frame (where the error occurred).
            logging.error(f"Error in stream market on message: {e} {filename} {line_number} {function_name} {text}")
            
    async def __stream_market_on_error(self, ws, error):
        """
        Handles errors received from the market stream.

        Args:
            ws: The WebSocket connection.
            error: The error received.
        """
        logging.error("Error was sent from the server")

    async def __stream_market_on_close(self, ws, close_status_code, close_msg):
        """
        Handles WebSocket closure and attempts to reconnect.

        Args:
            ws: The WebSocket connection.
            close_status_code: The close status code.
            close_msg: The close message.
        """
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
        """
        Establishes and maintains the WebSocket connection to the Polymarket market stream.
        """
        try:
            self.market_subscription_message = {
                "auth": None,
                "type": "market",
                "assets_ids": self.subscribed_markets
            }
            self.user_subscription_message = {
                "auth": {
                    "apiKey": self.creds.api_key,
                    "secret": self.creds.api_secret,
                    "passphrase": self.creds.api_passphrase
                },
                "type": "user",
            }
            async with websockets.connect(f"{self._stream_host}/ws/market") as ws:
                self.ws = ws
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
        """
        Begins the market stream by connecting and streaming market data.
        """
        self.__connect()
        await self.__stream_market()

    async def endStream(self):
        """
        Ends the market stream by cancelling the ping task and closing the WebSocket connection.
        """
        if hasattr(self, 'ping_task') and self.ping_task:
            self.ping_task.cancel()
            try:
                await self.ping_task
            except asyncio.CancelledError:
                logging.info("Ping task cancelled")
        if hasattr(self, 'ws') and self.ws:
            await self.ws.close()
            logging.info("Websocket closed by endStream")
            self.ws = None

    def _download_markets(self, obj_vector, evt: Event):
        """
        Downloads market data from Polymarket's API and stores it in a file.

        Args:
            obj_vector (List[dict]): A list to store the downloaded market data.
            evt (Event): An event object to signal the completion of the download.
        """
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


    def getMarkets(self, download: bool) -> Union[List[dict], Tuple[Event, List[dict]]]:
        """
        Retrieves market data, either from cache or by downloading it.

        Args:
            download (bool): If True, forces a download of market data.

        Returns:
            Union[List[dict], Tuple[Event, List[dict]]]: Either the market data or an event and market data if a download is initiated.
        """
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
