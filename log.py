"""
===============================================================================
Projekt: Noatime
Dateiname: log.py
Version: 1.0.0
Entwickler: Annatina Christ
Datum: 29.11.2024


Changelog:
- [Datum]: Erste Version.
- [Datum]: Weitere Änderungen/Verbesserungen.

===============================================================================
"""

import logging
from logging.handlers import RotatingFileHandler
import os

class LoggerConfig:
    _configured = False

    def __init__(self, log_file="/home/pi_noatime/python/noatime/logs/app.log", sql_log_file="/home/pi_noatime/python/noatime/logs/sql.log", connection_log_file="/home/pi_noatime/python/noatime/logs/connection.log", 
                 rfid_log_file="/home/pi_noatime/python/noatime/logs/rfid.log", level=None, max_log_size=2*1024*1024, backup_count=5, formatter=None):
        self.log_file = log_file
        self.sql_log_file = sql_log_file
        self.connection_log_file = connection_log_file
        self.rfid_log_file = rfid_log_file
        self.level = level or os.getenv("LOG_LEVEL", "DEBUG").upper()
        self.max_log_size = max_log_size
        self.backup_count = backup_count
        self.formatter = formatter or logging.Formatter(
            fmt="{asctime} - {levelname} - {message}",
            style="{",
            datefmt="%d-%m-%Y %H:%M",
        )

    def configure(self):
        if LoggerConfig._configured:
            return
        self.configure_logger("general_logger", self.log_file)
        self.configure_logger("sql_logger", self.sql_log_file)
        self.configure_logger("connection_logger", self.connection_log_file)
        self.configure_logger("rfid_logger", self.rfid_log_file)
        LoggerConfig._configured = True

    def configure_logger(self, name, log_file):
        logger = logging.getLogger(name)
        logger.setLevel(self.level)
        self._configure_rotating_logger(log_file, logger)
        self._configure_console_logger(logger)
        return logger

    def _configure_rotating_logger(self, log_file, logger=None):
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        if not any(isinstance(h, RotatingFileHandler) and h.baseFilename == log_file for h in logger.handlers):
            rotating_handler = RotatingFileHandler(
                log_file,
                maxBytes=self.max_log_size,
                backupCount=self.backup_count,
                encoding="utf-8",
            )
            rotating_handler.setFormatter(self.formatter)
            logger.addHandler(rotating_handler)

    def _configure_console_logger(self, logger):
        if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.ERROR)
            console_handler.setFormatter(self.formatter)
            logger.addHandler(console_handler)

    def get_logger(self, name):
        return logging.getLogger(name)
