from .base_strategy import BaseStrategy
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from Gateway import Gateway
from sklearn.ensemble import RandomForestRegressor
import time
import os
import pandas as pd
import datetime as dt
import numpy as np
import logging


class PairsTradingStrategy(BaseStrategy):
    NAME = "Pairs Trading Strategy"
    table_name = "pairs_trading"
    _MODEL_PATH = ".models/pairs_trading_model.pkl"

    def __init__(self, app: Gateway, pairs: list[list[str, str]], **kwargs):
        super().__init__(app, **kwargs)
        self.pairs = pairs

        # does the model exist?
        if self._model_exists():
            # if yes, load it
            self.model = Pipeline.load(self._MODEL_PATH)
        else:
            # if not, create it
            self.model_template = Pipeline([
                ("StandardScaler", StandardScaler()),
                ("regressor", RandomForestRegressor())
            ])
        self.models = {}
        self.temp_table = pd.DataFrame()

    def begin(self):
        super().begin()
        self._instantiate_sqlite_connection()
        #self._handle_training()
        while not self._eflag.is_set():
            pass
        # on exit
        if self._eflag.is_set():
            #self._store_features(self.temp_table)
            pass
    
    def end(self):
        self._eflag.set()
    
    def _handle_training(self, hard: bool = False):
        super().handle_training()
        
        self._manage_data()

        if self.last_updated is not None and self.last_updated > pd.Timestamp.now() - pd.Timedelta(days=7) and not hard:
            self.train(hard=True)
        else:
            self.train()
        
        self._store_features(self.temp_table)

    def train(self, hard: bool = False):
        for symbol in self.temp_table["symbol"].unique():
            logging.debug(f"Training model for {symbol}...")
            df = self.temp_table[self.temp_table["symbol"] == symbol].copy()
            df.drop(columns=["symbol"], inplace=True)
            df["timestamp"] = pd.to_datetime(df["timestamp"], format="%Y-%m-%d %H:%M:%S+00:00", utc = True)
            df_resampled = df.set_index('timestamp').resample('T').ffill()

            X = df_resampled.drop(columns=["close", "high", "low"])
            y = df_resampled["close"]

            if symbol not in self.models or hard:
                self.models[symbol] = self.model_template

            self.models[symbol].fit(X, y)
            logging.debug(f"Trained model for {symbol}.")
    
    def predict(self, symbol: str, X: pd.DataFrame):
        return self.models[symbol].predict(X)

    def _get_data(self, subset: list | str = None, start_date: dt.datetime = None, end_date: dt.datetime = None):
        if subset is None:
            subset = [elem for pair in self.pairs for elem in pair]
        
        logging.debug(f"Downloading data for {len(subset)} symbols through Alpaca's API...")
        
        chunk_to_append = self._app.get_bars(subset, "1Min", self._app._fmt_date(start_date), self._app._fmt_date(end_date)).df

        logging.debug(f"Downloaded data for {len(subset)} symbols through Alpaca's API.")
        chunk_to_append.reset_index(inplace=True)
        chunk_to_append.dropna(inplace=True)
        self.temp_table = pd.concat([self.temp_table, chunk_to_append])
    
    def _extract_features(self, start_date: dt.datetime = None, end_date: dt.datetime = None):
        """Returns a dataframe representing the features of the model contained in the database.
        
        Keyword arguments:
        start_date -- start date of the data to extract (default None)
        end_date -- end date of the data to extract (default None)
        Return: pandas.DataFrame
        """
        
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT * FROM {self.table_name}")
        rows = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]
        df = pd.DataFrame(rows, columns=column_names)
        return df
    
    def _store_features(self, df: pd.DataFrame):
        """Stores the features of the model in the database.
        
        Keyword arguments:
        df -- dataframe representing the features of the model
        """
        df.to_sql(self.table_name, self.conn, if_exists="replace", index=False)
        self.conn.commit()
        print("Stored features in database.")

    @staticmethod
    def _worst_last_date(df: pd.DataFrame) -> np.datetime64:
        """Returns the worst last date of the dataframe.
        
        Keyword arguments:
        df -- dataframe to check
        Return: numpy.datetime64
        """
        date = df.groupby("symbol").agg({"timestamp": "max"}).min().values[0]
        if isinstance(date, str):
            return dt.datetime.strptime(date, "%Y-%m-%d %H:%M:%S+00:00")
        return date

    def _manage_data(self):
        if self.temp_table.empty:
            if self._pairs_trading_table_exists():
                self.temp_table = self._extract_features()
                if self.temp_table.empty:
                    self._get_data()
            else:
                self._create_pairs_trading_table()
                self._get_data()


        worst_last_date = self._worst_last_date(self.temp_table)
        if worst_last_date < pd.Timestamp.now() - pd.Timedelta(days=1):
            self._get_data(start_date=worst_last_date)
    

    def _pairs_trading_table_exists(self):
        c = self.conn.cursor()
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='pairs_trading'")
        return bool(c.fetchone())
    
    def _create_pairs_trading_table(self):
        c = self.conn.cursor()
        c.execute("CREATE TABLE pairs_trading (symbol TEXT, timestamp TIMESTAMP, open REAL, high REAL, low REAL, close REAL, volume INTEGER, vwap REAL, trade_count INTEGER)")
        self.conn.commit()

    @classmethod
    def _model_exists(cls):
        return os.path.exists(cls._MODEL_PATH)