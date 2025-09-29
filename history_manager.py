# history_manager.py

import json
import os

HISTORY_FILE = "download_history.json"

def load_history():
    """
    加载历史下载记录。
    如果历史文件不存在，返回一个空列表。
    """
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
    return []

def save_history(title, duration, url):
    """
    保存一条新的下载记录到历史文件中。
    """
    history = load_history()
    new_entry = {
        "title": title,
        "duration": duration,
        "url": url
    }
    history.insert(0, new_entry) # 在列表开头插入新记录
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=4)