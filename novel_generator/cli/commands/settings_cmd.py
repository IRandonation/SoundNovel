"""
settings 命令
用于配置生成模型和参数设置（新架构版本）
"""

import argparse
from pathlib import Path
import sys
import json
from typing import Optional

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.novel_manager import NovelManager
from api.manager import APIManager
from novel_generator.config.config_manager import ConfigManager


PROVIDERS = {
    "doubao": "豆包/火山引擎",
    "deepseek": "DeepSeek",
}

DEFAULT_MODELS = {
    "doubao": "doubao-seed-2-0-lite-260215",
    "deepseek": "deepseek-chat",
}

GEN_PARAMS = {
    "default_word_count": "默认字数目标",
    "outline_window": "大纲上下文窗口 (向前看过往大纲章数)",
    "draft_window": "正文上下文窗口 (向前看过往已生成正文章数)",
    "skeleton_batch_size": "骨架批次大小 (单次API调用生成的章数)",
    # 滑动窗口多轮配置
    "conversation_window": "对话窗口大小 (累积的上下文章数)",
    "enable_act_plan_injection": "是否动态注入幕规划",
    "save_conversation_checkpoints": "是否保存检查点",
    "max_conversation_tokens": "单对话最大token数 (触发修剪)",
}


def _get_current_novel_id(project_root: Path) -> Optional[str]:
    """获取当前小说ID"""
    novel_manager = NovelManager(str(project_root / "novels"))
    return novel_manager.get_current_novel_id()


def show_current_settings(project_root: Path):
    """显示当前配置"""
    novel_id = _get_current_novel_id(project_root)

    if not novel_id:
        print("\n" + "=" * 60)
        print("未选择小说，请先运行 'soundnovel novel create' 创建小说")
        print("=" * 60)
        return

    print("\n" + "=" * 60)
    print(f"当前小说: {novel_id}")
    print("=" * 60)

    try:
        config_manager = ConfigManager(str(project_root), novel_id)
        gen_config = config_manager.get_generation_config()

        print("\n生成流程配置:")
        for param, desc in GEN_PARAMS.items():
            value = gen_config.get(param, "未设置")
            print(f"  {desc}: {value}")

        # 显示API配置
        api_ref = config_manager.config.get("api_config_ref", "")
        if api_ref:
            api_manager = APIManager(str(project_root))
            api_config = api_manager.get_config(api_ref)
            if api_config:
                print(f"\nAPI配置: {api_ref}")
                print(f"  服务商: {PROVIDERS.get(api_config.get('provider', ''), '未知')}")
                print(f"  模型: {api_config.get('model', '未设置')}")
        else:
            print("\nAPI配置: 未设置")

    except Exception as e:
        print(f"  错误: {e}")

    print("\n" + "=" * 60)


def interactive_setup(project_root: Path):
    """交互式配置向导"""
    print("\n" + "=" * 60)
    print("交互式配置向导")
    print("=" * 60)

    novel_id = _get_current_novel_id(project_root)
    if not novel_id:
        print("\n未选择小说，请先运行 'soundnovel novel create' 创建小说")
        return

    while True:
        print("\n请选择配置项:")
        print("  1. 配置生成流程参数")
        print("  2. 配置当前小说的API")
        print("  3. 查看当前配置")
        print("  q. 退出")

        choice = input("\n请输入选择: ").strip().lower()

        if choice == "q":
            break
        elif choice == "1":
            _config_generation_params(project_root, novel_id)
        elif choice == "2":
            _config_novel_api(project_root, novel_id)
        elif choice == "3":
            show_current_settings(project_root)
        else:
            print("无效选择")

    print("\n配置完成！")


def _config_generation_params(project_root: Path, novel_id: str):
    """配置生成流程参数"""
    print("\n--- 生成流程参数配置 ---")

    try:
        config_manager = ConfigManager(str(project_root), novel_id)
        gen_config = config_manager.get_generation_config()

        updates = {}
        for param, desc in GEN_PARAMS.items():
            current = gen_config.get(param, "")
            new_value = input(f"{desc} (当前: {current}): ").strip()

            if new_value:
                try:
                    if isinstance(current, int):
                        updates[param] = int(new_value)
                    elif isinstance(current, float):
                        updates[param] = float(new_value)
                    else:
                        updates[param] = new_value
                except ValueError:
                    print(f"  无效输入，跳过")

        if updates:
            config_manager.set_generation_config(**updates)
            print("生成流程参数已保存")
        else:
            print("无更改")

    except Exception as e:
        print(f"配置失败: {e}")


def _config_novel_api(project_root: Path, novel_id: str):
    """配置当前小说使用的API"""
    print("\n--- API配置 ---")

    api_manager = APIManager(str(project_root))
    configs = api_manager.list_configs()

    if not configs:
        print("\n没有可用的API配置，请先运行 'soundnovel api create' 创建API配置")
        return

    print("\n可用API配置:")
    for i, config in enumerate(configs, 1):
        default_mark = " [默认]" if config.get("is_default") else ""
        print(f"  {i}. {config.get('name', '未命名')} ({config.get('provider', '未知')}){default_mark}")

    try:
        choice = input("\n请选择要使用的API配置: ").strip()
        idx = int(choice) - 1
        if idx < 0 or idx >= len(configs):
            print("无效选择")
            return

        selected = configs[idx]
        config_id = selected.get("id")

        # 更新小说配置
        novel_manager = NovelManager(str(project_root / "novels"))
        novel = novel_manager.get_novel(novel_id)
        if novel:
            novel_config = novel.load_config()
            novel_config["api_config_ref"] = config_id
            novel.save_config(novel_config)
            print(f"\n已设置小说 '{novel_id}' 使用API配置: {selected.get('name', config_id)}")

    except (ValueError, IndexError):
        print("无效输入")
    except Exception as e:
        print(f"配置失败: {e}")


