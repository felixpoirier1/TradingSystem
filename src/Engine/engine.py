from Gateway import Gateway
from Client import *
from Strategy import *
import time
from threading import Thread
import yaml
import colorama
import sys
import argparse
import logging
import os

from utils import ARGUMENT_TEMPLATES, init_logging, get_leaf_classes


class Engine:
    NAME = "ENGINE"
    _CLIENT_PARAMS_PATH = ".config/client_params.yaml"
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
        self.stream_thread = Thread(target=self.__init__stream, name="StreamThread", daemon=True, args=(self.app, *[]))
        logging.debug("Streaming thread has been initialized")

        logging.debug(f"Client params loaded from {self._CLIENT_PARAMS_PATH}")
        self._client_params = yaml.safe_load(open(self._CLIENT_PARAMS_PATH, "r"))

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
        logging.debug("Launching client threads")
        self._launch_clients()
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
        self._close_clients()
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
        
    def _launch_clients(self):
        self.client_threads = []
        self.client_objs = []
        for client in get_leaf_classes(BaseClient):
            if client.NAME in self._client_params:
                logging.debug(f"Launching {client.NAME}")
                client_obj = client(self.app, **{**self._client_params[client.NAME], "template": self.template, **self._general_params})
                self.client_objs.append(client_obj)
                client_thread = Thread(target=client_obj.begin, name=client.NAME)
                logging.debug(f"Attached {client.NAME} object to thread named {client_thread.name}")
                client_thread.start()
                logging.debug(f"{client.NAME} thread started")
                self.client_threads.append(client_thread)
        
    def _close_clients(self):
        for client_obj, client_thread in zip(self.client_objs, self.client_threads):
            logging.debug(f"Ending {client_obj.NAME}")
            client_obj.end()
            logging.debug(f"Joining {client_thread.name} thread")
            client_thread.join()
            logging.debug(f"Joined {client_thread.name} thread")