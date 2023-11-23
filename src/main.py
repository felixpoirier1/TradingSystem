from TradingApp import TradingApp
from Strategy import BaseStrategy
from Strategy.pairs_trading_strategy import *
import datetime as dt
import time
from threading import Thread, Lock, Event
import yaml
import colorama
import sys
import os

def main():
    app = TradingApp()
    watchlist = ["AAPL", "TSLA", "MSFT"]
    app.watchlist = watchlist
    stream_thread = Thread(target=stream, args=(app,))
    stream_thread.start()
    time.sleep(2)
    
    strategy_threads = []
    strategy_params = yaml.safe_load(open(".config/strategy_params.yaml", "r"))
    strategy_objs = []
    for strategy in BaseStrategy.__subclasses__():
        if strategy.NAME in strategy_params:
            strategy_obj = strategy(app, **strategy_params[strategy.NAME])
            strategy_objs.append(strategy_obj)
            print(colorama.Fore.BLUE, f"Starting {strategy.NAME} thread", colorama.Style.RESET_ALL)
            strategy_thread = Thread(target=strategy_obj.begin)
            strategy_thread.start()
            strategy_threads.append(strategy_thread)

    while True:
        buff = sys.stdin.read(1)
        if buff == "q":
            print("Quitting...")
            break
        elif buff == "a":
            print(app.get_account().status)
        time.sleep(1)

    for strategy_obj, strategy_thread in zip(strategy_objs, strategy_threads):
        strategy_obj.end()
        strategy_thread.join()
        print(colorama.Fore.BLUE, f"{strategy_obj.NAME} thread joined", colorama.Style.RESET_ALL)

    app.endStream()
    
    stream_thread.join()
    print(colorama.Fore.BLUE, "Stream thread joined", colorama.Style.RESET_ALL)
    exit(0)

def stream(app: TradingApp):
    app.beginStream()

if __name__ == "__main__":
    main()
    