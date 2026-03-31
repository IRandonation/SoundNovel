"""
Tests for GenerationConfigManager in novel_generator.config.generation_config
"""

import json
import os
import tempfile
import pytest

from novel_generator.config.generation_config import GenerationConfigManager, DEFAULT_CONFIG


class TestGenerationConfigManager:
    """Test suite for GenerationConfigManager class"""

    def test_config_load(self, tmp_path):
        """Test loading config from file"""
        config_data = {
            "version": "1.0",
            "generation": {
                "max_refine_iterations": 5,
                "pass_score_threshold": 80,
                "context_chapters": 20,
            },
            "roles": {
                "generator": {
                    "model": "test-model",
                    "temperature": 0.8,
                }
            }
        }
        
        config_file = tmp_path / "05_script" / "generation_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config_data, f, ensure_ascii=False, indent=2)
        
        manager = GenerationConfigManager(str(tmp_path))
        config = manager.load()
        
        assert config["generation"]["max_refine_iterations"] == 5
        assert config["generation"]["pass_score_threshold"] == 80
        assert config["generation"]["context_chapters"] == 20

    def test_config_save(self, tmp_path):
        """Test saving config to file"""
        config_file = tmp_path / "05_script" / "generation_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        manager = GenerationConfigManager(str(tmp_path))
        
        new_config = {
            "version": "1.0",
            "generation": {
                "max_refine_iterations": 10,
                "pass_score_threshold": 85,
            },
            "roles": DEFAULT_CONFIG["roles"],
            "providers": DEFAULT_CONFIG["providers"],
            "quality_check": DEFAULT_CONFIG["quality_check"],
        }
        
        result = manager.save(new_config)
        
        assert result is True
        assert config_file.exists()
        
        with open(config_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        
        assert saved_data["generation"]["max_refine_iterations"] == 10
        assert saved_data["generation"]["pass_score_threshold"] == 85

    def test_config_roundtrip(self, tmp_path):
        """Test load -> save -> load produces identical state"""
        config_file = tmp_path / "05_script" / "generation_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        original_config = {
            "version": "1.0",
            "generation": {
                "max_refine_iterations": 7,
                "pass_score_threshold": 75,
                "context_chapters": 12,
                "default_word_count": 2000,
                "batch_size": 20,
            },
            "roles": {
                "generator": {
                    "name": "生成者",
                    "model": "custom-model",
                    "temperature": 0.6,
                }
            },
            "providers": DEFAULT_CONFIG["providers"],
            "quality_check": DEFAULT_CONFIG["quality_check"],
        }
        
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(original_config, f, ensure_ascii=False, indent=2)
        
        manager1 = GenerationConfigManager(str(tmp_path))
        config1 = manager1.load()
        
        config_file2 = tmp_path / "roundtrip.json"
        manager1.export_config(str(config_file2))
        
        manager2 = GenerationConfigManager(str(tmp_path))
        manager2.import_config(str(config_file2))
        
        config2 = manager2.config
        
        assert config2["generation"]["max_refine_iterations"] == config1["generation"]["max_refine_iterations"]
        assert config2["generation"]["pass_score_threshold"] == config1["generation"]["pass_score_threshold"]
        assert config2["generation"]["context_chapters"] == config1["generation"]["context_chapters"]

    def test_get_generation_config(self, tmp_path):
        """Test get_generation_config method"""
        config_file = tmp_path / "05_script" / "generation_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        manager = GenerationConfigManager(str(tmp_path))
        gen_config = manager.get_generation_config()
        
        assert "max_refine_iterations" in gen_config
        assert "pass_score_threshold" in gen_config

    def test_get_role_config(self, tmp_path):
        """Test get_role_config method"""
        config_file = tmp_path / "05_script" / "generation_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        manager = GenerationConfigManager(str(tmp_path))
        role_config = manager.get_role_config("generator")
        
        assert "model" in role_config
        assert "temperature" in role_config

    def test_set_role_config(self, tmp_path):
        """Test set_role_config method"""
        config_file = tmp_path / "05_script" / "generation_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        manager = GenerationConfigManager(str(tmp_path))
        _ = manager.config
        
        result = manager.set_role_config("generator", temperature=0.9, model="new-model")
        
        assert result is True
        
        role_config = manager.get_role_config("generator")
        assert role_config["temperature"] == 0.9
        assert role_config["model"] == "new-model"

    def test_set_generation_config(self, tmp_path):
        """Test set_generation_config method"""
        config_file = tmp_path / "05_script" / "generation_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        manager = GenerationConfigManager(str(tmp_path))
        _ = manager.config
        
        result = manager.set_generation_config(max_refine_iterations=8, pass_score_threshold=90)
        
        assert result is True
        
        gen_config = manager.get_generation_config()
        assert gen_config["max_refine_iterations"] == 8
        assert gen_config["pass_score_threshold"] == 90

    def test_reset_to_default(self, tmp_path):
        """Test reset_to_default method"""
        config_file = tmp_path / "05_script" / "generation_config.json"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        
        manager = GenerationConfigManager(str(tmp_path))
        _ = manager.config
        manager.set_generation_config(max_refine_iterations=99)
        
        result = manager.reset_to_default()
        
        assert result is True
        
        gen_config = manager.get_generation_config()
        assert gen_config["max_refine_iterations"] == DEFAULT_CONFIG["generation"]["max_refine_iterations"]