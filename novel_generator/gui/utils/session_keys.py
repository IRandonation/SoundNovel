"""Session state keys documentation for SoundNovel GUI.

All session_state keys used across GUI tabs are documented here
for cross-module access and maintenance.

KEYS:
    core_setting_data: dict
        - Purpose: Stores core setting YAML data
        - Type: dict
        - Used by: config_tab (render_core_setting_tab)
        - Modified when: User edits core setting, reloads from file

    overall_outline_data: dict
        - Purpose: Stores overall outline YAML data
        - Type: dict
        - Used by: config_tab (render_overall_outline_tab)
        - Modified when: User edits overall outline, reloads from file

    gen_logs: list
        - Purpose: Stores generation log messages
        - Type: list[str]
        - Used by: generation_tab (batch outline generation)
        - Modified when: Log handler emits messages during generation

    review_result: ReviewResult
        - Purpose: Stores outline review result
        - Type: ReviewResult object
        - Used by: review_tab (outline review)
        - Modified when: Review completes

    reviewer_instance: OutlineReviewer
        - Purpose: Stores reviewer instance for saving results
        - Type: OutlineReviewer object
        - Used by: review_tab
        - Modified when: Review completes

    chat_service: OutlineChatService
        - Purpose: Stores AI chat service for outline modification
        - Type: OutlineChatService object
        - Used by: review_tab (AI chat)
        - Modified when: User initializes chat service

    chat_messages: list
        - Purpose: Stores chat message history
        - Type: list[dict] with keys 'role' and 'content'
        - Used by: review_tab (AI chat)
        - Modified when: User sends message, AI responds

    last_generated_draft_dir: str
        - Purpose: Stores last generated draft directory path
        - Type: str
        - Used by: expand_tab
        - Modified when: Chapter expansion completes
"""

# Key constants for reference (not used directly, session_state uses string keys)
CORE_SETTING_DATA = "core_setting_data"
OVERALL_OUTLINE_DATA = "overall_outline_data"
GEN_LOGS = "gen_logs"
REVIEW_RESULT = "review_result"
REVIEWER_INSTANCE = "reviewer_instance"
CHAT_SERVICE = "chat_service"
CHAT_MESSAGES = "chat_messages"
LAST_GENERATED_DRAFT_DIR = "last_generated_draft_dir"

ALL_KEYS = [
    CORE_SETTING_DATA,
    OVERALL_OUTLINE_DATA,
    GEN_LOGS,
    REVIEW_RESULT,
    REVIEWER_INSTANCE,
    CHAT_SERVICE,
    CHAT_MESSAGES,
    LAST_GENERATED_DRAFT_DIR,
]