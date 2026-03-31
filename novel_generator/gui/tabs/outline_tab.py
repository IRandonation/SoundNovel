from pathlib import Path
import yaml
import re

import streamlit as st


def render(project_root: Path):
    st.header("📋 章节细纲可视化编辑")

    outline_dir = project_root / "02_Outline"
    if not outline_dir.exists():
        st.error("找不到大纲目录 02_Outline/")
        return

    outline_files = list(outline_dir.glob("*.yaml")) + list(
        outline_dir.glob("*.txt")
    )
    
    if not outline_files:
        st.warning("大纲目录中没有找到 YAML 或 TXT 文件")
        return

    selected_file = st.selectbox(
        "选择要编辑的大纲文件",
        [f.name for f in outline_files],
        key="editor_file_select",
    )

    if selected_file:
        _render_editor(outline_dir, selected_file)


def _render_editor(outline_dir: Path, selected_file: str):
    file_path = outline_dir / selected_file

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            chapter_data = yaml.safe_load(f) or {}
    except Exception as e:
        st.error(f"读取文件失败：{e}")
        return

    if not chapter_data:
        st.warning("文件内容为空")
        return

    def get_chapter_num(key):
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