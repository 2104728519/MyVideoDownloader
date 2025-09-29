# main.py

import sys
from PySide6.QtWidgets import QApplication
from launcher_ui import MainWindow

# main.py 现在非常简洁，它的唯一工作就是启动GUI应用程序。
# 所有的项目数据和后台逻辑都已经被分离到其他模块中。

if __name__ == "__main__":
    # 1. 创建应用程序实例
    app = QApplication(sys.argv)

    # 2. 创建主窗口实例
    #    主窗口 (MainWindow) 的 __init__ 方法现在会负责加载项目数据和构建界面
    window = MainWindow()

    # 3. 显示窗口
    window.show()

    # 4. 启动应用程序的事件循环
    sys.exit(app.exec())