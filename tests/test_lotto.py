"""Поведенческие тесты генератора: настоящий разбор CSV, счёт частот, билеты."""

import json
import random
import sys
import tempfile
import unittest
from collections import Counter
from datetime import date, datetime, timedelta
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import lotto_core as core  # noqa: E402
import lotto_data as data  # noqa: E402
import lotto_update as upd  # noqa: E402

HEADER_MAX = ("PRODUCT,DRAW NUMBER,SEQUENCE NUMBER,DRAW DATE,NUMBER DRAWN 1,"
              "NUMBER DRAWN 2,NUMBER DRAWN 3,NUMBER DRAWN 4,NUMBER DRAWN 5,"
              "NUMBER DRAWN 6,NUMBER DRAWN 7,BONUS NUMBER")


def fake_max_csv(n_draws=800, seed=1, maxmillions=True):
    """CSV в формате BCLC. Основной тираж (SEQUENCE 0) и допрозыгрыши."""
    rng = random.Random(seed)
    lines = [HEADER_MAX]
    start = date(2009, 9, 25)
    mains = []
    for i in range(n_draws):
        d = start + timedelta(days=4 * i)
        top = core.LOTTO_MAX.max_ball(d)
        nums = rng.sample(range(1, top + 1), 8)
        mains.append((d, sorted(nums[:7])))
        lines.append(f"Lotto Max,{1000 + i},0,{d:%Y-%m-%d},"
                     + ",".join(map(str, nums[:7])) + f",{nums[7]}")
        if maxmillions:
            for seq in (1, 2):
                mm = rng.sample(range(1, top + 1), 7)
                lines.append(f"Lotto Max,{1000 + i},{seq},{d:%Y-%m-%d},"
                             + ",".join(map(str, mm)) + ",")
    return "\n".join(lines) + "\n", mains


class ParseTests(unittest.TestCase):
    def test_bclc_main_draw_only(self):
        text, mains = fake_max_csv(50)
        draws = core.parse_csv(text, core.LOTTO_MAX)
        # 50 тиражей, а не 150: MaxMillions не считаются.
        self.assertEqual(len(draws), 50)
        self.assertEqual([list(d.numbers) for d in draws], [m[1] for m in mains])

    def test_sequence_order_in_file_irrelevant(self):
        text, mains = fake_max_csv(30)
        head, *rows = text.strip().splitlines()
        shuffled = head + "\n" + "\n".join(reversed(rows))
        draws = core.parse_csv(shuffled, core.LOTTO_MAX)
        self.assertEqual([list(d.numbers) for d in draws], [m[1] for m in mains])

    def test_bad_rows_skipped(self):
        text = (HEADER_MAX + "\n"
                "Lotto Max,1,0,2020-01-03,1,2,3,4,5,6,7,8\n"
                "Lotto Max,2,0,2020-01-07,1,1,3,4,5,6,7,8\n"      # повтор числа
                "Lotto Max,3,0,2020-01-10,1,2,3,4,5,6,51,8\n"     # вне диапазона
                "Lotto Max,4,0,2018-01-10,1,2,3,4,5,6,50,8\n"     # 50 до 2019
                "Lotto Max,5,0,,1,2,3,4,5,6,7,8\n")               # нет даты
        draws = core.parse_csv(text, core.LOTTO_MAX)
        self.assertEqual(len(draws), 1)
        self.assertEqual(draws[0].numbers, (1, 2, 3, 4, 5, 6, 7))

    def test_headerless_fallback(self):
        text = "1982-06-12,3,11,12,14,41,43,13\n06/19/1982,8,33,36,37,39,41,9\n"
        draws = core.parse_csv(text, core.LOTTO_649)
        self.assertEqual([d.numbers for d in draws],
                         [(3, 11, 12, 14, 41, 43), (8, 33, 36, 37, 39, 41)])
        self.assertEqual(draws[0].bonus, 13)


class ExtraDrawTests(unittest.TestCase):
    def test_maxmillions_returned_separately(self):
        text, mains = fake_max_csv(40)
        main, extra = core.parse_all(text, core.LOTTO_MAX)
        self.assertEqual([list(d.numbers) for d in main], [m[1] for m in mains])
        self.assertEqual(len(extra), 80)            # по 2 MaxMillions на тираж
        main_set = {(d.when, d.numbers) for d in main}
        self.assertFalse(any((d.when, d.numbers) in main_set for d in extra))

    def test_extra_stats_count_only_extra(self):
        text = (HEADER_MAX + "\n"
                "Lotto Max,1,0,2020-01-03,1,2,3,4,5,6,7,8\n"
                "Lotto Max,1,1,2020-01-03,41,42,43,44,45,46,47,\n"
                "Lotto Max,1,2,2020-01-03,41,42,43,44,45,46,48,\n")
        main, extra = core.parse_all(text, core.LOTTO_MAX)
        st = core.compute_stats(core.LOTTO_MAX, extra)
        self.assertEqual(st.numbers[41].count, 2)
        self.assertEqual(st.numbers[1].count, 0)
        self.assertEqual(len(main), 1)


