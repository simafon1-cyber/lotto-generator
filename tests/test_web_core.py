"""Сверка ядра веб-версии (web/lotto.js) с ядром Mac (lotto_core.py).

Одни и те же данные считаются обоими; любое расхождение — провал.
Нужен node; без него тест пропускается (и это видно в выводе).
"""

import json
import random
import shutil
import subprocess
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

import lotto_core as core  # noqa: E402
import lotto_data as data  # noqa: E402
from test_lotto import HEADER_MAX  # noqa: E402

JS = HERE.parent / "web" / "lotto.js"


def make_max_text(n=900, seed=5):
    """Lotto Max с захватом всех трёх эпох: 1–49, 1–50, 1–52 и MaxMillions."""
    rng = random.Random(seed)
    lines = [HEADER_MAX]
    d = date(2018, 1, 2)
    for i in range(n):
        top = core.LOTTO_MAX.max_ball(d)
        nums = rng.sample(range(1, top + 1), 8)
        lines.append(f"Lotto Max,{i},0,{d},{','.join(map(str, nums[:7]))},{nums[7]}")
        mm = rng.sample(range(1, top + 1), 7)
        lines.append(f"Lotto Max,{i},1,{d},{','.join(map(str, mm))},")
        d += timedelta(days=rng.choice((3, 4)))
    return "\n".join(lines)


def run_node(payload: dict) -> dict:
    script = f"""
const L = require({json.dumps(str(JS))});
const P = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const out = {{}};
out.maxBall = P.dates.map(d => L.maxBall('LOTTOMAX', d));
const st = L.computeStats('LOTTOMAX', 7, P.draws);
out.counts = Object.values(st.numbers).map(s => [s.number, s.count, s.since]);
out.top = st.top; out.chi2 = st.chi2; out.p = st.p; out.expected = st.expected;
out.topTickets = L.generate(st, 'top', 6, {{avoid: P.avoid}});
out.popular = P.tickets.map(t => L.popularReasons(t));
out.check = P.checks.map(c => L.checkTicket('LOTTOMAX', 7, c[0], c[1], P.draws, P.extras).text);
out.next = P.dates.map(d => [L.nextDraw('LOTTOMAX', d), L.nextDraw('649', d)]);
out.money = L.moneySummary(P.items, '2026-10-17');
out.parse = P.parse.map(([t, d]) => {{ try {{ return L.parseNumbers(t, 'LOTTOMAX', 7, d); }}
                                       catch (e) {{ return 'ERR'; }} }});
out.odds = [L.comb(52, 7), L.comb(49, 6)];
out.bt = L.backtest('LOTTOMAX', 7, P.draws, ['top'], 150, 1)[0];
process.stdout.write(JSON.stringify(out));
"""
    r = subprocess.run(["node", "-e", script], input=json.dumps(payload),
                       capture_output=True, text=True, timeout=60)
    if r.returncode:
        raise AssertionError(r.stderr)
    return json.loads(r.stdout)


