import streamlit as st
import json
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    project_root = Path(sys.executable).parent
else:
    project_root = Path(__file__).parent.resolve()

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(project_root))

from novel_generator.gui.tabs import (
    render_config_tab,
    render_generation_tab,
    render_outline_tab,
    render_expand_tab,
    render_review_tab,
)
from novel_generator.gui.utils import get_config, get_session_manager


def render_sidebar(config):
    with st.sidebar:
        st.header("⚙️ 设置")

        with st.expander("🔑 API 密钥配置", expanded=True):
            model_provider = st.radio(
                "当前 AI 服务商",
                ["Doubao (豆包/火山)", "DeepSeek"],
                horizontal=True,
                index=0
                if config.get("models", {}).get("default_model_type", "doubao")
                == "doubao"
                else 1,
            )

            provider_map = {"Doubao (豆包/火山)": "doubao", "DeepSeek": "deepseek"}
            selected_provider_code = provider_map.get(model_provider, "doubao")

            current_model_type = config.get("models", {}).get("default_model_type", "doubao")
            if current_model_type != selected_provider_code:
                if "models" not in config:
                    config["models"] = {}
                config["models"]["default_model_type"] = selected_provider_code
                config["default_model"] = selected_provider_code
                with open(
                    project_root / "05_script" / "config.json", "w", encoding="utf-8"
                ) as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                st.rerun()

            st.markdown("---")
            doubao_key = st.text_input(
                "豆包/火山 API Key",
                value=config.get("doubao_api_key", ""),
                type="password",
            )
            deepseek_key = st.text_input(
                "DeepSeek API Key",
                value=config.get("deepseek_api_key", ""),
                type="password",
            )

            if st.button("💾 保存 API 密钥"):
                config["doubao_api_key"] = doubao_key
                config["deepseek_api_key"] = deepseek_key
                with open(
                    project_root / "05_script" / "config.json", "w", encoding="utf-8"
                ) as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                st.success("API 密钥已保存")

        with st.expander("📊 项目状态", expanded=False):
            session_mgr = get_session_manager()
            status = session_mgr.get_status_summary()

            provider_names = {"doubao": "豆包/火山", "deepseek": "DeepSeek"}

            st.caption(f"项目：{status['project_name']}")

            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.metric("大纲进度", f"{status['last_outline']} 章")
            with col_s2:
                st.metric("草稿进度", f"{status['last_draft']} 章")

            if status["total_chapters"] > 0:
                progress = status["last_draft"] / status["total_chapters"]
                st.progress(
                    progress,
                    text=f"总进度：{status['last_draft']}/{status['total_chapters']} ({progress * 100:.1f}%)",
                )

            st.caption(
                f"服务商：{provider_names.get(status['api_provider'], status['api_provider'])}"
            )

        st.info(f"当前工作目录：{project_root}")


def main():
    st.set_page_config(page_title="小说创作助手 AI", layout="wide", page_icon="📚")

    st.title("📚 小说创作助手 AI (GUI 版)")
    st.markdown("---")

    config = get_config()
    if not config:
        st.error("找不到配置文件 05_script/config.json，请确保在项目根目录下运行。")
        return

    render_sidebar(config)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📝 设定与整体大纲", "⛓️ 批量大纲生成", "📋 章节细纲编辑", "✍️ 章节智能扩写", "🔍 大纲审查与修改"]
    )

    with tab1:
        render_config_tab(project_root)

    with tab2:
        render_generation_tab(project_root)

    with tab3:
        render_outline_tab(project_root)

    with tab4:
        render_expand_tab(project_root)

    with tab5:
        render_review_tab(project_root)


if __name__ == "__main__":
    main()