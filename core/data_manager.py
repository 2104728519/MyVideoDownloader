# core/data_manager.py

import json
import os

# 定义数据文件的路径
# os.path.dirname(__file__) -> core/
# os.path.dirname(...) -> ProjectLauncher/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_FILE = os.path.join(BASE_DIR, "projects.json")

def load_projects():
    """从 projects.json 文件加载项目列表。"""
    if not os.path.exists(PROJECTS_FILE):
        return {}  # 如果文件不存在，返回空字典
    try:
        with open(PROJECTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        print(f"警告: 无法读取或解析 {PROJECTS_FILE}。将使用空的项目列表。")
        return {} # 如果文件损坏或读取错误，也返回空字典

def save_projects(projects_data):
    """将项目列表数据保存到 projects.json 文件。"""
    try:
        with open(PROJECTS_FILE, 'w', encoding='utf-8') as f:
            # indent=4 让json文件格式化，更易读
            # ensure_ascii=False 确保中文字符能被正确写入
            json.dump(projects_data, f, indent=4, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"错误: 无法写入到 {PROJECTS_FILE}: {e}")
        return False