def bresenham_line(x1, y1, x2, y2):
    points = []
    dx, dy = abs(x2 - x1), abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    error = dx - dy
    x, y = x1, y1
    while True:
        points.append((x, y))
        if x == x2 and y == y2:
            return points
        e2 = 2 * error
        if e2 > -dy:
            error -= dy
            x += sx
        if e2 < dx:
            error += dx
            y += sy
