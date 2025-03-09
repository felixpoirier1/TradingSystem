from .base_strategy import BaseStrategy
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from gateways import KalshiGateway
from sklearn.linear_model import LinearRegression
from typing import List

class KalshiMMStrategy(BaseStrategy):
    NAME = "Kalshi Market Maker Strategy"
    cli_cmd = "kmms"
    def __init__(self, gateways: List[KalshiGateway], **kwargs):
        if not isinstance(gateways[0], KalshiGateway) or len(gateways) != 1:
            raise Exception("PolymarketMMStrategy only works with KalshiGateway")
        super().__init__(gateways, **kwargs)

    async def begin(self):
        await super().begin()
        self._app : KalshiGateway = self._gateways[0]
    #     obj = self._app.getMarkets(download=False)
    #     if isinstance(obj, tuple):
    #         obj[0].wait()
    #         markets = obj[1]
    #     else:
    #         markets = obj
    async def end(self):
        self._eflag.clear()
    # def main(self):
    #     pass
        
