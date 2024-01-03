from ibapi.contract import Contract

class Stock(Contract):
    def __init__(self, symbol, exchange = None, currency = "USD"):
        super().__init__(self)
        self.symbol = symbol
        self.currency = currency
        self.exchange = exchange
        self.secType = "STK"