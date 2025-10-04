import os
import json
import shutil
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QTextEdit, QTabWidget, QScrollArea, QFrame, QCheckBox, QFileDialog, QMessageBox,
    QSpinBox, QToolButton, QSizePolicy, QDialog, QDialogButtonBox, QGridLayout,
    QGroupBox
)
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt, QSize, Slot

from core_utils import write_character_data_to_png, BOOK_WORKSPACE


class AutoResizingTextEdit(QTextEdit):
    # ... (此类无变化)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.document().contentsChanged.connect(self.updateGeometry)
        self.setLineWrapMode(QTextEdit.WidgetWidth)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def sizeHint(self):
        doc_size = self.document().size()
        height = doc_size.height() + self.contentsMargins().top() + self.contentsMargins().bottom()
        return QSize(int(doc_size.width()), int(height))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateGeometry()


class AddEntryDialog(QDialog):
    # ... (此类无变化)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加新世界书条目");
        self.setMinimumWidth(500);
        self.layout = QVBoxLayout(self)
        self.keys_edit = QLineEdit();
        self.layout.addWidget(QLabel("关键词 (逗号分隔):"));
        self.layout.addWidget(self.keys_edit)
        self.content_edit = QTextEdit();
        self.content_edit.setMinimumHeight(150);
        self.layout.addWidget(QLabel("内容:"));
        self.layout.addWidget(self.content_edit)
        self.enabled_check = QCheckBox("启用此条目");
        self.enabled_check.setChecked(True);
        self.layout.addWidget(self.enabled_check)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel);
        self.button_box.accepted.connect(self.accept);
        self.button_box.rejected.connect(self.reject);
        self.layout.addWidget(self.button_box)

    def get_data(self):
        keys_str = self.keys_edit.text().strip();
        keys = [k.strip() for k in keys_str.split(',') if k.strip()]
        return {"keys": keys, "content": self.content_edit.toPlainText().strip(),
                "enabled": self.enabled_check.isChecked()}


class CollapsibleBox(QWidget):
    # ... (此类无变化)
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.toggle_button = QToolButton();
        self.toggle_button.setText(title);
        self.toggle_button.setCheckable(True);
        self.toggle_button.setStyleSheet("QToolButton { border: none; text-align: left; font-weight: bold; }");
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon);
        self.toggle_button.setArrowType(Qt.RightArrow)
        self.content_area = QWidget();
        main_layout = QVBoxLayout(self);
        main_layout.setSpacing(0);
        main_layout.setContentsMargins(0, 0, 0, 0);
        main_layout.addWidget(self.toggle_button);
        main_layout.addWidget(self.content_area)
        self.toggle_button.toggled.connect(self.toggle);
        self.toggle_button.setChecked(False);
        self.content_area.setVisible(False)

    def setContentLayout(self, layout):
        old_layout = self.content_area.layout()
        if old_layout is not None:
            while old_layout.count():
                item = old_layout.takeAt(0);
                widget = item.widget()
                if widget: widget.deleteLater()
            del old_layout
        self.content_area.setLayout(layout)

    def toggle(self, checked):
        self.toggle_button.setArrowType(Qt.DownArrow if checked else Qt.RightArrow);
        self.content_area.setVisible(checked)
        if self.parentWidget() and self.parentWidget().layout(): self.parentWidget().layout().activate()


