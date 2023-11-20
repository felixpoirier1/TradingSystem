from typing import Any
from .base_strategy import BaseStrategy
from threading import Lock
import time

class PairsTradingStrategy(BaseStrategy):
    NAME = "Pairs Trading Strategy"

    def __init__(self, app: Any, pairs: list[tuple[str, str]]):
        super().__init__(app)
        self.pairs = pairs
        self.__lock = Lock()

    def begin(self):
        while not self.__lock.locked():
            time.sleep(1)
            pass
    
    def end(self):
        self.__lock.acquire()
