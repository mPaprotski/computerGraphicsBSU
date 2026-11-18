from __future__ import annotations

from typing import Optional

Point = tuple[float, float]
Segment = tuple[Point, Point]
Rect = tuple[float, float, float, float]

LEFT, RIGHT, BOTTOM, TOP = 1, 2, 4, 8


def _normalized(rect: Rect) -> Rect:
    xmin, ymin, xmax, ymax = rect
    if xmin >= xmax or ymin >= ymax:
        raise ValueError("Окно должно удовлетворять xmin < xmax и ymin < ymax")
    return xmin, ymin, xmax, ymax


def region_code(point: Point, rect: Rect) -> int:
    x, y = point
    xmin, ymin, xmax, ymax = rect
    code = 0
    if x < xmin:
        code |= LEFT
    elif x > xmax:
        code |= RIGHT
    if y < ymin:
        code |= BOTTOM
    elif y > ymax:
        code |= TOP
    return code


def cohen_sutherland(segment: Segment, rect: Rect) -> Optional[Segment]:
    """Отсечение отрезка прямоугольником по кодам областей."""
    xmin, ymin, xmax, ymax = _normalized(rect)
    x1, y1 = segment[0]
    x2, y2 = segment[1]
    code1, code2 = region_code((x1, y1), rect), region_code((x2, y2), rect)

    while True:
        if not (code1 | code2):
            return (x1, y1), (x2, y2)
        if code1 & code2:
            return None
        outside = code1 or code2
        if outside & TOP:
            x = x1 + (x2 - x1) * (ymax - y1) / (y2 - y1)
            y = ymax
        elif outside & BOTTOM:
            x = x1 + (x2 - x1) * (ymin - y1) / (y2 - y1)
            y = ymin
        elif outside & RIGHT:
            y = y1 + (y2 - y1) * (xmax - x1) / (x2 - x1)
            x = xmax
        else:
            y = y1 + (y2 - y1) * (xmin - x1) / (x2 - x1)
            x = xmin
        if outside == code1:
            x1, y1 = x, y
            code1 = region_code((x1, y1), rect)
        else:
            x2, y2 = x, y
            code2 = region_code((x2, y2), rect)


def liang_barsky(segment: Segment, rect: Rect) -> Optional[Segment]:
    """Параметрическое отсечение отрезка прямоугольником."""
    xmin, ymin, xmax, ymax = _normalized(rect)
    x1, y1 = segment[0]
    x2, y2 = segment[1]
    dx, dy = x2 - x1, y2 - y1
    p = (-dx, dx, -dy, dy)
    q = (x1 - xmin, xmax - x1, y1 - ymin, ymax - y1)
    enter, leave = 0.0, 1.0
    for pi, qi in zip(p, q):
        if pi == 0:
            if qi < 0:
                return None
            continue
        ratio = qi / pi
        if pi < 0:
            enter = max(enter, ratio)
        else:
            leave = min(leave, ratio)
        if enter > leave:
            return None
    return ((x1 + enter * dx, y1 + enter * dy),
            (x1 + leave * dx, y1 + leave * dy))


def midpoint_clip(segment: Segment, rect: Rect, depth: int = 32) -> Optional[Segment]:
    """Отсечение последовательным делением отрезка пополам."""
    _normalized(rect)
    p1, p2 = segment
    visible: list[tuple[float, float]] = []

    def search(a: Point, b: Point, ta: float, tb: float, remaining: int) -> None:
        code_a, code_b = region_code(a, rect), region_code(b, rect)
        if not (code_a | code_b):
            visible.append((ta, tb))
            return
        if code_a & code_b:
            return
        if remaining == 0:
            mid_t = (ta + tb) / 2
            mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            if region_code(mid, rect) == 0:
                visible.append((ta, tb))
            return
        mid_t = (ta + tb) / 2
        mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        search(a, mid, ta, mid_t, remaining - 1)
        search(mid, b, mid_t, tb, remaining - 1)

    search(p1, p2, 0.0, 1.0, depth)
    if not visible:
        return None
    start, end = min(a for a, _ in visible), max(b for _, b in visible)
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    return ((p1[0] + start * dx, p1[1] + start * dy),
            (p1[0] + end * dx, p1[1] + end * dy))
