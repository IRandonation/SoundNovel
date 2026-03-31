import sys
from pathlib import Path
import json

import streamlit as st

from novel_generator.config.session import SessionManager
from novel_generator.config.generation_config import GenerationConfigManager


def get_project_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent.parent.parent.resolve()


def get_config():
    project_root = get_project_root()
    session_manager = SessionManager(str(project_root))
    config = session_manager.get_api_config()
    if "paths" not in config:
        config["paths"] = {}
    config["paths"]["project_root"] = str(project_root)
    return config


def get_session_manager():
    project_root = get_project_root()
    return SessionManager(str(project_root))


def get_gen_config_manager():
    project_root = get_project_root()
    return GenerationConfigManager(str(project_root))


def init_session_state():
    if "core_setting_data" not in st.session_state:
        st.session_state.core_setting_data = {}
    if "overall_outline_data" not in st.session_state:
        st.session_state.overall_outline_data = {}
    if "gen_logs" not in st.session_state:
        st.session_state.gen_logs = []


__all__ = [
    "get_project_root",
    "get_config",
    "get_session_manager",
    "get_gen_config_manager",
    "init_session_state",
]