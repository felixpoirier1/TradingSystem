from TradingApp import TradingApp
from threading import Event
import yaml
import datetime as dt
import sqlite3

class BaseStrategy(object):
    NAME = "Base Strategy"


    def __init__(self, app: TradingApp):
        self._app: TradingApp = app
        self._eflag: Event = Event()
    
    def handle_training(self):
        # write in yaml file "strategy params last updated at: {time}"
        strategy_params = yaml.safe_load(open(".config/strategy_params.yaml", "r"))
        if self.NAME not in strategy_params:
            strategy_params[self.NAME] = {}
        
        if strategy_params[self.NAME].get("last_updated") is not None:
            self.last_updated = dt.datetime.strptime(strategy_params[self.NAME]["last_updated"], "%Y-%m-%d %H:%M:%S")
        else:
            self.last_updated = None

        strategy_params[self.NAME]["last_updated"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        yaml.safe_dump(strategy_params, open(".config/strategy_params.yaml", "w"))

    def _instantiate_sqlite_connection(self):
        self.conn = sqlite3.connect(self._app._DB_PATH)
        
    def begin(self):
        raise NotImplementedError(f"Strategy.begin() not implemented for {self.NAME}")

    def end(self):
        raise NotImplementedError(f"Strategy.end() not implemented for {self.NAME}")