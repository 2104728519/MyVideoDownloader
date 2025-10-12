import os
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QVBoxLayout, QTabWidget, QWidget,
    QFormLayout, QSpinBox, QSlider, QLabel, QPushButton, QFileDialog,
    QHBoxLayout, QListWidget, QListWidgetItem, QGroupBox
)
from PySide6.QtCore import Qt, QUrl

from crop_tool_dialog import CropToolDialog


class SettingsDialog(QDialog):
    def __init__(self, current_settings, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setMinimumSize(600, 450)
        self.settings = current_settings.copy()

        main_layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.create_appearance_tab()
        self.create_music_tab()

        # --- 核心修复：修正这里的打字错误 ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.load_settings_to_ui()

    def create_appearance_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        general_group = QGroupBox("通用设置")
        form_layout = QFormLayout(general_group)
        form_layout.setRowWrapPolicy(QFormLayout.WrapAllRows)
        self.font_size_spinbox = QSpinBox()
        self.font_size_spinbox.setRange(8, 30)
        form_layout.addRow("全局字体大小:", self.font_size_spinbox)
        opacity_layout = QHBoxLayout()
        self.opacity_slider = QSlider(Qt.Horizontal)
        self.opacity_slider.setRange(10, 100)
        self.opacity_label = QLabel()
        self.opacity_slider.valueChanged.connect(lambda val: self.opacity_label.setText(f"{val}%"))
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        form_layout.addRow("UI不透明度:", opacity_layout)
        layout.addWidget(general_group)

        background_group = QGroupBox("背景图片设置")
        bg_form_layout = QFormLayout(background_group)
        self.bg_left_label, bg_left_widget = self.create_background_selector('background_left')
        bg_form_layout.addRow("角色列表背景:", bg_left_widget)
        layout.addWidget(background_group)
        layout.addStretch()

        self.tabs.addTab(tab, "外观")

    def create_background_selector(self, key):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel("未设置")
        label.setStyleSheet("color: gray;")
        select_btn = QPushButton("裁剪/选择图片")
        select_btn.clicked.connect(lambda: self.open_crop_tool(key, label))
        clear_btn = QPushButton("清除背景")
        clear_btn.clicked.connect(lambda: self.clear_background(key, label))
        button_layout = QHBoxLayout()
        button_layout.addWidget(select_btn)
        button_layout.addWidget(clear_btn)
        button_layout.addStretch()
        layout.addWidget(label)
        layout.addLayout(button_layout)
        return label, container

    def create_music_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.addWidget(QLabel("背景音乐播放列表 (循环播放):"))
        self.music_list_widget = QListWidget()
        self.music_list_widget.setSelectionMode(QListWidget.SingleSelection)
        layout.addWidget(self.music_list_widget)
        button_layout = QHBoxLayout()
        add_music_btn = QPushButton("添加音乐");
        remove_music_btn = QPushButton("移除选中");
        clear_music_btn = QPushButton("清空列表")
        add_music_btn.clicked.connect(self.add_music);
        remove_music_btn.clicked.connect(self.remove_music);
        clear_music_btn.clicked.connect(self.clear_music)
        button_layout.addWidget(add_music_btn);
        button_layout.addWidget(remove_music_btn);
        button_layout.addWidget(clear_music_btn)
        button_layout.addStretch()
        layout.addLayout(button_layout)
        self.tabs.addTab(tab, "音乐")

    def open_crop_tool(self, key, label_widget):
        image_path, _ = QFileDialog.getOpenFileName(self, "选择一张图片进行裁剪", "", "Image Files (*.png *.jpg *.jpeg *.bmp)")
        if not image_path:
            return
        tool = CropToolDialog(image_path, self)
        if tool.exec():
            self.settings[key] = tool.cropped_image_path
            label_widget.setText(f"已裁剪: {os.path.basename(image_path)}")
            label_widget.setStyleSheet("color: green;")

    def clear_background(self, key, label_widget):
        cached_path = self.settings.get(key)
        if cached_path and os.path.exists(cached_path):
            try:
                os.remove(cached_path)
            except Exception as e:
                print(f"无法删除缓存背景文件 {cached_path}: {e}")
        self.settings[key] = ""
        label_widget.setText("未设置")
        label_widget.setStyleSheet("color: gray;")

    def add_music(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择音乐文件", "", "Audio Files (*.mp3 *.wav *.ogg)")
        for file in files:
            if file not in [self.music_list_widget.item(i).data(Qt.UserRole) for i in
                            range(self.music_list_widget.count())]:
                item = QListWidgetItem(os.path.basename(file));
                item.setData(Qt.UserRole, file);
                self.music_list_widget.addItem(item)

    def remove_music(self):
        selected_item = self.music_list_widget.currentItem()
        if selected_item: self.music_list_widget.takeItem(self.music_list_widget.row(selected_item))

    def clear_music(self):
        self.music_list_widget.clear()

    def load_settings_to_ui(self):
        self.font_size_spinbox.setValue(self.settings.get('font_size', 10))
        self.opacity_slider.setValue(self.settings.get('opacity', 100))
        self.opacity_label.setText(f"{self.settings.get('opacity', 100)}%")

        def update_label(label_widget, bg_path):
            if bg_path and os.path.exists(bg_path):
                label_widget.setText(f"已设置自定义背景")
                label_widget.setStyleSheet("color: green;")
            else:
                label_widget.setText("未设置")
                label_widget.setStyleSheet("color: gray;")

        update_label(self.bg_left_label, self.settings.get('background_left', ""))

        self.music_list_widget.clear()
        playlist = self.settings.get('music_playlist', [])
        for music_file in playlist:
            if os.path.exists(music_file):
                item = QListWidgetItem(os.path.basename(music_file));
                item.setData(Qt.UserRole, music_file);
                self.music_list_widget.addItem(item)

    def get_settings(self):
        playlist = [self.music_list_widget.item(i).data(Qt.UserRole) for i in range(self.music_list_widget.count())]
        self.settings['font_size'] = self.font_size_spinbox.value()
        self.settings['opacity'] = self.opacity_slider.value()
        self.settings['music_playlist'] = playlist
        return self.settings