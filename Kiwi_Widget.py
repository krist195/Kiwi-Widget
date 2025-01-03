import os
import subprocess
import sys
import requests
from datetime import datetime, timedelta
from PyQt5.QtGui import QPainterPath, QRegion, QMovie, QIcon, QColor, QFont, QPainter
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, QDialog, QVBoxLayout,
                             QLineEdit, QDialogButtonBox, QWidget, QCheckBox, QDesktopWidget, QMessageBox,
                             QSlider, QStyle, QStyleOptionSlider, QGraphicsOpacityEffect,)

from PyQt5.QtCore import Qt, QProcess, QTimer, QPropertyAnimation, QSize, QPoint
import winreg  # Импортируем модуль для работы с реестром Windows

DOCUMENTS_DIR = os.path.join(os.path.expanduser("~"), "Documents", "Kiwi Widget")
GIF_FOLDER = os.path.join(DOCUMENTS_DIR, 'gif_files')
CONFIG_FILE = os.path.join(DOCUMENTS_DIR, 'window_config.txt')
AUTOSTART_FILE = os.path.join(DOCUMENTS_DIR, 'autostart_config.txt')
LAST_GIF_FILE = os.path.join(DOCUMENTS_DIR, 'last_gif.txt')
AVATAR_IMAGE_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRbQET0UQUR67fyXYDkGJ9gCMy81rZ-W-gmSwaZdIdoifMUuKMoRz8fV-fXXXKO17VfJ5k&usqp=CAU"
AVATAR_IMAGE_PATH = os.path.join(DOCUMENTS_DIR, 'avatar.png')
OPACITY_FILE = os.path.join(DOCUMENTS_DIR, 'opacity_value.txt')

# Убедимся, что каталог существует
os.makedirs(DOCUMENTS_DIR, exist_ok=True)
os.makedirs(GIF_FOLDER, exist_ok=True)


AUTOSTART_PATH = os.path.expanduser('~/.config/autostart/kiwi_widget.desktop')  # Путь для автозапуска на Linux

def create_autostart_file():
    autostart_content = f"""[Desktop Entry]
Type=Application
Exec=python3 {sys.argv[0]}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name=Kiwi Widget
"""
    os.makedirs(os.path.dirname(AUTOSTART_PATH), exist_ok=True)
    with open(AUTOSTART_PATH, 'w') as f:
        f.write(autostart_content)

def remove_autostart_file():
    if os.path.exists(AUTOSTART_PATH):
        os.remove(AUTOSTART_PATH)

def create_autostart_windows():
    autostart_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "Kiwi Widget"
    app_path = f'"{sys.executable}" "{os.path.abspath(sys.argv[0])}"'
    
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, autostart_key, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path)
            print(f"Автозапуск {app_name} добавлен в реестр Windows.")
    except Exception as e:
        print(f"Ошибка при добавлении автозапуска в реестр: {e}")

def remove_autostart_windows():
    autostart_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "Kiwi Widget"

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, autostart_key, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, app_name)
            print(f"Автозапуск {app_name} удален из реестра Windows.")
    except FileNotFoundError:
        print(f"Запись {app_name} не найдена в реестре.")
    except Exception as e:
        print(f"Ошибка при удалении автозапуска из реестра: {e}")

def download_avatar_image():
    if not os.path.exists(AVATAR_IMAGE_PATH):
        try:
            response = requests.get(AVATAR_IMAGE_URL)
            response.raise_for_status()  
            with open(AVATAR_IMAGE_PATH, 'wb') as f:
                f.write(response.content)
            print(f"Аватарка загружена и сохранена по пути: {AVATAR_IMAGE_PATH}")
        except Exception as e:
            print(f"Ошибка загрузки аватарки: {e}")
    return AVATAR_IMAGE_PATH


