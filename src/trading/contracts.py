from ibapi.contract import Contract
from .conventions import CME_MONTH_CODES

class Stock(Contract):
    def __init__(self, symbol, exchange = None, currency = "USD"):
        super().__init__(self)
        self.symbol = symbol
        self.currency = currency
        self.exchange = exchange
        self.secType = "STK"

class SR3(Contract):
    def __init__(self, expiry_month: int, expiry_year: int):
        super().__init__()
        month_code = CME_MONTH_CODES[expiry_month]
        self.localSymbol = "SR3" + month_code + str(expiry_year % 10)
        self.secType = "FUT"
        self.exchange = "CME"
        self.currency = "USD"