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
    # Ensure we can find the app
    app_path = resolve_path("gui_app.py")
    
    # Set up arguments for streamlit
    sys.argv = [
        "streamlit",
        "run",
        app_path,
        "--global.developmentMode=false",
    ]
    
    # Run streamlit
    sys.exit(stcli.main())
