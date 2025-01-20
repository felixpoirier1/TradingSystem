from Gateway import Gateway
from threading import Event
import yaml
import datetime as dt

class BaseClient(object):
    NAME = "Base Strategy"

    def __init__(self, app: Gateway, **general_params):
        self._app: Gateway = app
        self._eflag: Event = Event()
        self._general_params = general_params

    def begin(self):
        self._app.set_logging(**self._general_params)

    def end(self):
        raise NotImplementedError(f"Strategy.end() not implemented for {self.NAME}")


