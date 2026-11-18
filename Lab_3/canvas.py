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

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        width, height = self.width(), self.height()
        cx, cy = self._origin()
        cell = self.cell
        # Сетка должна помогать читать координаты, но не конкурировать с
        # осями и растровыми пикселями.
        painter.setPen(QPen(QColor(244, 246, 248), 1))
        for x in range(cx % cell, width + cell, cell):
            painter.drawLine(x, 0, x, height)
        for y in range(cy % cell, height + cell, cell):
            painter.drawLine(0, y, width, y)
        painter.setPen(QPen(QColor(60, 60, 60), 2))
        painter.drawLine(0, cy, width, cy)
        painter.drawLine(cx, 0, cx, height)
        painter.drawText(width - 18, cy - 8, "X")
        painter.drawText(cx + 8, 16, "Y")

        needed = 1
        while needed * cell < 60:
            needed += 1
        label_step = next((n for n in (1, 2, 5, 10, 20, 50, 100, 200, 500) if needed <= n), needed)
        painter.setPen(QColor(80, 80, 80))
        label_font = painter.font()
        label_font.setPointSize(8)
        painter.setFont(label_font)
        metrics = painter.fontMetrics()
        for value in range(-(cx // cell), (width - cx) // cell + 2):
            if value and value % label_step == 0:
                x = cx + value * cell
                painter.drawLine(x, cy - 4, x, cy + 4)
                text = str(value)
                painter.drawText(x - metrics.horizontalAdvance(text) // 2, cy + 6 + metrics.height(), text)
        for value in range(-((height - cy) // cell), cy // cell + 2):
            if value and value % label_step == 0:
                y = cy - value * cell
                painter.drawLine(cx - 4, y, cx + 4, y)
                painter.drawText(cx + 6, y + metrics.ascent() // 2, str(value))
        painter.drawText(cx + 6, cy + 6 + metrics.ascent(), "0")

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
