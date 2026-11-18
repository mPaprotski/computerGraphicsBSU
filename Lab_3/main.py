import math
import sys
import time

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIntValidator
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QSlider, QVBoxLayout, QWidget)

from algorithms import bresenham_circle, bresenham_line, dda, step_by_step
from canvas import RasterCanvas


EXAMPLES = {0: ("0", "0", "31", "13", ""), 1: ("0", "0", "9", "27", ""),
            2: ("-19", "-14", "22", "17", ""), 3: ("0", "0", "", "", "23")}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ЛР3 — Базовые растровые алгоритмы")
        self.canvas = RasterCanvas()
        self._user_edited = False
        self._build_ui()
        self.load_example()
        self.draw()

    def _build_ui(self):
        panel = QGroupBox("Параметры")
        form = QFormLayout()
        self.algorithm = QComboBox()
        self.algorithm.addItems(("Пошаговый", "ЦДА (DDA)", "Брезенхем (линия)", "Брезенхем (окружность)"))
        self.algorithm.currentIndexChanged.connect(self.algorithm_changed)
        validator = QIntValidator(-1_000_000, 1_000_000, self)
        self.x1, self.y1, self.x2, self.y2, self.radius = [QLineEdit() for _ in range(5)]
        for edit in (self.x1, self.y1, self.x2, self.y2, self.radius):
            edit.setValidator(validator)
            edit.textEdited.connect(self._on_user_edited)
        example = QPushButton("Пример")
        example.clicked.connect(self.load_example)
        draw = QPushButton("Построить")
        draw.clicked.connect(self.draw)
        self.info = QLabel("Точек: —\nВремя: —")
        self.centers = QCheckBox("Показывать центры")
        self.centers.toggled.connect(self.toggle_centers)
        form.addRow("Алгоритм:", self.algorithm)
        for label, edit in (("x1:", self.x1), ("y1:", self.y1), ("x2:", self.x2),
                            ("y2:", self.y2), ("R:", self.radius)):
            form.addRow(label, edit)
        for widget in (example, draw, self.info, self.centers):
            form.addRow(widget)
        panel.setLayout(form)
        panel.setFixedWidth(260)

        plus, minus = QPushButton("+"), QPushButton("−")
        plus.setFixedWidth(40); minus.setFixedWidth(40)
        plus.clicked.connect(lambda: self.zoom(1.25)); minus.clicked.connect(lambda: self.zoom(0.8))
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setInvertedAppearance(True)
        self.slider.valueChanged.connect(lambda value: self.canvas.set_cell(self.slider_to_cell(value)))
        bottom = QWidget()
        bottom_layout = QHBoxLayout(bottom)
        bottom_layout.setContentsMargins(8, 4, 8, 8)
        bottom_layout.addWidget(QLabel("Масштаб:")); bottom_layout.addWidget(plus)
        bottom_layout.addWidget(self.slider, 1); bottom_layout.addWidget(minus)

        central = QWidget(); content = QHBoxLayout(central)
        content.setContentsMargins(8, 8, 8, 0)
        right = QWidget(); right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(panel); right_layout.addStretch(1)
        content.addWidget(self.canvas, 1); content.addWidget(right)
        root = QWidget(); layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(central, 1); layout.addWidget(bottom)
        self.setCentralWidget(root); self.resize(1100, 800)

    def cell_bounds(self):
        side = max(1, min(self.canvas.width(), self.canvas.height()))
        return max(1, round(side / 500)), max(2, round(side / 10))

    def slider_to_cell(self, value):
        minimum, maximum = self.cell_bounds()
        return round(minimum * (maximum / minimum) ** (value / 1000))

    def sync_slider(self):
        minimum, maximum = self.cell_bounds()
        cell = max(minimum, min(maximum, self.canvas.cell))
        value = 500 if maximum <= minimum else round(math.log(cell / minimum) / math.log(maximum / minimum) * 1000)
        self.slider.blockSignals(True); self.slider.setValue(value); self.slider.blockSignals(False)

    def zoom(self, factor):
        self.canvas.zoom(factor); self.sync_slider()

    def toggle_centers(self, checked):
        self.canvas.show_centers = checked; self.canvas.update()

    def _on_user_edited(self, _text):
        self._user_edited = True

    def algorithm_changed(self):
        circle = self.algorithm.currentIndex() == 3
        self.x2.setEnabled(not circle); self.y2.setEnabled(not circle); self.radius.setEnabled(circle)
        if not self._user_edited:
            self.load_example()

    def load_example(self):
        for edit, value in zip((self.x1, self.y1, self.x2, self.y2, self.radius), EXAMPLES[self.algorithm.currentIndex()]):
            edit.blockSignals(True); edit.setText(value); edit.blockSignals(False)
        self._user_edited = False

    @staticmethod
    def integer(edit, name):
        if not edit.text().strip():
            raise ValueError(f"Поле {name} не заполнено")
        return int(edit.text())

    def primitive_fits_grid(self, index, x1, y1, x2=None, y2=None, radius=None):
        x_min, x_max, y_min, y_max = self.canvas.coordinate_bounds()
        if index == 3:
            fits = (
                x_min <= x1 - radius and x1 + radius <= x_max
                and y_min <= y1 - radius and y1 + radius <= y_max
            )
        else:
            fits = (
                x_min <= x1 <= x_max and x_min <= x2 <= x_max
                and y_min <= y1 <= y_max and y_min <= y2 <= y_max
            )
        if not fits:
            QMessageBox.warning(
                self,
                "Выход за пределы сетки",
                "Заданный примитив не помещается в доступную область сетки.\n\n"
                f"Допустимый диапазон X: от {x_min} до {x_max}.\n"
                f"Допустимый диапазон Y: от {y_min} до {y_max}.\n\n"
                "Уменьшите координаты или радиус.",
            )
        return fits

    def draw(self):
        try:
            x1, y1 = self.integer(self.x1, "x1"), self.integer(self.y1, "y1")
            index = self.algorithm.currentIndex()
            if index == 3:
                radius = self.integer(self.radius, "R")
                if radius < 0:
                    raise ValueError("Радиус не может быть отрицательным")
                if not self.primitive_fits_grid(index, x1, y1, radius=radius):
                    return
                function, args = bresenham_circle, (x1, y1, radius)
            else:
                x2, y2 = self.integer(self.x2, "x2"), self.integer(self.y2, "y2")
                if not self.primitive_fits_grid(index, x1, y1, x2, y2):
                    return
                function, args = (step_by_step, dda, bresenham_line)[index], (x1, y1, x2, y2)
            started = time.perf_counter_ns(); points = function(*args)
            elapsed = (time.perf_counter_ns() - started) / 1000
        except ValueError as error:
            QMessageBox.warning(self, "Ошибка ввода", str(error)); return
        self.info.setText(f"Точек: {len(points)}\nВремя: {elapsed:.1f} мкс")
        self.canvas.set_points(points); self.canvas.fit(); self.sync_slider()


def main():
    app = QApplication(sys.argv)
    window = MainWindow(); window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
