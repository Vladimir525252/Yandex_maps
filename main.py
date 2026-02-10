import sys

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtWidgets import QApplication, QLabel, QMainWindow, QLineEdit, QPushButton
import requests
from requests.adapters import HTTPAdapter
from urllib3 import Retry

API_KEY_STATIC = 'f3a0fe3a-b07e-4840-a1da-06f18b2ddf13'
API_KEY_GEOCODER = '8013b162-6b42-4997-9691-77b7074026e0'  # Вам нужен ключ от Geocoder API


class MainWindow(QMainWindow):
    g_map: QLabel
    press_delta = 0.1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        uic.loadUi('main_window.ui', self)

        # Находим виджеты, которые должны быть в UI-файле
        self.search_line: QLineEdit = self.findChild(QLineEdit, 'search_line')
        self.search_button: QPushButton = self.findChild(QPushButton, 'search_button')

        # Подключаем обработчики
        if self.search_button:
            self.search_button.clicked.connect(self.search_object)
        if self.search_line:
            self.search_line.returnPressed.connect(self.search_object)

        self.map_zoom = 10
        self.map_ll = [37.977751, 55.757718]
        self.map_key = ''
        self.theme = "dark"
        self.map_pt = ''  # Для хранения координат метки

        self.refresh_map()

    def search_object(self):
        """Поиск объекта по введенному запросу"""
        if not self.search_line:
            return

        search_text = self.search_line.text().strip()
        if not search_text:
            return

        # Геокодирование запроса
        geocoder_params = {
            'apikey': API_KEY_GEOCODER,
            'geocode': search_text,
            'format': 'json'
        }

        try:
            session = requests.Session()
            retry = Retry(total=5, connect=3, backoff_factor=0.5)
            adapter = HTTPAdapter(max_retries=retry)
            session.mount('http://', adapter)
            session.mount('https://', adapter)

            response = session.get('https://geocode-maps.yandex.ru/1.x/',
                                   params=geocoder_params)
            response.raise_for_status()

            data = response.json()

            # Получаем координаты первого результата
            feature_member = data['response']['GeoObjectCollection']['featureMember']
            if not feature_member:
                print("Объект не найден")
                return

            geo_object = feature_member[0]['GeoObject']
            pos = geo_object['Point']['pos']
            lon, lat = map(float, pos.split())

            # Обновляем центр карты
            self.map_ll = [lon, lat]

            # Устанавливаем метку на карте
            self.map_pt = f"{lon},{lat},pm2rdl"  # Красная метка

            # Меняем масштаб для лучшего обзора
            self.map_zoom = 14

            # Обновляем карту
            self.refresh_map()

        except Exception as e:
            print(f"Ошибка при поиске: {e}")

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_PageUp:
            if self.map_zoom < 17:
                self.map_zoom += 1
        elif key == Qt.Key.Key_PageDown:
            if self.map_zoom > 0:
                self.map_zoom -= 1
        elif key == Qt.Key.Key_Right:
            self.map_ll[0] += self.press_delta
            if self.map_ll[0] > 180:
                self.map_ll[0] = self.map_ll[0] - 360
        elif key == Qt.Key.Key_Left:
            self.map_ll[0] -= self.press_delta
            if self.map_ll[0] < 0:
                self.map_ll[0] = self.map_ll[0] + 360
        elif key == Qt.Key.Key_Up:
            if self.map_ll[1] + self.press_delta < 90:
                self.map_ll[1] += self.press_delta
        elif key == Qt.Key.Key_Down:
            if self.map_ll[1] - self.press_delta > -90:
                self.map_ll[1] -= self.press_delta
        elif key == Qt.Key.Key_T:
            if self.theme == "dark":
                self.theme = "light"
            else:
                self.theme = "dark"
        elif key == Qt.Key.Key_Escape:
            # Сбрасываем метку при нажатии Escape
            self.map_pt = ''
        else:
            return

        self.refresh_map()

    def refresh_map(self):
        map_params = {
            "ll": ','.join(map(str, self.map_ll)),
            'z': self.map_zoom,
            'apikey': API_KEY_STATIC,
            "theme": self.theme
        }

        # Добавляем параметр метки, если она есть
        if self.map_pt:
            map_params['pt'] = self.map_pt

        session = requests.Session()
        retry = Retry(total=10, connect=5, backoff_factor=0.5)
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        response = session.get('https://static-maps.yandex.ru/v1',
                               params=map_params)
        img = QImage.fromData(response.content)
        pixmap = QPixmap.fromImage(img)
        self.g_map.setPixmap(pixmap)


app = QApplication(sys.argv)
main_window = MainWindow()
main_window.show()
sys.exit(app.exec())