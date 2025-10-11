# 文档5 修改后 -> 建议保存为 main.py
import sys
from PySide6.QtWidgets import QApplication
from main_window import MainWindow  # 从我们新建的模块中导入MainWindow

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())