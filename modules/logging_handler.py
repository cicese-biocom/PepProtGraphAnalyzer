import logging
import logging.config
from utils import json_parser as json_parser
from pathlib import Path


class LoggingHandler:
    @staticmethod
    def initialize_logger(logger_settings_path: Path, log_output_path: Path):
        setting_json = Path(logger_settings_path).resolve()
        settings = json_parser.load_json(setting_json)
        settings['handlers']['file']['filename'] = log_output_path
        logging.config.dictConfig(settings)
