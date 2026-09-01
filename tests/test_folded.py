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


if __name__ == "__main__":
    unittest.main()
