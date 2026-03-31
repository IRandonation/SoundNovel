from pathlib import Path

import streamlit as st

from novel_generator.config.config_manager import ConfigManager
from novel_generator.core.outline_reviewer import OutlineReviewer
from novel_generator.core.outline_chat_service import OutlineChatService
from novel_generator.utils.multi_model_client import MultiModelClient
from novel_generator.gui.utils import get_config


def render(project_root: Path):
    st.header("大纲审查与AI对话修改")
    st.markdown("审查大纲一致性、角色弧线、剧情连贯性，并通过AI对话方式优化大纲。")

    config = get_config()
    core_setting_path = project_root / "01_source" / "core_setting.yaml"
    overall_outline_path = project_root / "01_source" / "overall_outline.yaml"

    if not core_setting_path.exists() or not overall_outline_path.exists():
        st.error("⚠️ 请先在「设定与整体大纲」标签页中创建核心设定和整体大纲文件。")
        return

    col_review, col_chat = st.columns([1, 1])

    with col_review:
        _render_review_section(project_root, config, core_setting_path, overall_outline_path)

    with col_chat:
        _render_chat_section(project_root, config, core_setting_path, overall_outline_path)


def _render_review_section(project_root, config, core_setting_path, overall_outline_path):
    st.subheader("审查结果")

    review_mode = st.radio(
        "审查模式",
        ["规则硬审查", "AI智能审查"],
        horizontal=True,
        help="规则硬审查：快速检查格式和结构问题\nAI智能审查：深度语义分析，需要API"
    )

    use_ai = review_mode == "AI智能审查"

    if use_ai and not config.get("api_key"):
        st.warning("AI审查需要配置API密钥，请先在左侧边栏设置")

    include_commercial = False
    if use_ai:
        include_commercial = st.checkbox("包含商业节奏分析", value=False)

    if st.button("开始审查", type="primary", disabled=(use_ai and not config.get("api_key"))):
        _run_review(project_root, config, core_setting_path, overall_outline_path, use_ai, include_commercial)

    if "review_result" in st.session_state:
        _display_review_results(project_root)


def _run_review(project_root, config, core_setting_path, overall_outline_path, use_ai, include_commercial):
    with st.spinner("正在审查大纲..." if not use_ai else "AI正在深度分析大纲..."):
        config_manager = ConfigManager(str(project_root))
        api_config = config_manager.get_api_config()

        client = None
        if use_ai:
            client = MultiModelClient(api_config)

        reviewer = OutlineReviewer(config_manager.get_role_config("reviewer"), client)
        if reviewer.load_settings(str(core_setting_path), str(overall_outline_path)):
            if use_ai:
                result = reviewer.review_with_ai(include_commercial=include_commercial)
            else:
                result = reviewer.review_with_rules()
            st.session_state["review_result"] = result
            st.session_state["reviewer_instance"] = reviewer
            st.rerun()
        else:
            st.error("加载设定文件失败")


