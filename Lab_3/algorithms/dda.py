import math


def _round_half_away_from_zero(value):
    return math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5)


def dda(x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    steps = max(abs(dx), abs(dy))
    if steps == 0:
        return [(x1, y1)]
    x_inc, y_inc = dx / steps, dy / steps
    x, y = float(x1), float(y1)
    points = []
    for _ in range(steps + 1):
        points.append((_round_half_away_from_zero(x), _round_half_away_from_zero(y)))
        x += x_inc
        y += y_inc
    return points
