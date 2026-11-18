import math
import sys
import time

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QApplication, QComboBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QMessageBox,
    QPushButton, QPlainTextEdit, QSlider, QVBoxLayout, QWidget)

from algorithms import cohen_sutherland, liang_barsky, midpoint_clip, sutherland_hodgman
from canvas import ClippingCanvas
from input_parser import parse_segments_file

LINE_FUNCTIONS = {"Сазерленд–Коэн": cohen_sutherland,
                  "Лианг–Барски": liang_barsky, "Средняя точка": midpoint_clip}
SEGMENT_EXAMPLE = "-18 -10 18 12\n-15 4 15 4\n-4 -14 -4 14\n-18 11 -13 8\n-6 -2 7 10"
POLYGON_EXAMPLE = "-16 -4\n-6 -12\n8 -10\n17 0\n7 13\n-9 11"
MAX_COORDINATE = 10000


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Лабораторная работа №4 — отсечение")
        self.canvas = ClippingCanvas()
        self._user_edited = self._syncing_slider = False
        self._build_ui()
        self.load_example()
        self.clip()

    def _build_ui(self):
        panel = QGroupBox("Параметры"); panel.setFixedWidth(300)
        panel_layout, form = QVBoxLayout(panel), QFormLayout()
        self.mode = QComboBox(); self.mode.addItems(("Отрезки", "Выпуклый многоугольник"))
        self.algorithm = QComboBox(); self.algorithm.addItems(tuple(LINE_FUNCTIONS))
        self.mode.currentIndexChanged.connect(self.mode_changed)
        form.addRow("Режим:", self.mode); form.addRow("Алгоритм:", self.algorithm)
        self.xmin, self.ymin, self.xmax, self.ymax = [QLineEdit() for _ in range(4)]
        for label, edit in (("xmin:", self.xmin), ("ymin:", self.ymin),
                            ("xmax:", self.xmax), ("ymax:", self.ymax)):
            edit.textEdited.connect(self._on_user_edited); form.addRow(label, edit)
        panel_layout.addLayout(form)
        self.input_label = QLabel("Отрезки: x1 y1 x2 y2"); panel_layout.addWidget(self.input_label)
        self.data = QPlainTextEdit(); self.data.setMinimumHeight(210)
        self.data.textChanged.connect(self._on_user_edited); panel_layout.addWidget(self.data)
        for text, callback in (("Загрузить файл", self.load_file), ("Пример", self.load_example),
                               ("Выполнить отсечение", self.clip)):
            button = QPushButton(text); button.clicked.connect(callback); panel_layout.addWidget(button)
        self.info = QLabel("Исходных объектов: —\nВидимых объектов: —\nВремя: —")
        panel_layout.addWidget(self.info); panel_layout.addStretch(1)
        panel_layout.addWidget(QLabel("Синее — окно\nСерое — исходные данные\nКрасное — результат"))

        scale = QWidget(); scale_layout = QHBoxLayout(scale); scale_layout.setContentsMargins(0, 0, 0, 0)
        scale_layout.addWidget(QLabel("Масштаб:"))
        plus, minus = QPushButton("+"), QPushButton("−")
        plus.setFixedWidth(42); minus.setFixedWidth(42)
        plus.clicked.connect(lambda: self._zoom_by(1.25)); minus.clicked.connect(lambda: self._zoom_by(.8))
        self.scale_slider = QSlider(Qt.Horizontal); self.scale_slider.setRange(0, 1000)
        self.scale_slider.setInvertedAppearance(True); self.scale_slider.valueChanged.connect(self._on_slider)
        scale_layout.addWidget(plus); scale_layout.addWidget(self.scale_slider, 1); scale_layout.addWidget(minus)
        left = QVBoxLayout(); left.addWidget(self.canvas, 1); left.addWidget(scale)
        root = QWidget(); root_layout = QHBoxLayout(root)
        root_layout.addLayout(left, 1); root_layout.addWidget(panel)
        self.setCentralWidget(root); self.resize(1100, 800); self._sync_slider()

    def _on_user_edited(self, *_args):
        self._user_edited = True

    def mode_changed(self):
        polygon = self.mode.currentIndex() == 1
        self.algorithm.setEnabled(not polygon)
        self.input_label.setText("Вершины: x y" if polygon else "Отрезки: x1 y1 x2 y2")
        if not self._user_edited:
            self.load_example()

    def load_example(self):
        self.data.blockSignals(True)
        for edit, value in zip((self.xmin, self.ymin, self.xmax, self.ymax), ("-10", "-7", "10", "7")):
            edit.setText(value)
        self.data.setPlainText(POLYGON_EXAMPLE if self.mode.currentIndex() else SEGMENT_EXAMPLE)
        self.data.blockSignals(False); self._user_edited = False

    def load_file(self):
        if self.mode.currentIndex() == 1:
            QMessageBox.information(self, "Формат файла", "Формат из условия предназначен для списка отрезков.")
            return
        path, _ = QFileDialog.getOpenFileName(self, "Открыть входной файл", "",
                                              "Текстовые файлы (*.txt);;Все файлы (*)")
        if not path: return
        try:
            segments, rect = parse_segments_file(path)
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Ошибка файла", str(error)); return
        self.data.blockSignals(True)
        self.data.setPlainText("\n".join(f"{a[0]:g} {a[1]:g} {b[0]:g} {b[1]:g}" for a, b in segments))
        self.data.blockSignals(False)
        for edit, value in zip((self.xmin, self.ymin, self.xmax, self.ymax), rect): edit.setText(f"{value:g}")
        self._user_edited = True; self.clip()

    def rectangle(self):
        try: rect = tuple(float(edit.text().strip()) for edit in (self.xmin, self.ymin, self.xmax, self.ymax))
        except ValueError as error: raise ValueError("Координаты окна должны быть числами") from error
        if rect[0] >= rect[2] or rect[1] >= rect[3]: raise ValueError("Требуется xmin < xmax и ymin < ymax")
        return rect

    def rows(self, count):
        result = []
        for number, line in enumerate(self.data.toPlainText().splitlines(), 1):
            if not (line := line.strip()): continue
            parts = line.split()
            if len(parts) != count: raise ValueError(f"Строка {number}: ожидается {count} числа")
            try: result.append(tuple(map(float, parts)))
            except ValueError as error: raise ValueError(f"Строка {number}: обнаружено нечисловое значение") from error
        return result

    @staticmethod
    def check_limits(values):
        if any(abs(value) > MAX_COORDINATE for value in values):
            raise ValueError(f"Координаты должны находиться в диапазоне ±{MAX_COORDINATE}")

    def clip(self):
        try:
            rect = self.rectangle(); self.check_limits(rect); started = time.perf_counter_ns()
            if self.mode.currentIndex() == 0:
                rows = self.rows(4)
                if not rows: raise ValueError("Введите хотя бы один отрезок")
                self.check_limits(value for row in rows for value in row)
                segments = [((r[0], r[1]), (r[2], r[3])) for r in rows]
                function = LINE_FUNCTIONS[self.algorithm.currentText()]
                clipped = [value for segment in segments if (value := function(segment, rect)) is not None]
                elapsed = (time.perf_counter_ns() - started) / 1000
                self.canvas.set_scene(rect, segments=segments, clipped_segments=clipped)
                self.info.setText(f"Исходных отрезков: {len(segments)}\nВидимых частей: {len(clipped)}\nВремя: {elapsed:.1f} мкс")
            else:
                rows = self.rows(2); self.check_limits(value for row in rows for value in row)
                polygon = [(r[0], r[1]) for r in rows]; clipped = sutherland_hodgman(polygon, rect)
                elapsed = (time.perf_counter_ns() - started) / 1000
                self.canvas.set_scene(rect, polygon=polygon, clipped_polygon=clipped)
                self.info.setText(f"Исходных вершин: {len(polygon)}\nВидимых вершин: {len(clipped)}\nВремя: {elapsed:.1f} мкс")
            self._sync_slider()
        except ValueError as error: QMessageBox.warning(self, "Ошибка входных данных", str(error))

    def _cell_to_slider(self, cell):
        low, high = math.log(self.canvas.MIN_CELL), math.log(self.canvas.MAX_CELL)
        return round(1000 * (high - math.log(cell)) / (high - low))

    def _slider_to_cell(self, value):
        low, high = math.log(self.canvas.MIN_CELL), math.log(self.canvas.MAX_CELL)
        return math.exp(high - value / 1000 * (high - low))

    def _sync_slider(self):
        self._syncing_slider = True; self.scale_slider.setValue(self._cell_to_slider(self.canvas.cell)); self._syncing_slider = False

    def _on_slider(self, value):
        if not self._syncing_slider: self.canvas.set_cell(self._slider_to_cell(value))

    def _zoom_by(self, factor):
        self.canvas.zoom(factor); self._sync_slider()


def main():
    app = QApplication(sys.argv); window = MainWindow(); window.show(); sys.exit(app.exec_())


if __name__ == "__main__": main()