def _display_review_results(project_root):
    result = st.session_state["review_result"]

    mode_badge = "AI" if result.review_mode == "ai" else "规则"
    st.info(f"审查模式: {mode_badge}")

    col_stats = st.columns(4)
    col_stats[0].metric("总问题数", result.total_issues)
    col_stats[1].metric("严重问题", result.errors, delta=None if result.errors == 0 else f"-{result.errors}")
    col_stats[2].metric("警告", result.warnings)
    col_stats[3].metric("建议", result.suggestions)

    if result.total_issues > 0:
        st.markdown("---")

        severity_filter = st.multiselect(
            "筛选问题类型",
            ["error", "warning", "suggestion"],
            default=["error", "warning", "suggestion"],
            format_func=lambda x: {"error": "严重问题", "warning": "警告", "suggestion": "建议"}[x]
        )

        all_categories = list(set(issue.category for issue in result.issues))
        category_filter = st.multiselect(
            "筛选问题类别",
            all_categories,
            default=all_categories
        )

        for issue in result.issues:
            if issue.severity in severity_filter and issue.category in category_filter:
                severity_colors = {"error": "red", "warning": "orange", "suggestion": "blue"}
                color = severity_colors.get(issue.severity, "gray")

                with st.expander(f"[{issue.severity.upper()}] [{issue.category}] {issue.description[:50]}...", expanded=False):
                    st.markdown(f"**章节范围**: {issue.chapter_range}")
                    st.markdown(f"**问题描述**: {issue.description}")
                    st.markdown(f"**修改建议**: {issue.suggestion}")
                    if issue.related_content:
                        st.markdown(f"**相关内容**: {issue.related_content}")
    else:
        st.success("大纲结构完整，未发现明显问题！")

    if st.button("保存审查结果"):
        output_path = project_root / "06_log" / "review_result.yaml"
        if "reviewer_instance" in st.session_state:
            if st.session_state["reviewer_instance"].save_review_result(result, str(output_path)):
                st.success(f"审查结果已保存至: {output_path}")


def _render_chat_section(project_root, config, core_setting_path, overall_outline_path):
    st.subheader("💬 AI对话修改")

    if not config.get("api_key"):
        st.warning("⚠️ 请先在左侧边栏配置API密钥")
        return

    if "chat_service" not in st.session_state:
        if st.button("🔄 初始化对话服务"):
            _init_chat_service(project_root, core_setting_path, overall_outline_path)
    else:
        _display_chat_interface(project_root)


def _init_chat_service(project_root, core_setting_path, overall_outline_path):
    config_manager = ConfigManager(str(project_root))
    api_config = config_manager.get_api_config()
    roles_config = config_manager.get_all_roles_config()

    client = MultiModelClient(api_config)
    chat_service = OutlineChatService(roles_config.get("refiner", {}), client)

    if chat_service.load_settings(str(core_setting_path), str(overall_outline_path)):
        st.session_state["chat_service"] = chat_service
        st.session_state["chat_messages"] = []
        st.rerun()
    else:
        st.error("初始化对话服务失败")


def _display_chat_interface(project_root):
    chat_service = st.session_state["chat_service"]
    messages = st.session_state.get("chat_messages", [])

    if "review_result" in st.session_state and not messages:
        result = st.session_state["review_result"]
        if result.total_issues > 0:
            initial_prompt = f"审查发现了{result.total_issues}个问题，请帮我分析和优化大纲。主要问题包括：\n"
            for issue in result.issues[:5]:
                initial_prompt += f"- [{issue.severity}] {issue.description}\n"

            with st.spinner("AI正在分析..."):
                response = chat_service.chat(initial_prompt)
                messages.append({"role": "assistant", "content": response})
                st.session_state["chat_messages"] = messages

    chat_container = st.container(height=400)
    with chat_container:
        for msg in messages:
            if msg["role"] == "user":
                st.chat_message("user").write(msg["content"])
            else:
                st.chat_message("assistant").write(msg["content"])

    user_input = st.chat_input("输入你的问题或修改需求...")
    if user_input:
        messages.append({"role": "user", "content": user_input})
        st.session_state["chat_messages"] = messages

        with st.spinner("AI思考中..."):
            response = chat_service.chat(user_input)
            messages.append({"role": "assistant", "content": response})
            st.session_state["chat_messages"] = messages
        st.rerun()

    col_actions = st.columns(3)
    with col_actions[0]:
        if st.button("💾 保存修改"):
            if chat_service.save_all():
                st.success("设定和大纲已保存！")
                st.session_state["review_result"] = None
            else:
                st.error("保存失败")

    with col_actions[1]:
        if st.button("🔄 重新审查"):
            st.session_state["review_result"] = None
            st.session_state["chat_messages"] = []
            st.rerun()

    with col_actions[2]:
        if st.button("🗑️ 清空对话"):
            st.session_state["chat_messages"] = []
            chat_service.clear_history()
            st.rerun()