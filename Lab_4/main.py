import sys
import time

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QComboBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QPlainTextEdit, QVBoxLayout, QWidget)

from algorithms import cohen_sutherland, liang_barsky, midpoint_clip, sutherland_hodgman
from canvas import ClippingCanvas
from input_parser import parse_segments_file


LINE_FUNCTIONS = {
    "Сазерленд–Коэн": cohen_sutherland,
    "Лианг–Барски": liang_barsky,
    "Средняя точка": midpoint_clip,
}
SEGMENT_EXAMPLE = "-18 -10 18 12\n-15 4 15 4\n-4 -14 -4 14\n-18 11 -13 8\n-6 -2 7 10"
POLYGON_EXAMPLE = "-16 -4\n-6 -12\n8 -10\n17 0\n7 13\n-9 11"
MAX_COORDINATE = 10000


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ЛР4 — Отсечение отрезков и многоугольников")
        self.canvas = ClippingCanvas()
        self._build_ui()
        self.load_example()
        self.clip()

    def _build_ui(self):
        panel = QGroupBox("Параметры")
        panel.setFixedWidth(330)
        layout = QVBoxLayout(panel)
        form = QFormLayout()
        self.mode = QComboBox()
        self.mode.addItems(("Отрезки", "Выпуклый многоугольник"))
        self.mode.currentIndexChanged.connect(self.mode_changed)
        self.algorithm = QComboBox()
        self.algorithm.addItems(tuple(LINE_FUNCTIONS))
        form.addRow("Режим:", self.mode)
        form.addRow("Алгоритм:", self.algorithm)
        self.xmin, self.ymin, self.xmax, self.ymax = [QLineEdit() for _ in range(4)]
        for name, edit in (("xmin:", self.xmin), ("ymin:", self.ymin),
                           ("xmax:", self.xmax), ("ymax:", self.ymax)):
            form.addRow(name, edit)
        layout.addLayout(form)
        self.input_label = QLabel("Отрезки: x1 y1 x2 y2")
        layout.addWidget(self.input_label)
        self.data = QPlainTextEdit()
        self.data.setMinimumHeight(210)
        layout.addWidget(self.data)
        load_button = QPushButton("Загрузить файл")
        load_button.clicked.connect(self.load_file)
        example_button = QPushButton("Пример")
        example_button.clicked.connect(self.load_example)
        clip_button = QPushButton("Выполнить отсечение")
        clip_button.clicked.connect(self.clip)
        for button in (load_button, example_button, clip_button):
            layout.addWidget(button)
        self.info = QLabel("Исходных объектов: —\nВидимых объектов: —\nВремя: —")
        layout.addWidget(self.info)
        layout.addStretch(1)
        legend = QLabel("Синее — окно\nСерое — исходные данные\nКрасное — результат")
        layout.addWidget(legend)

        plus, minus = QPushButton("+"), QPushButton("−")
        plus.setFixedWidth(42); minus.setFixedWidth(42)
        plus.clicked.connect(lambda: self.canvas.zoom(1.25))
        minus.clicked.connect(lambda: self.canvas.zoom(0.8))
        zoom = QHBoxLayout(); zoom.addWidget(QLabel("Масштаб:")); zoom.addWidget(plus); zoom.addWidget(minus)
        right = QVBoxLayout(); right.addWidget(self.canvas, 1); right.addLayout(zoom)
        root = QWidget(); root_layout = QHBoxLayout(root)
        root_layout.addLayout(right, 1); root_layout.addWidget(panel)
        self.setCentralWidget(root)
        self.resize(1180, 820)

    def mode_changed(self):
        polygon = self.mode.currentIndex() == 1
        self.algorithm.setEnabled(not polygon)
        self.input_label.setText("Вершины: x y" if polygon else "Отрезки: x1 y1 x2 y2")
        self.load_example()

    def load_example(self):
        for edit, value in zip((self.xmin, self.ymin, self.xmax, self.ymax), ("-10", "-7", "10", "7")):
            edit.setText(value)
        self.data.setPlainText(POLYGON_EXAMPLE if self.mode.currentIndex() else SEGMENT_EXAMPLE)

    def load_file(self):
        if self.mode.currentIndex() == 1:
            QMessageBox.information(self, "Формат файла", "Формат из условия предназначен для списка отрезков.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Открыть входной файл", "", "Текстовые файлы (*.txt);;Все файлы (*)")
        if not path:
            return
        try:
            segments, rect = parse_segments_file(path)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Ошибка файла", str(error))
            return
        self.data.setPlainText("\n".join(f"{a[0]:g} {a[1]:g} {b[0]:g} {b[1]:g}" for a, b in segments))
        for edit, value in zip((self.xmin, self.ymin, self.xmax, self.ymax), rect):
            edit.setText(f"{value:g}")
        self.clip()

    def rectangle(self):
        try:
            rect = tuple(float(edit.text().strip()) for edit in (self.xmin, self.ymin, self.xmax, self.ymax))
        except ValueError as error:
            raise ValueError("Координаты окна должны быть числами") from error
        if rect[0] >= rect[2] or rect[1] >= rect[3]:
            raise ValueError("Требуется xmin < xmax и ymin < ymax")
        return rect

    def rows(self, count):
        result = []
        for number, line in enumerate(self.data.toPlainText().splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != count:
                raise ValueError(f"Строка {number}: ожидается {count} числа")
            try:
                result.append(tuple(map(float, parts)))
            except ValueError as error:
                raise ValueError(f"Строка {number}: обнаружено нечисловое значение") from error
        return result

    @staticmethod
    def check_limits(values):
        if any(abs(value) > MAX_COORDINATE for value in values):
            raise ValueError(f"Координаты должны находиться в диапазоне ±{MAX_COORDINATE}")

    def clip(self):
        try:
            rect = self.rectangle()
            self.check_limits(rect)
            started = time.perf_counter_ns()
            if self.mode.currentIndex() == 0:
                rows = self.rows(4)
                if not rows:
                    raise ValueError("Введите хотя бы один отрезок")
                self.check_limits(value for row in rows for value in row)
                segments = [((row[0], row[1]), (row[2], row[3])) for row in rows]
                function = LINE_FUNCTIONS[self.algorithm.currentText()]
                clipped = [result for segment in segments if (result := function(segment, rect)) is not None]
                elapsed = (time.perf_counter_ns() - started) / 1000
                self.canvas.set_scene(rect, segments=segments, clipped_segments=clipped)
                self.info.setText(f"Исходных отрезков: {len(segments)}\nВидимых частей: {len(clipped)}\nВремя: {elapsed:.1f} мкс")
            else:
                rows = self.rows(2)
                self.check_limits(value for row in rows for value in row)
                polygon = [(row[0], row[1]) for row in rows]
                clipped = sutherland_hodgman(polygon, rect)
                elapsed = (time.perf_counter_ns() - started) / 1000
                self.canvas.set_scene(rect, polygon=polygon, clipped_polygon=clipped)
                self.info.setText(f"Исходных вершин: {len(polygon)}\nВидимых вершин: {len(clipped)}\nВремя: {elapsed:.1f} мкс")
        except ValueError as error:
            QMessageBox.warning(self, "Ошибка входных данных", str(error))


def main():
    app = QApplication(sys.argv)
    window = MainWindow(); window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
