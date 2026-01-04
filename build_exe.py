import PyInstaller.__main__
import os
import shutil
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

def build():
    # 1. PyInstaller Build
    datas = []
    binaries = []
    hiddenimports = []
    
    # Collect streamlit data
    st_datas, st_binaries, st_hiddenimports = collect_all('streamlit')
    datas.extend(st_datas)
    binaries.extend(st_binaries)
    hiddenimports.extend(st_hiddenimports)
    
    # Add gui_app.py as data so it can be run by streamlit
    datas.append(('gui_app.py', '.'))
    
    # Ensure novel_generator is included
    hiddenimports.append('novel_generator')
    
    # Build command args
    args = [
        'run_gui.py',
        '--name=SoundNovelAI',
        '--onedir',
        '--clean',
        '--noconfirm',
        '--windowed',
    ]
    
    for src, dst in datas:
        args.append(f'--add-data={src}{os.pathsep}{dst}')
        
    for name in hiddenimports:
        args.append(f'--hidden-import={name}')
        
    print("🚀 Starting PyInstaller build...")
    PyInstaller.__main__.run(args)
    print("✅ PyInstaller Build complete!")

    # 2. Post-build: Copy resources to dist folder
    print("📂 Copying resources to dist folder...")
    
    project_root = Path(__file__).parent.resolve()
    dist_dir = project_root / "dist" / "SoundNovelAI"
    
    if not dist_dir.exists():
        print(f"❌ Error: Dist directory {dist_dir} not found!")
        return

    # Directories to copy (source -> dest)
    dirs_to_copy = [
        ("01_source", "01_source"),
        ("04_prompt", "04_prompt"),
        ("05_script", "05_script"),
    ]
    
    # Directories to create (empty)
    dirs_to_create = [
        "02_outline",
        "03_draft",
        "06_log",
    ]

    # Copy directories
    for src_name, dst_name in dirs_to_copy:
        src_path = project_root / src_name
        dst_path = dist_dir / dst_name
        
        if src_path.exists():
            if dst_path.exists():
                shutil.rmtree(dst_path)
            shutil.copytree(src_path, dst_path)
            print(f"   ✅ Copied {src_name} -> {dst_path}")
            
            # Special handling for config files inside copied directories
            if src_name == "05_script":
                # Ensure config.json exists
                config_json = dst_path / "config.json"
                config_example = dst_path / "config.example.json"
                if not config_json.exists() and config_example.exists():
                    shutil.copy(config_example, config_json)
                    print(f"      📝 Created default config.json from example")
            
            if src_name == "01_source":
                # Ensure core_setting.yaml and overall_outline.yaml exist
                for f_name in ["core_setting", "overall_outline"]:
                    yaml_path = dst_path / f"{f_name}.yaml"
                    example_path = dst_path / f"{f_name}.example.yaml"
                    if not yaml_path.exists() and example_path.exists():
                        shutil.copy(example_path, yaml_path)
                        print(f"      📝 Created default {f_name}.yaml from example")

        else:
            print(f"   ⚠️ Warning: Source directory {src_name} not found")

    # Create empty directories
    for dir_name in dirs_to_create:
        dir_path = dist_dir / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"   ✅ Created directory {dir_name}")

    print("\n🎉 All done! You can now zip the following folder and share it:")
    print(f"   👉 {dist_dir}")

if __name__ == '__main__':
    build()
