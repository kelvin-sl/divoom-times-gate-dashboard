"""python3 -m unittest discover tests"""
import json, os, shutil, sys, tempfile, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import dash

EX = os.path.join(dash.ROOT, "examples")
CLAUDE = {"date": "2026-11-19", "at": 0, "sessions": 3, "output_tokens": 12345}


class Numbers(unittest.TestCase):
    def test_human(self):
        self.assertEqual([dash.human(n) for n in (None, 0, 999, 9999, 12345, 2_000_000, 1_250_000)],
                         ["–", "0", "999", "9,999", "12.3K", "2M", "1.2M"])

    def test_week_change_never_compares_a_day_with_itself(self):
        snap = {"days": {"2026-11-19": {"a": {"followers": 10}}}}
        self.assertIsNone(dash.week_change(snap, "a", 10))
        snap["days"]["2026-11-14"] = {"a": {"followers": 4}}
        snap["days"]["2026-11-16"] = {"a": {"followers": 8}}
        self.assertEqual(dash.week_change(snap, "a", 10), ("+6", True))  # oldest day in the window
        self.assertEqual(dash.week_change(snap, "a", 3), ("−1", False))

    def test_dig(self):
        self.assertEqual(dash.dig({"a": [{"b": 2}]}, "a.0.b"), 2)
        self.assertIsNone(dash.dig({"a": 1}, "a.b"))


class Pool(unittest.TestCase):
    def test_draw_never_repeats_the_previous_pair(self):
        ids = ["a", "b", "c", "d"]
        for _ in range(500):
            pick = dash.draw(ids, ["a", "b"])
            self.assertEqual(len(set(pick)), 2)
            self.assertNotEqual(sorted(pick), ["a", "b"])

    def test_draw_with_pinned_first_and_tiny_pools(self):
        self.assertEqual(dash.draw(["a", "b", "c"], ["a", "b"], first="a"), ["a", "c"])
        self.assertEqual(sorted(dash.draw(["a", "b"], ["a", "b"])), ["a", "b"])
        self.assertEqual(dash.draw(["a"]), ["a", "a"])

    def test_redraw_only_when_due(self):
        cfg = json.load(open(os.path.join(EX, "scenes.json")))
        with tempfile.TemporaryDirectory() as d:
            state = os.path.join(d, "state.json")
            first, specs = dash.current_tiles(cfg, state, now=1000)
            self.assertEqual(len(specs), 5)
            self.assertEqual(dash.current_tiles(cfg, state, now=1000 + 60)[0], first)  # not due yet
            self.assertNotEqual(dash.current_tiles(cfg, state, now=1000 + 301)[0], first)  # due: new pair


class Render(unittest.TestCase):
    def test_demo_renders_five_tiles(self):
        name, imgs = dash.render(EX, EX, claude=CLAUDE, write_state=False)
        self.assertEqual([i.size for i in imgs], [(128, 128)] * 5)

    def test_every_pool_tile_renders(self):
        cfg = json.load(open(os.path.join(EX, "scenes.json")))
        for t in cfg["pool"]:
            _, imgs = dash.render(EX, EX, forced=f"{t['id']},{t['id']}", claude=CLAUDE, write_state=False)
            self.assertEqual(len(imgs), 5)

    def test_no_data_shows_placeholders_instead_of_failing(self):
        with tempfile.TemporaryDirectory() as d:
            for f in ("scenes.json", "accounts.json"):
                shutil.copy(os.path.join(EX, f), d)
            with open(os.path.join(d, "latest.json"), "w") as f:
                f.write("not json")  # a half-written pull
            _, imgs = dash.render(d, d, claude=CLAUDE)
            self.assertEqual(len(imgs), 5)
            # placeholder dots use ink4; a tile with data would not have them at (16, 46)
            ink4 = tuple(int(dash.THEMES["night"]["ink4"][i:i + 2], 16) for i in (1, 3, 5))
            self.assertEqual(imgs[0].getpixel((16, 46)), ink4)


if __name__ == "__main__":
    unittest.main()
