from typing import Dict, List, Union, Callable, Tuple
from abc import ABC, abstractmethod
import json
from enum import Enum
import numpy as np
from utils.conventions import price_adapter, size_adapter

class Action(Enum):
    MODIFY = "modify"
    REINIT = "reinit"
    TICK = "tick"
    END = "end"

class Side(Enum):
    BID = "bid"
    ASK = "ask"

class PriceLevelDoesNotExist(Exception):
    pass

class PredictionMarketOrderBook:
    def __init__(self, asset_id: str, tick_size: float, msg_processor: Callable, bids: Union[np.ndarray, None] = None, asks: Union[np.ndarray, None] = None):
        self.asset_id = asset_id
        self.tick_size = tick_size

        # representation of the order book price levels (in ascending order from 0, to 1000 using tick size as jump)
        if bids is None:
            self.bids: np.ndarray = np.zeros(int(1000 // tick_size + 1), dtype=float)
        else:
            self.bids: np.ndarray = bids
        if asks is None:
            self.asks: np.ndarray = np.zeros(int(1000 // tick_size + 1), dtype=float)
        else:
            self.asks: np.ndarray = asks
        self.msg_processor = msg_processor
        self.update_best_bid_ask()

    def update_best_bid_ask(self):
        """
        Find the best bid and ask prices.
        This is an expensive operation, so we should only do it when necessary.
        """
        non_zero_bids = np.nonzero(self.bids)[0]
        non_zero_asks = np.nonzero(self.asks)[0]
        self.best_bid = self.get_price(np.max(non_zero_bids)) if non_zero_bids.size > 0 else 0
        self.best_ask = self.get_price(np.min(non_zero_asks)) if non_zero_asks.size > 0 else 1000

    def cheap_update_best_bid_ask(self):
        """
        Update the best bid and ask prices without recalculating them.
        """
        while self.bids[self.get_idx(self.best_bid)] == 0:
            self.best_bid -= self.tick_size
        while self.asks[self.get_idx(self.best_ask)] == 0:
            self.best_ask += self.tick_size

    def update_tick_size(self, tick_size: float):
        """
        Updates the tick size and generates new bids and asks with contiguous price levels.
        """
        if tick_size <= 0:
            raise ValueError("Tick size must be positive.")

        if self.tick_size == tick_size:
            return  # No change needed

        new_size = int(1000 / tick_size) + 1  # +1 to include 1000
        new_bids = np.zeros(new_size, dtype=float)
        new_asks = np.zeros(new_size, dtype=float)
        for i in range(len(self.bids)):
            price = i * self.tick_size
            new_bids[self.get_idx(price, tick_size)] = self.bids[i]
            new_asks[self.get_idx(price, tick_size)] = self.asks[i]

        self.bids = new_bids
        self.asks = new_asks

        self.tick_size = tick_size

    def get_idx(self, price: float, tick_size: Union[float, None] = None):
        """
        Get the index of the price in the order book.
        """
        if tick_size is None:
            tick_size = self.tick_size
        return int(price / tick_size)

    def get_price(self, idx: int, tick_size: Union[float, None] = None):
        if tick_size is None:
            tick_size = self.tick_size
        return idx * tick_size
    
    def update_order_book(self, price: float, side: Side, size: Union[float, None] = None, diff: Union[float, None] = None):
        """
        Update the order book with a new price level.
        """
        assert isinstance(price, (int, float)), f"Price must be an int or float, got {type(price)}"
        assert isinstance(side, Side), f"Side must be a Side, got {type(side)}"
        assert isinstance(size, (float, int)) or size is None, f"Size must be a float or int or None, got {type(size)}"
        assert isinstance(diff, (float, int)) or diff is None, f"Diff must be a float or int or None, got {type(diff)}"
        if (diff is not None and size is not None) or (diff is None and size is None):
            raise ValueError("Only one of size or diff can be provided.")
        idx = self.get_idx(price)
        if idx >= len(self.bids) or idx >= len(self.asks):
            raise ValueError(f"Price level {price} is out of bounds for the order book.")
        if side == Side.BID:
            if diff is not None:
                self.bids[idx] += diff
            else:
                self.bids[idx] = size
            qty = self.bids[idx]
            if qty > 0 and price > self.best_bid:
                self.best_bid = price
        elif side == Side.ASK:
            if diff is not None:
                self.asks[idx] += diff
            else:
                self.asks[idx] = size
            qty = self.asks[idx]
            if qty > 0 and price < self.best_ask:
                self.best_ask = price

    def reinit(self, bids: List[Tuple[int, float]], asks: List[Tuple[int, float]]):
        for pl in bids:
            if pl[0] > self.best_bid:
                self.best_bid = pl[0]
            self.bids[self.get_idx(pl[0])] = pl[1]
        for pl in asks:
            if pl[0] < self.best_ask:
                self.best_ask = pl[0]
            self.asks[self.get_idx(pl[0])] = pl[1]
        # self.update_best_bid_ask()

    def process_message(self, message):
        instructions = self.msg_processor(message)
        for action, args in instructions:
            if action == Action.MODIFY:
                self.update_order_book(**args)
            elif action == Action.REINIT:
                self.reinit(**args)
            elif action == Action.TICK:
                self.update_tick_size(**args)

    def get_order_book(self):
        return self.bids.tolist(), self.asks.tolist()

    def to_dict(self) -> Dict:
        return {
            "bids": [(self.get_price(idx), size_adapter(size * 100)) for idx, size in enumerate(self.bids) if size != 0],
            "asks": [(self.get_price(idx), size_adapter(size * 100)) for idx, size in enumerate(self.asks) if size != 0]
        }

    def to_json(self, *args, **kwargs) -> str:
        return json.dumps(self.to_dict(), *args, **kwargs)
    

def polymarket_msg_processor(message) -> List[Tuple[Action, Dict]]:
    if message["event_type"] == "book":
        return Action.REINIT, {"bids": [float(q)*1000 for p,q in message["bids"]], "asks": [float(q)*1000 for p,q in message["asks"]]}
    elif message["event_type"] == "price_change":
        return [(Action.MODIFY, {"price": float(msg["price"]) * 1000, "side": Side.ASK if msg["side"] == "SELL" else Side.BID, "size": float(msg["size"]) * 1000}) for msg in message["changes"]]
    elif message["event_type"] == "tick":
        return Action.TICK, {"tick_size": int(1000*float(message["new_tick_size"]))}
    else:
        return []

if __name__ == "__main__":
    order_book = PredictionMarketOrderBook("BTC", 100)
    order_book.update_tick_size(10)
    print(order_book.get_order_book())

