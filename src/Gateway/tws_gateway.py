import dotenv
import os

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.utils import iswrapper

import pandas as pd
import time
from threading import Lock

from .base_gateway import Gateway
from trading.order_types import Side


class TWSGateway(EWrapper, EClient): 
    NAME = "TWSGateway"
    dotenv.load_dotenv(".config/.env")
    _ACCOUNT_NAME = os.environ["TWS_ACCOUNT_NAME"]
    def __init__(self): 
        EClient.__init__(self, self)
        self.data = {}
        self.pos_df = pd.DataFrame(columns = ["Account","Symbol","SecType",
                                               "Currency","Position","Avg cost"])
        
        self.summary_df = pd.DataFrame(columns = ["ReqId","Account","Tag","Value","Currency"])
        self.books = {}
        self.books_locks = {}
        
    @iswrapper
    def nextValidId(self, orderId):
        super().nextValidId(orderId)
        self.nextValidOrderId = orderId
        return self.nextValidOrderId
    
    def position(self, account, contract, position, avgCost):
            super().position(account, contract, position, avgCost)
            dictionary = {"Account": account, "Symbol": contract.symbol, "SecType": contract.secType, 
                "Currency": contract.currency, "Position": position, "Avg cost": avgCost}
            print(dictionary)          

    def pnl(self, reqId, dailyPnL, unrealizedPnL, realizedPnL):
        super().pnl(reqId, dailyPnL, unrealizedPnL, realizedPnL)
        self._pnl = {"ReqId":reqId, "DailyPnL": dailyPnL, "UnrealizedPnL": unrealizedPnL, "RealizedPnL": realizedPnL, "Timestamp": time.time()}
        return self._pnl

    def accountSummary(self, account, tag, value, currency, *, reqId):
        super().accountSummary(reqId, account, tag, value, currency)
        self._account_summary = {"ReqId":reqId, "Account": account, "Tag": tag, "Value": value, "Currency": currency, "Timestamp": time.time()}
        print(self._account_summary)
        return self._account_summary
    
    def reqMktDepth(self, *args, **kwargs) -> tuple[Lock, Lock]:
        """Will apply original reqMktDepth, but will return thread locks for bid and ask books
        """
        super().reqMktDepth(*args, **kwargs)
        if args:
            ticker_id = str(args[0])
        elif "reqId" in kwargs:
            ticker_id = str(kwargs["reqId"])
        else:
            raise Exception
        if ticker_id not in self.books:
            self.books[ticker_id] = {
                "bids":pd.DataFrame(columns=["timestamp", "price", "size", "vwap"]),
                "asks":pd.DataFrame(columns=["timestamp", "price", "size", "vwap"])
                }
            self.books_locks[ticker_id] = {}
            self.books_locks[ticker_id] = {
                "bids": Lock(),
                "asks": Lock()
            }
            bids_lock = self.books_locks[ticker_id]["bids"]
            asks_lock = self.books_locks[ticker_id]["asks"]

        return bids_lock, asks_lock
    
    def updateMktDepth(self, reqId, position, operation, side, price, size):
        super().updateMktDepth(reqId, position, operation, side, price, size)
        ticker_id = str(reqId)    
        side_id = "bids" if side == Side.BID.value else "asks"

        with self.books_locks[ticker_id][side_id]:
            if operation == 2:
                self.books[ticker_id][side_id].loc[position] = [time.time(), None, None, None]
            else:
                self.books[ticker_id][side_id].loc[position] = [time.time(), price, int(size), None]
                vwap = (self.books[ticker_id][side_id].iloc[:position+1]["price"] * \
                         self.books[ticker_id][side_id].iloc[:position+1]["size"]).sum() / \
                         self.books[ticker_id][side_id].iloc[:position+1]["size"].sum()
                self.books[ticker_id][side_id].loc[position, "vwap"] = vwap
        
    def updateMktDepthL2(self, reqId, position, operation, side, price, size):
        super().updateMktDepthL2(reqId, position, operation, side, price, size)
        ticker_id = str(reqId)    
        side_id = "bids" if side == Side.BID.value else "asks"

        with self.books_locks[ticker_id][side_id]:
            if operation == 2:
                self.books[ticker_id][side_id].loc[position] = [time.time(), None, None, None]
            else:
                self.books[ticker_id][side_id].loc[position] = [time.time(), price, int(size), None]
                vwap = (self.books[ticker_id][side_id].iloc[:position+1]["price"] * \
                         self.books[ticker_id][side_id].iloc[:position+1]["size"]).sum() / \
                         self.books[ticker_id][side_id].iloc[:position+1]["size"].sum()
                self.books[ticker_id][side_id].loc[position, "vwap"] = vwap
        
    def begin(self):
        """Gateway is a websocket, hence it requires it's own thread"""
        self.run()

    def beginStream(self):
        pass
    def endStream(self):
        pass

if __name__ == "__main__":
    app = TWSGateway()