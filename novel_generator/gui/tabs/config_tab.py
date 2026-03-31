from pathlib import Path
import yaml

import streamlit as st


def render(project_root: Path):
    core_setting_path = project_root / "01_source" / "core_setting.yaml"
    outline_path = project_root / "01_source" / "overall_outline.yaml"
    
    col1, col2 = st.columns(2)
    with col1:
        _render_core_setting(project_root, core_setting_path)
    with col2:
        _render_overall_outline(project_root, outline_path)


def _render_core_setting(project_root: Path, core_setting_path: Path):
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


def _render_overall_outline(project_root: Path, outline_path: Path):
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