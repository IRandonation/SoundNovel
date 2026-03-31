from pathlib import Path
import os
import yaml
import re

import streamlit as st

from novel_generator.core.chapter_expander import ChapterExpander
from novel_generator.utils.multi_model_client import MultiModelClient
from novel_generator.gui.utils import get_config, get_config_manager


def render(project_root: Path):
    st.header("智能章节扩写")
    st.markdown("选择大纲文件，AI 将自动读取上下文并扩写正文。")

    config = get_config()
    outline_dir = project_root / "02_Outline"
    
    if not outline_dir.exists():
        st.error("找不到大纲目录 02_Outline/")
        return

    outline_files = list(outline_dir.glob("*.yaml"))
    if not outline_files:
        st.warning("大纲目录中没有找到 YAML 文件")
        return

    selected_file = st.selectbox(
        "选择大纲文件", [f.name for f in outline_files]
    )

    if selected_file:
        _render_expansion(project_root, config, outline_dir, selected_file)


def _render_expansion(project_root, config, outline_dir, selected_file):
    outline_file_path = outline_dir / selected_file
    with open(outline_file_path, "r", encoding="utf-8") as f:
        chapter_outline = yaml.safe_load(f)

    chapters = []
    for k in chapter_outline.keys():
        match = re.search(r"\d+", str(k))
        if match:
            chapters.append(int(match.group()))
    chapters.sort()

    if not chapters:
        st.warning("该文件中未识别到有效章节。")
        return

    st.info(f"文件中包含章节：{chapters[0]} - {chapters[-1]}")

    session_mgr = get_config_manager()
    continue_info = session_mgr.get_continue_info("draft")

    if continue_info["can_continue"]:
        st.success(
            f"📍 检测到上次进度：已完成第 {continue_info['last_chapter']} 章"
        )

    start_ch = st.number_input(
        "起始章节",
        value=chapters[0],
        min_value=chapters[0],
        max_value=chapters[-1],
    )
    end_ch = st.number_input(
        "结束章节",
        value=chapters[0],
        min_value=chapters[0],
        max_value=chapters[-1],
    )

    if st.button(
        "✍️ 开始扩写",
        disabled=not config.get("api_key") or start_ch > end_ch,
    ):
        _run_expansion(
            project_root, config, chapter_outline, outline_file_path,
            start_ch, end_ch, chapters
        )


def _run_expansion(
    project_root, config, chapter_outline, outline_file_path,
    start_ch, end_ch, chapters
):
    log_container = st.container()
    progress_bar = st.progress(0)

    try:
        client = MultiModelClient(config)
        expander = ChapterExpander(config, client)

        style_path = (
            project_root
            / "04_prompt"
            / "prompts"
            / "style_guide.yaml"
        )
        style_guide = {}
        if style_path.exists():
            with open(style_path, "r", encoding="utf-8") as f:
                style_guide = yaml.safe_load(f)

        draft_dir = config["paths"].get("draft_dir", "03_draft/")
        if not os.path.isabs(draft_dir):
            draft_dir = str(project_root / draft_dir)

        total = end_ch - start_ch + 1
        current_idx = 0
        context_window = config.get("novel_generation", {}).get(
            "context_chapters", 10
        )
        context_parts = []

        session_mgr_gui = get_config_manager()

        for ch_num in range(start_ch, end_ch + 1):
            with log_container:
                st.write(f"正在处理第 {ch_num} 章...")

            ch_data = None
            for key in [
                f"第{ch_num}章",
                f"{ch_num}",
                f"Chapter {ch_num}",
            ]:
                if key in chapter_outline:
                    ch_data = chapter_outline[key]
                    break

            if ch_data:
                previous_context = (
                    "\n\n".join(context_parts[-context_window:])
                    if context_parts
                    else ""
                )

                result = expander.expand_chapter(
                    ch_num, ch_data, previous_context, style_guide
                )
                content = (
                    result[0]
                    if isinstance(result, tuple)
                    else result
                )

                expander.save_chapter(ch_num, content, draft_dir)

                context_parts.append(
                    f"【第{ch_num}章摘要】\n{content[:500]}..."
                )

                session_mgr_gui.update_progress(
                    "draft",
                    start_ch,
                    ch_num,
                    str(outline_file_path),
                )

                st.toast(f"第 {ch_num} 章完成！", icon="✅")
            else:
                st.warning(
                    f"大纲中找不到第 {ch_num} 章的数据，跳过。"
                )

            current_idx += 1
            progress_bar.progress(current_idx / total)

        session_mgr_gui.add_session_record(
            action="expand",
            start_chapter=start_ch,
            end_chapter=end_ch,
            model_used=client.get_current_model(),
            success=True,
        )

        st.success("🎉 所有章节扩写完成！")
        st.balloons()

        st.session_state["last_generated_draft_dir"] = draft_dir
        st.rerun()

    except Exception as e:
        session_mgr_gui = get_config_manager()
        session_mgr_gui.add_session_record(
            action="expand",
            start_chapter=start_ch,
            end_chapter=end_ch,
            model_used="",
            success=False,
            error_message=str(e),
        )
        st.error(f"❌ 发生错误：{str(e)}")
        st.exception(e)