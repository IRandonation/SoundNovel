import os
import sys
import streamlit.web.cli as stcli
from pathlib import Path

# Dummy imports to ensure PyInstaller bundles these modules
if False:
    import gui_app
    import novel_generator
    import yaml
    import json
    import logging

def resolve_path(path):
    if getattr(sys, "frozen", False):
        basedir = sys._MEIPASS
    else:
        basedir = os.path.dirname(__file__)
    return os.path.join(basedir, path)

if __name__ == "__main__":
    try:
        # Ensure we can find the app
        app_path = resolve_path("gui_app.py")
        
        if not os.path.exists(app_path):
            print(f"Error: Could not find app script at {app_path}")
            input("Press Enter to exit...")
            sys.exit(1)

        # Set up arguments for streamlit
        sys.argv = [
            "streamlit",
            "run",
            app_path,
            "--global.developmentMode=false",
            "--server.headless=false",  # Ensure browser opens
        ]
        
        # Run streamlit
        sys.exit(stcli.main())
    except Exception as e:
        import traceback
        print("An error occurred during startup:")
        traceback.print_exc()
        input("\nPress Enter to exit...")
        sys.exit(1)
