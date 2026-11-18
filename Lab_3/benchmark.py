import gc
import statistics
import time
from algorithms import bresenham_circle, bresenham_line, dda, step_by_step


def bench(function, args, target=0.15, repeats=5):
    function(*args)
    samples = []
    for _ in range(repeats):
        count = 1
        while True:
            gc.disable()
            started = time.perf_counter()
            for _ in range(count):
                function(*args)
            elapsed = time.perf_counter() - started
            gc.enable()
            if elapsed >= target:
                samples.append(elapsed / count * 1e6)
                break
            count *= 2
    return statistics.median(samples)


def main():
    print("=== Отрезки, мкс ===")
    for length in (10, 50, 100, 500, 1000, 5000, 10000):
        args = (0, 0, length, length // 2)
        values = [bench(fn, args) for fn in (step_by_step, dda, bresenham_line)]
        print(f"L={length:>5}: step={values[0]:>8.1f}; dda={values[1]:>8.1f}; bres={values[2]:>8.1f}")
    print("\n=== Окружности, мкс ===")
    for radius in (10, 100, 500, 1000, 2000):
        elapsed = bench(bresenham_circle, (0, 0, radius))
        print(f"R={radius:>4}: {elapsed:>8.1f}; точек={len(bresenham_circle(0, 0, radius))}")


if __name__ == "__main__":
    main()
