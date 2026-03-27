import streamlit as st
import yaml
import json
import sys
import os
from pathlib import Path
import logging
import time
import subprocess
import platform

if getattr(sys, "frozen", False):
    project_root = Path(sys.executable).parent
else:
    project_root = Path(__file__).parent.resolve()

if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(project_root))

from novel_generator.core.batch_outline_generator import BatchOutlineGenerator
from novel_generator.core.chapter_expander import ChapterExpander
from novel_generator.core.outline_generator import OutlineGenerator
from novel_generator.core.outline_reviewer import OutlineReviewer
from novel_generator.core.outline_chat_service import OutlineChatService
from novel_generator.config.session import SessionManager
from novel_generator.config.generation_config import GenerationConfigManager
from novel_generator.utils.multi_model_client import MultiModelClient


def get_gen_config_manager():
    return GenerationConfigManager(str(project_root))


def load_config():
    session_manager = SessionManager(str(project_root))
    config = session_manager.get_api_config()
    if "paths" not in config:
        config["paths"] = {}
    config["paths"]["project_root"] = str(project_root)
    return config


def get_session_manager():
    return SessionManager(str(project_root))


def render_core_setting_tab(project_root, core_setting_path):
    """渲染核心设定编辑界面"""
    st.subheader("核心设定 (Core Setting)")

    if not core_setting_path.exists():
        st.warning(f"文件不存在：{core_setting_path}")
        return

    if "core_setting_data" not in st.session_state:
        try:
            with open(core_setting_path, "r", encoding="utf-8") as f:
                st.session_state.core_setting_data = yaml.safe_load(f) or {}
        except Exception as e:
            st.error(f"解析核心设定出错：{e}")
            st.session_state.core_setting_data = {}

    core_data = st.session_state.core_setting_data

    if st.button("🔄 从文件重载", help="放弃当前未保存的修改"):
        try:
            with open(core_setting_path, "r", encoding="utf-8") as f:
                st.session_state.core_setting_data = yaml.safe_load(f) or {}
            st.rerun()
        except Exception as e:
            st.error(f"重载失败：{e}")

    with st.expander("🌍 世界观与核心 (必填)", expanded=True):
        c_world = core_data.get("世界观", "")
        new_world = st.text_area("世界观", value=c_world, height=150)
        if new_world != c_world:
            core_data["世界观"] = new_world

        c_magic = core_data.get("魔力体系", "")
        new_magic = st.text_area("魔力体系 (可选)", value=c_magic, height=80)
        if new_magic != c_magic:
            core_data["魔力体系"] = new_magic

        c_conflict = core_data.get("核心冲突", "")
        new_conflict = st.text_area("核心冲突", value=c_conflict, height=100)
        if new_conflict != c_conflict:
            core_data["核心冲突"] = new_conflict

    with st.expander("👥 人物小传 (必填)", expanded=False):
        characters = core_data.get("人物小传", {})
        if not isinstance(characters, dict):
            characters = {}
            core_data["人物小传"] = characters

        char_names = list(characters.keys())

        c_col1, c_col2 = st.columns([3, 1])
        with c_col2:
            if st.button("➕ 新增人物", key="add_char_btn"):
                new_key = f"新角色_{len(char_names) + 1}"
                characters[new_key] = {
                    "角色类型": "主角",
                    "身份": "",
                    "性格": "",
                    "核心动机": "",
                }
                st.session_state.core_setting_data["人物小传"] = characters
                st.rerun()

        if char_names:
            selected_char = st.selectbox("选择角色", char_names, key="char_select")

            if selected_char:
                char_info = characters[selected_char]
                if not isinstance(char_info, dict):
                    char_info = {}
                    characters[selected_char] = char_info

                col_rename, col_delete = st.columns([4, 1])
                with col_rename:
                    new_char_name = st.text_input("角色名称", value=selected_char)
                with col_delete:
                    st.write("")
                    st.write("")
                    if st.button("🗑️ 删除", key=f"del_char_{selected_char}"):
                        del characters[selected_char]
                        st.session_state.core_setting_data["人物小传"] = characters
                        st.rerun()

                if new_char_name != selected_char and new_char_name not in characters:
                    characters[new_char_name] = characters.pop(selected_char)
                    st.session_state.core_setting_data["人物小传"] = characters
                    st.rerun()

                role_options = ["主角", "主要配角", "次要配角", "反派", "龙套/路人"]
                current_role = char_info.get("角色类型", "主角")
                if current_role not in role_options:
                    role_options.append(current_role)

                c_role = st.selectbox(
                    "角色类型",
                    role_options,
                    index=role_options.index(current_role)
                    if current_role in role_options
                    else 0,
                    key=f"role_{selected_char}",
                )
                if c_role != char_info.get("角色类型", ""):
                    char_info["角色类型"] = c_role

                c_identity = st.text_input(
                    "身份", value=char_info.get("身份", ""), key=f"id_{selected_char}"
                )
                if c_identity != char_info.get("身份", ""):
                    char_info["身份"] = c_identity

                c_personality = st.text_input(
                    "性格", value=char_info.get("性格", ""), key=f"per_{selected_char}"
                )
                if c_personality != char_info.get("性格", ""):
                    char_info["性格"] = c_personality

                c_motivation = st.text_area(
                    "核心动机",
                    value=char_info.get("核心动机", ""),
                    height=60,
                    key=f"mot_{selected_char}",
                )
                if c_motivation != char_info.get("核心动机", ""):
                    char_info["核心动机"] = c_motivation

                st.markdown("**其他属性**")
                core_fields = {"角色类型", "身份", "性格", "核心动机"}
                for k, v in list(char_info.items()):
                    if k not in core_fields:
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            if isinstance(v, str) and len(v) > 50:
                                new_v = st.text_area(
                                    k, value=v, height=60, key=f"cf_{selected_char}_{k}"
                                )
                            else:
                                new_v = st.text_input(
                                    k, value=str(v), key=f"cf_{selected_char}_{k}"
                                )
                            if new_v != str(v):
                                char_info[k] = new_v
                        with c2:
                            if st.button("🗑️", key=f"del_cf_{selected_char}_{k}"):
                                del char_info[k]
                                st.rerun()

                with st.popover("➕ 添加属性"):
                    new_attr = st.text_input("属性名", key=f"new_attr_{selected_char}")
                    if st.button("确认", key=f"add_attr_{selected_char}") and new_attr:
                        char_info[new_attr] = ""
                        st.rerun()

                characters[selected_char] = char_info
                core_data["人物小传"] = characters

    with st.expander("🕵️ 伏笔清单 (可选)", expanded=False):
        foreshadowing = core_data.get("伏笔清单", [])
        if not isinstance(foreshadowing, list):
            foreshadowing = []
            core_data["伏笔清单"] = foreshadowing

        new_fs_list = []
        for i, item in enumerate(foreshadowing):
            c1, c2 = st.columns([9, 1])
            with c1:
                val = st.text_input(f"伏笔{i + 1}", value=str(item), key=f"fs_{i}")
                new_fs_list.append(val)
            with c2:
                if st.button("✖️", key=f"del_fs_{i}"):
                    foreshadowing.pop(i)
                    core_data["伏笔清单"] = foreshadowing
                    st.rerun()

        if len(new_fs_list) == len(foreshadowing):
            core_data["伏笔清单"] = new_fs_list

        if st.button("➕ 添加伏笔", key="add_fs"):
            core_data["伏笔清单"].append("")
            st.rerun()

    with st.expander("🚫 设定禁忌 (可选)", expanded=False):
        taboos = core_data.get("设定禁忌", [])
        if not isinstance(taboos, list):
            taboos = []
            core_data["设定禁忌"] = taboos

        new_taboo_list = []
        for i, item in enumerate(taboos):
            c1, c2 = st.columns([9, 1])
            with c1:
                val = st.text_input(f"禁忌{i + 1}", value=str(item), key=f"taboo_{i}")
                new_taboo_list.append(val)
            with c2:
                if st.button("✖️", key=f"del_taboo_{i}"):
                    taboos.pop(i)
                    core_data["设定禁忌"] = taboos
                    st.rerun()

        if len(new_taboo_list) == len(taboos):
            core_data["设定禁忌"] = new_taboo_list

        if st.button("➕ 添加禁忌", key="add_taboo"):
            core_data["设定禁忌"].append("")
            st.rerun()

    with st.expander("🎨 风格约束 (可选)", expanded=False):
        style = core_data.get("风格约束", {})
        if not isinstance(style, dict):
            style = {}
            core_data["风格约束"] = style

        style_fields = ["语言风格", "对话特征", "场景描写", "节奏控制"]
        for field in style_fields:
            val = style.get(field, "")
            new_val = st.text_input(field, value=val, key=f"style_{field}")
            if new_val != val:
                style[field] = new_val

        core_data["风格约束"] = style

    if st.button("💾 保存核心设定", type="primary", use_container_width=True):
        with open(core_setting_path, "w", encoding="utf-8") as f:
            yaml.dump(core_data, f, allow_unicode=True, sort_keys=False)
        st.success("核心设定已保存！")


