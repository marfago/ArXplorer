import json
import os
from pathlib import Path
from typing import Dict, Any

from arxplorer.common.common import load_env

ARXPLORER_NAME: str = "arxplorer"
ARXPLORER_FOLDER: str = f".{ARXPLORER_NAME}"
ARXPLORER_DB_NAME: str = f"{ARXPLORER_NAME}_db.sqlite"

load_env()


def _get_or_create_folder(home: str, *folders: str) -> str:
    """Return the path to the PDF folder."""
    path = os.path.join(home, *folders)
    os.makedirs(path, exist_ok=True)
    return path


def _dump(configuration, config_file):
    with open(config_file, "w") as cf:
        json.dump(configuration, cf, indent=2)


class ConfigurationManager:
    CONFIG_FILE = Path.home() / ARXPLORER_FOLDER / "config.json"

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """
        Get the configuration. If the config file doesn't exist, create it with default values.
        """
        if not cls.CONFIG_FILE.exists():
            default_configuration = {
                "application_folder": _get_or_create_folder(str(Path.home()), ARXPLORER_FOLDER),
                "conversion_speed": "fast",
                "max_parallel_tasks": 10,
                "max_parallel_convert_processes": 2,
                "llm_model": "gemini/gemini-2.0-flash",
                "llm_client_retry_strategy": "exponential_backoff_retry",
                "llm_client_max_num_retries": 10,
                "max_queries_per_minute": 15,
            }
            cls.CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            _dump(default_configuration, cls.CONFIG_FILE)

        with open(cls.CONFIG_FILE, "r") as config_file:
            return json.load(config_file)

    @classmethod
    def update_config(cls, key: str, value: Any):
        """
        Update a specific configuration value.
        """
        configuration = cls.get_config()
        configuration[key] = value
        _dump(configuration, cls.CONFIG_FILE)

    @classmethod
    def get_application_folder(cls) -> str:
        return cls.get_config().get("application_folder", ".")

    @classmethod
    def get_cache_folder(cls) -> str:
        return _get_or_create_folder(cls.get_application_folder(), "cache")

    @classmethod
    def is_fast_conversion(cls) -> bool:
        return cls.get_config().get("conversion_speed", "fast").lower() == "fast"

    @classmethod
    def get_db_name(cls) -> str:
        return os.path.join(cls.get_application_folder(), f"{ARXPLORER_DB_NAME}.sqlite")

    @classmethod
    def get_llm_model(cls) -> str:
        return cls.get_config().get("llm_model", "gemini/gemini-2.0-flash")

    @classmethod
    def get_max_parallel_tasks(cls) -> int:
        return cls.get_config().get("max_parallel_tasks", 1)

    @classmethod
    def get_max_parallel_convert_processes(cls) -> int:
        return cls.get_config().get("max_parallel_convert_processes", 1)

    @classmethod
    def set_llm_model(cls, model: str):
        cls.update_config("llm_model", model)

    @classmethod
    def get_llm_client_retry_strategy(cls):
        return cls.get_config().get("llm_client_retry_strategy", "exponential_backoff_retry")

    @classmethod
    def get_llm_client_max_num_retries(cls):
        return cls.get_config().get("llm_client_max_num_retries", 10)

    @classmethod
    def get_max_queries_per_minute(cls):
        return cls.get_config().get("max_queries_per_minute", 15)

    @classmethod
    def get_conversion_speed(cls):
        return cls.get_config().get("conversion_speed", "fast")

    @classmethod
    def is_google_gemini_key_available(cls):
        return os.getenv("GEMINI_API_KEY")
