from abc import ABC, abstractmethod
from utils import init_logging
import logging

class OrderTypeNotSupportedError(Exception):
    def __init__(self, gateway, order):
        self.gateway = gateway
        self.order = order
        
    def __repr__(self):
        return f'Order type "{self.order.NAME}" is not supported on the "{self.gateway.NAME}" platform'

class Gateway(ABC):
    NAME = "BaseGateway"
    _DB_PATH = "data/data.db"
    def __init__(self):
        raise NotImplementedError()
    
    @staticmethod
    def set_logging(template, **general_params):
        init_logging(template, **general_params)
        logging.info("Logging started")

    @abstractmethod
    def beginStream(self):
        raise NotImplementedError()
    
    @abstractmethod
    def endStream(self):
        raise NotImplementedError()
    


    