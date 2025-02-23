from Gateway import Gateway
from threading import Event
from typing import List

class BaseClient(object):
    NAME = "Base Strategy"

    def __init__(self, gateways: List[Gateway], **general_params):
        self._gateways: List[Gateway] = gateways
        self._eflag: Event = Event()
        self._general_params = general_params

    def begin(self):
        for gw in self._gateways:
            gw.set_logging(**self._general_params)

    def end(self):
        raise NotImplementedError(f"Strategy.end() not implemented for {self.NAME}")
    
    def __repr__(self):
        return self.NAME


