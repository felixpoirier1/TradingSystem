from enum import Enum
from ibapi.contract import Contract

class Side(Enum):
    BID = 1
    ASK = 0

class BaseOrder:
    def __init__(
            self,
            contract: Contract,
            side: Side
            ):
        self.contract = contract
        self.side = side

class LimitOrder(BaseOrder):
    def __init__(
            self, 
            contract : Contract,
            side : Side,
            price : float, 
            quantity : int, 
            ):
        super().__init__(contract, side)
        self.price = price
        self.quantity = quantity

    def __repr__(self):
        return f"LimitOrder(ticker = {self.contract}, side = {Side(self.side).name}, price = {round(self.price, 2)}, quantity = {self.quantity})"
    
class MarketOrder(BaseOrder):
    def __init__(
            self, 
            contract : str,
            side : Side,
            quantity : int, 
            ):
        super().__init__(contract, side)
        self.quantity = quantity

    def __repr__(self):
        return f"MarketOrder(ticker = {self.contract}, side = {Side(self.side).name}, quantity = {self.quantity})"
    
if __name__ == "__main__":
    print(MarketOrder("AAPL",Side.BID, 1))