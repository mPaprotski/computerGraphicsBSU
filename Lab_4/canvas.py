import math

from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import QWidget


class ClippingCanvas(QWidget):
    MIN_CELL, MAX_CELL = 2.0, 500.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(700, 700)
        self.setStyleSheet("background: white;")
        self.cell = 30.0
        self.rect = (-10.0, -7.0, 10.0, 7.0)
        self.original_segments, self.clipped_segments = [], []
        self.original_polygon, self.clipped_polygon = [], []

    def set_scene(self, rect, segments=None, clipped_segments=None,
                  polygon=None, clipped_polygon=None):
        self.rect = tuple(rect)
        self.original_segments = list(segments or [])
        self.clipped_segments = list(clipped_segments or [])
        self.original_polygon = list(polygon or [])
        self.clipped_polygon = list(clipped_polygon or [])
        self.fit()

    def set_cell(self, value):
        self.cell = max(self.MIN_CELL, min(self.MAX_CELL, float(value)))
        self.update()

    def zoom(self, factor):
        self.set_cell(self.cell * factor)

    def fit(self, margin_ratio=.15, scale=.6):
        points = [(self.rect[0], self.rect[1]), (self.rect[2], self.rect[3])]
        for segment in self.original_segments:
            points.extend(segment)
        points.extend(self.original_polygon)
        max_x = max(abs(x + .5) for x, _ in points)
        max_y = max(abs(y + .5) for _, y in points)
        by_x = self.width() * (1 - 2 * margin_ratio) / max(1, 2 * max_x)
        by_y = self.height() * (1 - 2 * margin_ratio) / max(1, 2 * max_y)
        self.set_cell(min(by_x, by_y) * scale)

    def _origin(self):
        return QPointF(self.width() / 2, self.height() / 2)

    def _screen(self, point):
        origin = self._origin()
        return QPointF(origin.x() + (point[0] + .5) * self.cell,
                       origin.y() - (point[1] + .5) * self.cell)

    @staticmethod
    def _nice_step(cell):
        target = 55 / max(cell, .001)
        power = 10 ** math.floor(math.log10(target))
        return next(m * power for m in (1, 2, 5, 10) if m * power >= target)

    def _draw_grid(self, painter):
        width, height, origin = self.width(), self.height(), self._origin()
        step = self._nice_step(self.cell)
        pixels = step * self.cell
        painter.setPen(QPen(QColor(232, 232, 232), 1))
        for direction in (1, -1):
            x = origin.x() if direction == 1 else origin.x() - pixels
            while 0 <= x <= width:
                painter.drawLine(int(x), 0, int(x), height)
                x += direction * pixels
            y = origin.y() if direction == 1 else origin.y() - pixels
            while 0 <= y <= height:
                painter.drawLine(0, int(y), width, int(y))
                y += direction * pixels
        painter.setPen(QPen(QColor(65, 65, 65), 2))
        painter.drawLine(int(origin.x()), 0, int(origin.x()), height)
        painter.drawLine(0, int(origin.y()), width, int(origin.y()))
        painter.setPen(QColor(80, 80, 80))
        font = painter.font(); font.setPointSize(8); painter.setFont(font)
        for direction in (1, -1):
            index = 1
            while 0 <= origin.x() + direction * index * pixels <= width:
                x = origin.x() + direction * index * pixels
                painter.drawText(int(x + 3), int(origin.y() + 14), f"{direction * index * step:g}")
                index += 1
            index = 1
            while 0 <= origin.y() - direction * index * pixels <= height:
                y = origin.y() - direction * index * pixels
                painter.drawText(int(origin.x() + 5), int(y - 3), f"{direction * index * step:g}")
                index += 1

    def _polyline(self, painter, points, pen, closed=False, brush=None):
        if len(points) < 2:
            return
        polygon = QPolygonF([self._screen(point) for point in points])
        painter.setPen(pen)
        painter.setBrush(brush if brush is not None else Qt.NoBrush)
        painter.drawPolygon(polygon) if closed else painter.drawPolyline(polygon)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.fillRect(QRectF(0, 0, self.width(), self.height()), Qt.white)
        self._draw_grid(painter)
        xmin, ymin, xmax, ymax = self.rect
        painter.setPen(QPen(QColor(35, 105, 180), 3))
        painter.setBrush(QBrush(QColor(35, 105, 180, 24)))
        painter.drawRect(QRectF(self._screen((xmin - .5, ymax - .5)),
                                self._screen((xmax - .5, ymin - .5))).normalized())
        source_pen = QPen(QColor(105, 110, 118), 2, Qt.DashLine)
        for start, end in self.original_segments:
            painter.setPen(source_pen); painter.drawLine(self._screen(start), self._screen(end))
        self._polyline(painter, self.original_polygon, source_pen, True,
                       QBrush(QColor(105, 110, 118, 20)))
        result_pen = QPen(QColor(220, 55, 45), 4)
        for start, end in self.clipped_segments:
            painter.setPen(result_pen); painter.drawLine(self._screen(start), self._screen(end))
        self._polyline(painter, self.clipped_polygon, result_pen, True,
                       QBrush(QColor(220, 55, 45, 55)))
