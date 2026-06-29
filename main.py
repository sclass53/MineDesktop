import sys
import os
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QMessageBox, QMenu, QAction,
    QInputDialog, QFileDialog, QSystemTrayIcon
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QMovie, QIcon

class DesktopPet(QWidget):
    def __init__(self, gif_path, scale=1.0, title="Drated", content="GNZ"):
        super().__init__()
        self.gif_path = gif_path
        self.scale = scale
        self.drag_position = QPoint()
        self.tit = title
        self.cont = content

        # ---------- 窗口设置 ----------
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # ---------- 创建标签显示 GIF ----------
        self.label = QLabel(self)
        self.label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.label.setScaledContents(True)

        self.movie = QMovie(gif_path)
        self.label.setMovie(self.movie)
        self.movie.start()

        # 窗口大小自适应
        self.movie.frameChanged.connect(self.adjust_size)
        self._size_adjusted = False

        # ---------- 创建托盘图标 ----------
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("MineDesktop")

        # 加载托盘图标（优先使用同目录下的 icon.ico，否则使用默认）
        icon_path = self.resource_path('icon.ico')
        if os.path.exists(icon_path):
            tray_icon = QIcon(icon_path)
        else:
            # 使用内置图标
            tray_icon = QApplication.style().standardIcon(QApplication.style().SP_ComputerIcon)
        self.tray_icon.setIcon(tray_icon)

        # 创建托盘菜单（与宠物右键菜单一致）
        tray_menu = QMenu(self)

        scale_action = QAction("Scale..", self)
        scale_action.triggered.connect(self.change_scale)
        tray_menu.addAction(scale_action)

        change_action = QAction("Image..", self)
        change_action.triggered.connect(self.change_gif)
        tray_menu.addAction(change_action)

        tray_menu.addSeparator()

        exit_action = QAction("Quit", self)
        exit_action.triggered.connect(self.quit_app)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        # 可选：点击托盘图标显示/隐藏窗口（这里左键点击无操作，可改为双击显示/隐藏）
        self.tray_icon.activated.connect(self.tray_icon_activated)

        # ---------- 宠物右键菜单 ----------
        self.context_menu = QMenu(self)
        scale_action2 = QAction("Scale..", self)
        scale_action2.triggered.connect(self.change_scale)
        self.context_menu.addAction(scale_action2)

        change_action2 = QAction("Image..", self)
        change_action2.triggered.connect(self.change_gif)
        self.context_menu.addAction(change_action2)

        self.context_menu.addSeparator()

        exit_action2 = QAction("Quit", self)
        exit_action2.triggered.connect(self.quit_app)
        self.context_menu.addAction(exit_action2)

        # ---------- 事件过滤器 ----------
        self.label.installEventFilter(self)

        self.show()

    def resource_path(self, relative_path):
        """获取资源路径（exe外部文件）"""
        # 如果程序打包成exe，sys.executable是exe路径；如果未打包，是脚本路径
        base_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
        return os.path.join(base_dir, relative_path)

    def eventFilter(self, obj, event):
        if obj == self.label:
            if event.type() == event.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.drag_position = event.globalPos() - self.frameGeometry().topLeft()
                    self._press_pos = event.globalPos()
                    return True
                elif event.button() == Qt.RightButton:
                    self.context_menu.exec_(event.globalPos())
                    return True

            elif event.type() == event.MouseMove:
                if event.buttons() & Qt.LeftButton:
                    self.move(event.globalPos() - self.drag_position)
                    return True

            elif event.type() == event.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    if hasattr(self, '_press_pos'):
                        delta = event.globalPos() - self._press_pos
                        if delta.manhattanLength() < 10:
                            self.on_click()
                        delattr(self, '_press_pos')
                    return True

        return super().eventFilter(obj, event)

    def on_click(self):
        QMessageBox.information(self, self.tit, self.cont)

    def adjust_size(self):
        if not self._size_adjusted:
            size = self.movie.currentPixmap().size()
            if size.width() > 0 and size.height() > 0:
                scaled_w = max(1, int(size.width() * self.scale))
                scaled_h = max(1, int(size.height() * self.scale))
                self.resize(scaled_w, scaled_h)
                self.label.resize(scaled_w, scaled_h)
                self._size_adjusted = True
                self.movie.frameChanged.disconnect(self.adjust_size)

    def change_scale(self):
        new_scale, ok = QInputDialog.getDouble(
            self,
            "Change Scale",
            "Input scale (Ex. 0.8, 1.0, 2.0):",
            self.scale,
            0.1,
            10.0,
            2
        )
        if ok and new_scale > 0:
            self.scale = new_scale
            self._apply_scale()

    def change_gif(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select GIF Image",
            self.resource_path(''),  # 从exe目录开始
            "GIF File (*.gif);;All Files (*.*)"
        )
        if file_path:
            self.movie.stop()
            try:
                self.movie.frameChanged.disconnect(self.adjust_size)
            except TypeError:
                pass
            self.movie.setFileName(file_path)
            self._size_adjusted = False
            self.movie.frameChanged.connect(self.adjust_size)
            self.movie.start()
            self.gif_path = file_path

    def _apply_scale(self):
        size = self.movie.currentPixmap().size()
        if size.width() > 0 and size.height() > 0:
            scaled_w = max(1, int(size.width() * self.scale))
            scaled_h = max(1, int(size.height() * self.scale))
            self.resize(scaled_w, scaled_h)
            self.label.resize(scaled_w, scaled_h)
        else:
            self._size_adjusted = False

    def tray_icon_activated(self, reason):
        # 如果双击托盘图标，可以显示/隐藏窗口（可选）
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()  # 置于顶层

    def quit_app(self):
        """退出应用程序（清理托盘）"""
        self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        # 当窗口关闭时，只隐藏而不退出（除非用户通过菜单退出）
        # 但我们的退出菜单会调用 quit_app，所以这里不处理
        event.ignore()

if __name__ == '__main__':
    app = QApplication(sys.argv)

    # 获取exe所在目录（如果打包）或脚本目录
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    gif_path = os.path.join(base_dir, 'imgs/campfire.gif')
    scale = 0.75
    title = 'Something'
    content = 'A drated program'

    pet = DesktopPet(gif_path, scale, title, content)
    sys.exit(app.exec_())