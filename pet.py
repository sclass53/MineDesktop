import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QMenu, QAction,
    QInputDialog, QFileDialog, QSystemTrayIcon, QActionGroup, QMessageBox
)
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QMovie, QIcon

class DesktopPet(QWidget):
    def __init__(self, main_gif_path=None, click_gif_path=None, scale=1.0, theme_name=None):
        super().__init__()
        self.scale = scale
        self.drag_position = QPoint()
        self.is_playing_click = False
        self.animation_mode = 'immediate'   # 默认
        self.themes = {}                    # 主题字典
        self.current_theme_name = None

        # ---------- 加载主题配置 ----------
        self._load_themes()

        # ---------- 确定启动使用的 GIF 和模式 ----------
        if theme_name and theme_name in self.themes:
            theme = self.themes[theme_name]
            main_gif = theme['main']
            click_gif = theme['click']
            mode = theme['mode']
            self.current_theme_name = theme_name
        elif main_gif_path is not None and os.path.exists(main_gif_path):
            main_gif = main_gif_path
            click_gif = click_gif_path if click_gif_path else main_gif
            mode = 'immediate'
        elif self.themes:
            first_theme = list(self.themes.keys())[0]
            theme = self.themes[first_theme]
            main_gif = theme['main']
            click_gif = theme['click']
            mode = theme['mode']
            self.current_theme_name = first_theme
        else:
            # 无主题，使用默认硬编码（防止空）
            main_gif = os.path.join(self.resource_path(''), 'imgs', 'campfire.gif')
            click_gif = main_gif
            mode = 'immediate'

        self.main_gif_path = main_gif
        self.click_gif_path = click_gif if os.path.exists(click_gif) else main_gif
        self.animation_mode = mode

        # ---------- 帧检测相关 ----------
        self._prev_frame = -1
        self._expect_finish = False
        self._on_finish_callback = None
        self._size_adjusted = False

        # ---------- 窗口设置 ----------
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # ---------- 创建标签 ----------
        self.label = QLabel(self)
        self.label.setAttribute(Qt.WA_TranslucentBackground, True)
        self.label.setScaledContents(True)

        # ---------- 创建 QMovie ----------
        self.movie = QMovie(self.main_gif_path)
        self.label.setMovie(self.movie)

        # ---------- 托盘图标 ----------
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setToolTip("Desktop Pet")
        icon_path = self.resource_path('icon.ico')
        if os.path.exists(icon_path):
            tray_icon = QIcon(icon_path)
        else:
            tray_icon = QApplication.style().standardIcon(QApplication.style().SP_ComputerIcon)
        self.tray_icon.setIcon(tray_icon)

        # 托盘菜单
        self.tray_menu = QMenu(self)
        self._build_menus(self.tray_menu)

        self.tray_icon.setContextMenu(self.tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_icon_activated)

        # ---------- 宠物右键菜单 ----------
        self.context_menu = QMenu(self)
        self._build_menus(self.context_menu)

        self.label.installEventFilter(self)

        # ---------- 显示窗口并居中 ----------
        self.resize(1, 1)
        self.show()
        self._center_window()

        # ---------- 连接信号并开始播放 ----------
        self.movie.frameChanged.connect(self._on_frame_changed)
        self.movie.start()

    # ---------- 主题管理 ----------
    def _load_themes(self):
        """加载 themes.json 配置文件"""
        config_path = self.resource_path('themes.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                themes = data.get('themes', [])
                for theme in themes:
                    name = theme.get('name')
                    if name:
                        self.themes[name] = {
                            'main': theme.get('main_gif', ''),
                            'click': theme.get('click_gif', ''),
                            'mode': theme.get('mode', 'immediate')
                        }
            except Exception as e:
                print(f"加载主题配置失败: {e}")
        # 如果没有主题，则创建一个默认
        if not self.themes:
            default_main = os.path.join(self.resource_path(''), 'imgs', 'campfire.gif')
            default_click = os.path.join(self.resource_path(''), 'imgs', 'campfire.gif')
            if not os.path.exists(default_click):
                default_click = default_main
            self.themes['Default'] = {
                'main': default_main,
                'click': default_click,
                'mode': 'immediate'
            }

    def _apply_theme(self, theme_name):
        """应用指定主题（仅当 self.movie 已存在时使用）"""
        theme = self.themes.get(theme_name)
        if not theme:
            return
        self.current_theme_name = theme_name
        self.main_gif_path = theme['main']
        self.click_gif_path = theme['click']
        self.animation_mode = theme['mode']

        # 如果当前没有播放点击动画，立即切换到主 GIF
        if not self.is_playing_click:
            self._play_gif(self.main_gif_path, one_shot=False, on_finished=None)
        # 如果正在播放点击动画，则等待当前动画结束后会自动使用新的 main_gif_path

    # ---------- 菜单构建 ----------
    def _build_menus(self, menu):
        """构建菜单（同时用于托盘和宠物右键）"""
        menu.clear()

        scale_action = QAction("Adjust Scale", self)
        scale_action.triggered.connect(self.change_scale)
        menu.addAction(scale_action)

        # ---- 主题子菜单 ----
        if self.themes:
            theme_menu = QMenu("Themes", self)
            theme_group = QActionGroup(self)
            theme_group.setExclusive(True)

            for theme_name in self.themes.keys():
                action = QAction(theme_name, self, checkable=True)
                action.setChecked(theme_name == self.current_theme_name)
                action.triggered.connect(lambda checked, name=theme_name: self.switch_theme(name))
                theme_menu.addAction(action)
                theme_group.addAction(action)

            menu.addMenu(theme_menu)

        # ---- 动画模式子菜单 ----
        anim_menu = QMenu("Animation Mode", self)
        anim_group = QActionGroup(self)
        anim_group.setExclusive(True)

        wait_action = QAction("Wait for loop", self, checkable=True)
        wait_action.setChecked(self.animation_mode == 'wait')
        wait_action.triggered.connect(lambda: setattr(self, 'animation_mode', 'wait'))
        anim_menu.addAction(wait_action)
        anim_group.addAction(wait_action)

        immediate_action = QAction("Immediate", self, checkable=True)
        immediate_action.setChecked(self.animation_mode == 'immediate')
        immediate_action.triggered.connect(lambda: setattr(self, 'animation_mode', 'immediate'))
        anim_menu.addAction(immediate_action)
        anim_group.addAction(immediate_action)

        menu.addMenu(anim_menu)
        
        ad_menu = QMenu("Advanced", self)
        
        change_main = QAction("Select Main GIF", self)
        change_main.triggered.connect(self.change_main_gif)
        ad_menu.addAction(change_main)

        change_click = QAction("Select Click GIF", self)
        change_click.triggered.connect(self.change_click_gif)
        ad_menu.addAction(change_click)
        
        menu.addMenu(ad_menu)        

        menu.addSeparator()
        help_drater = QAction("About", self)
        help_drater.triggered.connect(self.show_help)
        exit_action = QAction("Quit", self)
        exit_action.triggered.connect(self.quit_app)
        menu.addAction(help_drater)
        menu.addAction(exit_action)

    def switch_theme(self, theme_name):
        """切换主题（由菜单触发）"""
        self._apply_theme(theme_name)
        self._rebuild_menus()

    def _rebuild_menus(self):
        """重建所有菜单（主题切换后更新勾选）"""
        self.tray_menu.clear()
        self.context_menu.clear()
        self._build_menus(self.tray_menu)
        self._build_menus(self.context_menu)

    # ---------- 辅助方法 ----------
    def resource_path(self, relative_path):
        base_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
        return os.path.join(base_dir, relative_path)

    def _center_window(self):
        screen = QApplication.primaryScreen()
        screen_geom = screen.availableGeometry()
        center = screen_geom.center()
        self.move(center.x() - self.width() // 2, center.y() - self.height() // 2)

    # ---------- 事件过滤器 ----------
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

    # ---------- 点击处理 ----------
    def on_click(self):
        if self.is_playing_click:
            return
        if self.click_gif_path == self.main_gif_path:
            return

        if self.animation_mode == 'wait':
            self._expect_finish = True
            self._on_finish_callback = self.start_click_animation
        else:
            self.start_click_animation()

    # ---------- 帧变化处理 ----------
    def _on_frame_changed(self):
        if not self._size_adjusted:
            size = self.movie.currentPixmap().size()
            if size.width() > 0 and size.height() > 0:
                self._resize_and_keep_center(size, self.scale)

        if self._expect_finish and self._on_finish_callback is not None:
            current = self.movie.currentFrameNumber()
            frame_count = self.movie.frameCount()
            if (self._prev_frame == frame_count - 1 and current == 0) or \
               (self._prev_frame != -1 and current == 0 and self._prev_frame != 0):
                callback = self._on_finish_callback
                self._expect_finish = False
                self._on_finish_callback = None
                callback()

        self._prev_frame = self.movie.currentFrameNumber()

    def _resize_and_keep_center(self, original_size, scale):
        current_center = self.frameGeometry().center()
        new_w = max(1, int(original_size.width() * scale))
        new_h = max(1, int(original_size.height() * scale))
        self.resize(new_w, new_h)
        self.label.resize(new_w, new_h)
        new_geom = self.frameGeometry()
        new_geom.moveCenter(current_center)
        self.move(new_geom.topLeft())
        self._size_adjusted = True

    # ---------- 播放控制 ----------
    def start_click_animation(self):
        self.is_playing_click = True
        self._play_gif(self.click_gif_path, one_shot=True, on_finished=self.back_to_main)

    def back_to_main(self):
        self.is_playing_click = False
        self._play_gif(self.main_gif_path, one_shot=False, on_finished=None)

    def _play_gif(self, gif_path, one_shot=False, on_finished=None):
        self.movie.stop()
        try:
            self.movie.frameChanged.disconnect(self._on_frame_changed)
        except TypeError:
            pass

        self.movie.setFileName(gif_path)
        self._size_adjusted = False
        self._prev_frame = -1
        if one_shot:
            self._expect_finish = True
            self._on_finish_callback = on_finished
        else:
            self._expect_finish = False
            self._on_finish_callback = None

        self.movie.frameChanged.connect(self._on_frame_changed)
        self.movie.start()

    # ---------- 菜单功能 ----------
    def change_scale(self):
        new_scale, ok = QInputDialog.getDouble(
            self,
            "Adjust Scale",
            "Enter new scale (e.g. 0.8, 1.0, 2.0):",
            self.scale,
            0.1,
            10.0,
            2
        )
        if ok and new_scale > 0:
            self.scale = new_scale
            self._apply_scale()

    def change_main_gif(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Main GIF",
            self.resource_path(''),
            "GIF Files (*.gif);;All Files (*.*)"
        )
        if file_path:
            self.main_gif_path = file_path
            if not self.is_playing_click:
                self._play_gif(self.main_gif_path, one_shot=False, on_finished=None)

    def change_click_gif(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Click GIF",
            self.resource_path(''),
            "GIF Files (*.gif);;All Files (*.*)"
        )
        if file_path:
            self.click_gif_path = file_path

    def _apply_scale(self):
        size = self.movie.currentPixmap().size()
        if size.width() > 0 and size.height() > 0:
            self._resize_and_keep_center(size, self.scale)
        else:
            self._size_adjusted = False

    # ---------- 托盘 ----------
    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()

    def quit_app(self):
        self.tray_icon.hide()
        QApplication.quit()

    def closeEvent(self, event):
        event.ignore()
        
    def show_help(self,*arg,**kw):
        QMessageBox.information(self,"Drater","Noob!")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    pet = DesktopPet(scale=0.75)
    sys.exit(app.exec_())
