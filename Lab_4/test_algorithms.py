import tempfile
import unittest
from pathlib import Path

from algorithms import cohen_sutherland, liang_barsky, midpoint_clip, sutherland_hodgman
from input_parser import parse_segments_file


class ClippingTests(unittest.TestCase):
    RECT = (-10.0, -7.0, 10.0, 7.0)

    def assert_segment_close(self, actual, expected, places=6):
        self.assertIsNotNone(actual)
        for point_actual, point_expected in zip(actual, expected):
            for value_actual, value_expected in zip(point_actual, point_expected):
                self.assertAlmostEqual(value_actual, value_expected, places=places)

    def test_line_algorithms_cross_window(self):
        segment = ((-20.0, 0.0), (20.0, 0.0))
        expected = ((-10.0, 0.0), (10.0, 0.0))
        self.assert_segment_close(cohen_sutherland(segment, self.RECT), expected)
        self.assert_segment_close(liang_barsky(segment, self.RECT), expected)
        self.assert_segment_close(midpoint_clip(segment, self.RECT), expected, places=5)

    def test_accept_and_reject(self):
        inside = ((-2.0, -1.0), (3.0, 4.0))
        outside = ((-20.0, 20.0), (-15.0, 15.0))
        for function in (cohen_sutherland, liang_barsky, midpoint_clip):
            self.assert_segment_close(function(inside, self.RECT), inside)
            self.assertIsNone(function(outside, self.RECT))

    def test_polygon_clipping(self):
        polygon = [(-15.0, -5.0), (0.0, -12.0), (15.0, -5.0), (0.0, 12.0)]
        result = sutherland_hodgman(polygon, self.RECT)
        self.assertGreaterEqual(len(result), 4)
        for x, y in result:
            self.assertLessEqual(abs(x), 10.0 + 1e-9)
            self.assertLessEqual(abs(y), 7.0 + 1e-9)

    def test_input_file(self):
        text = "2\n-20 0 20 0\n0 -10 0 10\n-10 -7 10 7\n"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.txt"
            path.write_text(text, encoding="utf-8")
            segments, rect = parse_segments_file(str(path))
        self.assertEqual(len(segments), 2)
        self.assertEqual(rect, self.RECT)


if __name__ == "__main__":
    unittest.main()
