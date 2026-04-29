import logging


def configure_logger(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger("wttj_scraper")
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False
    return logger
