import logging
import sys

from loguru import logger

from src.core.settings import Settings


class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def setup_logging(settings: Settings) -> None:
    logger.remove()

    effective_level = "WARNING" if settings.enduro_attack else settings.log_level

    if settings.log_json:
        logger.add(
            sys.stdout,
            level=effective_level,
            serialize=True,
        )
    else:
        logger.add(
            sys.stdout,
            level=effective_level,
            colorize=True,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
            ),
        )

    intercept_handler = InterceptHandler()
    logging.root.handlers = [intercept_handler]
    logging.root.setLevel(effective_level)

    loggers_to_intercept = (
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
        "sqlalchemy.engine",
    )

    for logger_name in loggers_to_intercept:
        log = logging.getLogger(logger_name)
        log.handlers = [intercept_handler]
        log.propagate = False
