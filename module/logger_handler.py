import logging
import logging.config
import os

from util import json_parser as json_parser
from pathlib import Path


class LoggerHandler:
    @staticmethod
    def init_logger(log_output_path: Path):
        settings_file = os.getenv("LOGGUER_CONFIG_PATH")

        if not settings_file:
            raise ValueError("Missing 'LOGGUER_CONFIG_PATH' environment variable in the .env file.")

        settings_file = Path(settings_file).resolve()

        settings = json_parser.load_json(settings_file)
        settings['handlers']['file']['filename'] = log_output_path
        logging.config.dictConfig(settings)
