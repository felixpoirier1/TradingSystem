import dotenv
import os
from .base_gateway import Gateway
from alpaca_trade_api import REST, Stream
from alpaca_trade_api.common import URL
from alpaca_trade_api.entity import Quote
import requests
from enum import Enum
import datetime as dt
from pandas import DataFrame

class Product(Enum):
    STOCK = "stocks"

class AlpacaGateway(Gateway, REST, Stream):
    dotenv.load_dotenv(".config/.env")
    _API_KEY = os.environ["API_KEY"]
    _API_SECRET_KEY = os.environ["API_SECRET_KEY"]
    _base_url = 'https://paper-api.alpaca.markets'
    _data_base_url = 'https://data.alpaca.markets'
    _DB_PATH = "data/data.db"
    _header = {"accept": "application/json", "APCA-API-KEY-ID": _API_KEY, "APCA-API-SECRET-KEY": _API_SECRET_KEY}

    def __init__(self):
        REST.__init__(self, self._API_KEY, self._API_SECRET_KEY, URL(self._base_url), "v2")
        Stream.__init__(self, self._API_KEY, self._API_SECRET_KEY, URL(self._base_url))
        self.session = requests.Session()

        self.watchlist = []
        self.latest_quotes = {}

    ## Streaming methods ##
    def beginStream(self):
        Stream.subscribe_quotes(self, self.quote_callback, *tuple(self.watchlist))
        Stream.subscribe_trade_updates(self, self._on_trade_update)
        Stream.run(self)
    
    def endStream(self):
        Stream.unsubscribe_trades(self)
        Stream.unsubscribe_quotes(self)
        Stream.stop(self)

    async def _on_trade_update(self, trade):
        print(trade)
    
    async def quote_callback(self, quote: Quote):
        self.latest_quotes[quote.symbol] = quote

    ## General methods ##
    @staticmethod
    def _fmt_date(date: dt.datetime) -> str:
        if date is None:
            return None
        return date.strftime("%Y-%m-%dT%H:%M:%SZ")