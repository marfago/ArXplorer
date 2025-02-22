import os
import unittest
from pathlib import Path
from unittest.mock import patch, mock_open

from arxplorer.configuration import ConfigurationManager, ARXPLORER_FOLDER


class TestConfigurationManager(unittest.TestCase):

    def setUp(self):
        self.test_config_file = Path("/tmp/test_config.json")
        os.environ["ARXPLORER_CONFIG_FILE"] = str(self.test_config_file)

    def tearDown(self):
        if "ARXPLORER_CONFIG_FILE" in os.environ:
            del os.environ["ARXPLORER_CONFIG_FILE"]
        if self.test_config_file.exists():
            self.test_config_file.unlink()

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.mkdir")
    @patch("builtins.open", new_callable=mock_open)
    def test_get_config_default(self, mock_file, mock_mkdir, mock_exists):
        mock_exists.return_value = False
        config = ConfigurationManager.get_config()

        self.assertEqual(config["application_folder"], str(Path.home() / ARXPLORER_FOLDER))
        self.assertEqual(config["conversion_speed"], "fast")
        self.assertEqual(config["max_parallel_tasks"], 10)
        self.assertEqual(config["llm_model"], "gemini/gemini-2.0-flash")
        self.assertEqual(config["max_tokens"], 8192)

        mock_file.assert_called_with(self.test_config_file, "w")
        mock_mkdir.assert_called_once()

    @patch("pathlib.Path.exists")
    @patch("builtins.open", new_callable=mock_open, read_data='{"llm_model": "custom_model", "max_tokens": 4096}')
    def test_get_config_existing(self, mock_file, mock_exists):
        mock_exists.return_value = True
        config = ConfigurationManager.get_config()

        self.assertEqual(config["llm_model"], "custom_model")
        self.assertEqual(config["max_tokens"], 4096)

        mock_file.assert_called_with(self.test_config_file, "r")

    @patch("arxplorer.configuration.ConfigurationManager.get_config")
    @patch("arxplorer.configuration.ConfigurationManager.get_config_file")
    @patch("builtins.open", new_callable=mock_open)
    def test_update_config(self, mock_file, mock_get_config_file, mock_get_config):
        # Setup
        mock_get_config.return_value = {"existing_key": "old_value"}
        mock_get_config_file.return_value = self.test_config_file

        # Execute
        ConfigurationManager.update_config("new_key", "new_value")

        # Verify
        mock_file.assert_called_with(self.test_config_file, "w")

        self.assertEqual(mock_file().write.call_args_list[4].args[0], '"old_value"')
        self.assertEqual(mock_file().write.call_args_list[8].args[0], '"new_value"')

        # Verify that the configuration was updated
        updated_config = ConfigurationManager.get_config()
        self.assertEqual(updated_config["existing_key"], "old_value")
        self.assertEqual(updated_config["new_key"], "new_value")

    def test_get_application_folder(self):
        with patch.object(ConfigurationManager, "get_config", return_value={"application_folder": "/custom/folder"}):
            self.assertEqual(ConfigurationManager.get_application_folder(), "/custom/folder")

    @patch("os.path.join")
    def test_get_cache_folder(self, mock_join):
        mock_join.return_value = "/custom/folder/cache"
        with patch.object(ConfigurationManager, "get_application_folder", return_value="/custom/folder"):
            self.assertEqual(ConfigurationManager.get_cache_folder(), "/custom/folder/cache")

    def test_is_fast_conversion(self):
        with patch.object(ConfigurationManager, "get_config", return_value={"conversion_speed": "fast"}):
            self.assertTrue(ConfigurationManager.is_fast_conversion())
        with patch.object(ConfigurationManager, "get_config", return_value={"conversion_speed": "slow"}):
            self.assertFalse(ConfigurationManager.is_fast_conversion())

    def test_get_db_name(self):
        with patch.object(ConfigurationManager, "get_application_folder", return_value="/custom/folder"):
            expected_path = os.path.join("/custom/folder", "arxplorer_db.sqlite")
            self.assertEqual(ConfigurationManager.get_db_name(), expected_path)

    def test_get_llm_model(self):
        with patch.object(ConfigurationManager, "get_config", return_value={"llm_model": "custom_model"}):
            self.assertEqual(ConfigurationManager.get_llm_model(), "custom_model")

    def test_get_max_tokens(self):
        with patch.object(ConfigurationManager, "get_config", return_value={"max_tokens": 4096}):
            self.assertEqual(ConfigurationManager.get_max_tokens(), 4096)

    def test_get_max_parallel_tasks(self):
        with patch.object(ConfigurationManager, "get_config", return_value={"max_parallel_tasks": 5}):
            self.assertEqual(ConfigurationManager.get_max_parallel_tasks(), 5)

    def test_get_max_parallel_convert_processes(self):
        with patch.object(ConfigurationManager, "get_config", return_value={"max_parallel_convert_processes": 3}):
            self.assertEqual(ConfigurationManager.get_max_parallel_convert_processes(), 3)

    def test_set_llm_model(self):
        with patch.object(ConfigurationManager, "update_config") as mock_update_config:
            ConfigurationManager.set_llm_model("new_model")
            mock_update_config.assert_called_once_with("llm_model", "new_model")

    def test_get_llm_client_retry_strategy(self):
        with patch.object(ConfigurationManager, "get_config", return_value={"llm_client_retry_strategy": "custom_strategy"}):
            self.assertEqual(ConfigurationManager.get_llm_client_retry_strategy(), "custom_strategy")

    def test_get_llm_client_max_num_retries(self):
        with patch.object(ConfigurationManager, "get_config", return_value={"llm_client_max_num_retries": 15}):
            self.assertEqual(ConfigurationManager.get_llm_client_max_num_retries(), 15)

    def test_get_max_queries_per_minute(self):
        with patch.object(ConfigurationManager, "get_config", return_value={"max_queries_per_minute": 20}):
            self.assertEqual(ConfigurationManager.get_max_queries_per_minute(), 20)

    def test_get_conversion_speed(self):
        with patch.object(ConfigurationManager, "get_config", return_value={"conversion_speed": "slow"}):
            self.assertEqual(ConfigurationManager.get_conversion_speed(), "slow")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"})
    def test_is_google_gemini_key_available(self):
        self.assertTrue(ConfigurationManager.is_google_gemini_key_available())

    @patch.dict(os.environ, {"GROQ_API_KEY": "dummy_key"})
    def test_is_groq_key_available(self):
        self.assertTrue(ConfigurationManager.is_groq_key_available())

    @patch.dict(os.environ, {"GEMINI_API_KEY": "dummy_key"})
    def test_is_any_key_available_true(self):
        self.assertTrue(ConfigurationManager.is_any_key_available())

    @patch.dict(os.environ, {}, clear=True)
    def test_is_any_key_available_false(self):
        self.assertFalse(ConfigurationManager.is_any_key_available())

    def test_get_log_level(self):
        test_cases = [
            ("DEBUG", 10),
            ("INFO", 20),
            ("WARNING", 30),
            ("ERROR", 40),
            ("CRITICAL", 50),
            ("INVALID", 40),  # Should default to ERROR
            (None, 40),  # Should default to ERROR when no log_level is set
        ]

        for log_level, expected_value in test_cases:
            with self.subTest(log_level=log_level):
                config = {"log_level": log_level} if log_level is not None else {}
                with patch.object(ConfigurationManager, "get_config", return_value=config):
                    self.assertEqual(ConfigurationManager.get_log_level(), expected_value)


if __name__ == "__main__":
    unittest.main()
