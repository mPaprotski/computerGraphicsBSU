from pathlib import Path


def parse_segments_file(path: str):
    """Читает формат: n, затем n отрезков, затем xmin ymin xmax ymax."""
    rows = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if line:
            rows.append(line)
    if not rows:
        raise ValueError("Файл пуст")
    try:
        count = int(rows[0])
    except ValueError as error:
        raise ValueError("Первая строка должна содержать число отрезков") from error
    if count < 0 or len(rows) != count + 2:
        raise ValueError(f"Ожидается {count} строк отрезков и одна строка окна")
    segments = []
    for number, row in enumerate(rows[1:count + 1], 1):
        values = row.split()
        if len(values) != 4:
            raise ValueError(f"Строка отрезка {number} должна содержать четыре числа")
        try:
            x1, y1, x2, y2 = map(float, values)
        except ValueError as error:
            raise ValueError(f"Некорректное число в строке отрезка {number}") from error
        segments.append(((x1, y1), (x2, y2)))
    try:
        rect_values = list(map(float, rows[-1].split()))
    except ValueError as error:
        raise ValueError("Некорректные координаты отсекающего окна") from error
    if len(rect_values) != 4:
        raise ValueError("Строка окна должна содержать xmin ymin xmax ymax")
    return segments, tuple(rect_values)
