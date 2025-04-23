import os
import sys
import time
import click
from datetime import datetime
from pathlib import Path
from logging import Handler, FileHandler, StreamHandler, Formatter, getLogger, INFO, ERROR, WARNING, DEBUG
from logging.handlers import RotatingFileHandler
import json


class BaseLogger:
    """ Base logger class providing basic logging functionality. """
    def __init__(self, logger_name: str, log_mode: str = "console") -> None:
        self.logger_name = logger_name
        self.log_mode = log_mode
        self.level_color = {}

        # Initialize logger
        self.logger = getLogger(self.logger_name)
        self._configure_logger()

    def _configure_logger(self):
        """ Configure the logger to either log to the console or file. """
        # Set log level
        self.logger.setLevel(INFO)

        # Console logging
        if self.log_mode == "console":
            console_handler = StreamHandler(sys.stdout)
            console_handler.setFormatter(self._get_log_formatter())
            self.logger.addHandler(console_handler)

        # File logging
        elif self.log_mode == "file":
            if not self.log_file:
                raise ValueError("log_file must be provided for file logging.")
            file_handler = RotatingFileHandler(self.log_file, maxBytes=1024 * 1024 * 5, backupCount=5)  # 5 MB per log file
            file_handler.setFormatter(self._get_log_formatter())
            self.logger.addHandler(file_handler)

    def _get_log_formatter(self):
        """ Returns a log formatter for consistent formatting. """
        return Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    def log(self, content: str, level: str) -> None:
        """ Log a message with the given level. """
        if level == "execute":
            self.logger.info(content)
        elif level == "suspend":
            self.logger.warning(content)
        elif level == "done":
            self.logger.debug(content)
        elif level == "error":
            self.logger.error(content)
        else:
            self.logger.debug(content)

    def load_log_file(self):
        """ Load the log file where logs will be stored. This method should be overridden. """
        raise NotImplementedError("Subclasses must implement this method.")


class SchedulerLogger(BaseLogger):
    """ Scheduler-specific logger that logs messages with color. """
    def __init__(self, logger_name: str, log_mode: str = "console") -> None:
        super().__init__(logger_name, log_mode)
        self.level_color = {
            "execute": "green",
            "suspend": "yellow",
            "info": "white",
            "done": "blue"
        }

    def load_log_file(self):
        """ Load the scheduler log file. """
        date_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_dir = os.path.join(os.getcwd(), "logs", "scheduler")
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_file = os.path.join(log_dir, f"{date_time}.log")
        return log_file


class AgentLogger(BaseLogger):
    """ Agent-specific logger with color coding for different levels. """
    def __init__(self, logger_name: str, log_mode: str = "console") -> None:
        super().__init__(logger_name, log_mode)
        self.level_color = {
            "info": "white",
            "executing": "green",
            "suspending": "yellow",
            "done": "blue"
        }

    def load_log_file(self):
        """ Load the agent-specific log file. """
        date_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_dir = os.path.join(os.getcwd(), "logs", "agents", self.logger_name)
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_file = os.path.join(log_dir, f"{date_time}.log")
        return log_file


class LLMKernelLogger(BaseLogger):
    """ Logger for LLM Kernel with specific color-coded logs. """
    def __init__(self, logger_name: str, log_mode: str = "console") -> None:
        super().__init__(logger_name, log_mode)
        self.level_color = {
            "info": "white",
            "executing": "green",
            "suspending": "yellow",
            "done": "blue"
        }

    def log_to_console(self, content: str, level: str):
        """ Log to console with emoji and colors. """
        click.secho(f"[\U0001F916 {self.logger_name}] " + content, fg=self.level_color.get(level, "white"), bold=True)

    def load_log_file(self):
        """ Load the LLM kernel-specific log file. """
        date_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_dir = os.path.join(os.getcwd(), "logs", "llm_kernel", self.logger_name)
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_file = os.path.join(log_dir, f"{date_time}.log")
        return log_file


class SDKLogger(BaseLogger):
    """ SDK Logger for logging SDK-related information. """
    def __init__(self, logger_name: str, log_mode: str = "console") -> None:
        super().__init__(logger_name, log_mode)
        self.level_color = {
            "info": "white",
            "warn": "yellow",
            "error": "red",
        }

    def load_log_file(self):
        """ Load the SDK-specific log file. """
        date_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        log_dir = os.path.join(os.getcwd(), "logs", "sdk", self.logger_name)
        Path(log_dir).mkdir(parents=True, exist_ok=True)
        log_file = os.path.join(log_dir, f"{date_time}.log")
        return log_file


# Utility function to retrieve logger configuration
def get_logger_config() -> dict:
    """ Load logger configuration from an external JSON or YAML file. """
    config_file = "logger_config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {}


def configure_loggers():
    """ Configure all loggers based on the external configuration. """
    logger_config = get_logger_config()
    for logger_name, config in logger_config.items():
        log_mode = config.get("log_mode", "console")
        logger_type = config.get("logger_type", "BaseLogger")

        if logger_type == "SchedulerLogger":
            logger = SchedulerLogger(logger_name, log_mode)
        elif logger_type == "AgentLogger":
            logger = AgentLogger(logger_name, log_mode)
        elif logger_type == "LLMKernelLogger":
            logger = LLMKernelLogger(logger_name, log_mode)
        elif logger_type == "SDKLogger":
            logger = SDKLogger(logger_name, log_mode)
        else:
            logger = BaseLogger(logger_name, log_mode)
        
        logger.log(f"Logger {logger_name} initialized successfully", "info")


# Main entry point
if __name__ == "__main__":
    # Configure all loggers based on the configuration file
    configure_loggers()
