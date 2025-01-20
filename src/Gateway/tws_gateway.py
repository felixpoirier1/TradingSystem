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
import logging


class TWSGateway(EWrapper, EClient, Gateway): 
    NAME = "TWSGateway"
    dotenv.load_dotenv(".config/.env")
    _ACCOUNT_NAME = os.environ["TWS_ACCOUNT_NAME"]
    def __init__(self): 
        EClient.__init__(self, self)
        self.data = {}
        self.pos_df = pd.DataFrame(columns = ["Account","Symbol","SecType",
                                               "Currency","Position","Avg cost"])
        
        self.summary_df = pd.DataFrame(columns = ["ReqId","Account","Value","Currency"])
        self.books = {}
        self.books_locks = {}
        self.historical_data = {}
        
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

    def accountSummary(self, reqId, account, tag, value, currency):
         super().accountSummary(reqId, account, tag, value, currency)
         self.summary_df.loc[tag] = [reqId, account, value, currency]

    def accountSummaryEnd(self, reqId:int):
        logging.info(self.summary_df)

    def historicalData(self, reqId:int, bar):
        if reqId not in self.historical_data:
            self.historical_data[reqId] = pd.DataFrame(columns=['open', 'high', 'low', 'close'])
        self.historical_data[reqId].loc[bar.date] = [bar.open, bar.high, bar.low, bar.close]

    def historicalDataEnd(self, reqId: int, start: str, end: str):
       super().historicalDataEnd(reqId, start, end)
       logging.info(f"Data downloaded for {reqId}\n {self.historical_data[reqId].head()}")

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
    
    def establish_connection(self):
        self.connect(host='127.0.0.1', port=7496, clientId=23)

    def begin(self):
        """Gateway is a websocket, hence it requires it's own thread"""
        self.run()

    def beginStream(self):
        self.establish_connection()
        self.begin()

    def endStream(self):
        pass

if __name__ == "__main__":
    app = TWSGateway()
    app.reqMktDepth