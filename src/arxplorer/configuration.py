import json
import os
from pathlib import Path
from typing import Dict, Any

ARXPLORER_FOLDER = ".arxplorer"


class ConfigurationManager:
    DEFAULT_CONFIG_FILE = Path.home() / ARXPLORER_FOLDER / "config.json"

    @classmethod
    def _get_level_names_mapping(cls):
        return {"CRITICAL": 50, "ERROR": 40, "WARNING": 30, "INFO": 20, "DEBUG": 10, "NOTSET": 0}

    @classmethod
    def get_config_file(cls):
        return Path(os.environ.get("ARXPLORER_CONFIG_FILE", cls.DEFAULT_CONFIG_FILE))

    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        config_file = cls.get_config_file()
        if not config_file.exists():
            default_configuration = {
                "application_folder": str(Path.home() / ARXPLORER_FOLDER),
                "conversion_speed": "fast",
                "max_parallel_tasks": 10,
                "max_parallel_convert_processes": 2,
                "llm_model": "gemini/gemini-2.0-flash",
                "max_tokens": 8192,
                "llm_client_retry_strategy": "exponential_backoff_retry",
                "llm_client_max_num_retries": 10,
                "max_queries_per_minute": 15,
                "log_level": "ERROR",
            }
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, "w") as cf:
                json.dump(default_configuration, cf, indent=2)
            return default_configuration

        with open(config_file, "r") as config_file:
            return json.load(config_file)

    @classmethod
    def update_config(cls, key: str, value: Any):
        config_file = cls.get_config_file()
        configuration = cls.get_config()
        configuration[key] = value
        with open(config_file, "w") as cf:
            json.dump(configuration, cf, indent=2)

    @classmethod
    def get_application_folder(cls) -> str:
        return cls.get_config().get("application_folder", ".")

    @classmethod
    def get_cache_folder(cls) -> str:
        return os.path.join(cls.get_application_folder(), "cache")

    @classmethod
    def is_fast_conversion(cls) -> bool:
        return cls.get_config().get("conversion_speed", "fast").lower() == "fast"

    @classmethod
    def get_db_name(cls) -> str:
        return os.path.join(cls.get_application_folder(), "arxplorer_db.sqlite")

    @classmethod
    def get_llm_model(cls) -> str:
        return cls.get_config().get("llm_model", "gemini/gemini-2.0-flash")

    @classmethod
    def get_max_tokens(cls) -> int:
        return cls.get_config().get("max_tokens", 8192)

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
        return os.getenv("GEMINI_API_KEY") is not None

    @classmethod
    def is_groq_key_available(cls):
        return os.getenv("GROQ_API_KEY") is not None

    @classmethod
    def is_any_key_available(cls):
        return any([cls.is_groq_key_available(), cls.is_google_gemini_key_available()])

    @classmethod
    def get_log_level(cls) -> int:
        level_name = cls.get_config().get("log_level", "ERROR")
        return cls._get_level_names_mapping().get(level_name, 40)  # Default to ERROR (40) if not found
