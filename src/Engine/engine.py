import asyncio
import yaml
import colorama
import sys
import argparse
import logging
import os
from threading import Thread
from typing import List, Dict

from utils import ARGUMENT_TEMPLATES, init_logging, get_leaf_classes
from Gateway import Gateway
from Client import BaseClient


class Engine:
    NAME = "ENGINE"
    _GATEWAY_PARAMS_PATH = ".config/gateway_params.yaml"
    _CLIENT_PARAMS_PATH = ".config/client_params.yaml"
    _LOGGING_PARAMS_PATH = ".config/logging_config.yaml"

    def __init__(self):
        self._parse_arguments()
        init_logging(self.template, **self._general_params)
        logging.debug("All arguments parsed")

        self._gateway_params: Dict = yaml.safe_load(open(self._GATEWAY_PARAMS_PATH, "r"))

        self.gateways: Dict[str, Gateway] = {}
        for gateway_name, gateway_args in self._gateway_params.items():
            for gw in Gateway.__subclasses__():
                if gw.NAME == gateway_name:
                    self.gateways[gateway_name] = gw(**gateway_args)

        logging.debug(f"Client params loaded from {self._CLIENT_PARAMS_PATH}")
        self._client_params = yaml.safe_load(open(self._CLIENT_PARAMS_PATH, "r"))

        self._setup_db()

    def _parse_arguments(self):
        self.parser = argparse.ArgumentParser(description='Process command line inputs into a dictionary.')
        for arg_template in ARGUMENT_TEMPLATES:
            self.parser.add_argument(*arg_template.name_or_flags.split(),
                                     **{k: v for k, v in arg_template._asdict().items() if v is not None and k != "name_or_flags"})

        self._general_params = vars(self.parser.parse_args())
        self._general_params["verbose"] = True if self._general_params["verbose"] == "true" else False
        self._general_params["interactive"] = True if self._general_params["interactive"] == "true" else False
        self.template = yaml.safe_load(open(self._LOGGING_PARAMS_PATH, "r"))

    def _setup_db(self):
        for gw in self.gateways.values():
            dirname = os.path.dirname(gw._DB_PATH)
            if not os.path.exists(dirname):
                os.mkdir(dirname)
            if not os.path.exists(gw._DB_PATH):
                open(gw._DB_PATH, "x")

    async def launch(self):
        logging.debug("Launching streaming tasks")
        await self._launch_streams()
        logging.debug("Launching client threads")
        self._launch_clients()
        logging.debug("Launching CLI interface")
        logging.debug(f"Running with interactive set to {self._general_params['interactive']}")
        if self._general_params['interactive']:
            logging.debug("launching with interactive mode")
            await self.run()
        else:
            while True:
                await asyncio.sleep(1)

    async def run(self):
        while True:
            buff = sys.stdin.read(1)
            if buff == "q":
                print("Quitting...")
                await self.close()
                break
            await asyncio.sleep(1)

    async def close(self):
        self._close_clients()
        await self._close_streams()
        exit(0)

    async def _launch_streams(self):
        self.stream_tasks = []
        for gw_name, gw_obj in self.gateways.items():
            logging.debug(f"Launching {gw_name} stream")
            task = asyncio.create_task(gw_obj.beginStream())
            self.stream_tasks.append(task)
        await asyncio.sleep(2)

    async def _close_streams(self):
        for gw in self.gateways.values():
            await gw.endStream()
        for task in self.stream_tasks:
            await task
            print(colorama.Fore.BLUE, f"{task} stream task joined", colorama.Style.RESET_ALL)

    def _launch_clients(self):
        self.client_threads = []
        self.client_objs = []
        for client in get_leaf_classes(BaseClient):
            logging.debug(f"Analyzing {client}")
            if self._client_params and client.NAME in self._client_params:
                logging.debug(f"Launching {client.NAME}")
                gateways = [self.gateways[gw_name] for gw_name in self._client_params[client.NAME].pop("gateways")]
                client_obj = client(gateways, **{**self._client_params[client.NAME], "template": self.template, **self._general_params})
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

    def start(self):
        asyncio.run(self.launch())

if __name__ == "__main__":
    engine = Engine()
    engine.start()