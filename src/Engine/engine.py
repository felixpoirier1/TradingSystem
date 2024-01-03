from Gateway import Gateway
from Strategy import BaseStrategy
from Strategy.pairs_trading_strategy import *
import time
from threading import Thread
import yaml
import colorama
import sys
import argparse
import logging

from utils import ARGUMENT_TEMPLATES, init_logging


class Engine:
    NAME = "ENGINE"
    _STRATEGY_PARAMS_PATH = ".config/strategy_params.yaml"
    _LOGGING_PARAMS_PATH = ".config/logging_config.yaml"
    
    def __init__(self, app: Gateway):
        self._parse_arguments()
        init_logging(
            self.template,
            **self._general_params
            )
        logging.debug("All arguments parsed")

        self.app = app

        logging.debug("Initializing streaming thread")
        self.stream_thread = Thread(target=self.__init__stream, name="StreamThread", args=(self.app, *[]))
        logging.debug("Streaming thread has been initialized")

        logging.debug(f"Strategy params loaded from {self._STRATEGY_PARAMS_PATH}")
        self._strategy_params = yaml.safe_load(open(self._STRATEGY_PARAMS_PATH, "r"))

        self._setup_db()
    def _parse_arguments(self):
        self.parser = argparse.ArgumentParser(description='Process command line inputs into a dictionary.')
        for arg_template in ARGUMENT_TEMPLATES:
            self.parser.add_argument(*arg_template.name_or_flags.split(), \
                                     **{k: v for k, v in arg_template._asdict().items() if v is not None and k != "name_or_flags"})
        
        self._general_params = vars(self.parser.parse_args())
        self._general_params["verbose"] = True if self._general_params["verbose"] == "true" else False

        self.template=yaml.safe_load(open(self._LOGGING_PARAMS_PATH, "r"))

    def _setup_db(self):
        dirname = os.path.dirname(self.app._DB_PATH)
        if not os.path.exists(dirname): os.mkdir(dirname)
        if not os.path.exists(self.app._DB_PATH):
            with open(self.app._DB_PATH, "w"):
                pass
            
    def launch(self):
        logging.debug("Launching streaming thread")
        self._launch_stream()
        logging.debug("Launching strategy threads")
        self._launch_strategies()
        logging.debug("Launching CLI interface")
        self.run()

    def run(self):
        while True:
            buff = sys.stdin.read(1)
            if buff == "q":
                print("Quitting...")
                self.close()
                break
            elif buff == "a":
                print(self.app.get_account().status)
            time.sleep(1)

    def close(self):
        self._close_strategies()
        self._close_stream()

        exit(0)
    
    @staticmethod
    def __init__stream(app):
        app.beginStream()

    def _launch_stream(self):
        self.stream_thread.start()
        time.sleep(2)
    
    def _close_stream(self):
        self.app.endStream()
        self.stream_thread.join()
        print(colorama.Fore.BLUE, "Stream thread joined", colorama.Style.RESET_ALL)
        
    def _launch_strategies(self):
        self.strategy_threads = []
        self.strategy_objs = []
        for strategy in BaseStrategy.__subclasses__():
            if strategy.NAME in self._strategy_params:
                logging.debug(f"Launching {strategy.NAME}")
                strategy_obj = strategy(self.app, **{**self._strategy_params[strategy.NAME], "template": self.template, **self._general_params})
                self.strategy_objs.append(strategy_obj)
                strategy_thread = Thread(target=strategy_obj.begin, name=strategy.NAME)
                logging.debug(f"Attached {strategy.NAME} object to thread named {strategy_thread.name}")
                strategy_thread.start()
                logging.debug(f"{strategy.NAME} thread started")
                self.strategy_threads.append(strategy_thread)
        
    def _close_strategies(self):
        for strategy_obj, strategy_thread in zip(self.strategy_objs, self.strategy_threads):
            logging.debug(f"Ending {strategy_obj.NAME}")
            strategy_obj.end()
            logging.debug(f"Joining {strategy_thread.name} thread")
            strategy_thread.join()
            logging.debug(f"Joined {strategy_thread.name} thread")