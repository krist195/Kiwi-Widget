import os
import sys
import requests
from datetime import datetime  
from PyQt5.QtGui import QPainterPath, QRegion, QMovie, QIcon, QColor, QFont
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton, QDialog, QVBoxLayout,
                             QLineEdit, QDialogButtonBox, QWidget, QCheckBox, QDesktopWidget)
from PyQt5.QtCore import Qt, QProcess

DOCUMENTS_DIR = os.path.join(os.path.expanduser("~"), "Documents", "Kiwi Widget")
GIF_FOLDER = os.path.join(DOCUMENTS_DIR, 'gif_files')
CONFIG_FILE = os.path.join(DOCUMENTS_DIR, 'window_config.txt')
AUTOSTART_FILE = os.path.join(DOCUMENTS_DIR, 'autostart_config.txt')
LAST_GIF_FILE = os.path.join(DOCUMENTS_DIR, 'last_gif.txt')
AVATAR_IMAGE_URL = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRbQET0UQUR67fyXYDkGJ9gCMy81rZ-W-gmSwaZdIdoifMUuKMoRz8fV-fXXXKO17VfJ5k&usqp=CAU"
AVATAR_IMAGE_PATH = os.path.join(DOCUMENTS_DIR, 'avatar.png')

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

class OptionPopup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 400)

        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(0.9)

        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        self.setLayout(layout)

        # Кнопки
        self.close_button = self.create_styled_button("#ff4c4c", "Закрыть", self.parent().close)
        self.move_button = self.create_styled_button("#4caf50", "Перемещение: ВЫКЛ.", self.parent().toggle_move_mode)
        self.resize_button = self.create_styled_button("#2196f3", "Изменить размер", self.parent().change_size)
        self.change_gif_button = self.create_styled_button("#ff9800", "Изменить GIF", self.parent().change_gif)
        self.restart_button = self.create_styled_button("#9e9e9e", "Рестарт", self.parent().restart_application)

        # Чекбокс автозапуска с обновленным стилем
        self.autostart_checkbox = QCheckBox("Автозапуск", self)
        self.autostart_checkbox.setChecked(self.parent().load_autostart())
        self.autostart_checkbox.stateChanged.connect(self.parent().toggle_autostart)
        self.autostart_checkbox.setStyleSheet("""
            QCheckBox {
                color: white;
                font-size: 14px;
            }
            QCheckBox::indicator {
                width: 20px;
                height: 20px;
            }
        """)

        # Прямоугольник с более темным фоном и округленными углами
        self.autostart_checkbox.setStyleSheet("""
            QCheckBox {
                background-color: #333;
                color: white;
                border-radius: 15px;
                padding: 10px;
                font-size: 14px;
            }
        """)

        # Добавление кнопок в layout
        layout.addWidget(self.close_button)
        layout.addWidget(self.move_button)
        layout.addWidget(self.resize_button)
        layout.addWidget(self.change_gif_button)
        layout.addWidget(self.restart_button)
        layout.addWidget(self.autostart_checkbox)
        layout.setAlignment(Qt.AlignTop)

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
        
class TransparentWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('Kiwi Widget')

        self.moving_mode = False  # Флаг режима перемещения
        self.start_pos = None

        self.gif_movie = None  # Инициализируем как None
        self.gif_label = QLabel(self)

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

        self.gif_label.setStyleSheet("background-color: white; border-radius: 20px;")

        # Создаем всплывающее окно для параметров
        self.option_popup = OptionPopup(self)

        # Устанавливаем начальный текст кнопки перемещения
        self.update_move_button_text()

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
        if self.gif_movie:
            self.gif_movie.setScaledSize(self.gif_label.size())
            self.gif_movie.start()

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

    def contextMenuEvent(self, event):
        if not self.option_popup.isVisible():
            screen_geometry = QDesktopWidget().screenGeometry()
            center_x = (screen_geometry.width() - self.option_popup.width()) // 2
            center_y = (screen_geometry.height() - self.option_popup.height()) // 2
            self.option_popup.move(center_x, center_y)
            self.option_popup.show()

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
                self.resize(width, height)
                self.save_window_size_and_position()

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
        QProcess.startDetached(sys.executable, sys.argv)
        sys.exit()

    def toggle_autostart(self, state):
        if state == Qt.Checked:
            create_autostart_file()
        else:
            remove_autostart_file()

    def load_autostart(self):
        return os.path.exists(AUTOSTART_PATH)


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
        layout.addWidget(QLabel("Введите URL GIF:"))
        layout.addWidget(self.gif_url_input)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, self)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(button_box)

    def get_value(self):
        return self.gif_url_input.text()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TransparentWindow()
    window.show()
    sys.exit(app.exec_())
