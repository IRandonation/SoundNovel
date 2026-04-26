#!/usr/bin/env python3
"""
SoundNovel 打包脚本

用于生成可执行文件 (.exe)，方便分享给没有 Python 环境的用户。

使用方法:
    python build_exe.py              # 构建 CLI 版本
    python build_exe.py --clean      # 清理构建文件

输出:
    dist/SoundNovelAI_CLI/       # CLI 版本
    dist/SoundNovelAI_CLI.zip    # 打包好的 ZIP 文件
"""

import PyInstaller.__main__
import os
import shutil
import argparse
from pathlib import Path


def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.resolve()


def clean_build():
    """清理构建文件"""
    project_root = get_project_root()
    dirs_to_remove = ['build', 'dist']

    for dir_name in dirs_to_remove:
        dir_path = project_root / dir_name
        if dir_path.exists():
            print(f"🗑️  删除 {dir_path}")
            shutil.rmtree(dir_path)

    # 删除 spec 文件
    for spec_file in project_root.glob("*.spec"):
        print(f"🗑️  删除 {spec_file}")
        spec_file.unlink()

    print("✅ 清理完成")


def copy_project_resources(dist_dir: Path):
    """复制项目资源文件到输出目录"""
    project_root = get_project_root()

    # 要复制的目录
    dirs_to_copy = [
        ("01_source", "01_source"),
        ("04_prompt", "04_prompt"),
        ("05_script", "05_script"),
        ("novel_generator", "novel_generator"),
    ]

    # 要创建的空目录
    dirs_to_create = ["02_outline", "03_draft", "06_log"]

    # 要复制的单独文件
    files_to_copy = [
        ("soundnovel.py", "soundnovel.py"),
        ("README.md", "README.md"),
    ]

    print("📂 复制项目资源...")

    # 复制目录
    for src_name, dst_name in dirs_to_copy:
        src_path = project_root / src_name
        dst_path = dist_dir / dst_name

        if src_path.exists():
            if dst_path.exists():
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path)
            print(f"   ✅ 复制目录 {src_name}")

    # 创建空目录
    for dir_name in dirs_to_create:
        (dist_dir / dir_name).mkdir(parents=True, exist_ok=True)
        print(f"   ✅ 创建目录 {dir_name}")

    # 复制单独文件
    for src_name, dst_name in files_to_copy:
        src_path = project_root / src_name
        if src_path.exists():
            shutil.copy2(src_path, dist_dir / dst_name)
            print(f"   ✅ 复制文件 {src_name}")

    # 处理配置文件
    config_example = project_root / "05_script" / "config.example.json"
    config_dst = dist_dir / "05_script" / "config.json"
    if config_example.exists() and not config_dst.exists():
        shutil.copy(config_example, config_dst)
        print("   📝 创建默认 config.json")

    # 处理源文件模板
    for f_name in ["core_setting", "overall_outline"]:
        example = project_root / "01_source" / f"{f_name}.example.yaml"
        dst = dist_dir / "01_source" / f"{f_name}.yaml"
        if example.exists() and not dst.exists():
            shutil.copy(example, dst)
            print(f"   📝 创建默认 {f_name}.yaml")


def build_cli():
    """构建 CLI 版本"""
    print("\n" + "=" * 50)
    print("🔨 开始构建 CLI 版本")
    print("=" * 50 + "\n")

    project_root = get_project_root()

    hiddenimports = [
        'novel_generator', 'novel_generator.cli',
        'novel_generator.cli.commands', 'novel_generator.utils.common',
        'yaml', 'requests', 'json', 'logging', 'volcenginesdkarkruntime',
    ]

    args = [
        'soundnovel.py',
        '--name=SoundNovelCLI',
        '--onedir',
        '--clean',
        '--noconfirm',
        '--console',
    ]

    for name in hiddenimports:
        args.append(f'--hidden-import={name}')

    print("🚀 执行 PyInstaller...")
    PyInstaller.__main__.run(args)

    dist_dir = project_root / "dist" / "SoundNovelCLI"
    if dist_dir.exists():
        copy_project_resources(dist_dir)
        create_launcher_scripts(dist_dir)
        create_zip(dist_dir, "SoundNovelAI_CLI")
        print("\n✅ CLI 版本构建完成！")


def create_launcher_scripts(dist_dir: Path):
    """创建启动器脚本"""
    bat_content = '''@echo off
chcp 65001 >nul
echo ===================================
echo   SoundNovel AI - 小说创作助手
echo ===================================
echo.
echo 使用方式:
echo   初始化: SoundNovelCLI.exe cli init
echo   生成大纲: SoundNovelCLI.exe cli outline
echo   扩写: SoundNovelCLI.exe cli expand --chapter 1
echo   Agent模式: SoundNovelCLI.exe cli agent
echo.
"SoundNovelCLI.exe" %*
'''

    (dist_dir / "启动程序.bat").write_text(bat_content, encoding='utf-8')
    print("   📝 创建启动脚本")


def create_zip(dist_dir: Path, zip_name: str):
    """创建 ZIP 压缩包"""
    print("\n📦 创建 ZIP 压缩包...")

    project_root = get_project_root()
    zip_base = project_root / "dist" / zip_name

    try:
        zip_path = shutil.make_archive(
            base_name=str(zip_base),
            format='zip',
            root_dir=str(dist_dir.parent),
            base_dir=dist_dir.name
        )
        print(f"   ✅ ZIP 创建成功")
    except Exception as e:
        print(f"   ⚠️  ZIP 创建失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='SoundNovel 打包脚本',
        epilog="""
使用示例:
    python build_exe.py           # 构建 CLI 版本
    python build_exe.py --clean   # 清理构建文件
        """
    )

    parser.add_argument('--clean', action='store_true', help='清理构建文件')

    args = parser.parse_args()

    if args.clean:
        clean_build()
        return

    print("🚀 SoundNovel 打包工具")
    print("=" * 50)

    build_cli()

    print("\n" + "=" * 50)
    print("🎉 构建完成！")
    print("=" * 50)


if __name__ == '__main__':
    exit(main())
