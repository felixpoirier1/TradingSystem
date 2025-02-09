from .base_strategy import BaseStrategy
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from Gateway import PolymarketGateway
from sklearn.linear_model import LinearRegression
from typing import List

class PolymarketMMStrategy(BaseStrategy):
    NAME = "Polymarket Market Maker Strategy"
    cli_cmd = "pmms"
    def __init__(self, gateways: List[PolymarketGateway], **kwargs):
        if not isinstance(gateways[0], PolymarketGateway) or len(gateways) != 1:
            raise Exception("PolymarketMMStrategy only works with PolymarketGateway")
        super().__init__(gateways, **kwargs)

    def begin(self):
        super().begin()
        self._app : PolymarketGateway = self._gateways[0]
        obj = self._app.getMarkets(download=False)
        if isinstance(obj, tuple):
            obj[0].wait()
            markets = obj[1]
        else:
            markets = obj

    def main(self):
        pass
        
