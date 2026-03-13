import streamlit as st
import yaml
import json
import sys
import os
from pathlib import Path
import logging
import time

if getattr(sys, 'frozen', False):
    project_root = Path(sys.executable).parent
else:
    project_root = Path(__file__).parent.resolve()

if not getattr(sys, 'frozen', False):
    sys.path.insert(0, str(project_root))

from novel_generator.core.batch_outline_generator import BatchOutlineGenerator
from novel_generator.core.chapter_expander import ChapterExpander
from novel_generator.core.outline_generator import OutlineGenerator
from novel_generator.config.session import SessionManager
from novel_generator.config.generation_config import GenerationConfigManager


def get_gen_config_manager():
    return GenerationConfigManager(str(project_root))


def load_config():
    session_manager = SessionManager(str(project_root))
    config = session_manager.get_api_config()
    if 'paths' not in config:
        config['paths'] = {}
    config['paths']['project_root'] = str(project_root)
    return config


def get_session_manager():
    return SessionManager(str(project_root))

def main():
    st.set_page_config(page_title="小说创作助手 AI", layout="wide", page_icon="📚")
    
    st.title("📚 小说创作助手 AI (GUI版)")
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
            # Model Provider Selection
            model_provider = st.radio("当前 AI 服务商", ["ZhipuAI (智谱)", "Doubao (豆包)", "DeepSeek"], horizontal=True, 
                                    index=0 if config.get('models', {}).get('default_model_type', 'zhipu') == 'zhipu' else (1 if config.get('models', {}).get('default_model_type', 'doubao') == 'doubao' else 2))
            
            # Map selection back to config value
            provider_map = {"ZhipuAI (智谱)": "zhipu", "Doubao (豆包)": "doubao", "DeepSeek": "deepseek"}
            selected_provider_code = provider_map.get(model_provider, 'zhipu')
            
            # Save if changed
            if config.get('models', {}).get('default_model_type') != selected_provider_code:
                 if 'models' not in config: config['models'] = {}
                 config['models']['default_model_type'] = selected_provider_code
                 # Also update the top-level default_model for MultiModelClient init compatibility if needed
                 config['default_model'] = selected_provider_code
                 with open(project_root / "05_script" / "config.json", 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                 st.rerun()

            st.markdown("---")
            api_key = st.text_input("Zhipu API Key", value=config.get('api_key', ''), type="password")
            doubao_key = st.text_input("Doubao API Key", value=config.get('doubao_api_key', ''), type="password")
            deepseek_key = st.text_input("DeepSeek API Key", value=config.get('deepseek_api_key', ''), type="password")
            
            if st.button("💾 保存 API 密钥"):
                config['api_key'] = api_key
                config['doubao_api_key'] = doubao_key
                config['deepseek_api_key'] = deepseek_key
                with open(project_root / "05_script" / "config.json", 'w', encoding='utf-8') as f:
                    json.dump(config, f, indent=4, ensure_ascii=False)
                st.success("API 密钥已保存")

        # Model Configuration
        with st.expander("🤖 模型配置", expanded=False):
            model_config_tab1, model_config_tab2, model_config_tab3 = st.tabs(["智谱AI", "豆包(Doubao)", "DeepSeek"])
            
            with model_config_tab1:
                # Default Models if not in config
                default_zhipu_models = {
                    "logic_analysis_model": "glm-4-long",
                    "major_chapters_model": "glm-4-long",
                    "sub_chapters_model": "glm-4-long",
                    "expansion_model": "glm-4.5-flash",
                    "default_model": "glm-4.5-flash"
                }
                
                # Ensure 'models' dict exists
                if 'models' not in config:
                    config['models'] = default_zhipu_models.copy()
                
                current_models = config['models']
                
                st.caption("配置各阶段使用的模型名称")
                
                new_logic = st.text_input("逻辑分析模型", value=current_models.get("logic_analysis_model", "glm-4-long"), help="用于分析长文本逻辑")
                new_major = st.text_input("大纲生成模型 (主)", value=current_models.get("major_chapters_model", "glm-4-long"), help="用于生成主要大纲")
                new_sub = st.text_input("大纲生成模型 (副)", value=current_models.get("sub_chapters_model", "glm-4-long"), help="用于生成细分大纲")
                new_exp = st.text_input("章节扩写模型", value=current_models.get("expansion_model", "glm-4.5-flash"), help="用于正文扩写")
                new_def = st.text_input("默认模型", value=current_models.get("default_model", "glm-4.5-flash"), help="其他默认任务")
                
                if st.button("💾 保存智谱配置"):
                    config['models']['logic_analysis_model'] = new_logic
                    config['models']['major_chapters_model'] = new_major
                    config['models']['sub_chapters_model'] = new_sub
                    config['models']['expansion_model'] = new_exp
                    config['models']['default_model'] = new_def
                    
                    with open(project_root / "05_script" / "config.json", 'w', encoding='utf-8') as f:
                        json.dump(config, f, indent=4, ensure_ascii=False)
                    st.success("智谱模型配置已保存")

            with model_config_tab2:
                st.caption("配置豆包 Endpoint ID (形如 ep-2024...)")
                
                # Default Doubao Models
                default_doubao_models = {
                    "logic_analysis_model": "ep-20241210233657-lz8fv",
                    "major_chapters_model": "ep-20241210233657-lz8fv",
                    "sub_chapters_model": "ep-20241210233657-lz8fv",
                    "expansion_model": "ep-20241210233657-lz8fv",
                    "default_model": "ep-20241210233657-lz8fv"
                }

                if 'doubao_models' not in config:
                    config['doubao_models'] = default_doubao_models.copy()
                
                current_doubao = config['doubao_models']
                
                # Simplified configuration: One Endpoint ID for all, or individual
                use_single_endpoint = st.checkbox("使用统一的 Endpoint ID", value=True)
                
                if use_single_endpoint:
                    # Use default_model as the representative
                    common_endpoint = st.text_input("Endpoint ID", value=current_doubao.get("default_model", ""))
                    if st.button("💾 保存豆包配置"):
                        for k in current_doubao.keys():
                            current_doubao[k] = common_endpoint
                        config['doubao_models'] = current_doubao
                        with open(project_root / "05_script" / "config.json", 'w', encoding='utf-8') as f:
                            json.dump(config, f, indent=4, ensure_ascii=False)
                        st.success("豆包配置已保存")
                else:
                    d_new_logic = st.text_input("逻辑分析 Endpoint", value=current_doubao.get("logic_analysis_model", ""))
                    d_new_major = st.text_input("大纲生成 Endpoint", value=current_doubao.get("major_chapters_model", ""))
                    d_new_sub = st.text_input("细分大纲 Endpoint", value=current_doubao.get("sub_chapters_model", ""))
                    d_new_exp = st.text_input("章节扩写 Endpoint", value=current_doubao.get("expansion_model", ""))
                    d_new_def = st.text_input("默认 Endpoint", value=current_doubao.get("default_model", ""))
                    
                    if st.button("💾 保存豆包配置", key="save_doubao_detailed"):
                        config['doubao_models']['logic_analysis_model'] = d_new_logic
                        config['doubao_models']['major_chapters_model'] = d_new_major
                        config['doubao_models']['sub_chapters_model'] = d_new_sub
                        config['doubao_models']['expansion_model'] = d_new_exp
                        config['doubao_models']['default_model'] = d_new_def
                        
                        with open(project_root / "05_script" / "config.json", 'w', encoding='utf-8') as f:
                            json.dump(config, f, indent=4, ensure_ascii=False)
                        st.success("豆包配置已保存")

            with model_config_tab3:
                st.caption("配置 DeepSeek 模型")
                
                default_deepseek_models = {
                    "logic_analysis_model": "deepseek-chat",
                    "major_chapters_model": "deepseek-chat",
                    "sub_chapters_model": "deepseek-chat",
                    "expansion_model": "deepseek-chat",
                    "default_model": "deepseek-chat"
                }

                if 'deepseek_models' not in config:
                    config['deepseek_models'] = default_deepseek_models.copy()
                
                current_deepseek = config['deepseek_models']
                
                use_single_deepseek_model = st.checkbox("使用统一的模型名称", value=True, key="deepseek_single")
                
                if use_single_deepseek_model:
                    common_model = st.text_input("模型名称", value=current_deepseek.get("default_model", "deepseek-chat"), 
                                                help="如: deepseek-chat, deepseek-coder")
                    if st.button("💾 保存DeepSeek配置"):
                        for k in current_deepseek.keys():
                            current_deepseek[k] = common_model
                        config['deepseek_models'] = current_deepseek
                        with open(project_root / "05_script" / "config.json", 'w', encoding='utf-8') as f:
                            json.dump(config, f, indent=4, ensure_ascii=False)
                        st.success("DeepSeek配置已保存")
                else:
                    ds_new_logic = st.text_input("逻辑分析模型", value=current_deepseek.get("logic_analysis_model", "deepseek-chat"))
                    ds_new_major = st.text_input("大纲生成模型", value=current_deepseek.get("major_chapters_model", "deepseek-chat"))
                    ds_new_sub = st.text_input("细分大纲模型", value=current_deepseek.get("sub_chapters_model", "deepseek-chat"))
                    ds_new_exp = st.text_input("章节扩写模型", value=current_deepseek.get("expansion_model", "deepseek-chat"))
                    ds_new_def = st.text_input("默认模型", value=current_deepseek.get("default_model", "deepseek-chat"))
                    
                    if st.button("💾 保存DeepSeek配置", key="save_deepseek_detailed"):
                        config['deepseek_models']['logic_analysis_model'] = ds_new_logic
                        config['deepseek_models']['major_chapters_model'] = ds_new_major
                        config['deepseek_models']['sub_chapters_model'] = ds_new_sub
                        config['deepseek_models']['expansion_model'] = ds_new_exp
                        config['deepseek_models']['default_model'] = ds_new_def
                        
                        with open(project_root / "05_script" / "config.json", 'w', encoding='utf-8') as f:
                            json.dump(config, f, indent=4, ensure_ascii=False)
                        st.success("DeepSeek配置已保存")

            
            st.markdown("---")
            if st.button("🧪 测试模型连接", help="测试当前配置的 API Key 和模型是否可用"):
                try:
                    with st.spinner("正在连接模型服务器..."):
                        client = MultiModelClient(config)
                        results = client.test_all_connections()
                        
                        has_success = False
                        for model_type, success in results.items():
                            if success:
                                st.success(f"✅ {model_type} 服务连接成功")
                                has_success = True
                            else:
                                st.error(f"❌ {model_type} 服务连接失败")
                        
                        if not has_success:
                            st.warning("⚠️ 没有可用的模型服务，请检查 API Key 和网络设置。")
                            
                except Exception as e:
                    st.error(f"测试过程发生错误: {str(e)}")

        with st.expander("AI角色配置", expanded=False):
            st.caption("为不同AI角色配置专用模型")
            
            gen_config_mgr = get_gen_config_manager()
            
            gen_config = gen_config_mgr.get_generation_config()
            st.subheader("生成流程参数")
            col_a, col_b = st.columns(2)
            with col_a:
                max_iterations = st.number_input(
                    "最大润色迭代次数",
                    min_value=1, max_value=10,
                    value=gen_config.get('max_refine_iterations', 3),
                    key="max_refine_iterations"
                )
                context_chapters = st.number_input(
                    "上下文章节数",
                    min_value=1, max_value=20,
                    value=gen_config.get('context_chapters', 10),
                    key="context_chapters"
                )
            with col_b:
                pass_score = st.number_input(
                    "评审通过分数",
                    min_value=0, max_value=100,
                    value=gen_config.get('pass_score_threshold', 70),
                    key="pass_score_threshold"
                )
                default_words = st.number_input(
                    "默认字数目标",
                    min_value=500, max_value=5000,
                    value=gen_config.get('default_word_count', 1500),
                    step=100,
                    key="default_word_count"
                )
            
            if st.button("保存生成流程参数"):
                gen_config_mgr.set_generation_config(
                    max_refine_iterations=max_iterations,
                    pass_score_threshold=pass_score,
                    context_chapters=context_chapters,
                    default_word_count=default_words
                )
                st.success("生成流程参数已保存")
            
            st.markdown("---")
            
            st.subheader("角色模型配置")
            
            role_names = {
                "generator": "生成者 (Generator)",
                "reviewer": "评审者 (Reviewer)", 
                "refiner": "润色者 (Refiner)"
            }
            
            role_descriptions = {
                "generator": "负责大纲生成、章节扩写等创作任务",
                "reviewer": "负责质量检查、一致性检查等评审任务",
                "refiner": "负责内容润色、修复问题等优化任务"
            }
            
            providers = gen_config_mgr.get_all_providers()
            provider_options = list(providers.keys())
            
            role_tabs = st.tabs(["生成者", "评审者", "润色者"])
            
            for idx, (role_key, role_name) in enumerate(role_names.items()):
                with role_tabs[idx]:
                    st.caption(role_descriptions[role_key])
                    
                    role_config = gen_config_mgr.get_role_config(role_key)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        current_provider = role_config.get('provider', 'zhipu')
                        provider_idx = provider_options.index(current_provider) if current_provider in provider_options else 0
                        new_provider = st.selectbox(
                            "服务商",
                            provider_options,
                            index=provider_idx,
                            format_func=lambda x: providers.get(x, x),
                            key=f"role_{role_key}_provider"
                        )
                    
                    with col2:
                        models = gen_config_mgr.get_provider_models(new_provider)
                        default_model = models[0] if models else ""
                        new_model = st.text_input(
                            "模型名称",
                            value=role_config.get('model', default_model),
                            key=f"role_{role_key}_model"
                        )
                    
                    col3, col4 = st.columns(2)
                    with col3:
                        new_temp = st.slider(
                            "Temperature",
                            min_value=0.0,
                            max_value=1.0,
                            value=float(role_config.get('temperature', 0.7)),
                            step=0.1,
                            key=f"role_{role_key}_temp"
                        )
                    with col4:
                        new_enabled = st.checkbox(
                            "启用此角色",
                            value=role_config.get('enabled', True),
                            key=f"role_{role_key}_enabled"
                        )
                    
                    new_max_tokens = st.number_input(
                        "Max Tokens",
                        min_value=1000,
                        max_value=32000,
                        value=int(role_config.get('max_tokens', 8000)),
                        step=500,
                        key=f"role_{role_key}_max_tokens"
                    )
                    
                    if st.button(f"保存{role_name}配置", key=f"save_role_{role_key}"):
                        gen_config_mgr.set_role_config(
                            role_name=role_key,
                            provider=new_provider,
                            model=new_model,
                            temperature=new_temp,
                            max_tokens=new_max_tokens,
                            enabled=new_enabled
                        )
                        st.success(f"{role_name}配置已保存")
            
            st.markdown("---")
            st.caption("提示：生成者使用较高temperature增加创意，评审者使用较低temperature提高精确度")

        with st.expander("🚀 项目初始化", expanded=False):
            st.caption("配置 API 连接并测试")
            
            init_provider = st.selectbox(
                "选择服务商",
                ["智谱 AI (ZhipuAI)", "豆包 (Doubao)", "DeepSeek"],
                key="init_provider_select"
            )
            
            if "智谱" in init_provider:
                init_api_key = st.text_input("API Key", type="password", key="init_zhipu_key")
                init_api_url = st.text_input(
                    "API 地址（可选）",
                    value="https://open.bigmodel.cn/api/paas/v4",
                    key="init_zhipu_url"
                )
                init_endpoint = None
            elif "豆包" in init_provider:
                init_api_key = st.text_input("API Key", type="password", key="init_doubao_key")
                init_api_url = st.text_input(
                    "API 地址（可选）",
                    value="https://ark.cn-beijing.volces.com/api/v3",
                    key="init_doubao_url"
                )
                init_endpoint = st.text_input(
                    "模型名称", 
                    key="init_doubao_endpoint", 
                    placeholder="doubao-1-5-lite-32k-250115 或 ep-2024xxxx",
                    help="支持直接模型名（如 doubao-1-5-lite-32k-250115）或 Endpoint ID（如 ep-2024xxxx）"
                )
            else:  # DeepSeek
                init_api_key = st.text_input("API Key", type="password", key="init_deepseek_key")
                init_api_url = st.text_input(
                    "API 地址（可选）",
                    value="https://api.deepseek.com",
                    key="init_deepseek_url"
                )
                init_endpoint = None
            
            if st.button("💾 保存并测试连接", key="init_save_test"):
                if not init_api_key:
                    st.error("请输入 API Key")
                else:
                    with st.spinner("正在测试连接..."):
                        from novel_generator.core.project_manager import ProjectManager
                        manager = ProjectManager(str(project_root))
                        
                        if "智谱" in init_provider:
                            provider_code = "zhipu"
                        elif "豆包" in init_provider:
                            provider_code = "doubao"
                        else:
                            provider_code = "deepseek"
                        
                        success, message = manager.update_api_config(
                            provider=provider_code,
                            api_key=init_api_key,
                            api_url=init_api_url if init_api_url else None,
                            endpoint=init_endpoint
                        )
                        
                        if success:
                            st.success(f"✅ {message}")
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")

        with st.expander("📊 项目状态", expanded=False):
            session_mgr = get_session_manager()
            status = session_mgr.get_status_summary()
            
            provider_names = {"zhipu": "智谱 AI", "doubao": "豆包", "ark": "Ark", "deepseek": "DeepSeek"}
            
            st.caption(f"项目: {status['project_name']}")
            
            col_s1, col_s2 = st.columns(2)
            with col_s1:
                st.metric("大纲进度", f"{status['last_outline']} 章")
            with col_s2:
                st.metric("草稿进度", f"{status['last_draft']} 章")
            
            if status['total_chapters'] > 0:
                progress = status['last_draft'] / status['total_chapters']
                st.progress(progress, text=f"总进度: {status['last_draft']}/{status['total_chapters']} ({progress*100:.1f}%)")
            
            st.caption(f"服务商: {provider_names.get(status['api_provider'], status['api_provider'])}")
            
            if st.button("🔄 同步文件状态", help="从实际文件检测最新进度"):
                session_mgr.sync_with_files()
                st.rerun()

        st.info(f"当前工作目录: {project_root}")

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📝 设定与整体大纲", "⛓️ 批量大纲生成", "📋 章节细纲编辑", "✍️ 章节智能扩写"])

    # --- Tab 1: 设定与整体大纲 ---
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("核心设定 (Core Setting)")
            core_setting_path = project_root / "01_source" / "core_setting.yaml"
            
            if core_setting_path.exists():
                # Initialize Session State for Core Setting
                if 'core_setting_data' not in st.session_state:
                    try:
                        logging.info(f"Loading core setting from {core_setting_path}")
                        with open(core_setting_path, 'r', encoding='utf-8') as f:
                            st.session_state.core_setting_data = yaml.safe_load(f) or {}
                    except Exception as e:
                        st.error(f"解析核心设定出错: {e}")
                        st.session_state.core_setting_data = {}
                
                # Use reference to session state data
                core_data = st.session_state.core_setting_data

                # Reload Button (in case file changed externally)
                if st.button("🔄 从文件重载", help="放弃当前未保存的修改，重新读取文件"):
                    logging.info("Reloading core setting from file...")
                    try:
                        with open(core_setting_path, 'r', encoding='utf-8') as f:
                            st.session_state.core_setting_data = yaml.safe_load(f) or {}
                        st.toast("已重载文件", icon="🔄")
                        st.rerun()
                    except Exception as e:
                        st.error(f"重载失败: {e}")

                # ---------------------------------------------------------
                # 1. 基础/必填设定 (Basic / Required)
                # ---------------------------------------------------------
                with st.expander("🌍 世界观与核心 (必填)", expanded=True):
                    st.caption("这是生成小说的基石，请务必详细填写。")
                    
                    # World View
                    c_world = core_data.get('世界观', '')
                    new_world = st.text_area("世界观 (World View)", value=c_world, height=150, 
                                           help="必填。描述故事背景、世界规则、力量体系等。")
                    if new_world != c_world:
                        core_data['世界观'] = new_world

                    # Core Conflict
                    c_conflict = core_data.get('核心冲突', '')
                    new_conflict = st.text_area("核心冲突 (Core Conflict)", value=c_conflict, height=100,
                                              help="必填。主线矛盾、主角的核心目标。")
                    if new_conflict != c_conflict:
                        core_data['核心冲突'] = new_conflict

                # ---------------------------------------------------------
                # 2. 人物小传 (Characters)
                # ---------------------------------------------------------
                with st.expander("👥 人物小传 (Characters)", expanded=False):
                    characters = core_data.get('人物小传', {})
                    if not isinstance(characters, dict):
                        characters = {}
                        core_data['人物小传'] = characters
                    
                    # Character Tabs/Selector
                    char_names = list(characters.keys())
                    
                    # Add Character UI
                    c_col1, c_col2 = st.columns([3, 1])
                    with c_col2:
                         if st.button("➕ 新增人物"):
                             new_key = f"新角色_{len(char_names)+1}"
                             logging.info(f"Adding new character: {new_key}")
                             characters[new_key] = {"身份": "", "性格": "", "核心动机": ""}
                             # Force update session state (though reference should handle it, explicit is better)
                             st.session_state.core_setting_data['人物小传'] = characters
                             st.rerun()
                    
                    if char_names:
                        selected_char = st.selectbox("选择编辑角色", char_names, key="char_select")
                        
                        if selected_char:
                            st.markdown(f"### ✏️ 编辑: {selected_char}")
                            char_info = characters[selected_char]
                            if not isinstance(char_info, dict):
                                char_info = {}
                                characters[selected_char] = char_info
                            
                            # 1. 角色重命名 (Key)
                            col_rename, col_delete = st.columns([4, 1])
                            with col_rename:
                                new_char_name = st.text_input("📝 角色名称 (Key/ID)", value=selected_char, help="修改此项将改变角色在数据中的唯一标识（如：主角、配角1）")
                            with col_delete:
                                st.write("") # Spacer
                                st.write("")
                                if st.button("🗑️ 删除此人", key=f"del_char_btn_{selected_char}", type="primary"):
                                    logging.info(f"Deleting character: {selected_char}")
                                    del characters[selected_char]
                                    st.session_state.core_setting_data['人物小传'] = characters
                                    st.rerun()

                            if new_char_name != selected_char:
                                if new_char_name in characters:
                                    st.error(f"角色名 '{new_char_name}' 已存在，请换一个名字。")
                                else:
                                    logging.info(f"Renaming character {selected_char} to {new_char_name}")
                                    characters[new_char_name] = characters.pop(selected_char)
                                    st.session_state.core_setting_data['人物小传'] = characters
                                    st.rerun()

                            # 2. 核心属性编辑
                            st.markdown("#### 核心属性")

                            # Role Type
                            role_options = ["主角", "主要配角", "次要配角", "反派", "龙套/路人"]
                            current_role = char_info.get('角色类型', '主角')
                            if current_role not in role_options:
                                role_options.append(current_role) # Handle custom existing values
                            
                            c_role_type = st.selectbox("🏷️ 角色类型", role_options, index=role_options.index(current_role) if current_role in role_options else 0)
                            if c_role_type != char_info.get('角色类型', ''):
                                char_info['角色类型'] = c_role_type
                                characters[selected_char] = char_info
                            
                            # Identity
                            c_identity = st.text_input("🎭 身份", value=char_info.get('身份', ''), placeholder="例如：高中生、异能者")
                            if c_identity != char_info.get('身份', ''):
                                char_info['身份'] = c_identity
                                characters[selected_char] = char_info # Ensure update

                            # Personality
                            c_personality = st.text_input("🧠 性格", value=char_info.get('性格', ''), placeholder="例如：冷酷、热血、腹黑")
                            if c_personality != char_info.get('性格', ''):
                                char_info['性格'] = c_personality
                                characters[selected_char] = char_info

                            # Motivation
                            c_motivation = st.text_area("🎯 核心动机", value=char_info.get('核心动机', ''), placeholder="例如：为了复仇、为了守护世界")
                            if c_motivation != char_info.get('核心动机', ''):
                                char_info['核心动机'] = c_motivation
                                characters[selected_char] = char_info
                            
                            # Custom Fields for Character
                            st.markdown("---")
                            st.caption("其他特征 (选填)")
                            for k, v in list(char_info.items()):
                                if k not in ['身份', '性格', '核心动机']:
                                    c1, c2 = st.columns([3, 1])
                                    with c1:
                                        new_v = st.text_input(f"{k}", value=str(v))
                                        if new_v != str(v):
                                            char_info[k] = new_v
                                    with c2:
                                        if st.button("🗑️", key=f"del_{selected_char}_{k}"):
                                            logging.info(f"Deleting feature {k} from {selected_char}")
                                            del char_info[k]
                                            st.rerun()
                            
                            # Add Custom Field
                            with st.popover("➕ 添加特征"):
                                new_field_key = st.text_input("特征名 (如: 外貌)")
                                if st.button("确认添加", key=f"add_field_{selected_char}"):
                                    if new_field_key:
                                        logging.info(f"Adding feature {new_field_key} to {selected_char}")
                                        char_info[new_field_key] = ""
                                        st.rerun()
                            
                            # Ensure char_info updates in main dict
                            characters[selected_char] = char_info
                    
                    core_data['人物小传'] = characters

                # ---------------------------------------------------------
                # 3. 伏笔与悬念 (Foreshadowing)
                # ---------------------------------------------------------
                with st.expander("🕵️ 伏笔清单 (Foreshadowing)", expanded=False):
                    foreshadowing = core_data.get('伏笔清单', [])
                    if isinstance(foreshadowing, str): # Handle legacy text format
                         foreshadowing = [line.strip().lstrip('-').strip() for line in foreshadowing.split('\n') if line.strip()]
                    
                    if not isinstance(foreshadowing, list):
                        foreshadowing = []
                        core_data['伏笔清单'] = foreshadowing
                    
                    # Editable List
                    new_foreshadowing = []
                    for i, item in enumerate(foreshadowing):
                        col_f1, col_f2 = st.columns([9, 1])
                        with col_f1:
                            val = st.text_input(f"伏笔 {i+1}", value=str(item), key=f"fs_{i}")
                            new_foreshadowing.append(val)
                        with col_f2:
                            if st.button("✖️", key=f"del_fs_{i}"):
                                logging.info(f"Deleting foreshadowing item {i}")
                                foreshadowing.pop(i)
                                core_data['伏笔清单'] = foreshadowing
                                st.rerun()
                    
                    # Update with edited values (if not deleted)
                    if len(new_foreshadowing) == len(foreshadowing):
                        core_data['伏笔清单'] = new_foreshadowing

                    if st.button("➕ 添加伏笔"):
                        logging.info("Adding new foreshadowing item")
                        core_data['伏笔清单'].append("")
                        st.rerun()

                # ---------------------------------------------------------
                # 4. 补充/约束设定 (Optional Constraints)
                # ---------------------------------------------------------
                with st.expander("✨ 补充与约束设定 (选填)", expanded=False):
                    st.caption("在此添加额外的约束条件，确保AI生成符合预期。")
                    
                    optional_fields = {
                        '风格基调': '如：暗黑、幽默、严肃',
                        '力量体系': '详细的等级划分',
                        '地理环境': '重要地点描述',
                        '特殊禁忌': '绝对不能出现的情节或设定'
                    }
                    
                    # Existing optional fields
                    for key in list(core_data.keys()):
                        if key not in ['世界观', '核心冲突', '人物小传', '伏笔清单']:
                            col_o1, col_o2 = st.columns([9, 1])
                            with col_o1:
                                val = st.text_area(key, value=str(core_data[key]), height=80)
                                if val != str(core_data[key]):
                                    core_data[key] = val
                            with col_o2:
                                if st.button("🗑️", key=f"del_opt_{key}"):
                                    logging.info(f"Deleting optional field {key}")
                                    del core_data[key]
                                    st.rerun()

                    # Add new optional field
                    selected_opt = st.selectbox("选择或输入要添加的设定项", 
                                              list(optional_fields.keys()) + ["(自定义)"],
                                              index=None,
                                              placeholder="选择要添加的约束项...")
                    
                    if selected_opt:
                        if selected_opt == "(自定义)":
                            custom_key = st.text_input("输入自定义设定名称")
                            if st.button("添加自定义项") and custom_key:
                                if custom_key not in core_data:
                                    logging.info(f"Adding custom field {custom_key}")
                                    core_data[custom_key] = ""
                                    st.rerun()
                        elif selected_opt not in core_data:
                            if st.button(f"添加【{selected_opt}】"):
                                logging.info(f"Adding optional field {selected_opt}")
                                core_data[selected_opt] = ""
                                st.rerun()

                # Save Button (Main)
                if st.button("💾 保存核心设定", type="primary", use_container_width=True):
                    logging.info("Saving core setting to file...")
                    with open(core_setting_path, 'w', encoding='utf-8') as f:
                        yaml.dump(core_data, f, allow_unicode=True, sort_keys=False)
                    st.success("核心设定已保存！")

            else:
                st.warning(f"文件不存在: {core_setting_path}")

        with col2:
            st.subheader("整体大纲 (Overall Outline)")
            outline_path = project_root / "01_source" / "overall_outline.yaml"
            if outline_path.exists():
                # Load as dict for structured editing
                try:
                    with open(outline_path, 'r', encoding='utf-8') as f:
                        overall_data = yaml.safe_load(f) or {}
                    
                    st.info("💡 点击下方卡片展开编辑各项内容")
                    
                    # Editable container
                    new_overall_data = {}
                    
                    # Iterate through existing keys to maintain order
                    for key, value in overall_data.items():
                        with st.expander(f"📌 {key}", expanded=False):
                            if isinstance(value, list):
                                # List editor
                                value_str = "\n".join([f"- {v}" for v in value]) if value else ""
                                new_val_str = st.text_area(f"{key} 内容", value=value_str, height=100, help="每行一项，以 - 开头")
                                # Parse back to list
                                new_val = [line.strip().lstrip('-').strip() for line in new_val_str.split('\n') if line.strip()]
                                new_overall_data[key] = new_val
                            else:
                                # String editor
                                new_val = st.text_area(f"{key} 内容", value=str(value) if value else "", height=100)
                                new_overall_data[key] = new_val
                    
                    # Add new item section
                    with st.expander("➕ 添加新条目"):
                        new_key = st.text_input("新条目名称 (如: 第四幕)")
                        new_value = st.text_area("新条目内容")
                        if new_key:
                            new_overall_data[new_key] = new_value

                    if st.button("💾 保存整体大纲"):
                        with open(outline_path, 'w', encoding='utf-8') as f:
                            yaml.dump(new_overall_data, f, allow_unicode=True, sort_keys=False)
                        st.success("整体大纲已保存")
                        st.rerun()
                        
                except Exception as e:
                    st.error(f"解析整体大纲出错: {e}")
                    # Fallback to raw text editor
                    with open(outline_path, 'r', encoding='utf-8') as f:
                        raw_content = f.read()
                    st.warning("切换到纯文本编辑模式")
                    new_raw = st.text_area("编辑整体大纲 (Raw)", raw_content, height=500)
                    if st.button("💾 保存整体大纲 (Raw)"):
                        with open(outline_path, 'w', encoding='utf-8') as f:
                            f.write(new_raw)
                        st.success("已保存")
            else:
                st.warning(f"文件不存在: {outline_path}")

    # --- Tab 2: 批量大纲生成 ---
    with tab2:
        st.header("批量生成章节大纲")
        st.markdown("基于核心设定和整体大纲，使用 AI 拆分生成详细的章节细纲。")
        
        # Check API Key first
        if not config.get('api_key'):
            st.error("⚠️ 未配置 Zhipu API Key！请先在左侧侧边栏设置 API 密钥。")
        
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            total_chapters = st.number_input("预计总章节数", value=100, step=10, help="全书预计的总章节数，用于计算进度和规划")
        with col_g2:
            batch_size = st.number_input("每批次生成数量", value=5, min_value=1, max_value=20, help="减少批次大小可以降低超时风险")
        
        # Range Selection
        st.markdown("#### 🎯 生成范围")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            start_gen_ch = st.number_input("起始章节", value=1, min_value=1, max_value=total_chapters)
        with col_r2:
            end_gen_ch = st.number_input("结束章节", value=min(20, total_chapters), min_value=1, max_value=total_chapters)
            
        if start_gen_ch > end_gen_ch:
            st.error("起始章节不能大于结束章节")
             
        if st.button("🚀 开始生成大纲", disabled=not config.get('api_key') or start_gen_ch > end_gen_ch):
            
            # Progress Bar and Status
            progress_bar = st.progress(0)
            status_text = st.empty()
            log_area = st.empty() # For logs
            
            def update_progress(current, total, message):
                percent = min(current / total, 1.0) if total > 0 else 0
                progress_bar.progress(percent)
                status_text.text(f"[{int(percent*100)}%] {message}")

            with st.spinner("正在初始化生成任务..."):
                try:
                    # Reload latest data
                    with open(core_setting_path, 'r', encoding='utf-8') as f:
                        core_setting = yaml.safe_load(f)
                    with open(outline_path, 'r', encoding='utf-8') as f:
                        overall_outline = yaml.safe_load(f)
                    
                    # Capture logs
                    class StreamlitLogHandler(logging.Handler):
                        def emit(self, record):
                            msg = self.format(record)
                            # Append to log area
                            current_logs = st.session_state.get('gen_logs', [])
                            current_logs.append(msg)
                            st.session_state['gen_logs'] = current_logs
                            log_area.code("\n".join(current_logs[-10:])) # Show last 10 lines

                    st.session_state['gen_logs'] = []
                    logger = logging.getLogger()
                    handler = StreamlitLogHandler()
                    logger.addHandler(handler)
                    
                    generator = BatchOutlineGenerator(config)
                    result = generator.generate_batch_outline(
                        core_setting, overall_outline, 
                        total_chapters=total_chapters, 
                        batch_size=batch_size,
                        start_chapter_idx=start_gen_ch,
                        end_chapter_idx=end_gen_ch,
                        progress_callback=update_progress
                    )
                    
                    # Remove handler
                    logger.removeHandler(handler)

                    # Save
                    outline_dir = project_root / "02_outline"
                    outline_dir.mkdir(exist_ok=True)
                    output_filename = f"chapter_outline_{start_gen_ch:03d}-{end_gen_ch:03d}.yaml"
                    output_path = outline_dir / output_filename
                    generator.save_batch_outline(result, str(output_path))
                    
                    status_text.success(f"✅ 大纲生成成功！已保存至: {output_filename}")
                    st.json(result)
                            
                except Exception as e:
                    status_text.error(f"❌ 生成失败: {str(e)}")
                    # Show full error details if available
                    if hasattr(e, 'response') and e.response:
                        st.error(f"API 响应内容: {e.response.text}")
                    logging.exception(e)

    # --- Tab 3: 章节细纲编辑 (New) ---
    with tab3:
        st.header("📋 章节细纲可视化编辑")
        
        outline_dir = project_root / "02_outline"
        if outline_dir.exists():
            outline_files = list(outline_dir.glob("*.yaml")) + list(outline_dir.glob("*.txt"))
            selected_file = st.selectbox("选择要编辑的大纲文件", [f.name for f in outline_files], key="editor_file_select")
            
            if selected_file:
                file_path = outline_dir / selected_file
                
                # Load data
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        # Handle potential duplicate keys or custom format if needed, but standard yaml should work
                        chapter_data = yaml.safe_load(f) or {}
                except Exception as e:
                    st.error(f"读取文件失败: {e}")
                    chapter_data = {}

                if chapter_data:
                    # Sort chapters
                    def get_chapter_num(key):
                        import re
                        match = re.search(r'\d+', str(key))
                        return int(match.group()) if match else 9999
                    
                    sorted_keys = sorted(chapter_data.keys(), key=get_chapter_num)
                    
                    # Main Editor Form
                    with st.form("chapter_editor_form"):
                        st.info("💡 修改下方卡片内容后，点击底部的【保存修改】按钮生效")
                        
                        updated_data = {}
                        
                        # Display cards
                        for key in sorted_keys:
                            details = chapter_data[key]
                            with st.expander(f"📄 {key}: {details.get('标题', '无标题')}", expanded=False):
                                col_a, col_b = st.columns(2)
                                
                                # Prepare current values
                                c_title = details.get('标题', '')
                                c_core = details.get('核心事件', '')
                                c_scene = details.get('场景', '')
                                c_action = details.get('人物行动', '')
                                c_foreshadow = details.get('伏笔回收', '')
                                c_word_count = details.get('字数目标', '1500字左右')
                                
                                with col_a:
                                    new_title = st.text_input(f"标题 ({key})", value=c_title)
                                    new_core = st.text_area(f"核心事件 ({key})", value=c_core, height=100)
                                    new_scene = st.text_area(f"场景 ({key})", value=c_scene, height=80)
                                
                                with col_b:
                                    new_word_count = st.text_input(f"字数目标 ({key})", value=c_word_count)
                                    new_action = st.text_area(f"人物行动 ({key})", value=c_action, height=100)
                                    new_foreshadow = st.text_area(f"伏笔回收 ({key})", value=c_foreshadow, height=80)
                                
                                # Store updated values
                                updated_data[key] = {
                                    '标题': new_title,
                                    '核心事件': new_core,
                                    '场景': new_scene,
                                    '人物行动': new_action,
                                    '伏笔回收': new_foreshadow,
                                    '字数目标': new_word_count
                                }
                        
                        # Save Button
                        submitted = st.form_submit_button("💾 保存所有修改")
                        if submitted:
                            with open(file_path, 'w', encoding='utf-8') as f:
                                yaml.dump(updated_data, f, allow_unicode=True, sort_keys=False)
                            st.success(f"已保存到 {selected_file}")
                            st.rerun()

                    # Add New Chapter Section (Outside Form)
                    with st.expander("➕ 添加新章节"):
                        with st.form("add_chapter_form"):
                            new_ch_num = st.number_input("新章节号", min_value=1, value=len(sorted_keys)+1)
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
                                        '标题': n_title,
                                        '核心事件': n_core,
                                        '场景': n_scene,
                                        '人物行动': n_action,
                                        '伏笔回收': '',
                                        '字数目标': '1500字左右'
                                    }
                                    chapter_data[new_ch_key] = new_entry
                                    # Save immediately
                                    with open(file_path, 'w', encoding='utf-8') as f:
                                        yaml.dump(chapter_data, f, allow_unicode=True, sort_keys=False)
                                    st.success(f"已添加 {new_ch_key}")
                                    st.rerun()

    # --- Tab 4: 章节扩写 ---
    with tab4:
        st.header("智能章节扩写")
        st.markdown("选择大纲文件，AI 将自动读取上下文并扩写正文。")
        
        outline_dir = project_root / "02_outline"
        if outline_dir.exists():
            outline_files = list(outline_dir.glob("*.yaml"))
            selected_file = st.selectbox("选择大纲文件", [f.name for f in outline_files])
            
            if selected_file:
                outline_file_path = outline_dir / selected_file
                with open(outline_file_path, 'r', encoding='utf-8') as f:
                    chapter_outline = yaml.safe_load(f)
                
                # Parse chapter numbers
                chapters = []
                for k in chapter_outline.keys():
                    # Support "第1章" or "1" format
                    import re
                    match = re.search(r'\d+', str(k))
                    if match:
                        chapters.append(int(match.group()))
                chapters.sort()
                
                if chapters:
                    st.info(f"文件中包含章节: {chapters[0]} - {chapters[-1]}")
                    
                    session_mgr = get_session_manager()
                    continue_info = session_mgr.get_continue_info("draft")
                    
                    if continue_info["can_continue"]:
                        st.success(f"📍 检测到上次进度: 已完成第 {continue_info['last_chapter']} 章")
                        
                        col_cont1, col_cont2 = st.columns(2)
                        with col_cont1:
                            if st.button("🔄 一键续写", type="primary", key="quick_continue_btn"):
                                st.session_state['quick_continue_mode'] = True
                                st.session_state['continue_start'] = continue_info['next_chapter']
                                st.session_state['continue_end'] = continue_info['total_chapters'] if continue_info['total_chapters'] > 0 else chapters[-1]
                                st.rerun()
                        with col_cont2:
                            if st.button("📝 手动选择范围", key="manual_select_btn"):
                                st.session_state['quick_continue_mode'] = False
                                st.rerun()
                    
                    if st.session_state.get('quick_continue_mode'):
                        start_ch = st.session_state.get('continue_start', chapters[0])
                        end_ch = st.session_state.get('continue_end', chapters[-1])
                        st.info(f"续写范围: 第 {start_ch} 章 - 第 {end_ch} 章")
                        
                        if st.button("❌ 取消续写", key="cancel_continue"):
                            st.session_state['quick_continue_mode'] = False
                            st.rerun()
                    else:
                        c1, c2 = st.columns(2)
                        with c1:
                            start_ch = st.number_input("起始章节", value=chapters[0], min_value=chapters[0], max_value=chapters[-1])
                        with c2:
                            end_ch = st.number_input("结束章节", value=chapters[0], min_value=chapters[0], max_value=chapters[-1])
                    
                    # 结果展示区（位于按钮下方）
                    if 'last_generated_novel_dir' in st.session_state or 'last_generated_draft_dir' in st.session_state:
                        st.success("上次任务已完成！")
                        
                        col_open1, col_open2 = st.columns(2)
                        
                        with col_open1:
                            if 'last_generated_novel_dir' in st.session_state:
                                if st.button("📂 打开小说文件夹 (07_novel)", key="open_novel_folder"):
                                    import subprocess
                                    import platform
                                    folder_path = st.session_state['last_generated_novel_dir']
                                    try:
                                        if platform.system() == "Windows":
                                            os.startfile(folder_path)
                                        elif platform.system() == "Darwin":
                                            subprocess.run(["open", folder_path])
                                        else:
                                            subprocess.run(["xdg-open", folder_path])
                                    except Exception as e:
                                        st.error(f"无法打开文件夹: {e}")
                        
                        with col_open2:
                            if 'last_generated_draft_dir' in st.session_state:
                                if st.button("📂 打开草稿文件夹 (03_draft)", key="open_draft_folder"):
                                    import subprocess
                                    import platform
                                    folder_path = st.session_state['last_generated_draft_dir']
                                    try:
                                        if platform.system() == "Windows":
                                            os.startfile(folder_path)
                                        elif platform.system() == "Darwin":
                                            subprocess.run(["open", folder_path])
                                        else:
                                            subprocess.run(["xdg-open", folder_path])
                                    except Exception as e:
                                        st.error(f"无法打开文件夹: {e}")

                    if st.button("✍️ 开始扩写", disabled=not config.get('api_key') or start_ch > end_ch):
                        log_container = st.container()
                        progress_bar = st.progress(0)
                        
                        try:
                            client = MultiModelClient(config)
                            expander = ChapterExpander(config, client)
                            
                            style_path = project_root / "04_prompt" / "prompts" / "style_guide.yaml"
                            style_guide = {}
                            if style_path.exists():
                                with open(style_path, 'r', encoding='utf-8') as f:
                                    style_guide = yaml.safe_load(f)
                            
                            draft_dir = config['paths'].get('draft_dir', '03_draft/')
                            if not os.path.isabs(draft_dir):
                                draft_dir = str(project_root / draft_dir)
                            
                            total = end_ch - start_ch + 1
                            current_idx = 0
                            
                            session_mgr_gui = get_session_manager()
                            
                            context_window = config.get('novel_generation', {}).get('context_chapters', 10)
                            context_parts = []
                            
                            for ch_num in range(start_ch, end_ch + 1):
                                with log_container:
                                    st.write(f"正在处理第 {ch_num} 章...")
                                
                                ch_data = None
                                for key in [f"第{ch_num}章", f"{ch_num}", f"Chapter {ch_num}"]:
                                    if key in chapter_outline:
                                        ch_data = chapter_outline[key]
                                        break
                                
                                if ch_data:
                                    previous_context = "\n\n".join(context_parts[-context_window:]) if context_parts else ""
                                    
                                    result = expander.expand_chapter(ch_num, ch_data, previous_context, style_guide)
                                    content = result[0] if isinstance(result, tuple) else result
                                    
                                    expander.save_chapter(ch_num, content, draft_dir)
                                    
                                    context_parts.append(f"【第{ch_num}章摘要】\n{content[:500]}...")
                                    
                                    session_mgr_gui.update_progress("draft", start_ch, ch_num, str(outline_file_path))
                                    
                                    st.toast(f"第 {ch_num} 章完成！", icon="✅")
                                else:
                                    st.warning(f"大纲中找不到第 {ch_num} 章的数据，跳过。")
                                
                                current_idx += 1
                                progress_bar.progress(current_idx / total)
                            
                            session_mgr_gui.add_session_record(
                                action="expand",
                                start_chapter=start_ch,
                                end_chapter=end_ch,
                                model_used=client.get_current_model(),
                                success=True
                            )
                            
                            if 'quick_continue_mode' in st.session_state:
                                st.session_state['quick_continue_mode'] = False
                            
                            st.success("🎉 所有章节扩写完成！")
                            st.balloons()
                            
                            st.session_state['last_generated_draft_dir'] = draft_dir
                            st.rerun()
                            
                        except Exception as e:
                            session_mgr_gui = get_session_manager()
                            session_mgr_gui.add_session_record(
                                action="expand",
                                start_chapter=start_ch,
                                end_chapter=end_ch,
                                model_used="",
                                success=False,
                                error_message=str(e)
                            )
                            st.error(f"❌ 发生错误: {str(e)}")
                            st.exception(e)
                else:
                    st.warning("该文件中未识别到有效章节。")
        else:
            st.error("找不到大纲目录 02_outline/")

if __name__ == "__main__":
    main()
