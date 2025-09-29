# core/project_manager.py

import os
import requests
import zipfile
import shutil
import subprocess
import math

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
CACHE_DIR = os.path.join(BASE_DIR, "cache")
ENVIRONMENTS_DIR = os.path.join(BASE_DIR, "environments")


def run_command(command, description=""):
    # ... (无变化)
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        print(result.stdout);
        print(result.stderr)
        return True, "Success"
    except Exception:
        return False, "Error"


class ProjectManager:
    def __init__(self, project_id, project_data):
        self.project_id = project_id
        self.project_data = project_data
        self.name = project_data.get("name", "Unknown Project")
        # 新增：读取项目类型，默认为 'python'
        self.type = project_data.get("type", "python")
        self.source_url = project_data.get("source_url")
        self.requirements = project_data.get("requirements")
        self.entry_point = project_data.get("entry_point")
        self.project_dir = os.path.join(PROJECTS_DIR, self.project_id)
        self.cache_zip_path = os.path.join(CACHE_DIR, f"{self.project_id}.zip")

    def install_dependencies(self, venv_path):
        """只有python项目才需要安装依赖。"""
        if self.type != "python":
            print("非Python项目，跳过依赖安装。")
            return True  # 直接视为成功

        if not self.requirements: return True
        pip = os.path.join(venv_path, "Scripts", "pip.exe")
        req_file = os.path.join(self.project_dir, self.requirements)
        if not os.path.exists(pip) or not os.path.exists(req_file): return True
        return run_command([pip, "install", "-r", req_file])[0]

    def run(self, venv_path):
        """根据项目类型，用不同的方式运行。"""
        print(f"--- Attempting to run project of type: {self.type} ---")
        if not self.entry_point:
            print("No entry_point defined. Cannot run.")
            return

        if self.type == "python":
            # --- Python 项目的运行逻辑 ---
            python_executable = os.path.join(venv_path, "Scripts", "python.exe")
            entry_script = os.path.join(self.project_dir, self.entry_point)
            if not os.path.exists(python_executable) or not os.path.exists(entry_script):
                print("Python或入口脚本未找到！")
                return
            command = [python_executable, entry_script]

        elif self.type == "executable":
            # --- 可执行文件项目的运行逻辑 ---
            executable_path = os.path.join(self.project_dir, self.entry_point)
            if not os.path.exists(executable_path):
                print(f"可执行文件未找到: {executable_path}")
                return
            command = [executable_path]

        else:
            print(f"未知的项目类型: {self.type}")
            return

        try:
            print(f"Launching command: {' '.join(command)}")
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW
            subprocess.Popen(command, cwd=self.project_dir, creationflags=flags)
        except Exception as e:
            print(f"启动失败: {e}")

    # ... (download, unzip, install, delete 方法无变化)
    def download(self, progress_callback=None):
        if not self.source_url: return False
        try:
            with requests.get(self.source_url, stream=True) as r:
                r.raise_for_status()
                total_size = int(r.headers.get('content-length', 0))
                dl_size = 0
                with open(self.cache_zip_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                        dl_size += len(chunk)
                        if progress_callback and total_size > 0:
                            progress_callback(math.ceil((dl_size / total_size) * 100))
            if progress_callback: progress_callback(100)
            return True
        except Exception:
            return False

    def unzip(self):
        if not os.path.exists(self.cache_zip_path): return False
        if os.path.exists(self.project_dir): shutil.rmtree(self.project_dir)
        os.makedirs(self.project_dir)
        temp_dir = os.path.join(CACHE_DIR, f"{self.project_id}_temp")
        if os.path.exists(temp_dir): shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        try:
            with zipfile.ZipFile(self.cache_zip_path, 'r') as zf:
                zf.extractall(temp_dir)
            items = os.listdir(temp_dir)
            src_dir = temp_dir
            if len(items) == 1 and os.path.isdir(os.path.join(temp_dir, items[0])):
                src_dir = os.path.join(temp_dir, items[0])
            for item in os.listdir(src_dir):
                shutil.move(os.path.join(src_dir, item), self.project_dir)
            return True
        except Exception:
            return False
        finally:
            if os.path.exists(temp_dir): shutil.rmtree(temp_dir)

    def install(self, venv_path, progress_callback=None):
        if self.source_url:
            if not self.download(progress_callback=progress_callback) or not self.unzip(): return False
        if not self.install_dependencies(venv_path): return False
        return True

    def delete(self):
        try:
            venv_path = os.path.join(ENVIRONMENTS_DIR, f"{self.project_id}_venv")
            if os.path.exists(self.project_dir): shutil.rmtree(self.project_dir)
            if os.path.exists(venv_path): shutil.rmtree(venv_path)
            return True
        except Exception:
            return False