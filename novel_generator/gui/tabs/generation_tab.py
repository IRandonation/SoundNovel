from pathlib import Path
import yaml
import logging

import streamlit as st

from novel_generator.core.batch_outline_generator import BatchOutlineGenerator
from novel_generator.gui.utils import get_config


def render(project_root: Path):
    st.header("批量生成章节大纲")
    st.markdown("基于核心设定和整体大纲，使用 AI 拆分生成详细的章节细纲。")

    config = get_config()
    core_setting_path = project_root / "01_source" / "core_setting.yaml"
    outline_path = project_root / "01_source" / "overall_outline.yaml"

    if not config.get("api_key"):
        st.error("⚠️ 未配置 API Key！请先在左侧边栏设置 API 密钥。")

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        total_chapters = st.number_input(
            "预计总章节数", value=100, step=10, help="全书预计的总章节数"
        )
    with col_g2:
        batch_size = st.number_input(
            "每批次生成数量", value=5, min_value=1, max_value=20
        )

    st.markdown("#### 🎯 生成范围")
    col_r1, col_r2 = st.columns(2)
    with col_r1:
        start_gen_ch = st.number_input(
            "起始章节", value=1, min_value=1, max_value=total_chapters
        )
    with col_r2:
        end_gen_ch = st.number_input(
            "结束章节",
            value=min(20, total_chapters),
            min_value=1,
            max_value=total_chapters,
        )

    if start_gen_ch > end_gen_ch:
        st.error("起始章节不能大于结束章节")

    if st.button(
        "🚀 开始生成大纲",
        disabled=not config.get("api_key") or start_gen_ch > end_gen_ch,
    ):
        _run_generation(
            project_root, config, core_setting_path, outline_path,
            total_chapters, batch_size, start_gen_ch, end_gen_ch
        )


def _run_generation(
    project_root, config, core_setting_path, outline_path,
    total_chapters, batch_size, start_gen_ch, end_gen_ch
):
    progress_bar = st.progress(0)
    status_text = st.empty()
    log_area = st.empty()

    def update_progress(current, total, message):
        percent = min(current / total, 1.0) if total > 0 else 0
        progress_bar.progress(percent)
        status_text.text(f"[{int(percent * 100)}%] {message}")

    with st.spinner("正在初始化生成任务..."):
        try:
            with open(core_setting_path, "r", encoding="utf-8") as f:
                core_setting = yaml.safe_load(f)
            with open(outline_path, "r", encoding="utf-8") as f:
                overall_outline = yaml.safe_load(f)

            st.session_state["gen_logs"] = []

            class StreamlitLogHandler(logging.Handler):
                def emit(self, record):
                    msg = self.format(record)
                    current_logs = st.session_state.get("gen_logs", [])
                    current_logs.append(msg)
                    st.session_state["gen_logs"] = current_logs
                    log_area.code("\n".join(current_logs[-10:]))

            logger = logging.getLogger()
            handler = StreamlitLogHandler()
            logger.addHandler(handler)

            generator = BatchOutlineGenerator(config)
            result = generator.generate_batch_outline(
                core_setting,
                overall_outline,
                total_chapters=total_chapters,
                batch_size=batch_size,
                start_chapter_idx=start_gen_ch,
                end_chapter_idx=end_gen_ch,
                progress_callback=update_progress,
            )

            logger.removeHandler(handler)

            outline_dir = project_root / "02_Outline"
            outline_dir.mkdir(exist_ok=True)
            output_filename = (
                f"chapter_outline_{start_gen_ch:03d}-{end_gen_ch:03d}.yaml"
            )
            output_path = outline_dir / output_filename
            generator.save_batch_outline(result, str(output_path))

            status_text.success(f"✅ 大纲生成成功！已保存至：{output_filename}")
            st.json(result)

        except Exception as e:
            status_text.error(f"❌ 生成失败：{str(e)}")
            resp = getattr(e, "response", None)
            if resp is not None:
                resp_text = getattr(resp, "text", str(resp))
                st.error(f"API 响应内容：{resp_text}")
            logging.exception(e)