class DetailWidget(QWidget):
    def __init__(self, char_path, char_info, data_manager, main_window):
        super().__init__()

        # --- 终极修复：让这个“详情页”本身变得透明！ ---
        self.setAutoFillBackground(False)

        self.char_path = char_path;
        self.char_data = char_info['data'];
        self.char_format = char_info['format'];
        self.data_manager = data_manager;
        self.main_window = main_window
        self.text_widgets = [];
        self.widgets = {};
        self.book_entries_widgets = [];
        self.book_entries_data = [];
        self.profile_boxes = {};
        self.filter_checkboxes = {}
        self.init_ui()

    # ... 以下所有函数都无需修改，保持原样 ...
    def init_ui(self):
        main_layout = QHBoxLayout(self);
        left_panel = QFrame();
        left_layout = QVBoxLayout(left_panel);
        left_panel.setFixedWidth(270)
        self.avatar_label = QLabel();
        pixmap = QPixmap(self.char_path);
        self.avatar_label.setPixmap(pixmap.scaled(256, 256, Qt.KeepAspectRatio, Qt.SmoothTransformation));
        left_layout.addWidget(self.avatar_label);
        left_layout.addStretch()
        right_panel = QWidget();
        right_layout = QVBoxLayout(right_panel);
        top_control_layout = QHBoxLayout();
        font_label = QLabel("内容字体大小:");
        self.font_spinbox = QSpinBox();
        self.font_spinbox.setRange(8, 24);
        self.font_spinbox.setValue(10);
        self.font_spinbox.valueChanged.connect(self.update_font_size)
        self.export_btn = QPushButton("导出角色卡");
        self.export_btn.clicked.connect(self.export_character_card);
        self.save_btn = QPushButton("保存所有修改");
        self.save_btn.clicked.connect(self.save_changes)
        top_control_layout.addWidget(font_label);
        top_control_layout.addWidget(self.font_spinbox);
        top_control_layout.addStretch();
        top_control_layout.addWidget(self.export_btn);
        top_control_layout.addWidget(self.save_btn);
        right_layout.addLayout(top_control_layout)
        self.tabs = QTabWidget();
        profile_tab = QWidget();
        book_tab = QWidget();
        self.tabs.addTab(profile_tab, "角色档案");
        self.tabs.addTab(book_tab, "世界书")
        self.populate_profile_tab(profile_tab);
        self.populate_book_tab(book_tab);
        right_layout.addWidget(self.tabs);
        main_layout.addWidget(left_panel);
        main_layout.addWidget(right_panel)
        self.update_font_size(self.font_spinbox.value())
        if self.char_data.get('data', {}).get('is_sd_card'): self.set_read_only(True); self.save_btn.setText(
            f"{self.char_format} 卡片 (只读)")

    def set_read_only(self, read_only):
        for widget in self.widgets.values():
            if isinstance(widget, (QTextEdit, QLineEdit)): widget.setReadOnly(read_only)
        for entry_widgets in self.book_entries_widgets: entry_widgets['keys'].setReadOnly(read_only); entry_widgets[
            'content'].setReadOnly(read_only); entry_widgets['enabled'].setEnabled(not read_only)
        self.save_btn.setEnabled(not read_only)

    def populate_profile_tab(self, tab):
        tab_layout = QVBoxLayout(tab);
        tab_layout.setContentsMargins(0, 0, 0, 0);
        filter_group = QGroupBox("显示/隐藏模块");
        filter_layout = QGridLayout(filter_group);
        tab_layout.addWidget(filter_group)
        scroll_area = QScrollArea();
        scroll_area.setWidgetResizable(True);
        content_widget = QWidget();
        self.profile_layout = QVBoxLayout(content_widget);
        scroll_area.setWidget(content_widget);
        tab_layout.addWidget(scroll_area)
        data = self.char_data;
        data_source = data.get('data', data)
        profile_fields = {"name": "名称", "creator": "创建者", "character_version": "角色版本", "tags": "标签 (逗号分隔)",
                          "description": "描述与设定", "personality": "性格", "scenario": "场景", "first_mes": "开场白",
                          "alternate_greetings": "备用问候语 (每行一个)", "mes_example": "对话示例",
                          "system_prompt": "系统提示 (System Prompt)", "post_history_instructions": "后历史指令",
                          "creator_notes": "创建者笔记", "extensions": "扩展数据 (JSON)"}
        self.profile_layout.addLayout(
            self.create_labeled_input(f"{profile_fields['name']}:", "name", data_source.get("name")))
        row, col = 0, 0
        for key, title in profile_fields.items():
            if key == "name": continue
            box = CollapsibleBox(title);
            content_layout = QVBoxLayout();
            value = data_source.get(key)
            if key == "tags" and isinstance(value, list):
                value = ", ".join(value)
            elif key == "alternate_greetings" and isinstance(value, list):
                value = "\n".join(value)
            elif key == "extensions" and isinstance(value, dict):
                value = json.dumps(value, indent=4, ensure_ascii=False)
            is_multiline = key not in ["creator", "character_version", "tags"]
            self.create_labeled_input(None, key, value, multiline=is_multiline, parent_layout=content_layout);
            box.setContentLayout(content_layout);
            self.profile_layout.addWidget(box);
            self.profile_boxes[key] = box
            checkbox = QCheckBox(title);
            checkbox.setChecked(True);
            checkbox.stateChanged.connect(self.update_profile_visibility);
            self.filter_checkboxes[key] = checkbox;
            filter_layout.addWidget(checkbox, row, col)
            col += 1
            if col >= 4: col = 0; row += 1
        self.profile_layout.addStretch()

    @Slot()
    def update_profile_visibility(self):
        for key, box in self.profile_boxes.items():
            checkbox = self.filter_checkboxes.get(key)
            if checkbox: box.setVisible(checkbox.isChecked())

    def populate_book_tab(self, tab):
        layout = QVBoxLayout(tab);
        book_data = self.char_data.get('data', {}).get('character_book', {'name': '', 'entries': []});
        top_layout = QHBoxLayout()
        export_btn = QPushButton("导出世界书为JSON");
        export_btn.clicked.connect(self.export_world_book);
        add_entry_btn = QPushButton("添加新条目");
        add_entry_btn.clicked.connect(self.add_new_book_entry)
        top_layout.addWidget(export_btn);
        top_layout.addWidget(add_entry_btn);
        top_layout.addStretch();
        top_layout.addLayout(self.create_labeled_input("书名:", "book_name", book_data.get("name")));
        layout.addLayout(top_layout)
        scroll_area = QScrollArea();
        scroll_area.setWidgetResizable(True);
        scroll_content = QWidget();
        self.entries_layout = QVBoxLayout(scroll_content);
        scroll_area.setWidget(scroll_content);
        layout.addWidget(scroll_area)
        self.book_entries_data = book_data.get('entries', []);
        self.rebuild_book_entries_ui()

    def rebuild_book_entries_ui(self):
        while self.entries_layout.count(): item = self.entries_layout.takeAt(0); widget = item.widget(); (
            lambda: widget.deleteLater())() if widget else None
        self.book_entries_widgets = []
        for i, entry in enumerate(self.book_entries_data): self.add_book_entry_widget(entry, i)
        self.entries_layout.addStretch();
        self.update_font_size(self.font_spinbox.value())

    def add_book_entry_widget(self, entry, index):
        keys_str = ", ".join(entry.get("keys", []));
        box_title = f"条目 #{index + 1}: {keys_str[:30]}..." if keys_str else f"条目 #{index + 1}: (新条目)"
        box = CollapsibleBox(box_title);
        content_layout = QVBoxLayout();
        delete_btn = QPushButton("删除此条目");
        delete_btn.setStyleSheet("color: red;");
        delete_btn.clicked.connect(lambda _, b=box, i=index: self.delete_book_entry(b, i));
        content_layout.addWidget(delete_btn, alignment=Qt.AlignRight)
        self.create_labeled_input("关键词 (逗号分隔):", f"book_keys_{index}", keys_str, parent_layout=content_layout)
        self.create_labeled_input("内容:", f"book_content_{index}", entry.get("content", ""), multiline=True,
                                  parent_layout=content_layout)
        enabled_var = QCheckBox("启用");
        enabled_var.setChecked(entry.get("enabled", True));
        content_layout.addWidget(enabled_var);
        box.setContentLayout(content_layout);
        self.entries_layout.addWidget(box)
        self.book_entries_widgets.append(
            {"box": box, "keys": self.widgets[f"book_keys_{index}"], "content": self.widgets[f"book_content_{index}"],
             "enabled": enabled_var})

    def add_new_book_entry(self):
        dialog = AddEntryDialog(self)
        if dialog.exec():
            new_entry_data = dialog.get_data()
            if not new_entry_data["keys"] and not new_entry_data["content"]: QMessageBox.warning(self, "输入为空",
                                                                                                 "关键词和内容不能都为空。"); return
            full_new_entry = {"keys": new_entry_data["keys"], "content": new_entry_data["content"],
                              "enabled": new_entry_data["enabled"], "comment": "", "constant": False, "selective": True,
                              "insertion_order": 100, "extensions": {}, "id": 0}
            self.book_entries_data.append(full_new_entry);
            self.rebuild_book_entries_ui()

    def delete_book_entry(self, box_widget, index):
        reply = QMessageBox.question(self, "确认删除", f"确定要删除条目 #{index + 1} 吗?")
        if reply == QMessageBox.Yes: self.book_entries_data.pop(index); self.rebuild_book_entries_ui()

    def create_labeled_input(self, label_text, key, data_value, multiline=False, parent_layout=None):
        h_layout = QHBoxLayout();
        if label_text: label = QLabel(label_text); label.setFixedWidth(120); h_layout.addWidget(label)
        if multiline:
            widget = AutoResizingTextEdit(); widget.setPlainText(data_value or "")
        else:
            widget = QLineEdit(); widget.setText(data_value or "")
        self.widgets[key] = widget;
        if isinstance(widget, QTextEdit): self.text_widgets.append(widget)
        h_layout.addWidget(widget)
        if parent_layout is not None: parent_layout.addLayout(h_layout)
        return h_layout

    def update_font_size(self, size):
        font = QFont();
        font.setPointSize(size)
        for widget in self.text_widgets: widget.setFont(font); (lambda: widget.updateGeometry())() if isinstance(widget,
                                                                                                                 AutoResizingTextEdit) else None

    def get_current_data_from_ui(self):
        updated_data = self.char_data.copy()
        if 'data' not in updated_data: updated_data['data'] = {}
        data_target = updated_data['data']
        all_profile_keys = ["name", "creator", "character_version", "tags", "description", "personality", "scenario",
                            "first_mes", "alternate_greetings", "mes_example", "system_prompt",
                            "post_history_instructions", "creator_notes", "extensions"]
        for key in all_profile_keys:
            widget = self.widgets.get(key)
            if not widget: continue
            if key == "tags":
                tags_str = widget.text().strip(); data_target[key] = [tag.strip() for tag in tags_str.split(',') if
                                                                      tag.strip()]
            elif key == "alternate_greetings":
                greetings_text = widget.toPlainText().strip(); data_target[key] = [line.strip() for line in
                                                                                   greetings_text.split('\n') if
                                                                                   line.strip()]
            elif key == "extensions":
                try:
                    ext_text = widget.toPlainText().strip(); data_target[key] = json.loads(ext_text) if ext_text else {}
                except json.JSONDecodeError:
                    QMessageBox.critical(self, "数据错误", "扩展数据 (JSON) 格式无效。"); return None
            elif isinstance(widget, QTextEdit):
                data_target[key] = widget.toPlainText().strip()
            elif isinstance(widget, QLineEdit):
                data_target[key] = widget.text().strip()
        book_name = self.widgets["book_name"].text().strip();
        new_entries = []
        for i, entry_widgets in enumerate(self.book_entries_widgets):
            original_entry = self.book_entries_data[i];
            keys_str = entry_widgets["keys"].text().strip();
            original_entry["keys"] = [k.strip() for k in keys_str.split(',') if k.strip()];
            original_entry["content"] = entry_widgets["content"].toPlainText().strip();
            original_entry["enabled"] = entry_widgets["enabled"].isChecked();
            new_entries.append(original_entry)
        if 'character_book' not in data_target: data_target['character_book'] = {}
        data_target['character_book']['name'] = book_name;
        data_target['character_book']['entries'] = new_entries
        return updated_data

    def save_changes(self):
        updated_data = self.get_current_data_from_ui()
        if updated_data is None: return
        success, message = write_character_data_to_png(self.char_path, updated_data)
        if success:
            QMessageBox.information(self, "成功", message);
            self.char_data = updated_data
            if self.char_path in self.data_manager.characters: self.data_manager.characters[self.char_path][
                'data'] = updated_data
            self.main_window.load_initial_data()
        else:
            QMessageBox.critical(self, "失败", message)

    def export_character_card(self):
        current_data = self.get_current_data_from_ui()
        if current_data is None: return
        char_name = self.widgets['name'].text().strip() or "Unnamed Character";
        safe_char_name = "".join(c for c in char_name if c.isalnum() or c in " _-").rstrip();
        default_filename = f"{safe_char_name}.png"
        save_path, _ = QFileDialog.getSaveFileName(self, "导出角色卡为PNG", default_filename, "PNG Files (*.png)")
        if not save_path: return
        try:
            shutil.copy2(self.char_path, save_path);
            success, message = write_character_data_to_png(save_path, current_data)
            if success:
                QMessageBox.information(self, "导出成功", f"角色卡已成功导出到:\n{save_path}")
            else:
                QMessageBox.critical(self, "导出失败", f"写入数据到新文件时失败: {message}"); os.remove(save_path)
        except Exception as e:
            QMessageBox.critical(self, "导出错误", f"导出过程中发生错误: {e}")

    def export_world_book(self):
        book_data = self.char_data.get('data', {}).get('character_book')
        if not book_data: QMessageBox.warning(self, "无数据", "此角色卡不包含世界书信息。"); return
        char_name = self.char_data.get('data', {}).get('name') or self.char_data.get('name', 'UnknownChar');
        book_name = book_data.get('name', 'WorldBook');
        default_filename = f"{char_name}-{book_name}.json"
        file_path, _ = QFileDialog.getSaveFileName(self, "导出世界书", os.path.join(BOOK_WORKSPACE, default_filename),
                                                   "JSON Files (*.json)")
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(book_data, f, indent=4, ensure_ascii=False)
                QMessageBox.information(self, "成功", f"世界书已导出到:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "失败", f"导出时发生错误:\n{e}")