class CustomSlider(QSlider):
    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setRange(30, 100)
        self.valueChanged.connect(self.update_parent_opacity)
        self.setFixedHeight(40)


    def update_parent_opacity(self, value):
        parent_window = self.parent()
        while parent_window and not hasattr(parent_window, 'set_gif_opacity'):
            parent_window = parent_window.parent()
        if parent_window:
            parent_window.set_gif_opacity(value)
            parent_window.save_opacity(value)
        print(f"CustomSlider: Изменено значение прозрачности на {value}")


    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        option = QStyleOptionSlider()
        self.initStyleOption(option)
        handle_rect = self.style().subControlRect(QStyle.CC_Slider, option, QStyle.SC_SliderHandle, self)
        if self.orientation() == Qt.Horizontal:
            handle_rect.moveCenter(QPoint(handle_rect.center().x(), handle_rect.center().y()))
        else:
            handle_rect.moveCenter(QPoint(handle_rect.center().x(), handle_rect.center().y()))
        
        value = self.value()
        text_rect = handle_rect.adjusted(0, 0, 0, 0)
        painter.setPen(Qt.black)
        painter.drawText(text_rect, Qt.AlignCenter, f"{value}%")
        painter.end()

class OptionPopup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.opacity_slider = QSlider(self)
        self.opacity_slider.setVisible(False)
        self.setFixedSize(200, 450)

        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(1)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        self.setLayout(layout)

        self.setStyleSheet("background-color: rgba(51, 51, 51, 200); border-radius: 20px;")

        # Кнопки
        self.close_button = self.create_styled_button("#ff4c4c", "Закрыть", self.parent().close)
        self.move_button = self.create_styled_button("#4caf50", "Перемещение: ВЫКЛ.", self.parent().toggle_move_mode)
        self.resize_button = self.create_styled_button("#2196f3", "Изменить размер", self.parent().change_size)
        self.change_gif_button = self.create_styled_button("#ff9800", "Изменить GIF", self.parent().change_gif)
        self.restart_button = self.create_styled_button("#9e9e9e", "Рестарт", self.parent().restart_application)
        self.opacity_slider.setVisible(False)
        self.autostart_checkbox = QCheckBox("Автозапуск", self)
        self.autostart_checkbox.setChecked(self.parent().load_autostart())
        self.autostart_checkbox.stateChanged.connect(self.parent().toggle_autostart)
        self.autostart_checkbox.setStyleSheet("""
            QCheckBox {
                background-color: #333;
                color: white;
                border-radius: 15px;
                padding: 10px;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """)

        # Ползунок прозрачности
        self.opacity_slider = CustomSlider(Qt.Horizontal, self)
        self.opacity_slider.setRange(30, 100)

        parent_window = self.parent()
        while parent_window and not hasattr(parent_window, 'load_opacity'):
            parent_window = parent_window.parent()
        if parent_window:
            parent_window.load_opacity()  # Устанавливаем значение из родителя
            self.opacity_slider.setValue(parent_window.opacity_slider.value())  # Устанавливаем значение ползунка в OptionPopup

        self.opacity_slider.valueChanged.connect(self.update_opacity)

        self.opacity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(34, 30, 32, 8);
                height: 7px;
                border-radius: 10px;
            }
            QSlider::handle:horizontal {
                background: #7a8eeb;
                width: 40px;
                border: 1px solid #000;
                margin: -5px 0;
                border-radius: 15px;
            }
            QSlider::sub-page:horizontal {
                background: #44559c;
                border-radius: 5px;
            }
            QSlider::add-page:horizontal {
                background: #8289ab;
                border-radius: 5px;
            }
        """)

        layout.addWidget(self.close_button)
        layout.addWidget(self.move_button)
        layout.addWidget(self.resize_button)
        layout.addWidget(self.change_gif_button)
        layout.addWidget(self.restart_button)
        layout.addWidget(self.autostart_checkbox)
        layout.addWidget(self.opacity_slider)
        layout.setAlignment(Qt.AlignTop)


    def update_opacity(self, value):
        parent_window = self.parent()
        while parent_window and not hasattr(parent_window, 'set_gif_opacity'):
            parent_window = parent_window.parent()
        if parent_window:
            parent_window.set_gif_opacity(value)
            parent_window.save_opacity(value)
        print(f"OptionPopup: Изменено значение прозрачности на {value}")

    def create_styled_button(self, color, text, callback):
        button = QPushButton(text, self)
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                border: none;
                border-radius: 20px;
                width: 180px;
                height: 40px;
                color: white;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {self.darker_color(color)};
            }}
        """)
        button.clicked.connect(callback)
        return button

    def darker_color(self, color):
        qcolor = QColor(color)
        qcolor = qcolor.darker(150)
        return qcolor.name()

    def fade_in(self):
        print("Starting fade_in animation")
        self.setWindowOpacity(1)
        animation = QPropertyAnimation(self, b"windowOpacity")
        animation.setDuration(300)  # Длительность анимации в миллисекундах
        animation.setStartValue(0)
        animation.setEndValue(1)
        animation.finished.connect(lambda: print("Animation complete: fade_in"))
        animation.start()
        self.show()

    def fade_out(self):
        print("Starting fade_out animation")
        animation = QPropertyAnimation(self, b"windowOpacity")
        animation.setDuration(300)  # Длительность анимации в миллисекундах
        animation.setStartValue(1)
        animation.setEndValue(0)
        animation.finished.connect(lambda: print("Animation complete: fade_out"))
        animation.finished.connect(self.hide)
        animation.start()




class TransparentWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Kiwi Widget')

        self.moving_mode = False  # Флаг режима перемещения
        self.start_pos = None

        self.gif_movie = None  # Инициализируем как None
        self.gif_label = QLabel(self)
        self.opacity_slider = QSlider(self)
        self.opacity_slider.setVisible(False)
        self.opacity_slider.setRange(30, 100)  # Установи диапазон значений ползунка
       
       
         # Подключаем сигнал к методу после загрузки значения
        self.opacity_slider.valueChanged.connect(self.on_opacity_slider_changed)
        
        # Загружаем значение прозрачности при запуске
        self.load_opacity()





        self.setStyleSheet("background-color: transparent;")  # Устанавливаем прозрачный фон
        self.load_opacity()

        self.load_window_size_and_position()  # Загрузка размеров и позиции окна

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(1)

        self.setMask(self.create_mask())

        # Загружаем аватарку
        download_avatar_image()
        self.setWindowIcon(QIcon(AVATAR_IMAGE_PATH))

        # Загрузка последнего GIF
        self.load_last_gif_path()

        self.gif_label.setGeometry(0, 0, self.width(), self.height())
        if self.gif_movie:
            self.gif_movie.setScaledSize(self.gif_label.size())
            self.gif_movie.start()

        self.gif_label.setStyleSheet("background-color: white; border-radius: 20px;")  # Белый фон для gif_label

        self.gif_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.gif_label.customContextMenuRequested.connect(self.toggle_menu)

        # Добавь этот код для обработки ПКМ
        self.gif_label.setContextMenuPolicy(Qt.CustomContextMenu)
        self.gif_label.customContextMenuRequested.connect(self.showContextMenu)

        # Создаем всплывающее окно для параметров
        self.option_popup = OptionPopup(self)

        # Устанавливаем начальный текст кнопки перемещения
        self.update_move_button_text()

        # Таймер для изменения размеров гифки
        self.resize_timer = QTimer()
        self.resize_timer.timeout.connect(self.animate_resize)

        self.target_size = None  # Целевая величина для изменения размеров



    def text(self, value):
        text = ("Прозрачность")

    def save_opacity(self, value):
        with open(OPACITY_FILE, "w") as file:
            file.write(str(value))
        print(f"Сохранено значение: {value} в {OPACITY_FILE}")

    def load_opacity(self):
        try:
            with open(OPACITY_FILE, "r") as file:
                value = int(file.read().strip())
                self.opacity_slider.blockSignals(True)
                self.opacity_slider.setValue(value)
                self.set_gif_opacity(value)
                self.opacity_slider.blockSignals(False)
            print(f"Загружено значение: {value} из {OPACITY_FILE}")
        except FileNotFoundError:
            print("Файл не найден, устанавливаем значение по умолчанию")
        except ValueError:
            print("Неверное значение в файле")

    def set_gif_opacity(self, value):
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(value / 100)
        self.gif_label.setGraphicsEffect(opacity_effect)
        print(f"Применено значение прозрачности: {value}")

    def on_opacity_slider_changed(self, value):
        print(f"Изменение ползунка до: {value}")
        self.set_gif_opacity(value)
        self.save_opacity(value)
        print(f"Сохранено новое значение: {value}")


    def update_gif_size(self):
        if self.gif_movie:
            self.gif_movie.setScaledSize(QSize(self.width() + 10, self.height() + 10))  # Гифка чуть больше размера окна
            self.gif_movie.start()

    def animate_resize(self):
        if self.target_size:
            current_width = self.width()
            current_height = self.height()
            target_width, target_height = self.target_size

            if current_width != target_width or current_height != target_height:
                step_width = (target_width - current_width) // max(1, abs(target_width - current_width))
                step_height = (target_height - current_height) // max(1, abs(target_height - current_height))

                new_width = current_width + step_width
                new_height = current_height + step_height

                self.setUpdatesEnabled(False)
                self.resize(new_width, new_height)
                if self.gif_movie:
                    self.gif_movie.setScaledSize(QSize(new_width + 10, new_height + 10))  # Гифка на 10px больше окна
                    self.gif_movie.start()
                self.setUpdatesEnabled(True)
                self.repaint()
            else:
                self.resize_timer.stop()
                self.save_window_size_and_position()
                if self.gif_movie:
                    self.gif_movie.setScaledSize(self.size())
                    self.gif_movie.start()


    def showContextMenu(self, pos):
        print("showContextMenu called")
        if self.option_popup.isVisible():
            print("Menu is visible, calling fade_out")
            self.option_popup.fade_out()
        else:
            print("Menu is not visible, calling fade_in")
            screen_geometry = QDesktopWidget().screenGeometry()
            center_x = (screen_geometry.width() - self.option_popup.width()) // 2
            center_y = (screen_geometry.height() - self.option_popup.height()) // 2
            self.option_popup.move(center_x, center_y)
            self.option_popup.fade_in()



    def create_mask(self):
        path = QPainterPath()
        radius = 20
        path.addRoundedRect(0, 0, self.width(), self.height(), radius, radius)
        region = QRegion(path.toFillPolygon().toPolygon())
        return region

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setMask(self.create_mask())
        self.gif_label.setGeometry(0, 0, self.width(), self.height())
        self.update_gif_size()

    def moveEvent(self, event):
        super().moveEvent(event)
        self.save_window_size_and_position()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.moving_mode:
            self.start_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.moving_mode and event.buttons() == Qt.LeftButton:
            self.move(event.globalPos() - self.start_pos)
            event.accept()
    def load_window_size_and_position(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                size_position = f.read().split()
                if len(size_position) == 4:
                    width, height, x, y = map(int, size_position)
                    self.resize(width, height)
                    self.move(x, y)
    def load_last_gif_path(self):
       if os.path.exists(LAST_GIF_FILE):
            with open(LAST_GIF_FILE, 'r') as f:
                gif_path = f.read()
                if os.path.exists(gif_path):
                    self.gif_movie = QMovie(gif_path)
                    self.gif_label.setMovie(self.gif_movie)
                     
    def toggle_move_mode(self):
        self.moving_mode = not self.moving_mode
        self.update_move_button_text()

    def update_move_button_text(self):
        move_button_text = "Перемещение: ВКЛ." if self.moving_mode else "Перемещение: ВЫКЛ."
        self.option_popup.move_button.setText(move_button_text)
    def change_size(self):
        dialog = SizeInputDialog(self.width(), self.height(), self)
        if dialog.exec_() == QDialog.Accepted:
            width, height = dialog.get_values()
            if width and height:
                self.target_size = (width, height)
                self.resize_timer.start(10)  # Интервал в миллисекундах
    def change_gif(self):
        dialog = GifUrlInputDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            gif_url = dialog.get_value()
            if gif_url:
                self.set_gif_from_url(gif_url)

    def restart_application(self):
        try:
            executable = sys.executable if hasattr(sys, 'frozen') else sys.argv[0]
            task_name = "Kiwi_Widget_Restart"
            
            # Удаляем задание, если оно уже существует
            subprocess.call(['schtasks', '/delete', '/tn', task_name, '/f'])
            
            # Создаем новое задание на перезапуск
            subprocess.call([
                'schtasks', '/create', '/tn', task_name, '/tr', f'"{executable} {os.path.abspath(sys.argv[0])}"',
                '/sc', 'once', '/st', '00:00', '/sd', '01/01/1990', '/f'
            ])
            
            # Запускаем задание
            subprocess.call(['schtasks', '/run', '/tn', task_name])
            
            QApplication.quit()
        except Exception as e:
            print(f"Ошибка при перезапуске: {e}")






    def load_autostart(self):
        return os.path.exists(AUTOSTART_PATH) or self.autostart_windows_exists()

    def autostart_windows_exists(self):
        autostart_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "Kiwi Widget"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, autostart_key, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, app_name)
                return True
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"Ошибка при проверке автозапуска в реестре: {e}")
            return False

    def toggle_autostart(self, state):
        if state == Qt.Checked:
            create_autostart_file()
            create_autostart_windows()
        else:
            remove_autostart_file()
            remove_autostart_windows()



    def save_window_size_and_position(self):
        with open(CONFIG_FILE, 'w') as f:
            f.write(f"{self.width()} {self.height()} {self.x()} {self.y()}")

    def fade_in(self):
        self.setWindowOpacity(0)
        animation = QPropertyAnimation(self, b"windowOpacity")
        animation.setDuration(300)
        animation.setStartValue(0)
        animation.setEndValue(0.9)
        animation.finished.connect(lambda: print("Animation complete: fade_in"))
        animation.start()
        self.show()

    def fade_out(self):
        animation = QPropertyAnimation(self, b"windowOpacity")
        animation.setDuration(300)
        animation.setStartValue(0.9)
        animation.setEndValue(0)
        animation.finished.connect(lambda: print("Animation complete: fade_out"))
        animation.finished.connect(self.hide)
        animation.start()

    def toggle_menu(self):
        if self.option_popup.isVisible():
            self.option_popup.hide()
        else:
            screen_geometry = QDesktopWidget().screenGeometry()
            center_x = (screen_geometry.width() - self.option_popup.width()) // 2
            center_y = (screen_geometry.height() - self.option_popup.height()) // 2
            self.option_popup.move(center_x, center_y)
            self.option_popup.show()


    def show_error_message(self, text):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText(text)
        msg.setWindowTitle("Ошибка")
        msg.exec_()
        
    def set_gif_from_url(self, url):
        if not url.lower().endswith('.gif'):
            self.show_error_message("Неверный формат ссылки. Пожалуйста, введите ссылку на GIF.")
            return
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            gif_path = os.path.join(GIF_FOLDER, f"custom_gif_{int(datetime.now().timestamp())}.gif")
            with open(gif_path, 'wb') as f:
                f.write(response.content)

            self.gif_movie = QMovie(gif_path)
            self.gif_label.setMovie(self.gif_movie)
            self.gif_movie.setScaledSize(self.gif_label.size())
            self.gif_movie.start()

            self.save_last_gif_path(gif_path)
        except requests.exceptions.RequestException:
            self.show_error_message("Ссылка недоступна. Пожалуйста, введите действующую ссылку на GIF.")

    def save_last_gif_path(self, gif_path):
        with open(LAST_GIF_FILE, 'w') as f:
            f.write(gif_path)


    def set_opacity_effect(self, opacity):
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(opacity)
        return effect



    def contextMenuEvent(self, event):
        print("contextMenuEvent called")
        if self.option_popup.isVisible():
            self.option_popup.fade_out()
        else:
            screen_geometry = QDesktopWidget().screenGeometry()
            center_x = (screen_geometry.width() - self.option_popup.width()) // 2
            center_y = (screen_geometry.height() - self.option_popup.height()) // 2
            self.option_popup.move(center_x, center_y)
            self.option_popup.fade_in()

    def toggle_move_mode(self):
        self.moving_mode = not self.moving_mode
        self.update_move_button_text()

    def update_move_button_text(self):
        move_button_text = "Перемещение: ВКЛ." if self.moving_mode else "Перемещение: ВЫКЛ."
        self.option_popup.move_button.setText(move_button_text)

    def change_size(self):
        dialog = SizeInputDialog(self.width(), self.height(), self)
        if dialog.exec_() == QDialog.Accepted:
            width, height = dialog.get_values()
            if width and height:
                self.target_size = (width, height)
                self.resize_timer.start(10)  # Интервал в миллисекундах

    def animate_resize(self):
        if self.target_size:
            current_width = self.width()
            current_height = self.height()
            target_width, target_height = self.target_size

            if current_width != target_width or current_height != target_height:
                step_width = (target_width - current_width) // abs(target_width - current_width) if current_width != target_width else 0
                step_height = (target_height - current_height) // abs(target_height - current_height) if current_height != target_height else 0

                self.setUpdatesEnabled(False)  # Блокируем перерисовку
                self.resize(current_width + step_width, current_height + step_height)
                self.setUpdatesEnabled(True)  # Включаем перерисовку
                self.repaint()  # Перерисовываем окно
            else:
                self.resize_timer.stop()
                self.save_window_size_and_position()
                if self.gif_movie:
                    QTimer.singleShot(50, self.gif_movie.start)  # Запускаем GIF после завершения анимации


    def change_gif(self):
        dialog = GifUrlInputDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            gif_url = dialog.get_value()
            if gif_url:
                self.set_gif_from_url(gif_url)

    def set_gif_from_url(self, url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            gif_path = os.path.join(GIF_FOLDER, f"custom_gif_{int(datetime.now().timestamp())}.gif")
            with open(gif_path, 'wb') as f:
                f.write(response.content)

            self.gif_movie = QMovie(gif_path)
            self.gif_label.setMovie(self.gif_movie)
            self.gif_movie.setScaledSize(self.gif_label.size())
            self.gif_movie.start()

            self.save_last_gif_path(gif_path)
        except Exception as e:
            print(f"Ошибка загрузки GIF: {e}")

    def save_window_size_and_position(self):
        with open(CONFIG_FILE, 'w') as f:
            f.write(f"{self.width()} {self.height()} {self.x()} {self.y()}")

    def load_window_size_and_position(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                size_position = f.read().split()
                if len(size_position) == 4:
                    width, height, x, y = map(int, size_position)
                    self.resize(width, height)
                    self.move(x, y)


    def save_last_gif_path(self, gif_path):
        with open(LAST_GIF_FILE, 'w') as f:
            f.write(gif_path)

    def load_last_gif_path(self):
        if os.path.exists(LAST_GIF_FILE):
            with open(LAST_GIF_FILE, 'r') as f:
                gif_path = f.read()
                if os.path.exists(gif_path):
                    self.gif_movie = QMovie(gif_path)
                    self.gif_label.setMovie(self.gif_movie)

    def restart_application(self):
        try:
            executable = sys.executable if hasattr(sys, 'frozen') else sys.argv[0]
            if hasattr(sys, 'frozen'):
                executable = os.path.abspath(sys.executable)
            else:
                executable = os.path.abspath(sys.argv[0])
    
            task_name = "Kiwi_Widget_Restart"
    
            # Удаляем задание, если оно уже существует
            subprocess.call(['schtasks', '/delete', '/tn', task_name, '/f'])

            # Создаем новое задание на перезапуск
            subprocess.call([
                'schtasks', '/create', '/tn', task_name, '/tr', f'"{executable}"',
                '/sc', 'once', '/st', (datetime.now() + timedelta(seconds=10)).strftime("%H:%M"), '/f'
            ])

            # Запускаем задание
            subprocess.call(['schtasks', '/run', '/tn', task_name])
        
            QApplication.quit()
        except Exception as e:
            print(f"Ошибка при перезапуске: {e}")


    def toggle_autostart(self, state):
        if state == Qt.Checked:
            create_autostart_file()
            create_autostart_windows()
        else:
            remove_autostart_file()
            remove_autostart_windows()

    def load_autostart(self):
        return os.path.exists(AUTOSTART_PATH) or self.autostart_windows_exists()

    def autostart_windows_exists(self):
        autostart_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
        app_name = "Kiwi Widget"
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, autostart_key, 0, winreg.KEY_READ) as key:
                winreg.QueryValueEx(key, app_name)
                return True
        except FileNotFoundError:
            return False
        except Exception as e:
            print(f"Ошибка при проверке автозапуска в реестре: {e}")
            return False

    def showContextMenu(self, pos):
        print("showContextMenu called")
        if self.option_popup.isVisible():
            print("Menu is visible, calling fade_out")
            self.option_popup.fade_out()
        else:
            print("Menu is not visible, calling fade_in")
            screen_geometry = QDesktopWidget().screenGeometry()
            center_x = (screen_geometry.width() - self.option_popup.width()) // 2
            center_y = (screen_geometry.height() - self.option_popup.height()) // 2
            self.option_popup.move(center_x, center_y)
            self.option_popup.fade_in()




class SizeInputDialog(QDialog):
    def __init__(self, current_width, current_height, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Изменить размер окна")
        self.setFixedSize(300, 150)
        layout = QVBoxLayout(self)

        self.width_input = QLineEdit(str(current_width), self)
        self.height_input = QLineEdit(str(current_height), self)
        layout.addWidget(QLabel("Ширина:"))
        layout.addWidget(self.width_input)
        layout.addWidget(QLabel("Высота:"))
        layout.addWidget(self.height_input)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Устанавливаем стили
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: black;
            }
            QLineEdit {
                color: black;
                background-color: white;
                border: 1px solid #ccc;
            }
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 10px;
            }
        """)

    def get_values(self):
        width = int(self.width_input.text())
        height = int(self.height_input.text())
        return width, height

class GifUrlInputDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Изменить GIF")
        self.setFixedSize(300, 150)
        layout = QVBoxLayout(self)

        self.gif_url_input = QLineEdit(self)
        layout.addWidget(QLabel("Введите ссылку на GIF:"))
        layout.addWidget(self.gif_url_input)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Устанавливаем стили
        self.setStyleSheet("""
            QDialog {
                background-color: white;
            }
            QLabel {
                color: black;
            }
            QLineEdit {
                color: black;
                background-color: white;
                border: 1px solid #ccc;
            }
            QPushButton {
                background-color: #2196f3;
                color: white;
                border: none;
                border-radius: 10px;
            }
        """)

    def get_value(self):
        return self.gif_url_input.text()



if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TransparentWindow()
    window.show()
    sys.exit(app.exec_())
