"""
API配置管理命令

管理多服务商API配置（豆包/DeepSeek）
支持列表、创建、编辑、删除、切换、测试等操作
"""

import argparse
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))  # noqa: E402

from novel_generator.cli.utils import (  # noqa: E402
    print_success,
    print_error,
    print_info,
    print_warning,
    confirm_action,
)
from novel_generator.config.config_manager import ConfigManager  # noqa: E402


PROVIDERS = {
    "doubao": "豆包/火山引擎",
    "deepseek": "DeepSeek",
}

DEFAULT_API_URLS = {
    "doubao": "https://ark.cn-beijing.volces.com/api/v3",
    "deepseek": "https://api.deepseek.com",
}

DEFAULT_MODELS = {
    "doubao": "doubao-seed-2-0-lite-260215",
    "deepseek": "deepseek-chat",
}


def _get_config_manager(project_root: str = ".") -> ConfigManager:
    """获取配置管理器实例"""
    return ConfigManager(project_root)


def _list_api_configs_table(configs: List[Dict[str, Any]], default_id: Optional[str]) -> None:
    """以表格形式展示API配置列表"""
    from rich.console import Console
    from rich.table import Table
    from rich import box

    console = Console()

    table = Table(
        title="API配置列表",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("ID", style="dim", width=15)
    table.add_column("名称", width=25)
    table.add_column("服务商", width=15)
    table.add_column("默认", width=8, justify="center")

    for config in configs:
        config_id = config.get("id", "")
        is_default = "*" if config_id == default_id else ""
        provider_name = PROVIDERS.get(config.get("provider", ""), config.get("provider", ""))

        table.add_row(
            config_id,
            config.get("name", ""),
            provider_name,
            is_default,
        )

    console.print(table)


def _get_all_api_configs(project_root: Path) -> List[Dict[str, Any]]:
    """获取所有API配置（使用新架构 APIManager）"""
    from api.manager import APIManager

    api_manager = APIManager(str(project_root))
    configs = []

    for config_dict in api_manager.list_configs():
        configs.append({
            "id": config_dict.get("id"),
            "name": config_dict.get("name"),
            "provider": config_dict.get("provider"),
            "is_default": config_dict.get("is_default", False),
        })

    return configs


def _test_api_connection(provider: str, api_key: str, api_url: str, model: str) -> tuple:
    """测试API连接"""
    import requests

    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        test_data = {
            "model": model,
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 10,
        }
        response = requests.post(
            f"{api_url.rstrip('/')}/chat/completions",
            headers=headers,
            json=test_data,
            timeout=15,
        )
        if response.status_code == 200:
            return True, "API连接正常"
        elif response.status_code == 401:
            return False, "API Key无效"
        elif response.status_code == 404:
            return False, f"模型不存在: {model}"
        else:
            return False, f"HTTP错误: {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "连接超时，请检查网络"
    except requests.exceptions.ConnectionError:
        return False, "无法连接服务器"
    except Exception as e:
        return False, f"测试失败: {str(e)}"


def api_list(args: argparse.Namespace) -> int:
    """列出所有API配置"""
    project_root = Path.cwd()
    configs = _get_all_api_configs(project_root)

    if not configs:
        print_info("暂无API配置")
        print_info("运行 'soundnovel api create' 创建新配置")
        return 0

    # 获取默认配置
    from api.manager import APIManager
    api_manager = APIManager(str(project_root))
    default_config = api_manager.get_default()
    default_id = default_config.id if default_config else None

    _list_api_configs_table(configs, default_id)

    return 0


def api_create(args: argparse.Namespace) -> int:
    """交互式创建API配置"""
    from api.manager import APIManager

    project_root = Path.cwd()
    api_manager = APIManager(str(project_root))

    print_info("=" * 60)
    print_info("创建新的API配置")
    print_info("=" * 60)

    # 服务商选择
    print_info("\n可用服务商:")
    for i, (code, name) in enumerate(PROVIDERS.items(), 1):
        print(f"  {i}. {name} ({code})")

    provider_choice = input("\n请选择服务商: ").strip()
    try:
        provider_idx = int(provider_choice) - 1
        if provider_idx < 0 or provider_idx >= len(PROVIDERS):
            print_error("无效选择")
            return 1
        provider = list(PROVIDERS.keys())[provider_idx]
    except ValueError:
        print_error("无效输入")
        return 1

    provider_name = PROVIDERS[provider]
    default_url = DEFAULT_API_URLS[provider]
    default_model = DEFAULT_MODELS[provider]

    # 配置名称
    name = input(f"\n配置名称 (默认: {provider_name}): ").strip()
    if not name:
        name = provider_name

    # API Key
    api_key = input("\n请输入API Key: ").strip()
    if not api_key:
        print_error("API Key不能为空")
        return 1

    # API Base URL
    api_url = input(f"API Base URL (直接回车使用默认: {default_url}): ").strip()
    if not api_url:
        api_url = default_url

    # 模型名称
    model = input(f"模型名称 (直接回车使用默认: {default_model}): ").strip()
    if not model:
        model = default_model

    # 测试连接
    print_info(f"\n正在测试 {provider_name} API连接...")
    success, message = _test_api_connection(provider, api_key, api_url, model)

    if not success:
        print_error(f"连接测试失败: {message}")
        if not confirm_action("是否仍要保存此配置?"):
            print_info("已取消")
            return 0
    else:
        print_success(f"连接测试成功: {message}")

    # 保存配置
    try:
        config_data = {
            "id": provider,
            "name": name,
            "provider": provider,
            "api_key": api_key,
            "api_base_url": api_url,
            "models": {
                "expansion_model": model,
                "outline_model": model,
            },
        }

        api_config = api_manager.create_config(config_data)

        if api_config:
            print_success(f"\n配置 '{name}' 创建成功")
            print_info(f"  服务商: {provider_name}")
            print_info(f"  模型: {model}")
            print_info(f"  API URL: {api_url}")

            if api_config.is_default:
                print_info("  状态: 默认配置")

            return 0
        else:
            print_error("保存配置失败")
            return 1
    except Exception as e:
        print_error(f"保存配置失败: {e}")
        return 1


def api_use(args: argparse.Namespace) -> int:
    """设置默认API配置"""
    from api.manager import APIManager

    project_root = Path.cwd()
    api_manager = APIManager(str(project_root))
    config_id = args.config_id

    # 检查配置是否存在
    config = api_manager.get_config(config_id)
    if not config:
        print_error(f"配置 '{config_id}' 不存在")
        print_info("运行 'soundnovel api list' 查看可用配置")
        return 1

    # 设置为默认
    if api_manager.set_default(config_id):
        print_success(f"已将 '{config.name}' 设为默认API配置")
    else:
        print_error(f"设置默认配置失败: {config_id}")
        return 1

    return 0


def api_test(args: argparse.Namespace) -> int:
    """测试API连接"""
    from api.manager import APIManager

    project_root = Path.cwd()
    api_manager = APIManager(str(project_root))

    config_id = getattr(args, 'config_id', None)

    if config_id:
        # 测试指定配置
        config = api_manager.get_config(config_id)
        if not config:
            print_error(f"配置 '{config_id}' 不存在")
            return 1

        success, message = _test_api_connection(
            config.provider,
            config.api_key,
            config.api_base_url,
            config.models.get("expansion_model", DEFAULT_MODELS.get(config.provider, "")),
        )

        if success:
            print_success(f"[{config.name}] {message}")
        else:
            print_error(f"[{config.name}] {message}")
    else:
        # 测试所有配置
        configs = api_manager.list_configs()
        if not configs:
            print_info("暂无API配置")
            return 0

        print_info("测试所有API配置...")
        for config in configs:
            success, message = _test_api_connection(
                config.provider,
                config.api_key,
                config.api_base_url,
                config.models.get("expansion_model", DEFAULT_MODELS.get(config.provider, "")),
            )
            if success:
                print_success(f"[{config.name}] {message}")
            else:
                print_error(f"[{config.name}] {message}")

    return 0


def api_delete(args: argparse.Namespace) -> int:
    """删除API配置"""
    from api.manager import APIManager

    project_root = Path.cwd()
    api_manager = APIManager(str(project_root))
    config_id = args.config_id

    # 检查配置是否存在
    config = api_manager.get_config(config_id)
    if not config:
        print_error(f"配置 '{config_id}' 不存在")
        return 1

    # 确认删除
    print_warning(f"即将删除API配置: {config.name} ({config_id})")
    if not confirm_action("此操作不可撤销，确认删除?"):
        print_info("已取消")
        return 0

    # 执行删除
    if api_manager.delete_config(config_id):
        print_success(f"已删除API配置: {config.name}")
    else:
        print_error(f"删除配置失败: {config_id}")
        return 1

    return 0

    provider_name = PROVIDERS[config_id]

    # 确认删除
    if not confirm_action(f"确认删除 '{provider_name}' 配置?"):
        print_info("已取消")
        return 0

    # 删除配置
    if config_id == "doubao":
        session.api_config.doubao_api_key = ""
        session.api_config.doubao_models = {}
    elif config_id == "deepseek":
        session.api_config.deepseek_api_key = ""
        session.api_config.deepseek_models = {}

    # 如果删除的是默认配置，清空默认
    if session.api_config.provider == config_id:
        session.api_config.provider = ""

    config_mgr.save()

    print_success(f"已删除 '{provider_name}' 配置")
    return 0


def api_edit(args: argparse.Namespace) -> int:
    """编辑API配置"""
    from api.manager import APIManager

    project_root = Path.cwd()
    api_manager = APIManager(str(project_root))
    config_id = args.config_id

    # 加载现有配置
    config = api_manager.get_config(config_id)
    if not config:
        print_error(f"配置 '{config_id}' 不存在")
        return 1

    provider_name = config.name
    default_url = config.api_base_url

    print_info("=" * 60)
    print_info(f"编辑 {provider_name} 配置")
    print_info("=" * 60)

    # 配置名称
    name = input(f"配置名称 (当前: {config.name}): ").strip()
    if not name:
        name = config.name

    # API Key
    api_key = input("API Key (直接回车保持当前): ").strip()
    if not api_key:
        api_key = config.api_key
    else:
        print_info("API Key已更新")

    # API Base URL
    api_url = input(f"API Base URL (当前: {config.api_base_url}): ").strip()
    if not api_url:
        api_url = config.api_base_url

    # 模型名称
    current_model = config.models.get("expansion_model", DEFAULT_MODELS.get(config.provider, ""))
    model = input(f"模型名称 (当前: {current_model}): ").strip()
    if not model:
        model = current_model

    # 测试连接
    print_info(f"\n正在测试更新后的配置...")
    success, message = _test_api_connection(config.provider, api_key, api_url, model)

    if not success:
        print_error(f"连接测试失败: {message}")
        if not confirm_action("是否仍要保存此配置?"):
            print_info("已取消")
            return 0
    else:
        print_success(f"连接测试成功: {message}")

    # 保存配置
    config_data = {
        "id": config_id,
        "name": name,
        "provider": config.provider,
        "api_key": api_key,
        "api_base_url": api_url,
        "models": {
            "expansion_model": model,
            "outline_model": model,
        },
        "is_default": config.is_default,
    }

    if api_manager.update_config(config_id, config_data):
        print_success(f"\n'{name}' 配置已更新")
        return 0
    else:
        print_error("保存配置失败")
        return 1


def run(args: argparse.Namespace) -> int:
    """主入口函数"""
    if not args.subcommand:
        print_error("请指定子命令: list, create, use, test, delete, edit")
        return 1

    command_map = {
        "list": api_list,
        "create": api_create,
        "use": api_use,
        "test": api_test,
        "delete": api_delete,
        "edit": api_edit,
    }

    handler = command_map.get(args.subcommand)
    if not handler:
        print_error(f"未知子命令: {args.subcommand}")
        return 1

    return handler(args)


def add_parser(subparsers):
    """添加API命令解析器（用于嵌套在cli下）"""
    api_parser = subparsers.add_parser(
        "api",
        help="管理API配置",
        description="管理多服务商API配置（豆包/DeepSeek）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  %(prog)s api list              列出所有API配置
  %(prog)s api create            交互式创建新配置
  %(prog)s api use doubao        设置豆包为默认配置
  %(prog)s api test              测试所有配置连接
  %(prog)s api test doubao       测试豆包配置连接
  %(prog)s api delete deepseek   删除DeepSeek配置
  %(prog)s api edit doubao       编辑豆包配置
        """
    )

    api_parser.add_argument(
        "subcommand",
        nargs="?",
        choices=["list", "create", "use", "test", "delete", "edit"],
        help="子命令",
    )

    api_parser.add_argument(
        "config_id",
        nargs="?",
        help="配置ID (doubao/deepseek)",
    )

    api_parser.set_defaults(func=run)

    return api_parser


def _create_api_parser() -> argparse.ArgumentParser:
    """创建独立的API命令解析器（用于soundnovel api入口）"""
    parser = argparse.ArgumentParser(
        prog='soundnovel api',
        description='管理多服务商API配置（豆包/DeepSeek）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  soundnovel api list              列出所有API配置
  soundnovel api create            交互式创建新配置
  soundnovel api use doubao        设置豆包为默认配置
  soundnovel api test              测试所有配置连接
  soundnovel api test doubao       测试豆包配置连接
  soundnovel api delete deepseek   删除DeepSeek配置
  soundnovel api edit doubao       编辑豆包配置
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='子命令')

    # list 命令
    list_parser = subparsers.add_parser('list', help='列出所有API配置')
    list_parser.set_defaults(func=api_list)

    # create 命令
    create_parser = subparsers.add_parser('create', help='创建新API配置')
    create_parser.set_defaults(func=api_create)

    # use 命令
    use_parser = subparsers.add_parser('use', help='设置默认API配置')
    use_parser.add_argument('config_id', help='配置ID (doubao/deepseek)')
    use_parser.set_defaults(func=api_use)

    # test 命令
    test_parser = subparsers.add_parser('test', help='测试API连接')
    test_parser.add_argument('config_id', nargs='?', help='配置ID (可选，不指定则测试所有)')
    test_parser.set_defaults(func=api_test)

    # delete 命令
    delete_parser = subparsers.add_parser('delete', help='删除API配置')
    delete_parser.add_argument('config_id', help='配置ID (doubao/deepseek)')
    delete_parser.set_defaults(func=api_delete)

    # edit 命令
    edit_parser = subparsers.add_parser('edit', help='编辑API配置')
    edit_parser.add_argument('config_id', help='配置ID (doubao/deepseek)')
    edit_parser.set_defaults(func=api_edit)

    return parser


def main(args_list=None):
    """独立入口函数（用于soundnovel api命令）"""
    parser = _create_api_parser()

    if args_list:
        args = parser.parse_args(args_list)
    else:
        args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    handler = getattr(args, 'func', None)
    if handler:
        return handler(args)

    return 0
