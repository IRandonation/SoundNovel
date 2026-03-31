"""
大纲审查命令

支持两种审查模式：
1. 规则硬审查（默认）：基于代码规则快速检查格式和结构问题
2. AI智能审查：使用Reviewer角色进行深度语义审查
"""

import argparse
from pathlib import Path
from typing import Optional
import sys

project_root = Path(__file__).parent.parent.parent.parent

from novel_generator.core.outline_reviewer import OutlineReviewer, ReviewResult
from novel_generator.core.outline_chat_service import OutlineChatService
from novel_generator.config.config_manager import ConfigManager
from novel_generator.utils.multi_model_client import MultiModelClient
from novel_generator.cli.utils import (
    print_success,
    print_error,
    print_info,
    print_warning,
)


def run(args: argparse.Namespace) -> int:
    project_root_path = Path.cwd()
    
    core_setting_path = project_root_path / "01_source" / "core_setting.yaml"
    overall_outline_path = project_root_path / "01_source" / "overall_outline.yaml"
    
    if not core_setting_path.exists():
        print_error(f"核心设定文件不存在: {core_setting_path}")
        print_info("请先创建核心设定文件，或运行 'soundnovel init' 初始化项目")
        return 1
    
    if not overall_outline_path.exists():
        print_error(f"整体大纲文件不存在: {overall_outline_path}")
        print_info("请先创建整体大纲文件，或运行 'soundnovel init' 初始化项目")
        return 1
    
    print()
    print_info("=" * 60)
    if args.ai:
        print_info("AI智能大纲审查")
    else:
        print_info("规则硬审查")
    print_info("=" * 60)
    print()
    
    config_manager = ConfigManager(str(project_root_path))
    config = config_manager.get_api_config()
    
    client = None
    if args.ai:
        if not config.get("api_key") and not config.get("deepseek_api_key"):
            print_error("AI审查需要配置API密钥，请先运行 'soundnovel init' 配置API")
            return 1
        client = MultiModelClient(config)
    
    reviewer = OutlineReviewer(config_manager.get_role_config("reviewer"), client)
    
    print_info("正在加载设定文件...")
    if not reviewer.load_settings(str(core_setting_path), str(overall_outline_path)):
        print_error("加载设定文件失败")
        return 1
    
    print_info("正在执行审查...")
    print()
    
    if args.ai:
        result = reviewer.review_with_ai(include_commercial=args.commercial)
    else:
        result = reviewer.review_with_rules()
    
    _print_review_result(result)
    
    if args.output:
        output_path = Path(args.output)
        if reviewer.save_review_result(result, str(output_path)):
            print_success(f"审查结果已保存: {output_path}")
    
    if args.chat:
        return _start_chat_mode(args, project_root_path, result)
    
    if result.errors > 0:
        print()
        print_warning("发现严重问题，建议修复后重新审查")
        print_info("提示: 使用 --chat 参数启动AI对话修改模式")
        return 1
    
    return 0


def _print_review_result(result: ReviewResult):
    mode_label = "AI智能审查" if result.review_mode == "ai" else "规则硬审查"
    print_info(f"审查模式: {mode_label}")
    print_info(f"审查时间: {result.timestamp}")
    print()
    
    print_info("--- 审查统计 ---")
    print(f"  总问题数: {result.total_issues}")
    
    if result.errors:
        print(f"  严重问题: {result.errors}个")
    if result.warnings:
        print(f"  警告: {result.warnings}个")
    if result.suggestions:
        print(f"  建议: {result.suggestions}个")
    
    if result.total_issues == 0:
        print()
        print_success("大纲结构完整，未发现明显问题！")
        return
    
    print()
    print_info("--- 问题详情 ---")
    print()
    
    severity_icons = {"error": "[X]", "warning": "[!]", "suggestion": "[?]"}
    
    for i, issue in enumerate(result.issues, 1):
        icon = severity_icons.get(issue.severity, "*")
        print(f"  {icon} [{issue.category}] 第{issue.chapter_range}")
        print(f"     问题: {issue.description}")
        print(f"     建议: {issue.suggestion}")
        print()
    
    print_info("--- 摘要 ---")
    print(result.summary)


