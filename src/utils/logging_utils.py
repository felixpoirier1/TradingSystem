from threading import current_thread
import logging
from logging.config import dictConfig
import copy
import os


def init_logging(template, level, verbose, **kwargs):
        if "log" not in os.listdir():
             os.mkdir("log")
        temp_template = copy.deepcopy(template)
        # Convert the string representation of the logging level to the corresponding numeric value
        log_level = getattr(logging, level.upper(), logging.INFO)
        if verbose:
            temp_template["handlers"]["default"]["level"] = log_level
        else:
            temp_template["handlers"].pop("default")
            temp_template["loggers"][""]["handlers"].remove("default")

        temp_template["handlers"]["thread_file_handler"]["level"], temp_template["loggers"][""]["level"] = log_level, log_level

        filename = current_thread().name.rstrip("Thread").replace(" ", "_").lower()
        filename_fmt = f'log/{filename}.log'
        temp_template["handlers"]["thread_file_handler"]["filename"] = filename_fmt
        dictConfig(temp_template)