class ScheduleTests(unittest.TestCase):
    def test_next_draw_days(self):
        # 2026-10-17 — суббота.
        sat = date(2026, 10, 17)
        self.assertEqual(core.next_draw(core.LOTTO_649, sat), sat)
        self.assertEqual(core.next_draw(core.LOTTO_649, sat + timedelta(days=1)),
                         date(2026, 10, 21))            # среда
        self.assertEqual(core.next_draw(core.LOTTO_MAX, sat), date(2026, 10, 20))  # вторник
        self.assertEqual(core.next_draw(core.LOTTO_MAX, date(2026, 10, 21)),
                         date(2026, 10, 23))            # пятница

    def test_new_draws_detected(self):
        text, _ = fake_max_csv(30, maxmillions=False)
        draws = core.parse_csv(text, core.LOTTO_MAX)
        self.assertEqual(core.new_draws(draws[:-2], draws), draws[-2:])
        self.assertEqual(core.new_draws(draws, draws), [])

    def test_needs_update(self):
        now = datetime(2026, 10, 17, 12, 0)
        self.assertTrue(data.needs_update(None, now))
        self.assertFalse(data.needs_update(now - timedelta(hours=2, minutes=59), now))
        self.assertTrue(data.needs_update(now - timedelta(hours=3), now))
        self.assertTrue(data.needs_update(now + timedelta(days=1), now))  # часы перевели

    def test_settings_roundtrip_and_last_update(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(data, "user_dir", return_value=Path(tmp)):
            self.assertIsNone(data.last_update())
            data.save_settings(province="Квебек (Loto-Québec)")
            data.save_settings(last_update="2026-10-17T10:00:00")
            self.assertEqual(data.load_settings()["province"], "Квебек (Loto-Québec)")
            self.assertEqual(data.last_update(), datetime(2026, 10, 17, 10, 0))

    def test_failed_download_does_not_mark_updated(self):
        good, _ = fake_max_csv(800, maxmillions=False)

        def fake_download(game, timeout=60):
            if game.key == "649":
                raise OSError("нет сети")
            return good

        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(data, "user_dir", return_value=Path(tmp)), \
                mock.patch.object(data, "download_csv", fake_download):
            report = data.update_all()
            self.assertTrue(report["Lotto Max"].startswith("обновлено"))
            self.assertIn("нет сети", report["Lotto 6/49"])
            self.assertIsNone(data.last_update())     # повторит через 10 минут
            self.assertTrue((Path(tmp) / "LOTTOMAX.csv").is_file())

    def test_success_marks_updated(self):
        good = {"649": "\n".join(
            ["PRODUCT,DRAW NUMBER,SEQUENCE NUMBER,DRAW DATE,NUMBER DRAWN 1,NUMBER DRAWN 2,"
             "NUMBER DRAWN 3,NUMBER DRAWN 4,NUMBER DRAWN 5,NUMBER DRAWN 6,BONUS NUMBER"]
            + [f"649,{i},0,{date(1982, 6, 12) + timedelta(days=3 * i)},"
               + ",".join(map(str, random.Random(i).sample(range(1, 50), 7)))
               for i in range(3100)]),
            "LOTTOMAX": fake_max_csv(800, maxmillions=False)[0]}
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(data, "user_dir", return_value=Path(tmp)), \
                mock.patch.object(data, "download_csv", lambda g, timeout=60: good[g.key]):
            before = datetime.now().replace(microsecond=0)
            report = data.update_all()
            self.assertTrue(all(v.startswith("обновлено") for v in report.values()), report)
            self.assertGreaterEqual(data.last_update(), before)

    def test_shop_urls_are_official_https(self):
        for name, url in data.PROVINCES.items():
            self.assertTrue(url.startswith("https://"), name)
        self.assertIn(data.DEFAULT_PROVINCE, data.PROVINCES)


class StatsTests(unittest.TestCase):
    def test_counts_match_independent_count(self):
        text, mains = fake_max_csv(400)
        draws = core.parse_csv(text, core.LOTTO_MAX)
        st = core.compute_stats(core.LOTTO_MAX, draws)
        truth = Counter(n for _, nums in mains for n in nums)
        self.assertEqual(st.max_ball, 49)   # 400 тиражей кончаются до 2019 года
        for n in st.numbers:
            self.assertEqual(st.numbers[n].count, truth.get(n, 0), n)
        self.assertEqual(sum(s.count for s in st.numbers.values()), 400 * 7)

    def test_draws_since(self):
        text = (HEADER_MAX + "\n"
                "Lotto Max,1,0,2020-01-03,1,2,3,4,5,6,7,8\n"
                "Lotto Max,2,0,2020-01-07,1,9,10,11,12,13,14,8\n")
        st = core.compute_stats(core.LOTTO_MAX, core.parse_csv(text, core.LOTTO_MAX))
        self.assertEqual(st.numbers[1].draws_since, 0)
        self.assertEqual(st.numbers[2].draws_since, 1)
        self.assertIsNone(st.numbers[50].draws_since)

    def test_mixed_49_and_50_periods(self):
        # 1500 тиражей с 2009 года заходят за май 2019: появляется число 50,
        # и его редкость не должна выглядеть «подозрительной».
        text, _ = fake_max_csv(1500, seed=7, maxmillions=False)
        draws = core.parse_csv(text, core.LOTTO_MAX)
        st = core.compute_stats(core.LOTTO_MAX, draws)
        self.assertEqual(st.max_ball, 50)
        after = sum(d.when >= core.LOTTO_MAX_50_FROM for d in draws)
        self.assertGreater(st.numbers[50].count, 0)
        self.assertLess(abs(st.numbers[50].count - after * 7 / 50), 4 * (after * 7 / 50) ** 0.5)

    def test_fair_lottery_not_flagged(self):
        text, _ = fake_max_csv(1500, seed=7, maxmillions=False)
        st = core.compute_stats(core.LOTTO_MAX, core.parse_csv(text, core.LOTTO_MAX))
        self.assertGreater(st.p_value, 0.001)

    def test_rigged_lottery_flagged(self):
        rng = random.Random(3)
        lines = [HEADER_MAX]
        for i in range(600):
            d = date(2020, 1, 1) + timedelta(days=3 * i)
            nums = [1, 2] + rng.sample(range(3, 51), 5)
            lines.append(f"Lotto Max,{i},0,{d},{','.join(map(str, nums))},")
        st = core.compute_stats(core.LOTTO_MAX, core.parse_csv("\n".join(lines),
                                                               core.LOTTO_MAX))
        self.assertLess(st.p_value, 1e-6)

    def test_chi2_sf_reference(self):
        # Справочные значения хи-квадрат: 49 степеней свободы, 66.34 -> 0.05.
        self.assertAlmostEqual(core.chi2_sf(66.34, 49), 0.05, delta=0.003)
        self.assertAlmostEqual(core.chi2_sf(48.33, 49), 0.50, delta=0.01)


class GenerateTests(unittest.TestCase):
    def setUp(self):
        text, _ = fake_max_csv(600, seed=11, maxmillions=False)
        self.st = core.compute_stats(core.LOTTO_MAX, core.parse_csv(text, core.LOTTO_MAX))

    def test_tickets_valid_for_every_strategy(self):
        rng = random.Random(5)
        for s in core.STRATEGIES:
            tickets = core.generate(self.st, s, 10, rng=rng)
            self.assertEqual(len(tickets), 10, s)
            self.assertEqual(len({tuple(t) for t in tickets}), 10, s)
            for t in tickets:
                self.assertEqual(len(t), 7)
                self.assertEqual(len(set(t)), 7)
                self.assertTrue(all(1 <= n <= 50 for n in t))
                self.assertEqual(t, sorted(t))

    def test_top_is_exactly_most_frequent(self):
        t = core.generate(self.st, "top", 1)[0]
        expected = sorted(s.number for s in self.st.ranked()[:7])
        self.assertEqual(t, expected)

    def test_fixed_and_excluded(self):
        rng = random.Random(2)
        fixed, excl = {7, 42}, set(range(10, 30))
        for t in core.generate(self.st, "hot", 20, fixed, excl, rng=rng):
            self.assertTrue(fixed <= set(t))
            self.assertFalse(set(t) & excl)

    def test_hot_prefers_frequent_cold_prefers_rare(self):
        rng = random.Random(9)
        ranked = [s.number for s in self.st.ranked()]
        hot10, cold10 = set(ranked[:10]), set(ranked[-10:])

        def share(strategy, group):
            picks = [n for t in core.generate(self.st, strategy, 300, strength=2,
                                              rng=rng) for n in t]
            return sum(n in group for n in picks) / len(picks)

        uniform = share("random", hot10)
        self.assertGreater(share("hot", hot10), uniform + 0.1)
        self.assertGreater(share("cold", cold10), share("random", cold10) + 0.1)

    def test_too_many_fixed_rejected(self):
        with self.assertRaises(ValueError):
            core.generate(self.st, "hot", 1, fixed=set(range(1, 9)))

    def test_history_matches(self):
        draws = self.st.draws
        m = core.history_matches(draws, list(draws[0].numbers))
        self.assertGreaterEqual(m.get(7, 0), 1)


class SaveTests(unittest.TestCase):
    def test_short_file_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            good, _ = fake_max_csv(800, maxmillions=False)
            self.assertEqual(data.save_checked(core.LOTTO_MAX, good, Path(tmp)), 800)
            bad, _ = fake_max_csv(10, maxmillions=False)
            with self.assertRaises(ValueError):
                data.save_checked(core.LOTTO_MAX, bad, Path(tmp))
            kept = (Path(tmp) / "LOTTOMAX.csv").read_text()
            self.assertEqual(len(core.parse_csv(kept, core.LOTTO_MAX)), 800)


class MyTicketsTests(unittest.TestCase):
    TEXT = (HEADER_MAX + "\n"
            "Lotto Max,1,0,2026-10-20,1,3,10,20,22,28,46,5\n"
            "Lotto Max,1,1,2026-10-20,12,14,18,19,23,36,45,\n")

    def setUp(self):
        self.main, self.extra = core.parse_all(self.TEXT, core.LOTTO_MAX)
        self.day = date(2026, 10, 20)

    def check(self, nums, day=None):
        return core.check_ticket(core.LOTTO_MAX, nums, day or self.day,
                                 self.main, self.extra)

    def test_waiting_before_draw(self):
        r = self.check([1, 2, 3, 4, 6, 7, 8], date(2026, 10, 23))
        self.assertFalse(r.drawn)
        self.assertEqual(r.text(core.LOTTO_MAX), "ждёт тиража")

    def test_only_draw_of_that_day(self):
        # Тираж 20.10 есть, а на 17.10 его нет: билет «на 17.10» не должен
        # сверяться с более поздним тиражом.
        r = self.check([1, 3, 10, 20, 22, 28, 46], date(2026, 10, 17))
        self.assertFalse(r.drawn)

    def test_jackpot(self):
        r = self.check([1, 3, 10, 20, 22, 28, 46])
        self.assertEqual((r.matches, r.prize), (7, "ДЖЕКПОТ"))

    def test_partial_and_bonus(self):
        r = self.check([1, 3, 10, 5, 40, 41, 42])          # 3 + бонус 5
        self.assertEqual((r.matches, r.bonus), (3, True))
        self.assertIn("денежный", r.prize)
        r = self.check([1, 3, 10, 40, 41, 42, 43])         # просто 3
        self.assertEqual(r.prize, "бесплатный билет")
        r = self.check([1, 3, 40, 41, 42, 43, 44])         # 2 — ничего
        self.assertEqual(r.prize, "")
        self.assertIn("без приза", r.text(core.LOTTO_MAX))

    def test_maxmillions_needs_full_match(self):
        r = self.check([12, 14, 18, 19, 23, 36, 45])
        self.assertEqual(r.maxmillions, 1)
        self.assertEqual(r.matches, 0)        # с основным не совпало ничего
        self.assertEqual(self.check([12, 14, 18, 19, 23, 36, 44]).maxmillions, 0)

    def test_649_free_play_at_two(self):
        text = ("PRODUCT,DRAW NUMBER,SEQUENCE NUMBER,DRAW DATE,NUMBER DRAWN 1,NUMBER DRAWN 2,"
                "NUMBER DRAWN 3,NUMBER DRAWN 4,NUMBER DRAWN 5,NUMBER DRAWN 6,BONUS NUMBER\n"
                "649,1,0,2026-10-17,5,25,26,27,29,46,16\n")
        d = core.parse_csv(text, core.LOTTO_649)
        day = date(2026, 10, 17)
        r = core.check_ticket(core.LOTTO_649, [5, 25, 1, 2, 3, 4], day, d)
        self.assertEqual(r.prize, "бесплатный билет")
        r = core.check_ticket(core.LOTTO_649, [5, 25, 16, 2, 3, 4], day, d)
        self.assertIn("денежный", r.prize)

    def test_parse_numbers(self):
        self.assertEqual(core.parse_numbers("46, 1 3;10 20 22 28", core.LOTTO_MAX),
                         [1, 3, 10, 20, 22, 28, 46])
        for bad in ("1 2 3", "1 1 2 3 4 5 6", "1 2 3 4 5 6 53", "0 1 2 3 4 5 6"):
            with self.assertRaises(ValueError):
                core.parse_numbers(bad, core.LOTTO_MAX)
        with self.assertRaises(ValueError):       # до 2019 года 50 не было
            core.parse_numbers("1 2 3 4 5 6 50", core.LOTTO_MAX, date(2018, 1, 1))
        with self.assertRaises(ValueError):       # до 14.04.2026 не было 51 и 52
            core.parse_numbers("1 2 3 4 5 6 52", core.LOTTO_MAX, date(2026, 4, 10))
        self.assertEqual(core.parse_numbers("52 51 1 2 3 4 5", core.LOTTO_MAX,
                                            date(2026, 10, 20)), [1, 2, 3, 4, 5, 51, 52])

    def test_generator_never_repeats_bought(self):
        text, _ = fake_max_csv(600, seed=11, maxmillions=False)
        st = core.compute_stats(core.LOTTO_MAX, core.parse_csv(text, core.LOTTO_MAX))
        top = core.generate(st, "top", 5)
        bought = {tuple(t) for t in top}
        again = core.generate(st, "top", 10, avoid=bought)
        self.assertEqual(len(again), 10)
        self.assertFalse({tuple(t) for t in again} & bought)
        rng = random.Random(1)
        fixed = {1, 2, 3, 4, 5, 6}       # остаётся 44 варианта на последнее число
        many = core.generate(st, "random", 40, fixed=fixed, rng=rng)
        rest = core.generate(st, "random", 40, fixed=fixed, rng=rng,
                             avoid={tuple(t) for t in many})
        self.assertFalse({tuple(t) for t in rest} & {tuple(t) for t in many})
        self.assertLessEqual(len(rest), 44 - 40)

    def test_tickets_storage(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict("os.environ", {"LOTTO_DATA_DIR": tmp}):
            self.assertEqual(data.user_dir(), Path(tmp))
            self.assertEqual(data.load_tickets(), [])
            n = data.add_tickets("LOTTOMAX", [[46, 1, 3, 10, 20, 22, 28],
                                              [12, 14, 18, 19, 23, 36, 45]],
                                 "2026-10-17", "2026-10-20")
            self.assertEqual(n, 2)
            # тот же билет на тот же тираж второй раз не пишется
            self.assertEqual(data.add_tickets("LOTTOMAX", [[1, 3, 10, 20, 22, 28, 46]],
                                              "2026-10-17", "2026-10-20"), 0)
            # а на другой тираж — пишется
            self.assertEqual(data.add_tickets("LOTTOMAX", [[1, 3, 10, 20, 22, 28, 46]],
                                              "2026-10-21", "2026-10-23"), 1)
            items = data.load_tickets()
            self.assertEqual(len(items), 3)
            self.assertEqual(items[0]["numbers"], [1, 3, 10, 20, 22, 28, 46])
            data.remove_ticket(items[1])
            self.assertEqual([t["numbers"][0] for t in data.load_tickets()], [1, 1])
            (Path(tmp) / "my_tickets.json").write_text("испорчено", encoding="utf-8")
            self.assertEqual(data.load_tickets(), [])     # не падает



class Rules52Tests(unittest.TestCase):
    """С 14.04.2026 Lotto Max — 7 из 52. Раньше программа такие тиражи теряла."""

    TEXT = (HEADER_MAX + "\n"
            "Lotto Max,1,0,2026-04-10,1,2,3,4,5,6,50,7\n"
            "Lotto Max,2,0,2026-04-14,1,2,3,4,5,51,52,50\n"
            "Lotto Max,2,1,2026-04-14,10,20,30,40,49,51,52,\n"
            "Lotto Max,3,0,2026-04-17,8,9,10,11,12,13,52,51\n"
            "Lotto Max,4,0,2026-04-07,1,2,3,4,5,6,51,7\n")   # 51 до смены — брак

    def test_max_ball_by_date(self):
        g = core.LOTTO_MAX
        self.assertEqual(g.max_ball(date(2019, 5, 13)), 49)
        self.assertEqual(g.max_ball(date(2026, 4, 13)), 50)
        self.assertEqual(g.max_ball(date(2026, 4, 14)), 52)
        self.assertEqual(g.max_ball(), 52)
        self.assertEqual(core.LOTTO_649.max_ball(date(2026, 10, 17)), 49)

    def test_draws_with_51_52_are_kept(self):
        main, extra = core.parse_all(self.TEXT, core.LOTTO_MAX)
        self.assertEqual([d.when.isoformat() for d in main],
                         ["2026-04-10", "2026-04-14", "2026-04-17"])
        self.assertEqual(main[1].numbers, (1, 2, 3, 4, 5, 51, 52))
        self.assertEqual(main[2].bonus, 51)
        self.assertEqual(len(extra), 1)
        # Строка от 07.04 с числом 51 — брак, и самопроверка это видит.
        self.assertEqual(core.count_draw_keys(self.TEXT), 4)

    def test_stats_cover_52(self):
        main, _ = core.parse_all(self.TEXT, core.LOTTO_MAX)
        st = core.compute_stats(core.LOTTO_MAX, main)
        self.assertEqual(st.max_ball, 52)
        self.assertEqual(st.numbers[52].count, 2)
        self.assertEqual(st.numbers[51].count, 1)
        t = core.generate(st, "random", 30, rng=random.Random(4))
        self.assertTrue(any(n > 50 for x in t for n in x))

    def test_check_ticket_with_52(self):
        main, _ = core.parse_all(self.TEXT, core.LOTTO_MAX)
        r = core.check_ticket(core.LOTTO_MAX, [1, 2, 3, 4, 5, 51, 52],
                              date(2026, 4, 14), main)
        self.assertEqual((r.matches, r.prize), (7, "ДЖЕКПОТ"))

    def test_odds(self):
        self.assertEqual(core.LOTTO_MAX.odds(date(2026, 10, 20)), 133_784_560)
        self.assertEqual(core.LOTTO_MAX.odds(date(2020, 1, 1)), 99_884_400)
        self.assertEqual(core.LOTTO_649.odds(), 13_983_816)

    def test_rejected_main_never_replaced_by_maxmillions(self):
        # Настоящий случай 16.10.2026: основной розыгрыш с 51, допрозыгрыш без.
        text = (HEADER_MAX + "\n"
                "Lotto Max,9,0,2026-10-16,1,11,13,36,41,43,51,52\n"
                "Lotto Max,9,1,2026-10-16,1,7,17,25,39,44,46,\n")
        old_rules = lambda self, d=None: 50 if self.key == "LOTTOMAX" else 49  # noqa: E731
        with mock.patch.object(core.Game, "max_ball", old_rules):
            main, extra = core.parse_all(text, core.LOTTO_MAX)
        self.assertEqual(main, [])                          # не подменён
        self.assertEqual([d.numbers for d in extra], [(1, 7, 17, 25, 39, 44, 46)])
        self.assertNotEqual(core.count_draw_rows(text), len(main) + len(extra))
        main, extra = core.parse_all(text, core.LOTTO_MAX)  # нынешние правила
        self.assertEqual(main[0].numbers, (1, 11, 13, 36, 41, 43, 51))
        self.assertEqual(main[0].bonus, 52)
        self.assertEqual(core.count_draw_rows(text), len(main) + len(extra))

    def test_build_guard_catches_lost_draws(self):
        # Ровно та ошибка, что была: правила «до 50» теряют тиражи с 51/52.
        with mock.patch.object(core.Game, "max_ball",
                               lambda self, d=None: 50 if self.key == "LOTTOMAX" else 49):
            main, _ = core.parse_all(self.TEXT, core.LOTTO_MAX)
        self.assertLess(len(main), core.count_draw_keys(self.TEXT) - 1)



class AppUpdateTests(unittest.TestCase):
    """Самообновление: версия, контрольная сумма, распаковка."""

    def release(self, zip_bytes, sha_text, digest=None):
        import hashlib
        dig = digest or "sha256:" + hashlib.sha256(zip_bytes).hexdigest()
        files = {}
        assets = []
        for a in ("apple-silicon", "intel"):
            zu = f"https://dl/{a}.zip"
            su = f"https://dl/{a}.sha"
            files[zu], files[su] = zip_bytes, sha_text.encode()
            assets += [{"name": f"LottoGenerator-mac-{a}.zip", "browser_download_url": zu,
                        "digest": dig, "size": len(zip_bytes)},
                       {"name": f"LottoGenerator-mac-{a}.sha", "browser_download_url": su}]
        files[upd.API] = json.dumps({"assets": assets}).encode()
        return lambda url, timeout=30: files[url]

    def make_zip(self):
        import io as _io
        import zipfile
        buf = _io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("Lotto Generator.app/Contents/Info.plist", "<plist/>")
        return buf.getvalue()

    def test_no_update_when_same_version(self):
        z = self.make_zip()
        with mock.patch.object(upd, "_get", self.release(z, "abc123")), \
                mock.patch.object(upd, "current_version", return_value="abc123"):
            self.assertIsNone(upd.check())

    def test_update_found_and_staged(self):
        z = self.make_zip()
        with mock.patch.object(upd, "_get", self.release(z, "new999\n")), \
                mock.patch.object(upd, "current_version", return_value="abc123"), \
                mock.patch.object(upd.sys, "platform", "linux"):
            info = upd.check()
            self.assertEqual(info["version"], "new999")
            app = upd.download_and_stage(info)
            self.assertEqual(app.name, "Lotto Generator.app")
            self.assertTrue((app / "Contents" / "Info.plist").is_file())

    def test_bad_digest_rejected(self):
        z = self.make_zip()
        with mock.patch.object(upd, "_get", self.release(z, "new999", "sha256:" + "0" * 64)), \
                mock.patch.object(upd, "current_version", return_value="abc123"):
            info = upd.check()
            with self.assertRaises(ValueError):
                upd.download_and_stage(info)

    def test_missing_digest_rejected(self):
        with self.assertRaises(ValueError):
            upd.verify_digest(b"x", "")

    def test_sha_missing_means_no_update(self):
        # .sha выкладывается после zip: пока его нет — сборка не закончена.
        z = self.make_zip()
        getter = self.release(z, "new999")
        rel = json.loads(getter(upd.API))
        rel["assets"] = [a for a in rel["assets"] if not a["name"].endswith(".sha")]
        with mock.patch.object(upd, "_get",
                               lambda u, timeout=30: json.dumps(rel).encode()
                               if u == upd.API else getter(u)), \
                mock.patch.object(upd, "current_version", return_value="abc123"):
            self.assertIsNone(upd.check())

    def test_source_is_fixed_github_repo(self):
        self.assertTrue(upd.API.startswith(
            "https://api.github.com/repos/simafon1-cyber/lotto-generator/releases/"))

    def test_swap_script_replaces_app(self):
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            old, new = Path(tmp) / "Lotto Generator.app", Path(tmp) / "stage" / "L.app"
            old.mkdir()
            (old / "v").write_text("old")
            new.mkdir(parents=True)
            (new / "v").write_text("new")
            script = Path(tmp) / "swap.sh"
            script.write_text(upd.SWAP_SCRIPT)
            dead = subprocess.Popen(["true"])
            dead.wait()
            subprocess.run(["/bin/bash", str(script), str(dead.pid), str(old), str(new)],
                           capture_output=True, timeout=30)
            self.assertEqual((old / "v").read_text(), "new")
            self.assertFalse(Path(str(old) + ".old").exists())

    def test_not_frozen_has_no_bundle(self):
        self.assertIsNone(upd.app_bundle())



class PopularTests(unittest.TestCase):
    def test_reasons(self):
        g = core.LOTTO_MAX
        self.assertTrue(core.popular_reasons([1, 5, 9, 12, 17, 23, 28], g))   # дни месяца
        self.assertIn("3 числа подряд", core.popular_reasons([4, 5, 6, 33, 40, 45, 50], g))
        self.assertTrue(any("лесенка" in r for r in
                            core.popular_reasons([3, 10, 17, 24, 35, 44, 52], g)))
        self.assertTrue(any("последней цифрой" in r for r in
                            core.popular_reasons([2, 12, 22, 32, 35, 47, 51], g)))
        self.assertEqual(core.popular_reasons([3, 8, 19, 26, 34, 41, 50], g), [])

    def test_generator_avoids_popular(self):
        text, _ = fake_max_csv(600, seed=11, maxmillions=False)
        st = core.compute_stats(core.LOTTO_MAX, core.parse_csv(text, core.LOTTO_MAX))
        rng = random.Random(8)
        plain = core.generate(st, "random", 40, rng=rng)
        self.assertTrue(any(core.popular_reasons(t, st.game) for t in plain))
        clean = core.generate(st, "random", 40, rng=rng, avoid_popular=True)
        self.assertEqual(len(clean), 40)
        self.assertFalse(any(core.popular_reasons(t, st.game) for t in clean))


class BacktestTests(unittest.TestCase):
    def test_no_look_ahead(self):
        # До проверяемого тиража A и B выпали поровну (30 и 30), сам тираж — B.
        # Без подглядывания «строго частые» берут A (меньшие числа при равенстве)
        # и совпадают на 0. Если бы считали вместе с проверяемым — взяли бы B: 7.
        A, B = [1, 2, 3, 4, 5, 6, 7], [10, 11, 12, 13, 14, 15, 16]
        draws = [core.Draw(date(2015, 1, 1) + timedelta(days=i), tuple(x))
                 for i, x in enumerate([A, B] * 30 + [B])]
        rows = core.backtest(core.LOTTO_MAX, draws, ["top"], last=1, per_draw=1)
        self.assertEqual((rows[0].tickets, rows[0].avg_matches), (1, 0.0))

    def test_fair_data_within_noise(self):
        text, _ = fake_max_csv(900, seed=21, maxmillions=False)
        draws = core.parse_csv(text, core.LOTTO_MAX)
        rows = core.backtest(core.LOTTO_MAX, draws, list(core.STRATEGIES), last=200)
        for r in rows:
            self.assertEqual(r.tickets, 2000)
            self.assertTrue(49 / 50 <= r.expected_avg <= 49 / 49)   # 7*7/50 … 7*7/49
            self.assertLess(abs(r.z), 4.5, r)

    def test_identical_tickets_do_not_shrink_spread(self):
        # Десять ОДИНАКОВЫХ билетов на тираж несут столько же сведений, сколько
        # один. Старая формула считала их независимыми и занижала разброс в √10
        # раз — отсюда ложные «способ лучше случайного» на честных данных.
        text, _ = fake_max_csv(700, seed=4, maxmillions=False)
        draws = core.parse_csv(text, core.LOTTO_MAX)
        same = lambda st, s, n, rng=None: [[1, 9, 17, 25, 33, 41, 49]] * n  # noqa: E731
        with mock.patch.object(core, "generate", same):
            one = core.backtest(core.LOTTO_MAX, draws, ["x"], last=200, per_draw=1)[0]
            ten = core.backtest(core.LOTTO_MAX, draws, ["x"], last=200, per_draw=10)[0]
        self.assertEqual(ten.tickets, 2000)
        self.assertAlmostEqual(ten.avg_matches, one.avg_matches, places=12)
        self.assertAlmostEqual(ten.se, one.se, places=12)
        self.assertGreater(one.se, 0.03)          # ≈ 0.86 / √200 ≈ 0.06


class MoneyTests(unittest.TestCase):
    def test_summary_and_limit(self):
        today = date(2026, 10, 17)                      # суббота
        items = [
            {"game": "LOTTOMAX", "numbers": [1], "bought": "2026-10-12", "draw": "x"},  # пн
            {"game": "LOTTOMAX", "numbers": [2], "bought": "2026-10-11", "draw": "x",
             "won": 20},                                                             # вс прошлой
            {"game": "649", "numbers": [3], "bought": "2026-09-30", "draw": "x"},       # сентябрь
            {"game": "649", "numbers": [4], "bought": "2026-10-17", "draw": "x", "cost": 6},
        ]
        m = data.money_summary(items, today)
        self.assertEqual(m["week"], 1.5 + 6)
        self.assertEqual(m["month"], 1.5 + 1.5 + 6)
        self.assertEqual(m["total"], 1.5 + 1.5 + 3 + 6)
        self.assertEqual(m["won"], 20)
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict("os.environ", {"LOTTO_DATA_DIR": tmp}):
            self.assertFalse(data.over_limit(items, today, 1000))      # лимита нет
            data.save_settings(weekly_limit=10)
            self.assertFalse(data.over_limit(items, today))            # 7.5 из 10
            self.assertTrue(data.over_limit(items, today, 3))          # 10.5 > 10
            data.save_settings(weekly_limit="мусор")
            self.assertEqual(data.weekly_limit(), 0.0)

    def test_set_won_and_cost(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict("os.environ", {"LOTTO_DATA_DIR": tmp}):
            data.add_tickets("LOTTOMAX", [[1, 2, 3, 4, 5, 6, 7]], "2026-10-17", "2026-10-20")
            data.add_tickets("649", [[1, 2, 3, 4, 5, 6]], "2026-10-17", "2026-10-21")
            items = data.load_tickets()
            self.assertEqual([t["cost"] for t in items], [1.5, 3.0])
            data.set_won(items[0], 20)
            self.assertEqual(data.load_tickets()[0]["won"], 20)
            with self.assertRaises(ValueError):
                data.set_won(data.load_tickets()[1], -5)

    def test_import_from_other_device(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict("os.environ", {"LOTTO_DATA_DIR": tmp}):
            data.add_tickets("LOTTOMAX", [[1, 2, 3, 4, 5, 6, 7]], "2026-10-17", "2026-10-20")
            incoming = [
                {"game": "LOTTOMAX", "numbers": [7, 6, 5, 4, 3, 2, 1], "bought": "2026-10-17",
                 "draw": "2026-10-20"},                                   # уже есть
                {"game": "LOTTOMAX", "numbers": [1, 2, 3, 4, 5, 6, 52], "bought": "2026-10-18",
                 "draw": "2026-10-20", "cost": 1.5, "won": 20},          # новый
                {"game": "649", "numbers": [1, 2, 3, 4, 5, 6], "draw": "кривая дата"},
                {"game": "ЧУЖАЯ", "numbers": [1], "draw": "2026-10-20"},
                "мусор",
            ]
            self.assertEqual(data.import_tickets(incoming), 1)
            items = data.load_tickets()
            self.assertEqual(len(items), 2)
            self.assertEqual(items[1]["won"], 20.0)
            self.assertEqual(data.import_tickets("не список"), 0)

    def test_notify_is_safe_off_mac(self):
        data.notify('за"головок', "текст \\ с кавычкой \"")   # не падает


if __name__ == "__main__":
    unittest.main(verbosity=2)
