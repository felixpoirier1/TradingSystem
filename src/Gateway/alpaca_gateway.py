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
    NAME = "AlpacaGateway"
    _base_url = 'https://paper-api.alpaca.markets'
    _data_base_url = 'https://data.alpaca.markets'

    def __init__(self):
        REST.__init__(self, self._API_KEY, self._API_SECRET_KEY, URL(self._base_url), "v2")

        dotenv.load_dotenv(".config/.env")
        self._API_KEY = os.environ["ALPACA_API_KEY"]
        self._API_SECRET_KEY = os.environ["ALPACA_API_SECRET_KEY"]

        Stream.__init__(self, self._API_KEY, self._API_SECRET_KEY, URL(self._base_url))
        self.session = requests.Session()

        self.watchlist = []
        self.latest_quotes = {}
        self.hist_quotes = {i:DataFrame() for i in self.watchlist}

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
        if quote.symbol not in self.hist_quotes:
            self.hist_quotes[quote.symbol] = DataFrame()
        self.hist_quotes[quote.symbol] = self.hist_quotes[quote.symbol].append(quote._raw)

    ## General methods ##
    @staticmethod
    def _fmt_date(date: dt.datetime) -> str:
        if date is None:
            return None
        return date.strftime("%Y-%m-%dT%H:%M:%SZ")