def run(args):
    project_root = Path.cwd()

    if args.interactive:
        interactive_setup(project_root)
        return 0

    if args.show_file:
        # 显示当前小说的配置
        novel_id = _get_current_novel_id(project_root)
        if novel_id:
            print(f"\n当前小说: {novel_id}")
            try:
                config_manager = ConfigManager(str(project_root), novel_id)
                gen_config = config_manager.get_generation_config()
                print("\n生成配置:")
                print(json.dumps(gen_config, ensure_ascii=False, indent=2))
            except Exception as e:
                print(f"无法读取配置: {e}")
        return 0

    if args.reset:
        confirm = input("确认重置为默认配置? (y/n): ").strip().lower()
        if confirm == "y":
            novel_id = _get_current_novel_id(project_root)
            if novel_id:
                try:
                    config_manager = ConfigManager(str(project_root), novel_id)
                    # 重置为默认配置
                    default_config = {
                        "default_word_count": 3200,
                        "outline_window": 30,
                        "draft_window": 10,
                        "skeleton_batch_size": 10,
                        # 滑动窗口多轮配置
                        "conversation_window": 100,
                        "enable_act_plan_injection": True,
                        "save_conversation_checkpoints": True,
                        "max_conversation_tokens": 800000,
                    }
                    config_manager.set_generation_config(**default_config)
                    print("已重置为默认配置")
                except Exception as e:
                    print(f"重置失败: {e}")
            else:
                print("未选择小说")
        return 0

    # 处理参数设置
    if any(
        getattr(args, attr, None) is not None
        for attr in [
            "default_words", "outline_window", "draft_window", "skeleton_batch_size",
            "conversation_window", "enable_act_plan_injection", "save_conversation_checkpoints", "max_conversation_tokens",
        ]
    ):
        novel_id = _get_current_novel_id(project_root)
        if not novel_id:
            print("错误: 未选择小说")
            return 1

        try:
            config_manager = ConfigManager(str(project_root), novel_id)
            updates = {}

            if args.default_words is not None:
                updates["default_word_count"] = args.default_words
            if args.outline_window is not None:
                updates["outline_window"] = args.outline_window
            if args.draft_window is not None:
                updates["draft_window"] = args.draft_window
            if args.skeleton_batch_size is not None:
                updates["skeleton_batch_size"] = args.skeleton_batch_size
            # 滑动窗口多轮配置
            if getattr(args, "conversation_window", None) is not None:
                updates["conversation_window"] = args.conversation_window
            if getattr(args, "enable_act_plan_injection", None) is not None:
                updates["enable_act_plan_injection"] = args.enable_act_plan_injection
            if getattr(args, "save_conversation_checkpoints", None) is not None:
                updates["save_conversation_checkpoints"] = args.save_conversation_checkpoints
            if getattr(args, "max_conversation_tokens", None) is not None:
                updates["max_conversation_tokens"] = args.max_conversation_tokens

            if updates:
                config_manager.set_generation_config(**updates)
                print("生成流程配置已更新")
                for param, value in updates.items():
                    print(f"  {GEN_PARAMS.get(param, param)}: {value}")

            return 0

        except Exception as e:
            print(f"配置失败: {e}")
            return 1

    show_current_settings(project_root)
    print("\n提示: 使用 --interactive 进入交互式配置")

    return 0


def add_parser(subparsers):
    parser = subparsers.add_parser(
        "settings",
        help="配置生成模型和生成参数",
        description="配置生成模型、模型参数和生成流程设置",
    )

    parser.add_argument("--show", "-s", action="store_true", help="显示当前配置")

    parser.add_argument("--show-file", action="store_true", help="显示完整配置文件内容")

    parser.add_argument(
        "--interactive", "-i", action="store_true", help="交互式配置向导"
    )

    parser.add_argument("--reset", action="store_true", help="重置为默认配置")

    parser.add_argument(
        "--default-words", type=int, dest="default_words", help="设置默认字数目标"
    )

    parser.add_argument(
        "--outline-window", type=int, dest="outline_window", help="设置大纲上下文窗口大小（默认30）"
    )

    parser.add_argument(
        "--draft-window", type=int, dest="draft_window", help="设置正文上下文窗口大小（默认10）"
    )

    parser.add_argument(
        "--skeleton-batch-size", type=int, dest="skeleton_batch_size",
        help="设置骨架批次大小：单次API调用生成的章数（默认10）"
    )

    # 滑动窗口多轮配置参数
    parser.add_argument(
        "--conversation-window",
        type=int,
        dest="conversation_window",
        help="设置对话窗口大小：累积的上下文章数（默认100）"
    )

    parser.add_argument(
        "--enable-act-plan-injection",
        type=lambda x: x.lower() in ('true', '1', 'yes'),
        dest="enable_act_plan_injection",
        help="设置是否动态注入幕规划: true/false（默认true）"
    )

    parser.add_argument(
        "--save-conversation-checkpoints",
        type=lambda x: x.lower() in ('true', '1', 'yes'),
        dest="save_conversation_checkpoints",
        help="设置是否保存检查点: true/false（默认true）"
    )

    parser.add_argument(
        "--max-conversation-tokens",
        type=int,
        dest="max_conversation_tokens",
        help="设置单对话最大token数，超过将触发修剪（默认800000）"
    )

    parser.set_defaults(func=run)
