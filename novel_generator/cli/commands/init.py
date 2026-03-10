"""
项目初始化命令

初始化小说创作项目的目录结构和配置文件
"""

import argparse
import sys
from pathlib import Path
from typing import Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from novel_generator.core.project_manager import ProjectManager
from novel_generator.utils.common import ensure_directories
from novel_generator.cli.utils import print_success, print_error, print_info, print_warning


def run(args: argparse.Namespace) -> int:
    """
    执行项目初始化
    
    Args:
        args: 命令行参数
        
    Returns:
        int: 退出码 (0=成功, 1=失败)
    """
    print_info("🚀 开始初始化小说创作项目...")
    
    # 确定项目根目录
    if args.project_root:
        project_root = Path(args.project_root).resolve()
    else:
        project_root = Path.cwd()
    
    print_info(f"项目根目录: {project_root}")
    
    # 检查目录是否已存在内容
    if project_root.exists() and any(project_root.iterdir()):
        if not args.force:
            print_warning("目录不为空")
            response = input("是否继续初始化? [y/N]: ").strip().lower()
            if response not in ('y', 'yes'):
                print_info("初始化已取消")
                return 0
    
    try:
        # 确保目录结构
        ensure_directories(project_root)
        print_success("创建目录结构")
        
        # 使用ProjectManager初始化
        manager = ProjectManager(project_root)
        
        if manager.initialize_project():
            print_success("项目初始化完成！")
            print()
            print_info("📋 下一步操作指南:")
            print("  1. 填写 01_source/core_setting.yaml - 小说核心设定")
            print("  2. 填写 01_source/overall_outline.yaml - 整体大纲")
            print("  3. 配置 05_script/config.json - API密钥")
            print("  4. 运行 'soundnovel outline' 生成章节大纲")
            return 0
        else:
            print_error("项目初始化失败")
            return 1
            
    except Exception as e:
        print_error(f"初始化过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1
