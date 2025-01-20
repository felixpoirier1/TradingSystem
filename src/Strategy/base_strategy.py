from Gateway import Gateway
from threading import Event
from Client import BaseClient
import yaml
import datetime as dt
import sqlite3

class BaseStrategy(BaseClient):
    NAME = "Base Strategy"
        
    def handle_training(self):
        strategy_params = yaml.safe_load(open(".config/client_params.yaml", "r"))
        if self.NAME not in strategy_params:
            strategy_params[self.NAME] = {}
        
        if strategy_params[self.NAME].get("last_updated") is not None:
            self.last_updated = dt.datetime.strptime(strategy_params[self.NAME]["last_updated"], "%Y-%m-%d %H:%M:%S")
        else:
            self.last_updated = None

        strategy_params[self.NAME]["last_updated"] = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        yaml.safe_dump(strategy_params, open(".config/client_params.yaml", "w"))

    def _instantiate_sqlite_connection(self):
        self.conn = sqlite3.connect(self._app._DB_PATH)


