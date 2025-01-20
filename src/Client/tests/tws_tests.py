from ..base_client import BaseClient
from trading import SR3
import datetime
import time
import pandas as pd
from typing import Dict

class TWSTestAccountSummary(BaseClient):
    NAME = "TWS Unit Test"

    def begin(self):
        super().begin()
        self._app.reqAccountSummary(1, "All", "$LEDGER:ALL")
        curr_id, ids = 4000, {}
        for month in [3, 6, 9, 12]:
            for year in [2024,2025,2026]:
                contract = SR3(month, year)
                ids[curr_id] = contract.localSymbol
                queryTime = (datetime.datetime.today() - datetime.timedelta(days=180)).strftime("%Y%m%d-%H:%M:%S")
                self._app.reqHistoricalData(curr_id, contract, queryTime,"1 M", "10 mins", "MIDPOINT", 1, 1, False, [])
                curr_id += 1
        time.sleep(120)
        all_data: Dict[int, pd.DataFrame] = self._app.historical_data
        concat_data = pd.DataFrame(columns=['date', 'symbol', 'open', 'high', 'low', 'close'])
        for reqId, table in all_data.items():
            table["symbol"] = ids[reqId]
            table = table.reset_index(names=['date'])
            concat_data = pd.concat([concat_data, table], ignore_index=True)


        print(concat_data)
        concat_data.to_csv("sr3_bars.csv")

    def end(self):
        self._eflag.set()