def _start_chat_mode(args: argparse.Namespace, project_root: Path, result: ReviewResult) -> int:
    print()
    print_info("=" * 60)
    print_info("AI对话修改模式")
    print_info("=" * 60)
    print()
    print_info("输入你的问题或修改需求，AI将帮助你优化大纲")
    print_info("命令: quit=退出, save=保存, review=重新审查, help=帮助")
    print()
    
    config_manager = ConfigManager(str(project_root))
    config = config_manager.get_api_config()
    roles_config = config_manager.get_all_roles_config()
    
    if not config.get("api_key") and not config.get("deepseek_api_key"):
        print_error("未配置API密钥，请先运行 'soundnovel init' 配置API")
        return 1
    
    client = MultiModelClient(config)
    chat_service = OutlineChatService(roles_config.get("refiner", {}), client)
    
    core_setting_path = project_root / "01_source" / "core_setting.yaml"
    overall_outline_path = project_root / "01_source" / "overall_outline.yaml"
    
    if not chat_service.load_settings(str(core_setting_path), str(overall_outline_path)):
        print_error("加载设定文件失败")
        return 1
    
    initial_message = _build_initial_message(result)
    print_info("AI助手: " + initial_message[:500] + "..." if len(initial_message) > 500 else "AI助手: " + initial_message)
    print()
    
    while True:
        try:
            user_input = input("你: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == "quit":
                print_info("退出对话模式")
                break
            
            elif user_input.lower() == "save":
                if chat_service.save_all():
                    print_success("设定和大纲已保存")
                else:
                    print_error("保存失败")
                continue
            
            elif user_input.lower() == "review":
                reviewer = OutlineReviewer({})
                reviewer.load_settings(str(core_setting_path), str(overall_outline_path))
                new_result = reviewer.review_with_rules()
                _print_review_result(new_result)
                continue
            
            elif user_input.lower() == "help":
                print_info("可用命令:")
                print("  quit   - 退出对话模式")
                print("  save   - 保存当前修改")
                print("  review - 重新审查大纲")
                print("  help   - 显示帮助")
                print()
                print_info("你可以直接输入问题或修改需求，例如:")
                print("  - 帮我优化第一幕的剧情要点")
                print("  - 主角的成长弧线不够明显，如何改进")
                print("  - 添加一个新的伏笔")
                continue
            
            print_info("思考中...")
            response = chat_service.chat(user_input)
            print()
            print("AI助手: " + response)
            print()
            
        except KeyboardInterrupt:
            print()
            print_info("退出对话模式")
            break
        except EOFError:
            break
    
    return 0


def _build_initial_message(result: ReviewResult) -> str:
    if result.total_issues == 0:
        return "大纲结构完整，暂未发现问题。如果你有具体的修改需求，请告诉我。"
    
    issues_summary = []
    for issue in result.issues[:5]:
        issues_summary.append(f"- [{issue.severity}] {issue.description}")
    
    return f"审查发现了{result.total_issues}个问题。主要问题包括:\n" + "\n".join(issues_summary) + "\n\n你希望我帮助解决哪些问题？"


def add_parser(subparsers):
    parser = subparsers.add_parser(
        'review',
        help='审查大纲',
        description='审查整体大纲的一致性、角色弧线、剧情连贯性'
    )
    parser.add_argument(
        '--ai',
        action='store_true',
        help='使用AI智能审查模式（需要配置API）'
    )
    parser.add_argument(
        '--commercial',
        action='store_true',
        help='在AI审查中包含商业节奏分析'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        help='审查结果输出文件路径'
    )
    parser.add_argument(
        '--chat',
        action='store_true',
        help='审查后启动AI对话修改模式'
    )
    parser.set_defaults(func=run)
