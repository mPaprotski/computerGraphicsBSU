import statistics
import time

from algorithms import cohen_sutherland, liang_barsky, midpoint_clip, sutherland_hodgman


def bench(function, args, iterations=5000, repeats=5):
    samples = []
    for _ in range(repeats):
        started = time.perf_counter_ns()
        for _ in range(iterations):
            function(*args)
        samples.append((time.perf_counter_ns() - started) / iterations / 1000)
    return statistics.median(samples)


def main():
    rect = (-100.0, -70.0, 100.0, 70.0)
    segment = ((-180.0, -100.0), (180.0, 120.0))
    print("Отсечение одного отрезка, мкс:")
    for name, function in (("Сазерленд-Коэн", cohen_sutherland),
                           ("Лианг-Барски", liang_barsky),
                           ("Средняя точка", midpoint_clip)):
        print(f"{name:20} {bench(function, (segment, rect)):8.3f}")
    polygon = [(-160.0, -40.0), (-60.0, -120.0), (80.0, -100.0),
               (170.0, 0.0), (70.0, 130.0), (-90.0, 110.0)]
    print("Сазерленд-Ходжман:   ", f"{bench(sutherland_hodgman, (polygon, rect)):8.3f}")


if __name__ == "__main__":
    main()
