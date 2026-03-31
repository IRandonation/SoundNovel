import pytest


def test_import_config_tab():
    from novel_generator.gui.tabs.config_tab import render
    assert callable(render)


def test_import_generation_tab():
    from novel_generator.gui.tabs.generation_tab import render
    assert callable(render)


def test_import_outline_tab():
    from novel_generator.gui.tabs.outline_tab import render
    assert callable(render)


def test_import_expand_tab():
    from novel_generator.gui.tabs.expand_tab import render
    assert callable(render)


def test_import_review_tab():
    from novel_generator.gui.tabs.review_tab import render
    assert callable(render)


def test_import_tabs_module():
    from novel_generator.gui.tabs import (
        render_config_tab,
        render_generation_tab,
        render_outline_tab,
        render_expand_tab,
        render_review_tab,
    )
    assert callable(render_config_tab)
    assert callable(render_generation_tab)
    assert callable(render_outline_tab)
    assert callable(render_expand_tab)
    assert callable(render_review_tab)


def test_import_utils_module():
    from novel_generator.gui.utils import (
        get_project_root,
        get_config,
        get_session_manager,
        get_gen_config_manager,
        init_session_state,
    )
    assert callable(get_project_root)
    assert callable(get_config)
    assert callable(get_session_manager)
    assert callable(get_gen_config_manager)
    assert callable(init_session_state)


def test_import_gui_module():
    from novel_generator.gui import (
        render_config_tab,
        render_generation_tab,
        render_outline_tab,
        render_expand_tab,
        render_review_tab,
        init_session_state,
        get_project_root,
        get_config,
    )
    assert callable(render_config_tab)
    assert callable(render_generation_tab)
    assert callable(render_outline_tab)
    assert callable(render_expand_tab)
    assert callable(render_review_tab)
    assert callable(init_session_state)
    assert callable(get_project_root)
    assert callable(get_config)


def test_session_keys_module():
    from novel_generator.gui.utils.session_keys import (
        CORE_SETTING_DATA,
        OVERALL_OUTLINE_DATA,
        GEN_LOGS,
        REVIEW_RESULT,
        REVIEWER_INSTANCE,
        CHAT_SERVICE,
        CHAT_MESSAGES,
        LAST_GENERATED_DRAFT_DIR,
        ALL_KEYS,
    )
    assert CORE_SETTING_DATA == "core_setting_data"
    assert OVERALL_OUTLINE_DATA == "overall_outline_data"
    assert GEN_LOGS == "gen_logs"
    assert len(ALL_KEYS) == 8