def render_overall_outline_tab(project_root, outline_path):
    """渲染整体大纲编辑界面"""
    st.subheader("整体大纲 (Overall Outline)")

    if not outline_path.exists():
        st.warning(f"文件不存在：{outline_path}")
        return

    if "overall_outline_data" not in st.session_state:
        try:
            with open(outline_path, "r", encoding="utf-8") as f:
                st.session_state.overall_outline_data = yaml.safe_load(f) or {}
        except Exception as e:
            st.error(f"解析整体大纲出错：{e}")
            st.session_state.overall_outline_data = {}

    overall_data = st.session_state.overall_outline_data

    if st.button("🔄 从文件重载", help="放弃当前未保存的修改", key="reload_outline"):
        try:
            with open(outline_path, "r", encoding="utf-8") as f:
                st.session_state.overall_outline_data = yaml.safe_load(f) or {}
            st.rerun()
        except Exception as e:
            st.error(f"重载失败：{e}")

    total_ch = overall_data.get("总章节数", 100)
    new_total = st.number_input(
        "总章节数", value=int(total_ch) if total_ch else 100, min_value=1
    )
    if new_total != total_ch:
        overall_data["总章节数"] = new_total

    overview = overall_data.get("故事概述", "")
    new_overview = st.text_area("故事概述", value=overview, height=100)
    if new_overview != overview:
        overall_data["故事概述"] = new_overview

    st.markdown("---")
    st.markdown("### 📖 幕结构")

    acts = overall_data.get("幕结构", {})
    if not isinstance(acts, dict):
        acts = {}
        overall_data["幕结构"] = acts

    act_names = list(acts.keys())

    if st.button("➕ 新增幕", key="add_act"):
        new_act = f"第{len(act_names) + 1}幕"
        acts[new_act] = {"章节范围": "", "概述": "", "剧情要点": []}
        st.session_state.overall_outline_data["幕结构"] = acts
        st.rerun()

    for act_name in act_names:
        with st.expander(f"🎬 {act_name}", expanded=False):
            act_data = acts[act_name]
            if not isinstance(act_data, dict):
                act_data = {"章节范围": "", "概述": "", "剧情要点": []}
                acts[act_name] = act_data

            c1, c2 = st.columns([4, 1])
            with c1:
                new_act_name = st.text_input(
                    "幕名称", value=act_name, key=f"act_name_{act_name}"
                )
            with c2:
                st.write("")
                if st.button("🗑️ 删除", key=f"del_act_{act_name}"):
                    del acts[act_name]
                    st.session_state.overall_outline_data["幕结构"] = acts
                    st.rerun()

            if new_act_name != act_name and new_act_name not in acts:
                acts[new_act_name] = acts.pop(act_name)
                st.session_state.overall_outline_data["幕结构"] = acts
                st.rerun()

            ch_range = act_data.get("章节范围", "")
            new_range = st.text_input(
                "章节范围",
                value=ch_range,
                placeholder="如：第 1-20 章",
                key=f"range_{act_name}",
            )
            if new_range != ch_range:
                act_data["章节范围"] = new_range

            summary = act_data.get("概述", "")
            new_summary = st.text_area(
                "概述", value=summary, height=60, key=f"sum_{act_name}"
            )
            if new_summary != summary:
                act_data["概述"] = new_summary

            points = act_data.get("剧情要点", [])
            if not isinstance(points, list):
                points = []
                act_data["剧情要点"] = points

            st.markdown("**剧情要点:**")
            new_points = []
            for i, pt in enumerate(points):
                c1, c2 = st.columns([9, 1])
                with c1:
                    new_pt = st.text_area(
                        f"要点{i + 1}",
                        value=str(pt),
                        height=40,
                        key=f"pt_{act_name}_{i}",
                    )
                    new_points.append(new_pt)
                with c2:
                    if st.button("✖️", key=f"del_pt_{act_name}_{i}"):
                        points.pop(i)
                        st.rerun()

            if len(new_points) == len(points):
                act_data["剧情要点"] = new_points

            if st.button("➕ 添加要点", key=f"add_pt_{act_name}"):
                act_data["剧情要点"].append("")
                st.rerun()

            acts[act_name] = act_data

    st.markdown("---")
    st.markdown("### 🔑 关键转折点")

    turning_points = overall_data.get("关键转折点", [])
    if not isinstance(turning_points, list):
        turning_points = []
        overall_data["关键转折点"] = turning_points

    new_tp_list = []
    for i, tp in enumerate(turning_points):
        if not isinstance(tp, dict):
            tp = {"章节": 0, "事件": "", "影响": ""}

        with st.container():
            c1, c2, c3, c4 = st.columns([1, 3, 3, 1])
            with c1:
                ch = tp.get("章节", 0)
                new_ch = st.number_input(
                    "章节", value=int(ch) if ch else 0, min_value=0, key=f"tp_ch_{i}"
                )
            with c2:
                evt = tp.get("事件", "")
                new_evt = st.text_input("事件", value=evt, key=f"tp_evt_{i}")
            with c3:
                impact = tp.get("影响", "")
                new_impact = st.text_input("影响", value=impact, key=f"tp_impact_{i}")
            with c4:
                st.write("")
                if st.button("✖️", key=f"del_tp_{i}"):
                    turning_points.pop(i)
                    st.session_state.overall_outline_data["关键转折点"] = turning_points
                    st.rerun()

            new_tp_list.append({"章节": new_ch, "事件": new_evt, "影响": new_impact})

    if len(new_tp_list) == len(turning_points):
        overall_data["关键转折点"] = new_tp_list

    if st.button("➕ 添加转折点", key="add_tp"):
        overall_data["关键转折点"].append({"章节": 0, "事件": "", "影响": ""})
        st.rerun()

    if st.button("💾 保存整体大纲", type="primary", use_container_width=True):
        with open(outline_path, "w", encoding="utf-8") as f:
            yaml.dump(overall_data, f, allow_unicode=True, sort_keys=False)
        st.success("整体大纲已保存！")


