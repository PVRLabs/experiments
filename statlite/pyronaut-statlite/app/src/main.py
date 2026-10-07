from logback.config import dictConfig

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "colored": {
            "format": "%cyan(%d{HH:mm:ss.SSS}) %highlight(%-5level) %magenta(%logger{36}): %msg"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "colored",
            "stream": "ext://sys.stdout"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    }
}

dictConfig(LOGGING)
