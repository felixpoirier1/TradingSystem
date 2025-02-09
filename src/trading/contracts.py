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

class ZQ(Contract):
    def __init__(self, expiry_month: int, expiry_year: int):
        super().__init__()
        month_code = CME_MONTH_CODES[expiry_month]
        self.localSymbol = "ZQ" + month_code + str(expiry_year % 10)
        self.secType = "FUT"
        self.exchange = "CBOT"
        self.currency = "USD"

class CRA(Contract):
    def __init__(self, expiry_month: int, expiry_year: int):
        super().__init__()
        month_code = CME_MONTH_CODES[expiry_month]
        self.localSymbol = "CRA" + month_code + str(expiry_year % 100)
        self.secType = "FUT"
        self.exchange = "CDE"
        self.currency = "CAD"

class CL(Contract):
    """NYMEX Crude Oil"""
    def __init__(self, expiry_month: int, expiry_year: int):
        super().__init__()
        month_code = CME_MONTH_CODES[expiry_month]
        self.localSymbol = "CL" + month_code + str(expiry_year % 10)
        self.secType = "FUT"
        self.exchange = "NYMEX"
        self.currency = "USD"

