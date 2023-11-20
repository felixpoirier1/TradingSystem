import os
from TradingApp import TradingApp


class BaseStrategy(object):
    NAME = "Base Strategy"

    def __init__(self, app: TradingApp):
        self._app = app

    def begin(self):
        NotImplementedError(f"Strategy.begin() not implemented for {self.NAME}")

    def end(self):
        NotImplementedError(f"Strategy.end() not implemented for {self.NAME}")