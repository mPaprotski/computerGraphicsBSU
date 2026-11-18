from __future__ import annotations

Point = tuple[float, float]
Rect = tuple[float, float, float, float]


def _intersection(start: Point, end: Point, axis: int, value: float) -> Point:
    delta = end[axis] - start[axis]
    if delta == 0:
        return start
    t = (value - start[axis]) / delta
    return (start[0] + t * (end[0] - start[0]),
            start[1] + t * (end[1] - start[1]))


def sutherland_hodgman(polygon: list[Point], rect: Rect) -> list[Point]:
    """Отсечение выпуклого многоугольника прямоугольным окном."""
    xmin, ymin, xmax, ymax = rect
    if xmin >= xmax or ymin >= ymax:
        raise ValueError("Окно должно удовлетворять xmin < xmax и ymin < ymax")
    if len(polygon) < 3:
        raise ValueError("Многоугольник должен содержать минимум три вершины")

    result = list(polygon)
    boundaries = (
        (lambda p: p[0] >= xmin, 0, xmin),
        (lambda p: p[0] <= xmax, 0, xmax),
        (lambda p: p[1] >= ymin, 1, ymin),
        (lambda p: p[1] <= ymax, 1, ymax),
    )
    for inside, axis, value in boundaries:
        source, result = result, []
        if not source:
            break
        start = source[-1]
        for end in source:
            start_inside, end_inside = inside(start), inside(end)
            if end_inside:
                if not start_inside:
                    result.append(_intersection(start, end, axis, value))
                result.append(end)
            elif start_inside:
                result.append(_intersection(start, end, axis, value))
            start = end
    return result
