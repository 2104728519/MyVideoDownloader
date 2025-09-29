# launcher_ui.py

import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QLabel, QWidget,
                               QVBoxLayout, QHBoxLayout, QFrame, QScrollArea, QPushButton,
                               QSizePolicy, QMessageBox, QProgressBar, QPlainTextEdit)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont, QTextCursor

from core.data_manager import load_projects
from core.env_manager import EnvironmentManager
from core.project_manager import ProjectManager


class Worker(QThread):
    # ... (Worker 类无变化)
    finished = Signal(str, str)
    error = Signal(str, str)
    log = Signal(str)
    progress_updated = Signal(int)

    def __init__(self, project_id, project_data, venv_path, task_type):
        super().__init__()
        self.project_id, self.project_data, self.venv_path, self.task_type = project_id, project_data, venv_path, task_type

    def run(self):
        self.log.emit(f"开始执行 '{self.project_data['name']}' 的 {self.task_type} 任务...")
        pm = ProjectManager(self.project_id, self.project_data)
        try:
            success = False
            if self.task_type == 'install':
                self.log.emit("开始下载项目文件...")
                success = pm.install(self.venv_path, progress_callback=lambda p: self.progress_updated.emit(p))
            elif self.task_type == 'run':
                pm.run(self.venv_path)
                success = True
            elif self.task_type == 'delete':
                success = pm.delete()
            if success:
                self.finished.emit(self.project_id, self.task_type)
            else:
                raise Exception(f"{self.task_type.capitalize()} 任务失败。")
        except Exception as e:
            self.log.emit(f"错误: {e}")
            self.error.emit(self.project_id, str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        # ... (__init__ 无变化)
        super().__init__()
        self.projects = load_projects()
        self.env_manager = EnvironmentManager()
        self.setWindowTitle("项目启动器")
        self.setGeometry(100, 100, 800, 700)
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.main_layout = QVBoxLayout(main_widget)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        container = QWidget()
        scroll_area.setWidget(container)
        self.projects_layout = QVBoxLayout(container)
        self.log_area = QPlainTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #2b2b2b; color: #f0f0f0;")
        self.log_area.setMaximumHeight(200)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.status_label = QLabel("欢迎使用！")
        self.status_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.main_layout.addWidget(scroll_area)
        self.main_layout.addWidget(self.log_area)
        self.main_layout.addWidget(self.progress_bar)
        self.main_layout.addWidget(self.status_label)
        self.create_project_widgets()

    def start_task(self, project_id, project_data, task_type):
        """根据项目类型，智能决定是否创建虚拟环境。"""
        self.set_buttons_enabled(False)
        self.append_log(f"--- 新任务开始: {task_type} for {project_data['name']} ---")

        venv_path = None
        project_type = project_data.get("type", "python")

        # --- 核心优化 ---
        if project_type == "python":
            self.update_status(f"正在为 Python 项目 '{project_data['name']}' 准备环境...")
            self.append_log("项目类型为 Python，正在准备虚拟环境...")
            success, venv_path = self.env_manager.create_venv(project_id)
            if not success and task_type not in ['delete']:
                self.update_status("环境准备失败！")
                self.set_buttons_enabled(True)
                return
        else:
            self.update_status(f"正在处理可执行文件项目 '{project_data['name']}'...")
            self.append_log(f"项目类型为 {project_type}，跳过虚拟环境创建。")

        # 启动后台线程
        self.worker = Worker(project_id, project_data, venv_path, task_type)
        self.worker.log.connect(self.append_log)
        self.worker.error.connect(self.task_error)
        self.worker.finished.connect(self.task_finished)
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.start()

    # ... (所有其他方法 create_project_widgets, confirm_delete, update_status, 等都无变化)
    def create_project_widgets(self):
        for pid, pdata in self.projects.items():
            card = QFrame()
            card.setFrameShape(QFrame.StyledPanel)
            card.setFrameShadow(QFrame.Raised)
            layout = QVBoxLayout(card)
            name = QLabel(pdata.get("name", "未知"))
            font = QFont()
            font.setBold(True)
            font.setPointSize(14)
            name.setFont(font)
            desc = QLabel(pdata.get("description", ""))
            desc.setWordWrap(True)
            layout.addWidget(name)
            layout.addWidget(desc)
            pm = ProjectManager(pid, pdata)
            is_installed = os.path.exists(pm.project_dir)
            if is_installed:
                btn_layout = QHBoxLayout()
                launch_btn = QPushButton("启动")
                launch_btn.setStyleSheet("background-color: #4CAF50; color: white;")
                launch_btn.clicked.connect(lambda c, p=pid, d=pdata: self.start_task(p, d, 'run'))
                delete_btn = QPushButton("删除")
                delete_btn.setStyleSheet("background-color: #f44336; color: white;")
                delete_btn.clicked.connect(lambda c, p=pid, d=pdata: self.confirm_delete(p, d))
                btn_layout.addWidget(launch_btn)
                btn_layout.addWidget(delete_btn)
                layout.addLayout(btn_layout)
            else:
                install_btn = QPushButton("安装")
                install_btn.setStyleSheet("background-color: #008CBA; color: white;")
                install_btn.clicked.connect(lambda c, p=pid, d=pdata: self.start_task(p, d, 'install'))
                layout.addWidget(install_btn)
            self.projects_layout.addWidget(card)
        self.projects_layout.addStretch()

    def confirm_delete(self, pid, pdata):
        if QMessageBox.question(self, '确认删除', f"确定删除 '{pdata.get('name')}'?", QMessageBox.Yes | QMessageBox.No,
                                QMessageBox.No) == QMessageBox.Yes:
            self.start_task(pid, pdata, 'delete')

    def update_status(self, msg):
        self.status_label.setText(msg)

    def append_log(self, msg):
        self.log_area.appendPlainText(msg); self.log_area.moveCursor(QTextCursor.End)

    def update_progress(self, val):
        if not self.progress_bar.isVisible(): self.progress_bar.setVisible(True)
        self.progress_bar.setValue(val)

    def task_finished(self, pid, task_type):
        name = self.projects[pid]['name']
        self.update_status(f"'{name}' {task_type} 任务成功！")
        self.append_log(f"--- 任务成功 ---")
        self.set_buttons_enabled(True);
        self.progress_bar.setVisible(False)
        if task_type in ['install', 'delete']: self.refresh_ui()

    def task_error(self, pid, err_msg):
        name = self.projects[pid]['name']
        self.update_status(f"'{name}' 任务失败: {err_msg}")
        self.append_log(f"--- 任务失败 ---")
        self.set_buttons_enabled(True)
        self.progress_bar.setVisible(False)

    def set_buttons_enabled(self, enabled):
        for card in self.findChildren(QFrame):
            for btn in card.findChildren(QPushButton): btn.setEnabled(enabled)

    def refresh_ui(self):
        while self.projects_layout.count():
            item = self.projects_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget(): sub_item.widget().deleteLater()
        self.projects = load_projects()
        self.create_project_widgets()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())