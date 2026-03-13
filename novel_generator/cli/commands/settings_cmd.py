"""
settings 命令
用于配置AI角色和模型设置
"""

import argparse
from pathlib import Path
import sys
import json

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.config.session import SessionManager
from novel_generator.config.generation_config import GenerationConfigManager


PROVIDERS = {
    "zhipu": "智谱AI",
    "doubao": "豆包",
    "deepseek": "DeepSeek",
    "ark": "火山引擎Ark"
}

ROLES = {
    "generator": "生成者 (负责大纲生成、章节扩写)",
    "reviewer": "评审者 (负责质量检查、一致性检查)",
    "refiner": "润色者 (负责内容润色、修复问题)"
}

GEN_PARAMS = {
    "max_refine_iterations": "最大润色迭代次数",
    "pass_score_threshold": "通过分数阈值",
    "context_chapters": "上下文章节数",
    "default_word_count": "默认字数目标",
    "batch_size": "批量处理大小"
}


def show_current_settings(gen_config_mgr: GenerationConfigManager, session_mgr: SessionManager):
    print("\n" + "="*60)
    print("生成流程配置")
    print("="*60)
    
    gen_config = gen_config_mgr.get_generation_config()
    for param, desc in GEN_PARAMS.items():
        value = gen_config.get(param)
        print(f"  {desc}: {value}")
    
    print("\n" + "="*60)
    print("AI角色配置")
    print("="*60)
    
    for role_name, role_desc in ROLES.items():
        role_config = gen_config_mgr.get_role_config(role_name)
        provider = role_config.get("provider", "zhipu")
        model = role_config.get("model", "")
        enabled = role_config.get("enabled", True)
        temperature = role_config.get("temperature", 0.7)
        max_tokens = role_config.get("max_tokens", 8000)
        
        status = "启用" if enabled else "禁用"
        provider_name = PROVIDERS.get(provider, provider)
        
        print(f"\n【{role_desc}】")
        print(f"  状态: {status}")
        print(f"  服务商: {provider_name}")
        print(f"  模型: {model}")
        print(f"  Temperature: {temperature}")
        print(f"  Max Tokens: {max_tokens}")
    
    print("\n" + "="*60)
    print("API密钥配置")
    print("="*60)
    
    api_config = session_mgr.state.api_config
    provider = api_config.provider
    provider_name = PROVIDERS.get(provider, provider)
    
    print(f"\n当前服务商: {provider_name}")
    
    if provider == "zhipu":
        key_status = "已配置" if api_config.api_key else "未配置"
        print(f"API Key: {key_status}")
    elif provider == "deepseek":
        key_status = "已配置" if api_config.deepseek_api_key else "未配置"
        print(f"API Key: {key_status}")
    
    print("\n" + "="*60)


def show_config_file(gen_config_mgr: GenerationConfigManager):
    print("\n" + "="*60)
    print("配置文件内容 (generation_config.json)")
    print("="*60)
    
    config = gen_config_mgr.config
    print(json.dumps(config, ensure_ascii=False, indent=2))
    
    print("\n" + "="*60)


