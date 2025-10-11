import os
import sys
import uuid
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QGraphicsView, QGraphicsScene,
    QGraphicsPixmapItem, QDialogButtonBox, QGraphicsRectItem
)
from PySide6.QtGui import QPixmap, QPainter, QPen, QColor, QCursor
from PySide6.QtCore import Qt, QRectF, QPointF
from PIL import Image

from core_utils import get_base_path


class FitInViewGraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing)
        self.setRenderHint(QPainter.SmoothPixmapTransform)

    def fit_scene_in_view(self):
        """一个独立的、可被调用的缩放函数"""
        if self.scene():
            self.fitInView(self.scene().sceneRect(), Qt.KeepAspectRatio)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fit_scene_in_view()


class CroppingRectItem(QGraphicsRectItem):
    def __init__(self, rect, parent=None):
        super().__init__(rect, parent)
        self.setPen(QPen(QColor(255, 255, 0, 200), 2, Qt.DashLine))
        self.setBrush(QColor(0, 0, 0, 70))
        self.setFlag(QGraphicsRectItem.ItemIsMovable)
        self.setFlag(QGraphicsRectItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.handles = {}
        self.handle_size = 10
        self.selected_handle = None
        self.mouse_press_scene_pos = None
        self.update_handles()

    def update_handles(self):
        scale = self.scene().views()[0].transform().m11() if self.scene() and self.scene().views() else 1.0
        hs = self.handle_size / scale if scale != 0 else self.handle_size
        rect = self.rect()
        self.handles[1] = QRectF(rect.left() - hs / 2, rect.top() - hs / 2, hs, hs)
        self.handles[2] = QRectF(rect.center().x() - hs / 2, rect.top() - hs / 2, hs, hs)
        self.handles[3] = QRectF(rect.right() - hs / 2, rect.top() - hs / 2, hs, hs)
        self.handles[4] = QRectF(rect.left() - hs / 2, rect.center().y() - hs / 2, hs, hs)
        self.handles[5] = QRectF(rect.right() - hs / 2, rect.center().y() - hs / 2, hs, hs)
        self.handles[6] = QRectF(rect.left() - hs / 2, rect.bottom() - hs / 2, hs, hs)
        self.handles[7] = QRectF(rect.center().x() - hs / 2, rect.bottom() - hs / 2, hs, hs)
        self.handles[8] = QRectF(rect.right() - hs / 2, rect.bottom() - hs / 2, hs, hs)
        self.update()

    def paint(self, painter, option, widget):
        super().paint(painter, option, widget)
        painter.setBrush(QColor("yellow"))
        painter.setPen(Qt.NoPen)
        for handle in self.handles.values(): painter.drawRect(handle)

    def hoverMoveEvent(self, event):
        pos = event.pos()
        for key, handle in self.handles.items():
            if handle.contains(pos): self.setCursor(self.get_cursor_for_handle(key)); return
        self.setCursor(QCursor(Qt.SizeAllCursor))

    def mousePressEvent(self, event):
        pos = event.pos()
        for key, handle in self.handles.items():
            if handle.contains(pos):
                self.selected_handle = key
                self.mouse_press_scene_pos = event.scenePos()
                self.mouse_press_rect = self.rect()
                return
        self.selected_handle = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.selected_handle:
            self.prepareGeometryChange()
            scene_delta = event.scenePos() - self.mouse_press_scene_pos
            rect = self.mouse_press_rect
            if self.selected_handle in [1, 4, 6]: rect.setLeft(rect.left() + scene_delta.x())
            if self.selected_handle in [1, 2, 3]: rect.setTop(rect.top() + scene_delta.y())
            if self.selected_handle in [3, 5, 8]: rect.setRight(rect.right() + scene_delta.x())
            if self.selected_handle in [6, 7, 8]: rect.setBottom(rect.bottom() + scene_delta.y())
            self.setRect(rect.normalized())
            self.update_handles()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.selected_handle = None
        super().mouseReleaseEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsRectItem.ItemPositionHasChanged:
            self.update_handles()
        return super().itemChange(change, value)

    def get_cursor_for_handle(self, handle_key):
        if handle_key in [1, 8]: return QCursor(Qt.SizeFDiagCursor)
        if handle_key in [3, 6]: return QCursor(Qt.SizeBDiagCursor)
        if handle_key in [2, 7]: return QCursor(Qt.SizeVerCursor)
        if handle_key in [4, 5]: return QCursor(Qt.SizeHorCursor)
        return QCursor(Qt.ArrowCursor)


class CropToolDialog(QDialog):
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("裁剪背景图片")

        # --- 核心修复1：采纳您的建议，增大默认窗口 ---
        self.setMinimumSize(1000, 800)

        self.image_path = image_path
        self.cropped_image_path = None

        main_layout = QVBoxLayout(self)
        self.scene = QGraphicsScene()
        self.view = FitInViewGraphicsView(self.scene)
        main_layout.addWidget(self.view)

        self.pixmap_item = QGraphicsPixmapItem(QPixmap(image_path))
        self.scene.addItem(self.pixmap_item)

        img_rect = self.pixmap_item.boundingRect()
        crop_rect = img_rect.adjusted(img_rect.width() * 0.1, img_rect.height() * 0.1, -img_rect.width() * 0.1,
                                      -img_rect.height() * 0.1)
        self.crop_rect_item = CroppingRectItem(crop_rect)
        self.scene.addItem(self.crop_rect_item)

        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept_crop)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    # --- 核心修复2：重新引入 showEvent 来保证初始视图正确 ---
    def showEvent(self, event):
        """在窗口首次显示时，强制进行一次缩放以适应内容"""
        super().showEvent(event)
        # 必须在 showEvent 之后调用，此时窗口尺寸才是最终的
        # 我们使用一个0毫秒的定时器来确保它在下一个事件循环中执行
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self.view.fit_scene_in_view)

    def accept_crop(self):
        crop_geo = self.crop_rect_item.mapToItem(self.pixmap_item, self.crop_rect_item.rect()).boundingRect()
        original_image = Image.open(self.image_path)
        cropped_image = original_image.crop(
            (int(crop_geo.left()), int(crop_geo.top()), int(crop_geo.right()), int(crop_geo.bottom())))
        base_dir = get_base_path()
        cache_dir = os.path.join(base_dir, 'assets', 'cache')
        os.makedirs(cache_dir, exist_ok=True)
        filename = f"{uuid.uuid4().hex}.png"
        self.cropped_image_path = os.path.join(cache_dir, filename)
        cropped_image.save(self.cropped_image_path, "PNG")
        self.accept()