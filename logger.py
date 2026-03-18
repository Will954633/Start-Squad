import logging
import sys
from config import Config


def setup_logger(name: str = "start_squad") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, Config.LOG_LEVEL, logging.INFO))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        if Config.is_production():
            formatter = logging.Formatter(
                '{"time":"%(asctime)s","level":"%(levelname)s",'
                '"module":"%(module)s","message":"%(message)s"}'
            )
        else:
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
            )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger


log = setup_logger()