def interactive_setup(gen_config_mgr: GenerationConfigManager, session_mgr: SessionManager):
    print("\n" + "="*60)
    print("交互式配置向导")
    print("="*60)
    
    while True:
        print("\n请选择配置项:")
        print("  1. 配置生成流程参数")
        print("  2. 配置AI角色")
        print("  3. 配置API密钥")
        print("  4. 查看当前配置")
        print("  5. 重置为默认配置")
        print("  q. 退出")
        
        choice = input("\n请输入选择: ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == '1':
            _config_generation_params(gen_config_mgr)
        elif choice == '2':
            _config_ai_role(gen_config_mgr)
        elif choice == '3':
            _config_api_key(session_mgr)
        elif choice == '4':
            show_current_settings(gen_config_mgr, session_mgr)
        elif choice == '5':
            confirm = input("确认重置为默认配置? (y/n): ").strip().lower()
            if confirm == 'y':
                gen_config_mgr.reset_to_default()
                print("已重置为默认配置")
        else:
            print("无效选择")
    
    print("\n配置完成！")


def _config_generation_params(gen_config_mgr: GenerationConfigManager):
    print("\n--- 生成流程参数配置 ---")
    
    gen_config = gen_config_mgr.get_generation_config()
    
    for param, desc in GEN_PARAMS.items():
        current = gen_config.get(param)
        new_value = input(f"{desc} (当前: {current}): ").strip()
        
        if new_value:
            try:
                if isinstance(current, int):
                    gen_config[param] = int(new_value)
                elif isinstance(current, float):
                    gen_config[param] = float(new_value)
                else:
                    gen_config[param] = new_value
            except ValueError:
                print(f"无效输入，保持原值: {current}")
    
    gen_config_mgr.set_generation_config(**gen_config)
    print("生成流程参数已保存")


def _config_ai_role(gen_config_mgr: GenerationConfigManager):
    print("\n可用角色:")
    for i, (role_name, role_desc) in enumerate(ROLES.items(), 1):
        print(f"  {i}. {role_desc}")
    
    role_names = list(ROLES.keys())
    choice = input("\n请选择角色 (1-3): ").strip()
    
    try:
        role_idx = int(choice) - 1
        if role_idx < 0 or role_idx >= len(role_names):
            print("无效选择")
            return
        role_name = role_names[role_idx]
    except ValueError:
        print("无效输入")
        return
    
    print(f"\n配置角色: {ROLES[role_name]}")
    
    role_config = gen_config_mgr.get_role_config(role_name)
    
    print("\n可用服务商:")
    providers = gen_config_mgr.get_all_providers()
    for i, (code, name) in enumerate(providers.items(), 1):
        print(f"  {i}. {name} ({code})")
    
    provider_choice = input("请选择服务商: ").strip()
    provider_codes = list(providers.keys())
    try:
        provider_idx = int(provider_choice) - 1
        if provider_idx < 0 or provider_idx >= len(provider_codes):
            print("无效选择")
            return
        provider = provider_codes[provider_idx]
    except ValueError:
        print("无效输入")
        return
    
    models = gen_config_mgr.get_provider_models(provider)
    print(f"\n推荐模型: {', '.join(models)}")
    model = input("请输入模型名称: ").strip()
    if not model and models:
        model = models[0]
    
    temp_input = input(f"Temperature (当前: {role_config.get('temperature', 0.7)}): ").strip()
    temperature = float(temp_input) if temp_input else role_config.get('temperature', 0.7)
    
    tokens_input = input(f"Max Tokens (当前: {role_config.get('max_tokens', 8000)}): ").strip()
    max_tokens = int(tokens_input) if tokens_input else role_config.get('max_tokens', 8000)
    
    enable_input = input("是否启用? (y/n): ").strip().lower()
    enabled = enable_input != 'n'
    
    gen_config_mgr.set_role_config(
        role_name=role_name,
        provider=provider,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        enabled=enabled
    )
    
    print(f"{ROLES[role_name]} 配置已保存")


def _config_api_key(session_mgr: SessionManager):
    print("\n--- API密钥配置 ---")
    
    print("\n可用服务商:")
    for i, (code, name) in enumerate(PROVIDERS.items(), 1):
        print(f"  {i}. {name} ({code})")
    
    provider_codes = list(PROVIDERS.keys())
    choice = input("请选择服务商: ").strip()
    
    try:
        provider_idx = int(choice) - 1
        if provider_idx < 0 or provider_idx >= len(provider_codes):
            print("无效选择")
            return
        provider = provider_codes[provider_idx]
    except ValueError:
        print("无效输入")
        return
    
    api_key = input("请输入API Key: ").strip()
    if not api_key:
        print("API Key不能为空")
        return
    
    session_mgr.set_api_config(provider=provider, api_key=api_key)
    print(f"{PROVIDERS[provider]} API Key已保存")


def set_role_config(gen_config_mgr: GenerationConfigManager, args):
    role_name = args.role
    if role_name not in ROLES:
        print(f"错误: 无效的角色名称 '{role_name}'")
        print(f"可用角色: {', '.join(ROLES.keys())}")
        return 1
    
    update_params = {}
    
    if args.provider:
        if args.provider not in PROVIDERS:
            print(f"错误: 无效的服务商 '{args.provider}'")
            print(f"可用服务商: {', '.join(PROVIDERS.keys())}")
            return 1
        update_params['provider'] = args.provider
    
    if args.model:
        update_params['model'] = args.model
    
    if args.temperature is not None:
        update_params['temperature'] = args.temperature
    
    if args.top_p is not None:
        update_params['top_p'] = args.top_p
    
    if args.max_tokens is not None:
        update_params['max_tokens'] = args.max_tokens
    
    if args.enable:
        update_params['enabled'] = True
    elif args.disable:
        update_params['enabled'] = False
    
    if not update_params:
        print("错误: 请指定至少一个配置项")
        return 1
    
    gen_config_mgr.set_role_config(role_name=role_name, **update_params)
    
    print(f"角色 '{role_name}' 配置已更新")
    return 0


def set_generation_config(gen_config_mgr: GenerationConfigManager, args):
    update_params = {}
    
    if args.max_iterations is not None:
        update_params['max_refine_iterations'] = args.max_iterations
    
    if args.pass_score is not None:
        update_params['pass_score_threshold'] = args.pass_score
    
    if args.context_chapters is not None:
        update_params['context_chapters'] = args.context_chapters
    
    if args.default_words is not None:
        update_params['default_word_count'] = args.default_words
    
    if args.batch_size is not None:
        update_params['batch_size'] = args.batch_size
    
    if not update_params:
        print("错误: 请指定至少一个配置项")
        return 1
    
    gen_config_mgr.set_generation_config(**update_params)
    
    print("生成流程配置已更新")
    gen_config = gen_config_mgr.get_generation_config()
    for param, desc in GEN_PARAMS.items():
        print(f"  {desc}: {gen_config.get(param)}")
    
    return 0


def run(args):
    project_root = Path.cwd()
    gen_config_mgr = GenerationConfigManager(str(project_root))
    session_mgr = SessionManager(str(project_root))
    
    if args.interactive:
        interactive_setup(gen_config_mgr, session_mgr)
        return 0
    
    if args.show_file:
        show_config_file(gen_config_mgr)
        return 0
    
    if args.reset:
        confirm = input("确认重置为默认配置? (y/n): ").strip().lower()
        if confirm == 'y':
            gen_config_mgr.reset_to_default()
            print("已重置为默认配置")
        return 0
    
    if args.export:
        if gen_config_mgr.export_config(args.export):
            print(f"配置已导出到: {args.export}")
            return 0
        else:
            print("导出失败")
            return 1
    
    if args.import_config:
        if gen_config_mgr.import_config(args.import_config):
            print(f"配置已导入: {args.import_config}")
            return 0
        else:
            print("导入失败")
            return 1
    
    if args.role:
        return set_role_config(gen_config_mgr, args)
    
    if hasattr(args, 'max_iterations') and args.max_iterations is not None:
        return set_generation_config(gen_config_mgr, args)
    
    show_current_settings(gen_config_mgr, session_mgr)
    print("\n提示: 使用 --interactive 进入交互式配置")
    print("      使用 --show-file 查看完整配置文件")
    print("      使用 --reset 重置为默认配置")
    
    return 0


def add_parser(subparsers):
    parser = subparsers.add_parser(
        'settings',
        help='配置AI角色和生成参数',
        description='配置AI角色、模型参数和生成流程设置'
    )
    
    parser.add_argument(
        '--show', '-s',
        action='store_true',
        help='显示当前配置'
    )
    
    parser.add_argument(
        '--show-file',
        action='store_true',
        help='显示完整配置文件内容'
    )
    
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='交互式配置向导'
    )
    
    parser.add_argument(
        '--reset',
        action='store_true',
        help='重置为默认配置'
    )
    
    parser.add_argument(
        '--export',
        type=str,
        metavar='FILE',
        help='导出配置到指定文件'
    )
    
    parser.add_argument(
        '--import-config',
        type=str,
        dest='import_config',
        metavar='FILE',
        help='从指定文件导入配置'
    )
    
    parser.add_argument(
        '--role', '-r',
        type=str,
        choices=list(ROLES.keys()),
        help='指定要配置的角色 (generator/reviewer/refiner)'
    )
    
    parser.add_argument(
        '--provider', '-p',
        type=str,
        choices=list(PROVIDERS.keys()),
        help='设置服务商'
    )
    
    parser.add_argument(
        '--model', '-m',
        type=str,
        help='设置模型名称'
    )
    
    parser.add_argument(
        '--temperature', '-t',
        type=float,
        help='设置temperature参数'
    )
    
    parser.add_argument(
        '--top-p',
        type=float,
        dest='top_p',
        help='设置top_p参数'
    )
    
    parser.add_argument(
        '--max-tokens',
        type=int,
        dest='max_tokens',
        help='设置max_tokens参数'
    )
    
    parser.add_argument(
        '--enable',
        action='store_true',
        help='启用指定角色'
    )
    
    parser.add_argument(
        '--disable',
        action='store_true',
        help='禁用指定角色'
    )
    
    parser.add_argument(
        '--max-iterations',
        type=int,
        dest='max_iterations',
        help='设置最大润色迭代次数'
    )
    
    parser.add_argument(
        '--pass-score',
        type=int,
        dest='pass_score',
        help='设置评审通过分数阈值 (0-100)'
    )
    
    parser.add_argument(
        '--context-chapters',
        type=int,
        dest='context_chapters',
        help='设置上下文章节数'
    )
    
    parser.add_argument(
        '--default-words',
        type=int,
        dest='default_words',
        help='设置默认字数目标'
    )
    
    parser.add_argument(
        '--batch-size',
        type=int,
        dest='batch_size',
        help='设置批量处理大小'
    )
    
    parser.set_defaults(func=run)