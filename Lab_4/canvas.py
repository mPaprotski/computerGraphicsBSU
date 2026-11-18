from PyQt5.QtCore import QPointF, QRectF, Qt
from PyQt5.QtGui import QBrush, QColor, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import QWidget


class ClippingCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(680, 600)
        self.setStyleSheet("background: white;")
        self.rect = (-10.0, -7.0, 10.0, 7.0)
        self.original_segments = []
        self.clipped_segments = []
        self.original_polygon = []
        self.clipped_polygon = []
        self.scale = 25.0
        self.center = (0.0, 0.0)

    def set_scene(self, rect, segments=None, clipped_segments=None,
                  polygon=None, clipped_polygon=None):
        self.rect = tuple(rect)
        self.original_segments = list(segments or [])
        self.clipped_segments = list(clipped_segments or [])
        self.original_polygon = list(polygon or [])
        self.clipped_polygon = list(clipped_polygon or [])
        self.fit_scene()
        self.update()

    def fit_scene(self):
        points = [(self.rect[0], self.rect[1]), (self.rect[2], self.rect[3])]
        for segment in self.original_segments:
            points.extend(segment)
        points.extend(self.original_polygon)
        if not points:
            return
        xs, ys = zip(*points)
        xmin, xmax, ymin, ymax = min(xs), max(xs), min(ys), max(ys)
        width, height = max(1.0, xmax - xmin), max(1.0, ymax - ymin)
        self.center = ((xmin + xmax) / 2, (ymin + ymax) / 2)
        self.scale = max(2.0, min(self.width() * 0.78 / width, self.height() * 0.78 / height))

    def zoom(self, factor):
        self.scale = max(2.0, min(300.0, self.scale * factor))
        self.update()

    def _screen(self, point):
        x, y = point
        cx, cy = self.width() / 2, self.height() / 2
        return QPointF(cx + (x - self.center[0]) * self.scale,
                       cy - (y - self.center[1]) * self.scale)

    def _draw_polyline(self, painter, points, pen, closed=False, brush=None):
        if len(points) < 2:
            return
        polygon = QPolygonF([self._screen(point) for point in points])
        painter.setPen(pen)
        painter.setBrush(brush if brush is not None else Qt.NoBrush)
        if closed:
            painter.drawPolygon(polygon)
        else:
            painter.drawPolyline(polygon)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        width, height = self.width(), self.height()
        origin = self._screen((0, 0))

        step = 1
        while step * self.scale < 38:
            step *= 2 if step in (1, 5) else 2.5
        step = max(1, int(step))
        painter.setPen(QPen(QColor(244, 246, 248), 1))
        x_min = int(self.center[0] - width / (2 * self.scale)) - 1
        x_max = int(self.center[0] + width / (2 * self.scale)) + 1
        y_min = int(self.center[1] - height / (2 * self.scale)) - 1
        y_max = int(self.center[1] + height / (2 * self.scale)) + 1
        for x in range(x_min - x_min % step, x_max + 1, step):
            sx = self._screen((x, 0)).x()
            painter.drawLine(int(sx), 0, int(sx), height)
        for y in range(y_min - y_min % step, y_max + 1, step):
            sy = self._screen((0, y)).y()
            painter.drawLine(0, int(sy), width, int(sy))

        painter.setPen(QPen(QColor(65, 72, 80), 2))
        if 0 <= origin.x() <= width:
            painter.drawLine(int(origin.x()), 0, int(origin.x()), height)
        if 0 <= origin.y() <= height:
            painter.drawLine(0, int(origin.y()), width, int(origin.y()))
        painter.setPen(QColor(80, 80, 80))
        font = painter.font(); font.setPointSize(8); painter.setFont(font)
        for x in range(x_min - x_min % step, x_max + 1, step):
            if x:
                p = self._screen((x, 0)); painter.drawText(int(p.x() + 3), int(origin.y() + 14), str(x))
        for y in range(y_min - y_min % step, y_max + 1, step):
            if y:
                p = self._screen((0, y)); painter.drawText(int(origin.x() + 5), int(p.y() - 3), str(y))

        xmin, ymin, xmax, ymax = self.rect
        top_left, bottom_right = self._screen((xmin, ymax)), self._screen((xmax, ymin))
        painter.setPen(QPen(QColor(35, 105, 180), 3))
        painter.setBrush(QBrush(QColor(35, 105, 180, 24)))
        painter.drawRect(QRectF(top_left, bottom_right))

        original_pen = QPen(QColor(100, 108, 118), 2, Qt.DashLine)
        for start, end in self.original_segments:
            painter.setPen(original_pen)
            painter.drawLine(self._screen(start), self._screen(end))
        self._draw_polyline(painter, self.original_polygon, original_pen, True,
                            QBrush(QColor(100, 108, 118, 20)))

        visible_pen = QPen(QColor(220, 55, 45), 4)
        for start, end in self.clipped_segments:
            painter.setPen(visible_pen)
            painter.drawLine(self._screen(start), self._screen(end))
        self._draw_polyline(painter, self.clipped_polygon, visible_pen, True,
                            QBrush(QColor(220, 55, 45, 55)))
