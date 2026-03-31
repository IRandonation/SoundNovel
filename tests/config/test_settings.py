"""
Tests for Settings class in novel_generator.config.settings
"""

import json
import os
import tempfile
import pytest

from novel_generator.config.settings import Settings, create_default_config


class TestSettings:
    """Test suite for Settings class"""

    def test_settings_load(self, tmp_path):
        """Test loading settings from file"""
        # Create a test config file
        config_data = create_default_config()
        config_data["api_key"] = "test-api-key-123"
        config_data["doubao_api_key"] = "test-doubao-key"
        
        config_file = tmp_path / "test_settings.json"
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        # Load settings from file
        settings = Settings()
        settings.load_from_file(str(config_file))
        
        # Verify loaded values
        assert settings.api_config.api_key == "test-api-key-123"
        assert settings.api_config.doubao_api_key == "test-doubao-key"

    def test_settings_save(self, tmp_path):
        """Test saving settings to file"""
        settings = Settings()
        settings.api_config.api_key = "saved-api-key"
        settings.api_config.doubao_api_key = "saved-doubao-key"
        settings.generation_config.default_word_count = 2000
        
        config_file = tmp_path / "saved_settings.json"
        
        # Save settings to file
        settings.save_to_file(str(config_file))
        
        # Verify file was created
        assert config_file.exists()
        
        # Verify saved content
        with open(config_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        
        assert saved_data["api_key"] == "saved-api-key"
        assert saved_data["doubao_api_key"] == "saved-doubao-key"
        assert saved_data["novel_generation"]["default_word_count"] == 2000

    def test_settings_roundtrip(self, tmp_path):
        """Test load -> save -> load produces identical state"""
        # Create original settings
        original_config = create_default_config()
        original_config["api_key"] = "roundtrip-key"
        original_config["doubao_api_key"] = "roundtrip-doubao"
        original_config["deepseek_api_key"] = "roundtrip-deepseek"
        original_config["novel_generation"]["default_word_count"] = 2500
        original_config["novel_generation"]["context_chapters"] = 15
        
        # First: load from dict
        settings1 = Settings()
        settings1.load_from_dict(original_config)
        
        # Save to file
        config_file = tmp_path / "roundtrip.json"
        settings1.save_to_file(str(config_file))
        
        # Load from file
        settings2 = Settings()
        settings2.load_from_file(str(config_file))
        
        # Verify state is identical
        assert settings2.api_config.api_key == settings1.api_config.api_key
        assert settings2.api_config.doubao_api_key == settings1.api_config.doubao_api_key
        assert settings2.api_config.deepseek_api_key == settings1.api_config.deepseek_api_key
        assert settings2.generation_config.default_word_count == settings1.generation_config.default_word_count
        assert settings2.generation_config.context_chapters == settings1.generation_config.context_chapters

    def test_settings_to_dict(self):
        """Test to_dict method"""
        settings = Settings()
        settings.api_config.api_key = "test-key"
        settings.generation_config.default_word_count = 3000
        
        config_dict = settings.to_dict()
        
        assert config_dict["api_key"] == "test-key"
        assert config_dict["novel_generation"]["default_word_count"] == 3000

    def test_settings_load_from_dict(self):
        """Test load_from_dict method"""
        config_dict = {
            "api_key": "dict-key",
            "doubao_api_key": "dict-doubao",
            "novel_generation": {
                "default_word_count": 1800,
                "context_chapters": 8,
            }
        }
        
        settings = Settings()
        settings.load_from_dict(config_dict)
        
        assert settings.api_config.api_key == "dict-key"
        assert settings.api_config.doubao_api_key == "dict-doubao"
        assert settings.generation_config.default_word_count == 1800
        assert settings.generation_config.context_chapters == 8