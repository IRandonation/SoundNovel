import yaml
from pathlib import Path
import requests

def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def select_from_list(prompt, options):
    """从列表中让用户选择一项"""
    print(f"{prompt}:")
    for i, opt in enumerate(options, 1):
        print(f"{i}. {opt}")
    while True:
        choice = input("请选择(1-{}): ".format(len(options)))
        if choice.isdigit() and 1 <= int(choice) <= len(options):
            return options[int(choice)-1]
        print("无效输入，请重新选择")

def load_prompt(name):
    path = Path("prompts") / f"{name}.md"
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def call_api(prompt, system_msg, temp, max_tokens):
    config = load_config()
    headers = {
        "Authorization": f"Bearer {config['api']['key']}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": config["api"]["model"],
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ],
        "temperature": temp,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"}
    }
    response = requests.post(config["api"]["url"], headers=headers, json=payload)
    return response.json()["choices"][0]["message"]["content"]