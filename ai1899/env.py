import os
from typing import Literal


def return_env(default, env_var, type_of_var: Literal[str, bool, int, list]):
    return default if not os.environ.get(env_var) else type_of_var(os.environ.get(env_var))


class Env:
    ST_HOME = return_env(None, "SENTENCE_TRANSFORMERS_HOME", type_of_var=str)
    FLASK_PORT = return_env(5000, "FLASK_PORT", type_of_var=int)
    LM_MODEL = "msmarco-distilbert-base-tas-b"
    QDRANT = return_env("localhost", "QDRANT", str)
    QDRANTPORT = return_env(6333, "QDRANTPORT", str)
    REDDIS_CELERY = return_env("redis://localhost:6379/0", "REDDIS_CELERY", str)