def main():
    st.set_page_config(page_title="小说创作助手 AI", layout="wide", page_icon="📚")

    st.title("📚 小说创作助手 AI (GUI 版)")
    st.markdown("---")

    config = load_config()
    if not config:
        st.error("找不到配置文件 05_script/config.json，请确保在项目根目录下运行。")
        return

    # Sidebar
    with st.sidebar:
        st.header("⚙️ 设置")

        # API Configuration
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

    # Main Tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["📝 设定与整体大纲", "⛓️ 批量大纲生成", "📋 章节细纲编辑", "✍️ 章节智能扩写", "🔍 大纲审查与修改"]
    )

    # Tab 1: Settings
    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            core_setting_path = project_root / "01_source" / "core_setting.yaml"
            render_core_setting_tab(project_root, core_setting_path)
        with col2:
            outline_path = project_root / "01_source" / "overall_outline.yaml"
            render_overall_outline_tab(project_root, outline_path)

    # Tab 2: Batch Outline Generation
    with tab2:
        st.header("批量生成章节大纲")
        st.markdown("基于核心设定和整体大纲，使用 AI 拆分生成详细的章节细纲。")

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

    # Tab 3: Chapter Outline Editor
    with tab3:
        st.header("📋 章节细纲可视化编辑")

        outline_dir = project_root / "02_Outline"
        if outline_dir.exists():
            outline_files = list(outline_dir.glob("*.yaml")) + list(
                outline_dir.glob("*.txt")
            )
            selected_file = st.selectbox(
                "选择要编辑的大纲文件",
                [f.name for f in outline_files],
                key="editor_file_select",
            )

            if selected_file:
                file_path = outline_dir / selected_file

                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        chapter_data = yaml.safe_load(f) or {}
                except Exception as e:
                    st.error(f"读取文件失败：{e}")
                    chapter_data = {}

                if chapter_data:

                    def get_chapter_num(key):
                        import re

                        match = re.search(r"\d+", str(key))
                        return int(match.group()) if match else 9999

                    sorted_keys = sorted(chapter_data.keys(), key=get_chapter_num)

                    with st.form("chapter_editor_form"):
                        st.info("💡 修改下方卡片内容后，点击底部的【保存修改】按钮生效")

                        updated_data = {}

                        for key in sorted_keys:
                            details = chapter_data[key]
                            with st.expander(
                                f"📄 {key}: {details.get('标题', '无标题')}",
                                expanded=False,
                            ):
                                col_a, col_b = st.columns(2)

                                c_title = details.get("标题", "")
                                c_core = details.get("核心事件", "")
                                c_scene = details.get("场景", "")
                                c_action = details.get("人物行动", "")
                                c_foreshadow = details.get("伏笔回收", "")
                                c_word_count = details.get("字数目标", "1500 字左右")

                                with col_a:
                                    new_title = st.text_input(
                                        f"标题 ({key})", value=c_title
                                    )
                                    new_core = st.text_area(
                                        f"核心事件 ({key})", value=c_core, height=100
                                    )
                                    new_scene = st.text_area(
                                        f"场景 ({key})", value=c_scene, height=80
                                    )

                                with col_b:
                                    new_word_count = st.text_input(
                                        f"字数目标 ({key})", value=c_word_count
                                    )
                                    new_action = st.text_area(
                                        f"人物行动 ({key})", value=c_action, height=100
                                    )
                                    new_foreshadow = st.text_area(
                                        f"伏笔回收 ({key})",
                                        value=c_foreshadow,
                                        height=80,
                                    )

                                updated_data[key] = {
                                    "标题": new_title,
                                    "核心事件": new_core,
                                    "场景": new_scene,
                                    "人物行动": new_action,
                                    "伏笔回收": new_foreshadow,
                                    "字数目标": new_word_count,
                                }

                        submitted = st.form_submit_button("💾 保存所有修改")
                        if submitted:
                            with open(file_path, "w", encoding="utf-8") as f:
                                yaml.dump(
                                    updated_data, f, allow_unicode=True, sort_keys=False
                                )
                            st.success(f"已保存到 {selected_file}")
                            st.rerun()

                    with st.expander("➕ 添加新章节"):
                        with st.form("add_chapter_form"):
                            new_ch_num = st.number_input(
                                "新章节号", min_value=1, value=len(sorted_keys) + 1
                            )
                            new_ch_key = f"第{new_ch_num}章"

                            c1, c2 = st.columns(2)
                            with c1:
                                n_title = st.text_input("标题")
                                n_core = st.text_area("核心事件")
                            with c2:
                                n_scene = st.text_input("场景")
                                n_action = st.text_area("人物行动")

                            n_add_submit = st.form_submit_button("添加章节")
                            if n_add_submit:
                                if new_ch_key in chapter_data:
                                    st.error(f"{new_ch_key} 已存在！")
                                else:
                                    new_entry = {
                                        "标题": n_title,
                                        "核心事件": n_core,
                                        "场景": n_scene,
                                        "人物行动": n_action,
                                        "伏笔回收": "",
                                        "字数目标": "1500 字左右",
                                    }
                                    chapter_data[new_ch_key] = new_entry
                                    with open(file_path, "w", encoding="utf-8") as f:
                                        yaml.dump(
                                            chapter_data,
                                            f,
                                            allow_unicode=True,
                                            sort_keys=False,
                                        )
                                    st.success(f"已添加 {new_ch_key}")
                                    st.rerun()

    # Tab 4: Chapter Expansion
    with tab4:
        st.header("智能章节扩写")
        st.markdown("选择大纲文件，AI 将自动读取上下文并扩写正文。")

        outline_dir = project_root / "02_Outline"
        if outline_dir.exists():
            outline_files = list(outline_dir.glob("*.yaml"))
            selected_file = st.selectbox(
                "选择大纲文件", [f.name for f in outline_files]
            )

            if selected_file:
                outline_file_path = outline_dir / selected_file
                with open(outline_file_path, "r", encoding="utf-8") as f:
                    chapter_outline = yaml.safe_load(f)

                import re

                chapters = []
                for k in chapter_outline.keys():
                    match = re.search(r"\d+", str(k))
                    if match:
                        chapters.append(int(match.group()))
                chapters.sort()

                if chapters:
                    st.info(f"文件中包含章节：{chapters[0]} - {chapters[-1]}")

                    session_mgr = get_session_manager()
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

                            session_mgr_gui = get_session_manager()

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
                            session_mgr_gui = get_session_manager()
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
                else:
                    st.warning("该文件中未识别到有效章节。")
        else:
            st.error("找不到大纲目录 02_Outline/")

    # Tab 5: Outline Review and Chat
    with tab5:
        st.header("大纲审查与AI对话修改")
        st.markdown("审查大纲一致性、角色弧线、剧情连贯性，并通过AI对话方式优化大纲。")
        
        core_setting_path = project_root / "01_source" / "core_setting.yaml"
        overall_outline_path = project_root / "01_source" / "overall_outline.yaml"
        
        if not core_setting_path.exists() or not overall_outline_path.exists():
            st.error("⚠️ 请先在「设定与整体大纲」标签页中创建核心设定和整体大纲文件。")
        else:
            col_review, col_chat = st.columns([1, 1])
            
            with col_review:
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
                    with st.spinner("正在审查大纲..." if not use_ai else "AI正在深度分析大纲..."):
                        session_manager = SessionManager(str(project_root))
                        config_manager = GenerationConfigManager(str(project_root))
                        api_config = session_manager.get_api_config()
                        
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
                
                if "review_result" in st.session_state:
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
            
            with col_chat:
                st.subheader("💬 AI对话修改")
                
                if not config.get("api_key"):
                    st.warning("⚠️ 请先在左侧边栏配置API密钥")
                else:
                    if "chat_service" not in st.session_state:
                        if st.button("🔄 初始化对话服务"):
                            session_manager = SessionManager(str(project_root))
                            config_manager = GenerationConfigManager(str(project_root))
                            api_config = session_manager.get_api_config()
                            roles_config = config_manager.get_all_roles_config()
                            
                            client = MultiModelClient(api_config)
                            chat_service = OutlineChatService(roles_config.get("refiner", {}), client)
                            
                            if chat_service.load_settings(str(core_setting_path), str(overall_outline_path)):
                                st.session_state["chat_service"] = chat_service
                                st.session_state["chat_messages"] = []
                                st.rerun()
                            else:
                                st.error("初始化对话服务失败")
                    else:
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


if __name__ == "__main__":
    main()
