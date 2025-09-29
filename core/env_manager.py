# core/env_manager.py

import os
import subprocess
import sys

# 我们将路径的定义也集中在这里管理
# BASE_DIR 指向项目根目录 ProjectLauncher/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- 这里是唯一的修改 ---
# 将路径指向我们新的、完整的Python运行环境
PYTHON_RUNTIME_PATH = os.path.join(BASE_DIR, "python", "python.exe")
# -------------------------

ENVIRONMENTS_DIR = os.path.join(BASE_DIR, "environments")


def run_command(command, description=""):
    """
    一个辅助函数，用于执行命令并打印输出。
    增加了 description 参数，让输出更清晰。
    """
    if description:
        print(f"--- {description} ---")
    else:
        print(f"--- Running Command: {' '.join(command)} ---")

    try:
        # 确保 environments 目录存在
        os.makedirs(ENVIRONMENTS_DIR, exist_ok=True)

        result = subprocess.run(command, capture_output=True, text=True, check=True, encoding='utf-8')
        print(result.stdout)
        if result.stderr:
            print("--- Stderr ---")
            print(result.stderr)
        return True, "Command executed successfully."
    except FileNotFoundError:
        error_msg = f"Error: Command not found at {command[0]}"
        print(error_msg)
        return False, error_msg
    except subprocess.CalledProcessError as e:
        error_msg = f"Command failed with return code {e.returncode}.\n--- Stdout ---\n{e.stdout}\n--- Stderr ---\n{e.stderr}"
        print(error_msg)
        return False, error_msg
    except Exception as e:
        error_msg = f"An unexpected error occurred: {e}"
        print(error_msg)
        return False, error_msg
    finally:
        print("-" * 30)


class EnvironmentManager:
    """负责管理所有项目的虚拟环境"""
    def __init__(self):
        # 使用更新后的路径
        self.python_executable = PYTHON_RUNTIME_PATH
        self.environments_dir = ENVIRONMENTS_DIR
        print("EnvironmentManager initialized.")
        print(f"Using Full Python Runtime: {self.python_executable}")
        print(f"Environments root: {self.environments_dir}")
        print("-" * 30)

    def create_venv(self, project_id):
        """为指定的项目ID创建一个虚拟环境"""
        venv_name = f"{project_id}_venv"
        venv_path = os.path.join(self.environments_dir, venv_name)

        print(f"Attempting to create virtual environment for '{project_id}' at: {venv_path}")

        if os.path.exists(venv_path):
            print(f"Virtual environment for '{project_id}' already exists. Skipping creation.")
            return True, venv_path

        command = [self.python_executable, "-m", "venv", venv_path]

        success, message = run_command(command, description=f"Creating venv for {project_id}")

        if success:
            print(f"Successfully created virtual environment for '{project_id}'.")
        else:
            print(f"Failed to create virtual environment for '{project_id}'.")

        return success, venv_path