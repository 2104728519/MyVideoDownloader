# main_window.py

import sys
import os
import shutil
import json
import pygame
from PIL import Image

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTreeWidget, QTreeWidgetItem,
    QFileDialog, QMessageBox, QInputDialog, QSplitter, QMenu,
    QLabel, QToolButton
)
from PySide6.QtGui import QIcon, QPixmap, QAction, QFont
from PySide6.QtCore import Qt, QSize, QTimer

from core_utils import (
    extract_character_data_from_png, write_character_data_to_png,
    CARD_WORKSPACE, BOOK_WORKSPACE, CONFIG_FILE, get_base_path
)
from detail_view import DetailWidget
from create_card_dialog import CreateCharacterDialog
from settings_dialog import SettingsDialog

APP_DIR = get_base_path()


class DataManager:
    def __init__(self):
        self.characters = {}
        self.groups = {}
        self.settings = {}
        self.setup_workspace()
        self.load_config()

    def get_default_settings(self):
        return {"font_size": 10, "background_left": "", "opacity": 100, "music_playlist": [], "music_volume": 50}

    def setup_workspace(self):
        os.makedirs(CARD_WORKSPACE, exist_ok=True)
        os.makedirs(BOOK_WORKSPACE, exist_ok=True)
        os.makedirs(os.path.join(APP_DIR, "assets", "backgrounds"), exist_ok=True)
        os.makedirs(os.path.join(APP_DIR, "assets", "music"), exist_ok=True)
        os.makedirs(os.path.join(APP_DIR, "assets", "cache"), exist_ok=True)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
                self.groups = config_data.get("groups", {"未分组": []})
                self.settings = self.get_default_settings()
                self.settings.update(config_data.get("settings", {}))
        else:
            self.groups = {"未分组": []}
            self.settings = self.get_default_settings()

        all_card_paths = set(self.get_workspace_cards())
        for group in list(self.groups.keys()):
            self.groups[group] = [p for p in self.groups[group] if p in all_card_paths]

        grouped_paths = set(p for paths in self.groups.values() for p in paths)
        ungrouped = all_card_paths - grouped_paths
        self.groups.setdefault("未分组", []).extend(list(ungrouped))
        self.save_config()

    def save_config(self):
        config_data = {"groups": self.groups, "settings": self.settings}
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=4)

    def get_workspace_cards(self):
        return [os.path.join(CARD_WORKSPACE, f) for f in os.listdir(CARD_WORKSPACE) if f.lower().endswith('.png')]

    def load_character_data(self, path):
        if path not in self.characters:
            data, format_str = extract_character_data_from_png(path)
            if data:
                self.characters[path] = {'data': data, 'format': format_str}
            elif format_str == "Invalid Image":
                self.characters[path] = {'data': {'name': '[图片损坏或无法读取]'}, 'format': 'Invalid'}
            else:
                self.characters[path] = {'data': {'name': f'[无角色数据] {os.path.basename(path)}'}, 'format': 'No Data'}
        return self.characters.get(path)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("角色卡工作台")
        self.setGeometry(100, 100, 1600, 900)
        self.data_manager = DataManager()
        pygame.init()
        pygame.mixer.init()
        self.current_music_playlist = []
        self.current_song_index = 0
        self.is_music_paused = False
        self.music_check_timer = QTimer(self)
        self.music_check_timer.timeout.connect(self.check_music_status)
        self.music_check_timer.start(1000)
        self.init_ui()
        self.load_initial_data()
        self.apply_settings()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)

        self.left_panel = QWidget()
        self.left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(self.left_panel)

        button_layout = QHBoxLayout()
        self.settings_btn = QPushButton("设置")
        self.music_toggle_btn = QPushButton("▶ 播放")
        self.music_toggle_btn.setCheckable(True)
        self.music_toggle_btn.toggled.connect(self.toggle_music_playback)
        self.import_btn = QPushButton("导入角色卡")
        self.create_btn = QPushButton("新建角色卡")
        self.add_group_btn = QPushButton("添加分组")

        self.settings_btn.clicked.connect(self.open_settings_dialog)
        self.import_btn.clicked.connect(self.import_files)
        self.create_btn.clicked.connect(self.create_new_card)
        self.add_group_btn.clicked.connect(self.add_group)

        button_layout.addWidget(self.settings_btn)
        button_layout.addWidget(self.music_toggle_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.import_btn)
        button_layout.addWidget(self.create_btn)
        button_layout.addWidget(self.add_group_btn)
        left_layout.addLayout(button_layout)

        bulk_action_layout = QHBoxLayout()
        self.bulk_actions_btn = QToolButton()
        self.bulk_actions_btn.setText("批量操作 ▼")
        self.bulk_actions_btn.setPopupMode(QToolButton.InstantPopup)
        bulk_menu = QMenu(self)
        self.import_folder_action = QAction("一键导入文件夹", self)
        self.delete_selected_action = QAction("一键删除选中", self)
        self.export_selected_action = QAction("一键导出选中", self)
        bulk_menu.addAction(self.import_folder_action)
        bulk_menu.addAction(self.delete_selected_action)
        bulk_menu.addAction(self.export_selected_action)
        self.bulk_actions_btn.setMenu(bulk_menu)
        bulk_action_layout.addWidget(self.bulk_actions_btn)
        bulk_action_layout.addStretch()
        left_layout.addLayout(bulk_action_layout)

        self.char_tree = QTreeWidget()
        self.char_tree.setHeaderLabel("角色分组")
        self.char_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.char_tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        self.char_tree.itemDoubleClicked.connect(self.open_detail_view)
        self.char_tree.setDragEnabled(True)
        self.char_tree.setAcceptDrops(True)
        self.char_tree.setDropIndicatorShown(True)
        self.char_tree.setDragDropMode(QTreeWidget.InternalMove)
        self.char_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        left_layout.addWidget(self.char_tree)

        self.right_panel = QWidget()
        self.right_panel.setObjectName("rightPanel")
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.addWidget(QLabel("双击左侧角色以查看/编辑详情"))

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.right_panel)
        splitter.setSizes([400, 1200])
        main_layout.addWidget(splitter)

        self.import_folder_action.triggered.connect(self.import_folder)
        self.delete_selected_action.triggered.connect(self.delete_selected_characters)
        self.export_selected_action.triggered.connect(self.export_selected_characters)

    def check_music_status(self):
        if self.current_music_playlist and not self.is_music_paused and not pygame.mixer.music.get_busy():
            self.play_next_song()

    def play_next_song(self):
        if not self.current_music_playlist:
            self.music_toggle_btn.setChecked(False)
            return
        song_path = self.current_music_playlist[self.current_song_index]
        try:
            pygame.mixer.music.load(song_path)
            volume = self.data_manager.settings.get('music_volume', 50) / 100.0
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play()
            self.current_song_index = (self.current_song_index + 1) % len(self.current_music_playlist)
        except pygame.error as e:
            print(f"无法播放音乐文件 {song_path}: {e}")
            self.current_song_index = (self.current_song_index + 1) % len(self.current_music_playlist)
            self.play_next_song()

    def toggle_music_playback(self, checked):
        if checked:
            self.music_toggle_btn.setText("❚❚❚❚ 暂停")
            if self.is_music_paused:
                pygame.mixer.music.unpause()
            else:
                self.play_next_song()
            self.is_music_paused = False
        else:
            self.music_toggle_btn.setText("▶ 播放")
            pygame.mixer.music.pause()
            self.is_music_paused = True

    def export_selected_characters(self):
        """任务3：修改一键导出功能，使用角色名称作为文件名"""
        selected_items = self.char_tree.selectedItems()
        char_items_to_export = [item for item in selected_items if item.data(0, Qt.UserRole) != "group"]

        if not char_items_to_export:
            QMessageBox.warning(self, "未选择", "请先在列表中选择要导出的角色卡。")
            return

        export_dir = QFileDialog.getExistingDirectory(self, "选择导出目录")
        if not export_dir:
            return

        exported_count = 0
        for item in char_items_to_export:
            char_path = item.data(0, Qt.UserRole)
            char_info = self.data_manager.load_character_data(char_path)

            if not char_info:
                QMessageBox.warning(self, "数据错误", f"无法读取角色卡数据: {char_path}")
                continue

            # 获取角色名称
            data = char_info['data']
            char_name = data.get("data", {}).get("name") or data.get("name", "Unnamed")

            # 安全化文件名
            safe_char_name = "".join(c for c in char_name if c.isalnum() or c in " _-").rstrip()
            if not safe_char_name:
                safe_char_name = "Unnamed"

            # 使用角色名称作为文件名
            dest_path = os.path.join(export_dir, f"{safe_char_name}.png")

            # 处理文件名冲突
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(dest_path)
                i = 1
                while os.path.exists(dest_path):
                    dest_path = f"{base}_{i}{ext}"
                    i += 1

            try:
                shutil.copy2(char_path, dest_path)
                exported_count += 1
            except Exception as e:
                QMessageBox.critical(self, "导出失败", f"导出角色卡 {char_name} 时出错: {e}")

        QMessageBox.information(self, "导出成功", f"成功导出 {exported_count} 张角色卡到目录: {export_dir}")

    def open_settings_dialog(self):
        dialog = SettingsDialog(self.data_manager.settings, self)
        if dialog.exec():
            new_settings = dialog.get_settings()
            self.data_manager.settings = new_settings
            self.data_manager.save_config()
            self.apply_settings()

    def apply_settings(self):
        settings = self.data_manager.settings
        font = QFont()
        font.setPointSize(settings.get('font_size', 10))
        QApplication.instance().setFont(font)

        opacity_percent = settings.get('opacity', 100)
        opacity_value = opacity_percent / 100.0
        ui_bg_color = "255, 255, 255" if settings.get('font_size', 10) < 18 else "40, 40, 40"
        ui_fg_color = "black" if settings.get('font_size', 10) < 18 else "white"

        base_style = f"""
            #leftPanel, #rightPanel {{ background-color: transparent; border: none; }}
            #leftPanel > QWidget, #rightPanel > QWidget,
            QFrame, QGroupBox, QTabWidget::pane, QScrollArea {{
                background-color: rgba({ui_bg_color}, {opacity_value * 0.85}); border-radius: 5px;
            }}
            QLabel, QPushButton, QCheckBox, QRadioButton, QSpinBox, QToolButton {{
                background-color: transparent; color: {ui_fg_color};
            }}
            QTreeWidget, QTextEdit, QLineEdit, QListWidget {{
                 background-color: rgba({ui_bg_color}, {opacity_value}); color: {ui_fg_color};
            }}
        """

        bg_path = settings.get('background_left', "")
        if bg_path and os.path.exists(bg_path):
            formatted_path = bg_path.replace("\\", "/")
            base_style += f"""
                #leftPanel {{
                    background-image: url({formatted_path});
                    background-size: cover;
                    background-position: center center;
                    background-repeat: no-repeat;
                }}
            """

        self.setStyleSheet(base_style)

        new_playlist = [f for f in settings.get('music_playlist', []) if os.path.exists(f)]
        if new_playlist != self.current_music_playlist:
            self.current_music_playlist = new_playlist
            pygame.mixer.music.stop()
            if self.current_music_playlist:
                self.current_song_index = 0
                self.music_toggle_btn.setChecked(True)
            else:
                self.music_toggle_btn.setChecked(False)

    def create_new_card(self):
        dialog = CreateCharacterDialog(self)
        if not dialog.exec():
            return

        card_info, image_path = dialog.get_data()
        greetings_text = card_info.get("alternate_greetings", "")
        alt_greetings_list = [line.strip() for line in greetings_text.split('\n') if line.strip()]
        tags_str = card_info.get("tags", "")
        tags_list = [tag.strip() for tag in tags_str.split(',') if tag.strip()]

        full_card_data = {
            "spec": "chara_card_v2",
            "spec_version": "2.0",
            "data": {
                "name": card_info.get("name", ""),
                "description": card_info.get("description", ""),
                "personality": card_info.get("personality", ""),
                "scenario": card_info.get("scenario", ""),
                "first_mes": card_info.get("first_mes", ""),
                "mes_example": card_info.get("mes_example", ""),
                "creator_notes": card_info.get("creator_notes", ""),
                "system_prompt": card_info.get("system_prompt", ""),
                "post_history_instructions": card_info.get("post_history_instructions", ""),
                "tags": tags_list,
                "creator": card_info.get("creator", ""),
                "character_version": card_info.get("character_version", ""),
                "alternate_greetings": alt_greetings_list,
                "character_book": {"name": "", "entries": []},
                "extensions": {}
            }
        }

        base_name = "".join(x for x in card_info.get("name") if x.isalnum()) or "NewCharacter"
        dest_path = os.path.join(CARD_WORKSPACE, f"{base_name}.png")

        if os.path.exists(dest_path):
            i = 1
            while os.path.exists(dest_path):
                dest_path = os.path.join(CARD_WORKSPACE, f"{base_name}_{i}.png")
                i += 1

        try:
            with Image.open(image_path) as img:
                img.save(dest_path, 'PNG')
        except Exception as e:
            QMessageBox.critical(self, "图片转换失败", f"无法将所选图片转换为PNG格式: {e}")
            return

        success, message = write_character_data_to_png(dest_path, full_card_data)
        if success:
            QMessageBox.information(self, "成功", f"角色卡 '{card_info.get('name')}' 已成功创建!")
            self.data_manager.groups.setdefault("未分组", []).append(dest_path)
            self.data_manager.save_config()
            self.load_initial_data()
        else:
            QMessageBox.critical(self, "写入失败", f"无法将角色数据写入PNG: {message}")
            os.remove(dest_path)

    def handle_drop_event(self, event):
        item = self.char_tree.itemAt(event.pos())
        if not item:
            return

        dragged_item = self.char_tree.selectedItems()[0]
        if dragged_item.parent() is None:
            return

        target_group_item = item if item.parent() is None else item.parent()
        old_group_name = dragged_item.parent().text(0)
        new_group_name = target_group_item.text(0)
        char_path = dragged_item.data(0, Qt.UserRole)

        if old_group_name != new_group_name:
            self.data_manager.groups[old_group_name].remove(char_path)

        self.data_manager.groups[new_group_name].append(char_path)
        self.data_manager.save_config()

        dragged_item.parent().removeChild(dragged_item)
        target_group_item.addChild(dragged_item)

    def load_initial_data(self):
        """任务2：修改左侧角色卡显示名称，移除格式后缀"""
        self.char_tree.clear()

        for group_name, paths in self.data_manager.groups.items():
            group_item = QTreeWidgetItem(self.char_tree, [group_name])
            group_item.setData(0, Qt.UserRole, "group")

            for path in paths:
                char_info = self.data_manager.load_character_data(path)
                if char_info:
                    data = char_info['data']
                    format_str = char_info['format']

                    # 只显示角色名称，不显示格式信息
                    display_name = data.get("data", {}).get("name") or data.get("name", "未知名称")

                    char_item = QTreeWidgetItem(group_item, [display_name])
                    char_item.setData(0, Qt.UserRole, path)

                    if format_str != "Invalid":
                        pixmap = QPixmap(path)
                        icon = QIcon(pixmap.scaled(QSize(64, 64), Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        char_item.setIcon(0, icon)

            group_item.setExpanded(True)

    def import_files(self):
        original_paths, _ = QFileDialog.getOpenFileNames(self, "选择角色卡", "", "PNG Files (*.png)")
        if original_paths:
            self.copy_files_to_workspace(original_paths)

    def import_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择包含角色卡的文件夹")
        if not folder_path:
            return

        png_files = [os.path.join(folder_path, f) for f in os.listdir(folder_path) if f.lower().endswith('.png')]
        if not png_files:
            QMessageBox.information(self, "未找到文件", "该文件夹中没有找到任何PNG文件。")
            return

        self.copy_files_to_workspace(png_files)

    def copy_files_to_workspace(self, file_paths):
        imported_count = 0
        for original_path in file_paths:
            filename = os.path.basename(original_path)
            dest_path = os.path.join(CARD_WORKSPACE, filename)

            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                i = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(CARD_WORKSPACE, f"{base}_{i}{ext}")
                    i += 1

            shutil.copy2(original_path, dest_path)
            self.data_manager.groups.setdefault("未分组", []).append(dest_path)
            imported_count += 1

        if imported_count > 0:
            self.data_manager.save_config()
            self.load_initial_data()
            QMessageBox.information(self, "导入成功", f"成功导入 {imported_count} 张角色卡。")

    def add_group(self):
        text, ok = QInputDialog.getText(self, '添加分组', '请输入新的分组名称:')
        if ok and text and text not in self.data_manager.groups:
            self.data_manager.groups[text] = []
            self.data_manager.save_config()
            self.load_initial_data()

    def show_tree_context_menu(self, position):
        item = self.char_tree.itemAt(position)
        if not item:
            return

        menu = QMenu()
        item_type = item.data(0, Qt.UserRole)

        if item_type == "group":
            rename_action = QAction("重命名分组", self)
            delete_action = QAction("删除分组", self)
            rename_action.triggered.connect(lambda: self.rename_group(item))
            delete_action.triggered.connect(lambda: self.delete_group(item))
            menu.addAction(rename_action)
            if item.text(0) != "未分组" and item.childCount() == 0:
                menu.addAction(delete_action)
        else:
            delete_action = QAction("删除角色卡", self)
            delete_action.triggered.connect(lambda: self.delete_character(item))
            menu.addAction(delete_action)

        menu.exec(self.char_tree.mapToGlobal(position))

    def rename_group(self, item):
        old_name = item.text(0)
        new_name, ok = QInputDialog.getText(self, "重命名分组", "新名称:", text=old_name)
        if ok and new_name and new_name != old_name and new_name not in self.data_manager.groups:
            self.data_manager.groups[new_name] = self.data_manager.groups.pop(old_name)
            self.data_manager.save_config()
            item.setText(0, new_name)

    def delete_group(self, item):
        group_name = item.text(0)
        reply = QMessageBox.question(self, "确认删除", f"确定要删除分组 '{group_name}' 吗?(角色卡将移至'未分组')")
        if reply == QMessageBox.Yes:
            paths = self.data_manager.groups.pop(group_name, [])
            self.data_manager.groups.setdefault("未分组", []).extend(paths)
            self.data_manager.save_config()
            self.load_initial_data()

    def delete_character(self, item):
        char_path = item.data(0, Qt.UserRole)
        char_name = item.text(0)
        reply = QMessageBox.question(self, "确认删除", f"确定要删除角色 '{char_name}' 吗?\n这将从工作区永久删除文件。")
        if reply == QMessageBox.Yes:
            self.delete_card_logic([item])

    def delete_selected_characters(self):
        selected_items = self.char_tree.selectedItems()
        char_items_to_delete = [item for item in selected_items if item.data(0, Qt.UserRole) != "group"]

        if not char_items_to_delete:
            QMessageBox.warning(self, "未选择", "请先在列表中选择要删除的角色卡。")
            return

        reply = QMessageBox.question(self, "确认删除", f"确定要删除选中的 {len(char_items_to_delete)} 张角色卡吗?\n这将从工作区永久删除文件。")
        if reply == QMessageBox.Yes:
            self.delete_card_logic(char_items_to_delete)

    def delete_card_logic(self, items_to_delete):
        for item in items_to_delete:
            char_path = item.data(0, Qt.UserRole)
            group_name = item.parent().text(0)

            if char_path in self.data_manager.groups.get(group_name, []):
                self.data_manager.groups[group_name].remove(char_path)

            self.data_manager.characters.pop(char_path, None)

            try:
                if os.path.exists(char_path):
                    os.remove(char_path)
            except OSError as e:
                QMessageBox.critical(self, "删除失败", f"无法删除文件: {char_path}\n错误: {e}")
                continue

            if item.parent():
                item.parent().removeChild(item)

        self.data_manager.save_config()
        QMessageBox.information(self, "删除成功", f"已成功删除 {len(items_to_delete)} 张角色卡。")

    def open_detail_view(self, item):
        item_data = item.data(0, Qt.UserRole)
        if item_data == "group" or not isinstance(item_data, str):
            return

        char_path = item_data
        char_info = self.data_manager.load_character_data(char_path)

        if not char_info or char_info['format'] == 'Invalid':
            QMessageBox.warning(self, "无法打开", "此文件无法读取或不包含有效的角色数据。")
            return

        for i in reversed(range(self.right_layout.count())):
            widget_to_remove = self.right_layout.itemAt(i).widget()
            if widget_to_remove:
                widget_to_remove.setParent(None)

        self.detail_widget = DetailWidget(char_path, char_info, self.data_manager, self)
        self.right_layout.addWidget(self.detail_widget)

    def closeEvent(self, event):
        pygame.quit()
        event.accept()