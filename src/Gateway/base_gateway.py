from abc import ABC
from utils import init_logging
import logging

class Gateway(ABC):
    def __init__(self):
        raise NotImplementedError()
    
    @staticmethod
    def set_logging(template, **general_params):
        init_logging(template, **general_params)
        logging.info("Logging started")
        
    def beginStream(self):
        raise NotImplementedError()
    
    def endStream(self):
        raise NotImplementedError()