import unittest

from flamegraph_studio import parse_folded


class FoldedStackTests(unittest.TestCase):
    def test_merges_duplicates_and_ranks_leaves(self) -> None:
        result = parse_folded(
            ["main;parse;tokenize 17\n", "main;parse;tokenize 3\n", "main;render 10\n"]
        )
        self.assertEqual(len(result.stacks), 2)
        self.assertEqual(result.total_weight, 30)
        hottest = result.hottest_leaves()
        self.assertEqual((hottest[0].frame, hottest[0].weight), ("tokenize", 20))
        self.assertAlmostEqual(hottest[0].share, 2 / 3)

    def test_rejects_empty_or_invalid_input(self) -> None:
        for lines in ([], ["main;work 0"], ["not-folded"]):
            with self.subTest(lines=lines), self.assertRaises(ValueError):
                parse_folded(lines)

    def test_validates_limit(self) -> None:
        with self.assertRaises(ValueError):
            parse_folded(["main 1"]).hottest_leaves(0)

    def test_ranks_inclusive_frames_without_double_counting_recursion(self) -> None:
        result = parse_folded(["main;parse;parse 20", "main;render 10"])
        frames = result.hottest_frames()
        self.assertEqual((frames[0].frame, frames[0].weight, frames[0].share), ("main", 30, 1.0))
        self.assertEqual((frames[1].frame, frames[1].weight), ("parse", 20))

    def test_validates_inclusive_limit(self) -> None:
        with self.assertRaises(ValueError):
            parse_folded(["main 1"]).hottest_frames(0)


if __name__ == "__main__":
    unittest.main()
