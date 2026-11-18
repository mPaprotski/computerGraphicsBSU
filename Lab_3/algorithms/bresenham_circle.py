def bresenham_circle(cx, cy, radius):
    if radius < 0:
        raise ValueError("Радиус не может быть отрицательным")
    if radius == 0:
        return [(cx, cy)]
    points = set()

    def plot(x, y):
        points.update({
            (cx + x, cy + y), (cx - x, cy + y),
            (cx + x, cy - y), (cx - x, cy - y),
            (cx + y, cy + x), (cx - y, cy + x),
            (cx + y, cy - x), (cx - y, cy - x),
        })

    x, y = 0, radius
    decision = 3 - 2 * radius
    while x <= y:
        plot(x, y)
        if decision > 0:
            y -= 1
            decision += 4 * (x - y) + 10
        else:
            decision += 4 * x + 6
        x += 1
    return list(points)