@unittest.skipUnless(shutil.which("node"), "node не установлен — сверка JS пропущена")
class WebCoreMatchesPython(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = make_max_text()
        cls.main, cls.extra = core.parse_all(text, core.LOTTO_MAX)
        rng = random.Random(77)
        cls.dates = [(date(2019, 5, 10) + timedelta(days=k * 37)).isoformat()
                     for k in range(80)] + ["2019-05-13", "2019-05-14", "2026-04-13",
                                            "2026-04-14"]
        st = core.compute_stats(core.LOTTO_MAX, cls.main)
        cls.tickets = [sorted(rng.sample(range(1, 53), 7)) for _ in range(400)] + [
            [1, 5, 9, 12, 17, 23, 28], [4, 5, 6, 33, 40, 45, 50], [3, 10, 17, 24, 35, 44, 52],
            [2, 12, 22, 32, 35, 47, 51], [3, 8, 19, 26, 34, 41, 50]]
        cls.checks = []
        for d in cls.main[-60:]:
            for _ in range(5):
                top = core.LOTTO_MAX.max_ball(d.when)
                t = sorted(rng.sample(range(1, top + 1), 7))
                if rng.random() < 0.3:      # подмешиваем совпадения и бонус
                    t = sorted(set(list(d.numbers[:4]) + ([d.bonus] if d.bonus else [])
                                   + rng.sample(range(1, top + 1), 7)))[:7]
                    t = sorted(set(t)) if len(set(t)) == 7 else sorted(d.numbers)
                cls.checks.append((t, d.when.isoformat()))
        mm = cls.extra[-1]
        cls.checks.append((list(mm.numbers), mm.when.isoformat()))
        cls.checks.append((list(cls.main[-1].numbers), "2030-01-01"))
        cls.avoid = [sorted(s.number for s in st.ranked()[:7])]
        cls.items = [
            {"game": "LOTTOMAX", "numbers": [1], "bought": "2026-10-12", "draw": "x"},
            {"game": "LOTTOMAX", "numbers": [2], "bought": "2026-10-11", "draw": "x", "won": 20},
            {"game": "649", "numbers": [3], "bought": "2026-09-30", "draw": "x"},
            {"game": "649", "numbers": [4], "bought": "2026-10-17", "draw": "x", "cost": 6}]
        cls.parse = [("1 2 3 4 5 6 52", "2026-10-20"), ("1 2 3 4 5 6 52", "2026-04-10"),
                     ("7 6 5 4 3 2 1", "2020-01-01"), ("1 1 2 3 4 5 6", "2026-10-20"),
                     ("1 2 3", "2026-10-20"), ("1 2 3 4 5 6 50", "2018-01-01")]
        payload = {
            "dates": cls.dates,
            "draws": [[d.when.isoformat(), list(d.numbers), d.bonus] for d in cls.main],
            "extras": [[d.when.isoformat(), list(d.numbers)] for d in cls.extra],
            "avoid": cls.avoid, "tickets": cls.tickets,
            "checks": cls.checks, "items": cls.items, "parse": cls.parse,
        }
        cls.js = run_node(payload)
        cls.st = st

    def test_eras_present(self):
        tops = {core.LOTTO_MAX.max_ball(d.when) for d in self.main}
        self.assertEqual(tops, {49, 50, 52})

    def test_max_ball(self):
        py = [core.LOTTO_MAX.max_ball(date.fromisoformat(d)) for d in self.dates]
        self.assertEqual(self.js["maxBall"], py)

    def test_stats(self):
        py = [[s.number, s.count, s.draws_since] for s in self.st.numbers.values()]
        self.assertEqual(self.js["counts"], py)
        self.assertEqual(self.js["top"], self.st.max_ball)
        self.assertAlmostEqual(self.js["chi2"], self.st.chi2, places=6)
        self.assertAlmostEqual(self.js["expected"], self.st.expected, places=9)
        self.assertAlmostEqual(self.js["p"], self.st.p_value, places=5)

    def test_top_generation_with_avoid(self):
        py = core.generate(self.st, "top", 6, avoid={tuple(t) for t in self.avoid})
        self.assertEqual(self.js["topTickets"], py)

    def test_popular(self):
        self.assertEqual(self.js["popular"],
                         [core.popular_reasons(t, core.LOTTO_MAX) for t in self.tickets])

    def test_check_ticket(self):
        py = [core.check_ticket(core.LOTTO_MAX, t, date.fromisoformat(d), self.main,
                                self.extra).text(core.LOTTO_MAX) for t, d in self.checks]
        self.assertEqual(self.js["check"], py)
        self.assertTrue(any("MaxMillions" in x for x in py))
        self.assertTrue(any("ждёт" in x for x in py))
        self.assertTrue(any("бонус" in x for x in py))

    def test_next_draw(self):
        py = [[core.next_draw(core.LOTTO_MAX, date.fromisoformat(d)).isoformat(),
               core.next_draw(core.LOTTO_649, date.fromisoformat(d)).isoformat()]
              for d in self.dates]
        self.assertEqual(self.js["next"], py)

    def test_money(self):
        py = data.money_summary(self.items, date(2026, 10, 17))
        for k in ("week", "month", "total", "won"):
            self.assertAlmostEqual(self.js["money"][k], py[k], places=9, msg=k)

    def test_parse_numbers(self):
        py = []
        for t, d in self.parse:
            try:
                py.append(core.parse_numbers(t, core.LOTTO_MAX, date.fromisoformat(d)))
            except ValueError:
                py.append("ERR")
        self.assertEqual(self.js["parse"], py)

    def test_backtest_matches(self):
        # «Строго частые» по одному билету — без случайности, значит совпасть
        # должно всё: среднее, ожидание и разброс.
        r = core.backtest(core.LOTTO_MAX, self.main, ["top"], last=150, per_draw=1)[0]
        js = self.js["bt"]
        self.assertEqual(js["tickets"], r.tickets)
        self.assertAlmostEqual(js["avg"], r.avg_matches, places=9)
        self.assertAlmostEqual(js["expected"], r.expected_avg, places=9)
        self.assertAlmostEqual(js["se"], r.se, places=9)
        self.assertEqual((js["hits3"], js["hits4"]), (r.hits3, r.hits4))

    def test_odds(self):
        self.assertEqual(self.js["odds"], [core.LOTTO_MAX.odds(), core.LOTTO_649.odds()])


if __name__ == "__main__":
    unittest.main(verbosity=2)
