import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit,
    QTextEdit, QScrollArea, QFileDialog, QMessageBox,
    QDialogButtonBox, QFrame, QGroupBox, QWidget
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class CreateCharacterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("新建角色卡")
        self.setMinimumSize(900, 800)  # 稍微增大默认尺寸
        self.widgets = {}
        self.image_path = None

        # 设置对话框样式
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                background-color: #f8f8f8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #cccccc;
                border-radius: 3px;
                padding: 5px;
                background-color: white;
            }
            QTextEdit {
                min-height: 80px;
            }
        """)

        main_layout = QVBoxLayout(self)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        content_widget = QWidget()
        form_layout = QVBoxLayout(content_widget)
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)

        # 基本信息组
        basic_info_group = QGroupBox("基本信息")
        basic_layout = QVBoxLayout(basic_info_group)
        basic_layout.addLayout(self.create_labeled_input("名称 (必填):", "name", ""))
        basic_layout.addLayout(self.create_labeled_input("创建者:", "creator", ""))
        basic_layout.addLayout(self.create_labeled_input("角色版本:", "character_version", ""))
        basic_layout.addLayout(self.create_labeled_input("标签 (逗号分隔):", "tags", ""))
        form_layout.addWidget(basic_info_group)

        # 角色描述组
        description_group = QGroupBox("角色描述")
        description_layout = QVBoxLayout(description_group)
        description_layout.addLayout(self.create_labeled_input("描述与设定:", "description", "", multiline=True))
        description_layout.addLayout(self.create_labeled_input("性格:", "personality", "", multiline=True))
        description_layout.addLayout(self.create_labeled_input("场景:", "scenario", "", multiline=True))
        form_layout.addWidget(description_group)

        # 对话内容组
        dialogue_group = QGroupBox("对话内容")
        dialogue_layout = QVBoxLayout(dialogue_group)
        dialogue_layout.addLayout(self.create_labeled_input("开场白:", "first_mes", "", multiline=True))
        dialogue_layout.addLayout(self.create_labeled_input("备用问候语 (每行一个):", "alternate_greetings", "", multiline=True))
        dialogue_layout.addLayout(self.create_labeled_input("对话示例:", "mes_example", "", multiline=True))
        form_layout.addWidget(dialogue_group)

        # 系统提示组
        system_group = QGroupBox("系统提示")
        system_layout = QVBoxLayout(system_group)
        system_layout.addLayout(self.create_labeled_input("系统提示:", "system_prompt", "", multiline=True))
        system_layout.addLayout(self.create_labeled_input("后历史指令:", "post_history_instructions", "", multiline=True))
        system_layout.addLayout(self.create_labeled_input("创建者笔记:", "creator_notes", "", multiline=True))
        form_layout.addWidget(system_group)

        form_layout.addStretch()

        # 图片选择部分
        image_group = QGroupBox("图片载体")
        image_layout = QVBoxLayout(image_group)
        image_inner_layout = QHBoxLayout()
        self.select_image_btn = QPushButton("选择图片作为载体 (必选)")
        self.select_image_btn.clicked.connect(self.select_image)
        self.image_path_label = QLabel("尚未选择图片...")
        self.image_path_label.setStyleSheet("color: gray;")
        self.image_path_label.setMinimumWidth(200)
        self.image_path_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        image_inner_layout.addWidget(self.select_image_btn)
        image_inner_layout.addWidget(self.image_path_label)
        image_inner_layout.addStretch()
        image_layout.addLayout(image_inner_layout)
        form_layout.addWidget(image_group)

        # 按钮框
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.validate_and_accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def create_labeled_input(self, label_text, key, data_value, multiline=False):
        h_layout = QHBoxLayout()
        label = QLabel(label_text)
        label.setFixedWidth(120)
        h_layout.addWidget(label)

        if multiline:
            widget = QTextEdit()
            widget.setPlainText(data_value or "")
            widget.setMinimumHeight(100)  # 确保多行文本框有足够高度
        else:
            widget = QLineEdit()
            widget.setText(data_value or "")

        self.widgets[key] = widget
        h_layout.addWidget(widget)
        return h_layout

    def select_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择图片", "", "Image Files (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.image_path = file_path
            font_metrics = self.image_path_label.fontMetrics()
            elided_text = font_metrics.elidedText(file_path, Qt.ElideMiddle, self.image_path_label.width())
            self.image_path_label.setText(elided_text)
            self.image_path_label.setToolTip(file_path)
            self.image_path_label.setStyleSheet("color: green;")

    def validate_and_accept(self):
        if not self.widgets['name'].text().strip():
            QMessageBox.warning(self, "输入缺失", "角色\"名称\"是必填项。")
            return
        if not self.image_path:
            QMessageBox.warning(self, "选择缺失", "请选择一个图片作为角色卡的载体。")
            return
        self.accept()

    def get_data(self):
        data = {}
        for key, widget in self.widgets.items():
            if isinstance(widget, QTextEdit):
                data[key] = widget.toPlainText().strip()
            else:
                data[key] = widget.text().strip()
        return data, self.image_path