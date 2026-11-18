import math

from PyQt5.QtCore import QPoint, Qt
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen
from PyQt5.QtWidgets import QWidget


class RasterCanvas(QWidget):
    MIN_CELL, MAX_CELL = 2, 500

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cell, self.points, self.show_centers = 30, [], False
        self.setMinimumSize(700, 700)
        self.setAutoFillBackground(True)
        self.setStyleSheet("background: white;")

    def set_points(self, points):
        self.points = list(points)
        self.update()

    def set_cell(self, value):
        self.cell = max(self.MIN_CELL, min(self.MAX_CELL, int(value)))
        self.update()

    def zoom(self, factor):
        self.set_cell(self.cell * factor)

    def fit(self, margin_ratio=0.15, scale=0.6):
        if not self.points:
            return
        xs, ys = zip(*self.points)
        dx, dy = max(1, max(xs) - min(xs)), max(1, max(ys) - min(ys))
        width = self.width() * (1 - 2 * margin_ratio)
        height = self.height() * (1 - 2 * margin_ratio)
        self.set_cell(min(width / dx, height / dy) * scale)

    def _origin(self):
        return self.width() // 2, self.height() // 2

    def coordinate_bounds(self):
        """Диапазон, видимый при максимальном отдалении сетки."""
        cx, cy = self._origin()
        margin = 2
        return (
            -cx // self.MIN_CELL + margin,
            (self.width() - cx) // self.MIN_CELL - margin,
            -(self.height() - cy) // self.MIN_CELL + margin,
            cy // self.MIN_CELL - margin,
        )

    def _screen(self, x, y):
        cx, cy = self._origin()
        return QPoint(int(cx + (x + 0.5) * self.cell), int(cy - (y + 0.5) * self.cell))

    @staticmethod
    def _nice_step(cell):
        target = 55 / max(cell, 0.001)
        power = 10 ** math.floor(math.log10(target))
        return next(multiplier * power for multiplier in (1, 2, 5, 10)
                    if multiplier * power >= target)

    def _draw_grid(self, painter):
        width, height = self.width(), self.height()
        cx, cy = self._origin()
        step = self._nice_step(self.cell)
        pixels = step * self.cell

        painter.setPen(QPen(QColor(232, 232, 232), 1))
        for direction in (1, -1):
            x = cx if direction == 1 else cx - pixels
            while 0 <= x <= width:
                painter.drawLine(int(x), 0, int(x), height)
                x += direction * pixels
            y = cy if direction == 1 else cy - pixels
            while 0 <= y <= height:
                painter.drawLine(0, int(y), width, int(y))
                y += direction * pixels

        painter.setPen(QPen(QColor(65, 65, 65), 2))
        painter.drawLine(cx, 0, cx, height)
        painter.drawLine(0, cy, width, cy)

        painter.setPen(QColor(80, 80, 80))
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)
        for direction in (1, -1):
            index = 1
            while 0 <= cx + direction * index * pixels <= width:
                x = cx + direction * index * pixels
                painter.drawText(int(x + 3), int(cy + 14),
                                 f"{direction * index * step:g}")
                index += 1
            index = 1
            while 0 <= cy - direction * index * pixels <= height:
                y = cy - direction * index * pixels
                painter.drawText(int(cx + 5), int(y - 3),
                                 f"{direction * index * step:g}")
                index += 1

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        cell = self.cell
        self._draw_grid(painter)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(220, 50, 50)))
        for x, y in self.points:
            point = self._screen(x, y)
            painter.drawRect(int(point.x() - cell / 2), int(point.y() - cell / 2), cell, cell)
        if self.show_centers:
            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(Qt.black)
            for x, y in self.points:
                painter.drawEllipse(self._screen(x, y), 2, 2)
