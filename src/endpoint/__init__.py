import logging
import logging.config
import os

config = {
    "version": 1,
    "disable_existing_loggers": False,  # allows other loggers (e.g. library loggers) to work
    "formatters": {
        "standard": {
            "format": "[%(levelname)s] %(name)s %(filename)s:%(lineno)d %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "loggers": {
        "entrypoint": {
            "handlers": ["console"],
            "level": os.environ.get("ENDPOINT_LOG_LEVEL", "INFO").upper(),
            "propagate": False,
        },
        "": {
            "handlers": ["console"],
            "level": "WARNING",
        },
    },
}
logging.config.dictConfig(config)

logger = logging.getLogger("entrypoint")
