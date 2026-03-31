import json

from novel_generator.config.config_manager import ConfigManager


class TestConfigManager:
    def test_load_creates_defaults_when_missing(self, tmp_path):
        manager = ConfigManager(str(tmp_path))
        loaded = manager.load()

        assert "generation" in loaded
        assert "roles" in loaded
        assert "session" in loaded

    def test_get_role_config_prefers_generation_roles(self, tmp_path):
        config_file = tmp_path / "05_script" / "generation_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "version": "1.0",
                    "generation": {},
                    "roles": {
                        "generator": {
                            "provider": "deepseek",
                            "model": "deepseek-chat",
                            "temperature": 0.66,
                        }
                    },
                    "providers": {},
                    "quality_check": {},
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        session_file = tmp_path / "05_script" / "session.json"
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "project_name": "demo",
                    "api_config": {"provider": "doubao", "doubao_api_key": "k"},
                    "ai_roles": {
                        "generator": {
                            "provider": "doubao",
                            "model": "legacy-model",
                            "temperature": 0.1,
                        }
                    },
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        manager = ConfigManager(str(tmp_path))
        role = manager.get_role_config("generator")
        assert role.get("model") == "deepseek-chat"

    def test_get_api_key_from_session(self, tmp_path):
        session_file = tmp_path / "05_script" / "session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "api_config": {
                        "provider": "deepseek",
                        "deepseek_api_key": "deepseek-key",
                        "doubao_api_key": "doubao-key",
                    }
                },
                f,
                ensure_ascii=False,
                indent=2,
            )

        manager = ConfigManager(str(tmp_path))
        manager.load()
        assert manager.get_api_key("deepseek") == "deepseek-key"
        assert manager.get_api_key("doubao") == "doubao-key"

    def test_roundtrip_load_save_load(self, tmp_path):
        manager1 = ConfigManager(str(tmp_path))
        manager1.load()
        manager1.set_generation_config(context_chapters=22, default_word_count=2800)
        manager1.set_role_config("reviewer", model="deepseek-chat", temperature=0.25)

        manager2 = ConfigManager(str(tmp_path))
        loaded = manager2.load()
        assert loaded["generation"]["context_chapters"] == 22
        assert manager2.get_role_config("reviewer").get("temperature") == 0.25

    def test_missing_fields_merge_defaults(self, tmp_path):
        config_file = tmp_path / "05_script" / "generation_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump({"roles": {}}, f, ensure_ascii=False, indent=2)

        manager = ConfigManager(str(tmp_path))
        data = manager.load()
        assert "generation" in data
        assert "providers" in data
        assert "quality_check" in data

    def test_backward_compatible_get_api_config_shape(self, tmp_path):
        manager = ConfigManager(str(tmp_path))
        config = manager.get_api_config()
        assert "default_model" in config
        assert "novel_generation" in config
        assert "ai_roles" in config
