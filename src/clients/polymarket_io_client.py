from queue import Queue
from threading import Lock, Event
import json
import numba
import asyncio
from datetime import datetime
from enum import Enum
from typing import Tuple, Dict, List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
import logging

from clients.base_client import BaseClient
from gateways import PolymarketGateway
from src.db.models import PriceChange, BookSnapshot, TickSizeChange, SideEnum, SnapshotTypeEnum
from db import DatabaseClient, DATABASE_URL
from utils.conventions import price_adapter, size_adapter

class WSMessageType(Enum):
    BOOK =          "book"
    PRICE_CHANGE =  "price_change"
    TICK =          "tick_size_change"

class PolymarketIOClient(BaseClient):
    """
    Client for interacting with the Polymarket IO websocket.
    Handles order book updates and snapshots, scheduling tasks for data collection.
    """
    NAME = "Polymarket IO Client"
    
    def __init__(self, gateways: List[PolymarketGateway], **kwargs):
        """
        Initializes the PolymarketIOClient.

        Args:
            gateways: A list containing a single PolymarketGateway instance.
            **kwargs: Additional keyword arguments passed to the BaseClient.
        Raises:
            Exception: If the gateways list does not contain a single PolymarketGateway.
        """
        if not isinstance(gateways[0], PolymarketGateway) or len(gateways) != 1:
            raise Exception("Polymarket IO Client only works with PolymarketGateway")
        super().__init__(gateways, **kwargs)
        logging.getLogger('apscheduler').setLevel(logging.WARNING)

        # PolymarketGateway instance
        self._gateway = self._gateways[0]

        self.__db_client = DatabaseClient(database_url = DATABASE_URL)
        # queue tasked with appending newly received messages from the websocket
        self.__msgs_queue = asyncio.Queue()
        # lock dedicated to the queue above
        self.__msgs_queue_lock = Lock()
        
        # scheduler meant to add row batches to the price table of the database
        self.db_scheduler = AsyncIOScheduler()
        self.db_scheduler.add_job(
            self.batch_write,
            IntervalTrigger(seconds = 10),

        )

        # scheduler meant to add single snapshots to the snapshot table of the database
        # self.snapshot_scheduler = BackgroundScheduler()
        # self.snapshot_scheduler.add_job(
        #     self.update_snapshots,
        #     IntervalTrigger(minutes = 30)
        # )

        # register callbacks connectivity to PolymarketGateway's CallbackManager
        self._register_callbacks()

    async def begin(self):
        """Starts the client and its schedulers."""
        await super().begin()
        logging.info("Launching schedulers")
        self.db_scheduler.start() # Start the scheduler here.


    async def batch_write(self):
        """Processes and clears the message queue."""
        if self.__msgs_queue.qsize() == 0:
            return
        msgs = []
        while self.__msgs_queue.qsize() > 0:
            msg = await self.__msgs_queue.get()
            msgs.extend(msg)

        with self.__db_client.get_session() as session:
            for (evt, msg_kwargs) in msgs:
                if evt is WSMessageType.PRICE_CHANGE:
                    # logging.debug(f"Adding trade to the db with key <({},{})>")
                    statement = insert(PriceChange).values([msg_kwargs])#.on_conflict_do_nothing()
                    session.execute(statement)
                elif evt is WSMessageType.BOOK:
                    statement = insert(BookSnapshot).values([msg_kwargs]).on_conflict_do_nothing()
                    session.execute(statement)
                elif evt is WSMessageType.TICK:
                    statement = insert(TickSizeChange).values([msg_kwargs])#.on_conflict_do_nothing()
                    session.execute(statement)

    def update_snapshots(self):
        """Updates market snapshots based on order book data."""
        with self.__msgs_queue_lock:
            msgs_to_append = {}
            for market_id, book in self._gateway.order_books.items():
                pass
    
    @staticmethod
    def process_message(msg: Dict) -> List[Tuple[WSMessageType, Dict]]:
        """
        Processes a websocket message and returns a list of events.

        Args:
            msg: The websocket message as a dictionary.

        Returns:
            A list of tuples, where each tuple contains the event type and event data.

        Raises:
            Exception: If the message event type is not recognized.
        """

        evt_type = WSMessageType(msg['event_type'])
        if evt_type is WSMessageType.BOOK:
            time = datetime.fromtimestamp(float(msg['timestamp'])/1000)
            market_id = msg['market']
            snapshot_type = SnapshotTypeEnum.INIT
            book = {
                "bids": [(price_adapter(pl['price']), size_adapter(pl['size'])) for pl in msg['bids']],
                "asks": [(price_adapter(pl['price']), size_adapter(pl['size'])) for pl in msg['asks']]
            }
            return [
                (
                    evt_type, 
                    {
                        "time": time, 
                        "market_id": market_id, 
                        "snapshot_type": snapshot_type, 
                        "book": book
                    }
                )
            ]
        
        elif evt_type is WSMessageType.PRICE_CHANGE:
            time = datetime.fromtimestamp(float(msg['timestamp'])/1000)
            market_id = msg["market"]
            changes = []
            for change in msg['changes']:
                changes.append(
                    (
                        evt_type,
                        {
                            "time": time,
                            "market_id": market_id,
                            "price": price_adapter(change['price']),
                            "size": size_adapter(change["size"]),
                            "side": SideEnum.BID if change['side'] == "BUY" else SideEnum.ASK
                        }
                    )
                )
            return changes
        
        elif evt_type is WSMessageType.TICK:
            time = datetime.fromtimestamp(float(msg['timestamp'])/1000)
            market_id = msg["market"]
            tick_size = price_adapter(msg["new_tick_size"])
            return [
                (
                    evt_type,
                    {
                        "time": time,
                        "market_id": market_id,
                        "tick_size": tick_size
                    }
                )
            ]
        
        else:
            raise Exception("Message not recognized as one of ('book', 'price_change', 'tick_size_change')")

    async def __on_ws_book_msg_callback(self, msg: Dict) -> None:
        """Callback function for handling websocket book messages."""
        await self.__msgs_queue.put(PolymarketIOClient.process_message(msg))

    def _register_callbacks(self):
        """Registers callbacks for websocket messages."""
        self._gateway.callback_mgr.register_callback_executable("market_ws_msg", self.__on_ws_book_msg_callback)

    async def end(self):
        """Shuts down the schedulers and ends the client."""
        self.db_scheduler.shutdown()
        # self.snapshot_scheduler.shutdown()