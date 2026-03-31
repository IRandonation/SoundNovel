"""
Tests for SessionManager in novel_generator.config.session
"""

import json
import os
import tempfile
import pytest

from novel_generator.config.session import SessionManager, SessionState


class TestSessionManager:
    """Test suite for SessionManager class"""

    def test_session_load(self, tmp_path):
        """Test loading session from file"""
        session_data = {
            "project_name": "Test Novel",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "api_config": {
                "provider": "deepseek",
                "deepseek_api_key": "test-key-123",
            },
            "generation_state": {
                "total_chapters": 100,
                "last_draft_chapter": 50,
            },
            "generation_config": {
                "batch_size": 10,
                "context_chapters": 5,
            },
            "ai_roles": {},
            "sessions": [],
        }
        
        session_file = tmp_path / "05_script" / "session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
        
        manager = SessionManager(str(tmp_path))
        state = manager.load()
        
        assert state.project_name == "Test Novel"
        assert state.api_config.deepseek_api_key == "test-key-123"
        assert state.generation_state.total_chapters == 100
        assert state.generation_state.last_draft_chapter == 50

    def test_session_save(self, tmp_path):
        """Test saving session to file"""
        session_file = tmp_path / "05_script" / "session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        
        manager = SessionManager(str(tmp_path))
        manager.state.project_name = "My Novel Project"
        manager.state.generation_state.total_chapters = 200
        manager.state.generation_state.last_draft_chapter = 75
        
        result = manager.save()
        
        assert result is True
        assert session_file.exists()
        
        with open(session_file, "r", encoding="utf-8") as f:
            saved_data = json.load(f)
        
        assert saved_data["project_name"] == "My Novel Project"
        assert saved_data["generation_state"]["total_chapters"] == 200
        assert saved_data["generation_state"]["last_draft_chapter"] == 75

    def test_session_roundtrip(self, tmp_path):
        """Test load -> save -> load produces identical state"""
        session_file = tmp_path / "05_script" / "session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        
        original_data = {
            "project_name": "Roundtrip Test",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "api_config": {
                "provider": "doubao",
                "doubao_api_key": "roundtrip-doubao",
                "deepseek_api_key": "roundtrip-deepseek",
            },
            "generation_state": {
                "total_chapters": 150,
                "last_outline_chapter": 30,
                "last_draft_chapter": 25,
            },
            "generation_config": {
                "batch_size": 12,
                "context_chapters": 8,
                "default_word_count": 1800,
            },
            "ai_roles": {
                "generator": {
                    "provider": "doubao",
                    "model": "test-model",
                    "temperature": 0.75,
                }
            },
            "sessions": [],
        }
        
        with open(session_file, "w", encoding="utf-8") as f:
            json.dump(original_data, f, ensure_ascii=False, indent=2)
        
        manager1 = SessionManager(str(tmp_path))
        state1 = manager1.load()
        
        manager1.save()
        
        manager2 = SessionManager(str(tmp_path))
        state2 = manager2.load()
        
        assert state2.project_name == state1.project_name
        assert state2.api_config.doubao_api_key == state1.api_config.doubao_api_key
        assert state2.api_config.deepseek_api_key == state1.api_config.deepseek_api_key
        assert state2.generation_state.total_chapters == state1.generation_state.total_chapters
        assert state2.generation_state.last_draft_chapter == state1.generation_state.last_draft_chapter

    def test_get_api_config(self, tmp_path):
        """Test get_api_config method"""
        session_file = tmp_path / "05_script" / "session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        
        manager = SessionManager(str(tmp_path))
        manager.state.api_config.doubao_api_key = "api-key-test"
        
        api_config = manager.get_api_config()
        
        assert api_config["doubao_api_key"] == "api-key-test"
        assert "default_model" in api_config

    def test_set_api_config(self, tmp_path):
        """Test set_api_config method"""
        session_file = tmp_path / "05_script" / "session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        
        manager = SessionManager(str(tmp_path))
        
        result = manager.set_api_config(
            provider="deepseek",
            api_key="new-deepseek-key",
            api_base_url="https://api.deepseek.com/v1",
        )
        
        assert result is True
        assert manager.state.api_config.deepseek_api_key == "new-deepseek-key"
        assert manager.state.api_config.deepseek_api_base_url == "https://api.deepseek.com/v1"

    def test_update_progress(self, tmp_path):
        """Test update_progress method"""
        session_file = tmp_path / "05_script" / "session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        
        manager = SessionManager(str(tmp_path))
        
        result = manager.update_progress(
            action="draft",
            start_chapter=1,
            end_chapter=10,
        )
        
        assert result is True
        assert manager.state.generation_state.last_draft_chapter == 10

    def test_get_last_chapter(self, tmp_path):
        """Test get_last_chapter method"""
        session_file = tmp_path / "05_script" / "session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        
        manager = SessionManager(str(tmp_path))
        manager.state.generation_state.last_draft_chapter = 25
        manager.state.generation_state.last_outline_chapter = 30
        
        last_draft = manager.get_last_chapter("draft")
        last_outline = manager.get_last_chapter("outline")
        
        assert last_draft == 25
        assert last_outline == 30

    def test_set_total_chapters(self, tmp_path):
        """Test set_total_chapters method"""
        session_file = tmp_path / "05_script" / "session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        
        manager = SessionManager(str(tmp_path))
        
        result = manager.set_total_chapters(100)
        
        assert result is True
        assert manager.state.generation_state.total_chapters == 100

    def test_get_status_summary(self, tmp_path):
        """Test get_status_summary method"""
        session_file = tmp_path / "05_script" / "session.json"
        session_file.parent.mkdir(parents=True, exist_ok=True)
        
        manager = SessionManager(str(tmp_path))
        manager.state.project_name = "Status Test"
        manager.state.generation_state.total_chapters = 50
        manager.state.generation_state.last_draft_chapter = 20
        
        summary = manager.get_status_summary()
        
        assert summary["project_name"] == "Status Test"
        assert summary["total_chapters"] == 50
        assert summary["last_draft"] == 20