"""Ядро генератора: чтение истории тиражей, частоты, генерация комбинаций.

Без графики и без сети — всё здесь проверяется тестами.

Важно и честно: тиражи лотереи независимы. То, что число чаще выпадало
раньше, НЕ повышает шанс, что оно выпадет в следующий раз. Генератор
просто даёт удобный способ выбрать числа по истории — не способ выиграть.
"""

from __future__ import annotations

import csv
import io
import math
import random
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from i18n import t

# ---------------------------------------------------------------------------
# Правила игр
# ---------------------------------------------------------------------------

# Lotto Max перешла с 1–49 на 1–50 в тираже 14 мая 2019 года,
# а с 1–50 на 1–52 — в тираже 14 апреля 2026 года (новые правила: 4 линии
# за 6 $, розыгрыши MaxPlus, потолок джекпота 90 млн).
LOTTO_MAX_50_FROM = date(2019, 5, 14)
LOTTO_MAX_52_FROM = date(2026, 4, 14)


@dataclass(frozen=True)
class Game:
    key: str            # имя файла BCLC без .zip
    title: str
    pick: int           # сколько чисел в билете
    min_draws: int      # меньше — файл явно битый или не тот

    def max_ball(self, d: date | None = None) -> int:
        if self.key == "LOTTOMAX":
            if d is None or d >= LOTTO_MAX_52_FROM:
                return 52
            if d >= LOTTO_MAX_50_FROM:
                return 50
            return 49
        return 49


    def odds(self, d: date | None = None) -> int:
        """Шанс главного приза одной линией: 1 к стольким."""
        return math.comb(self.max_ball(d), self.pick)


LOTTO_649 = Game("649", "Lotto 6/49", 6, 3000)
LOTTO_MAX = Game("LOTTOMAX", "Lotto Max", 7, 700)
GAMES = {g.key: g for g in (LOTTO_649, LOTTO_MAX)}


@dataclass
class Draw:
    when: date
    numbers: tuple[int, ...]
    bonus: int | None = None
    draw_no: str = ""


# ---------------------------------------------------------------------------
# Чтение CSV
# ---------------------------------------------------------------------------

_DATE_FORMATS = ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y",
                 "%b %d, %Y", "%B %d, %Y", "%a, %b %d, %Y", "%Y%m%d")


def _parse_date(text: str) -> date | None:
    text = text.strip().strip('"')
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def _to_int(text: str) -> int | None:
    text = (text or "").strip().strip('"')
    if re.fullmatch(r"\d{1,2}", text):
        return int(text)
    return None


def parse_csv(text: str, game: Game) -> list[Draw]:
    """Только основные розыгрыши — см. parse_all."""
    return parse_all(text, game)[0]


def parse_all(text: str, game: Game) -> tuple[list[Draw], list[Draw]]:
    """Разбирает CSV с историей тиражей: (основные, дополнительные).

    Основной формат — файлы BCLC (колонки DRAW DATE, NUMBER DRAWN 1..N,
    BONUS NUMBER, SEQUENCE NUMBER). Если заголовков нет или они другие —
    берёт из строки дату и первые N подходящих чисел.

    У Lotto Max в одном тираже бывают дополнительные розыгрыши MaxMillions
    (номер последовательности больше нуля). Основной розыгрыш — тот, у
    которого номер последовательности меньший; остальные возвращаются
    вторым списком.
    """
    text = text.lstrip("﻿")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return [], []

    header = [h.strip().upper() for h in rows[0]]
    has_header = any("DATE" in h for h in header)
    found: dict[tuple, Draw] = {}   # (дата, номер тиража, последовательность)
    main_seq: dict[tuple, int] = {}  # (дата, номер тиража) -> номер основного

    if has_header:
        date_col = next(i for i, h in enumerate(header) if "DATE" in h)
        num_cols = [i for i, h in enumerate(header)
                    if "NUMBER DRAWN" in h or re.fullmatch(r"(NUM|N|BALL)\s*\d+", h)]
        bonus_col = next((i for i, h in enumerate(header) if "BONUS" in h), None)
        seq_col = next((i for i, h in enumerate(header) if "SEQUENCE" in h), None)
        no_col = next((i for i, h in enumerate(header)
                       if "DRAW" in h and ("NUMBER" in h or "NO" in h)
                       and "DRAWN" not in h), None)
        body = rows[1:]
    else:
        body = rows

    for row in body:
        if not row or not any(c.strip() for c in row):
            continue
        if has_header and num_cols:
            if date_col >= len(row):
                continue
            when = _parse_date(row[date_col])
            nums = [_to_int(row[i]) for i in num_cols if i < len(row)]
            nums = [n for n in nums if n is not None]
            bonus = (_to_int(row[bonus_col])
                     if bonus_col is not None and bonus_col < len(row) else None)
            seq = (_to_int(row[seq_col]) or 0
                   if seq_col is not None and seq_col < len(row) else 0)
            draw_no = (row[no_col].strip()
                       if no_col is not None and no_col < len(row) else "")
        else:
            when = None
            ints = []
            for cell in row:
                if when is None:
                    when = _parse_date(cell)
                    if when is not None:
                        continue
                n = _to_int(cell)
                if n is not None:
                    ints.append(n)
            nums = ints[:game.pick]
            bonus = ints[game.pick] if len(ints) > game.pick else None
            seq, draw_no = 0, ""

        if when is None:
            continue
        # Номер основного розыгрыша запоминается ДО проверки чисел: если его
        # строка окажется браком, на его место нельзя ставить MaxMillions.
        # Именно так программа показывала MaxMillions вместо тиража, когда
        # Lotto Max перешла на 1–52, а здесь ещё было «до 50».
        k = (when, draw_no)
        if k not in main_seq or seq < main_seq[k]:
            main_seq[k] = seq
        if len(nums) < game.pick:
            continue
        nums = nums[:game.pick]
        top = game.max_ball(when)
        if len(set(nums)) != game.pick or not all(1 <= n <= top for n in nums):
            continue
        if bonus is not None and not 1 <= bonus <= top:
            bonus = None

        found[(when, draw_no, seq)] = Draw(when, tuple(sorted(nums)), bonus, draw_no)

    mains, extras = [], []
    for (when, draw_no, seq), d in found.items():
        (mains if main_seq[(when, draw_no)] == seq else extras).append(d)
    by_date = lambda d: d.when  # noqa: E731
    return sorted(mains, key=by_date), sorted(extras, key=by_date)


# ---------------------------------------------------------------------------
# Расписание тиражей
# ---------------------------------------------------------------------------

# Дни недели: 0 — понедельник. Тиражи около 22:30 по восточному времени.
DRAW_WEEKDAYS = {"649": (2, 5), "LOTTOMAX": (1, 4)}


def weekday_name(d: date, short: bool = False) -> str:
    return t(f"{'wds' if short else 'wd'}.{d.weekday()}")


def next_draw(game: Game, after: date) -> date:
    """Ближайший день тиража, начиная с сегодняшнего."""
    d = after
    while d.weekday() not in DRAW_WEEKDAYS[game.key]:
        d += timedelta(days=1)
    return d


def new_draws(old: list[Draw], new: list[Draw]) -> list[Draw]:
    """Тиражи, которых не было в старом списке (для сообщения «вышел новый»)."""
    seen = {(d.when, d.numbers) for d in old}
    return [d for d in new if (d.when, d.numbers) not in seen]


# ---------------------------------------------------------------------------
# Статистика
# ---------------------------------------------------------------------------

@dataclass
class NumberStat:
    number: int
    count: int
    share: float          # доля тиражей, где число выпало
    draws_since: int | None   # сколько тиражей назад выпало в последний раз


@dataclass
class Stats:
    game: Game
    draws: list[Draw]
    max_ball: int
    numbers: dict[int, NumberStat] = field(default_factory=dict)
    expected: float = 0.0
    chi2: float = 0.0
    p_value: float = 1.0

    def ranked(self, reverse: bool = True) -> list[NumberStat]:
        return sorted(self.numbers.values(),
                      key=lambda s: (s.count, -s.number), reverse=reverse)


def filter_draws(draws: list[Draw], since: date | None = None,
                 last_n: int | None = None) -> list[Draw]:
    out = [d for d in draws if since is None or d.when >= since]
    if last_n is not None:
        out = out[-last_n:]
    return out


def compute_stats(game: Game, draws: list[Draw]) -> Stats:
    """Частота каждого числа в выбранных тиражах.

    Если в выборке есть тиражи с разным диапазоном чисел (Lotto Max до и
    после 2019 года), ожидаемая частота считается для каждого числа своя:
    число 50 могло выпасть только в тиражах с 2019 года.
    """
    max_ball = max((game.max_ball(d.when) for d in draws),
                   default=game.max_ball())
    counts = {n: 0 for n in range(1, max_ball + 1)}
    last_seen: dict[int, int] = {}
    for i, d in enumerate(draws):
        for n in d.numbers:
            counts[n] += 1
            last_seen[n] = i

    total = len(draws)
    stats = Stats(game, draws, max_ball)
    for n in counts:
        stats.numbers[n] = NumberStat(
            n, counts[n], counts[n] / total if total else 0.0,
            (total - 1 - last_seen[n]) if n in last_seen else None)

    # Сколько раз каждое число «должно» было выпасть при честной лотерее.
    expected = {n: 0.0 for n in counts}
    for d in draws:
        top = game.max_ball(d.when)
        for n in range(1, top + 1):
            expected[n] += game.pick / top
    stats.expected = sum(expected.values()) / len(expected) if expected else 0.0
    if total:
        stats.chi2 = sum((counts[n] - expected[n]) ** 2 / expected[n]
                         for n in counts if expected[n] > 0)
        dof = len(counts) - 1
        stats.p_value = chi2_sf(stats.chi2, dof)
    return stats


def chi2_sf(x: float, k: int) -> float:
    """Вероятность получить разброс не меньше x при честной лотерее.

    Приближение Уилсона–Хилферти: для k≈48 точности хватает с запасом.
    """
    if x <= 0 or k <= 0:
        return 1.0
    z = ((x / k) ** (1 / 3) - (1 - 2 / (9 * k))) / math.sqrt(2 / (9 * k))
    return 0.5 * math.erfc(z / math.sqrt(2))


# ---------------------------------------------------------------------------
# Генерация
# ---------------------------------------------------------------------------

# Способы выбора (порядок — как в окне); названия — в переводах strat.<код>.
STRATEGIES = ("hot", "top", "cold", "overdue", "mix", "random")


def strategy_name(key: str) -> str:
    return t(f"strat.{key}")


def _weighted_sample(pool: list[int], weights: dict[int, float], k: int,
                     rng: random.Random) -> list[int]:
    pool = list(pool)
    chosen: list[int] = []
    while pool and len(chosen) < k:
        w = [max(weights.get(n, 0.0), 1e-9) for n in pool]
        n = rng.choices(pool, weights=w, k=1)[0]
        chosen.append(n)
        pool.remove(n)
    return chosen


def generate(stats: Stats, strategy: str = "hot", tickets: int = 1,
             fixed: set[int] | None = None, excluded: set[int] | None = None,
             strength: float = 1.0, rng: random.Random | None = None,
             avoid: set[tuple[int, ...]] | None = None,
             avoid_popular: bool = False) -> list[list[int]]:
    """Возвращает список билетов, каждый — отсортированные числа.

    fixed — числа, которые обязательно войдут в каждый билет.
    excluded — числа, которые не войдут ни в один.
    strength — насколько сильно перекашивать выбор к частым/редким числам
    (0 — как случайно, 1 — пропорционально частоте, больше — сильнее).
    avoid — комбинации, которые уже куплены: их генератор не предлагает.
    avoid_popular — пропускать комбинации, похожие на массовый выбор людей
    (см. popular_reasons): шанс тот же, но выигрыш реже придётся делить.
    """
    rng = rng or random.Random()
    pick = stats.game.pick
    fixed = set(fixed or ()) & set(stats.numbers)
    excluded = (set(excluded or ()) - fixed) & set(stats.numbers)
    if len(fixed) > pick:
        raise ValueError(t("err.pinned", n=len(fixed), pick=pick))
    pool = [n for n in stats.numbers if n not in fixed and n not in excluded]
    need = pick - len(fixed)
    if len(pool) < need:
        raise ValueError(t("err.excluded"))

    counts = {n: stats.numbers[n].count for n in stats.numbers}
    mean = (sum(counts.values()) / len(counts)) or 1.0

    def hot_w() -> dict[int, float]:
        return {n: ((counts[n] + 1) / (mean + 1)) ** (strength * 4) for n in pool}

    def cold_w() -> dict[int, float]:
        return {n: ((mean + 1) / (counts[n] + 1)) ** (strength * 4) for n in pool}

    def overdue_w() -> dict[int, float]:
        total = len(stats.draws)
        return {n: (1 + (stats.numbers[n].draws_since
                         if stats.numbers[n].draws_since is not None else total))
                ** (strength * 2) for n in pool}

    result: list[list[int]] = []
    seen: set[tuple[int, ...]] = {tuple(sorted(t)) for t in (avoid or ())}
    attempts = 0
    while len(result) < tickets and attempts < tickets * (200 if avoid_popular else 50):
        attempts += 1
        if strategy == "top":
            ranked = sorted(pool, key=lambda n: (-counts[n], n))
            # Первый билет — ровно топ; следующие сдвигаются по списку,
            # чтобы не выдавать один и тот же билет много раз.
            # Сдвиг по числу попыток, а не билетов: если топ уже куплен,
            # следующая попытка берёт следующие по частоте числа.
            start = (attempts - 1) * need
            part = ranked[start:start + need]
            if len(part) < need:
                part = _weighted_sample(pool, hot_w(), need, rng)
        elif strategy == "hot":
            part = _weighted_sample(pool, hot_w(), need, rng)
        elif strategy == "cold":
            part = _weighted_sample(pool, cold_w(), need, rng)
        elif strategy == "overdue":
            part = _weighted_sample(pool, overdue_w(), need, rng)
        elif strategy == "mix":
            hot_k = (need + 1) // 2
            part = _weighted_sample(pool, hot_w(), hot_k, rng)
            rest = [n for n in pool if n not in part]
            cw = {n: ((mean + 1) / (counts[n] + 1)) ** (strength * 4) for n in rest}
            part += _weighted_sample(rest, cw, need - hot_k, rng)
        elif strategy == "random":
            part = rng.sample(pool, need)
        else:
            raise ValueError(f"unknown strategy: {strategy}")
        ticket = tuple(sorted(fixed | set(part)))
        if ticket in seen:
            continue
        if avoid_popular and popular_reasons(list(ticket), stats.game):
            continue
        seen.add(ticket)
        result.append(list(ticket))
    return result


def history_matches(draws: list[Draw], ticket: list[int]) -> dict[int, int]:
    """Сколько раз в истории этот билет совпал бы на 3, 4, 5... чисел."""
    t = set(ticket)
    out: dict[int, int] = {}
    for d in draws:
        m = len(t & set(d.numbers))
        if m >= 3:
            out[m] = out.get(m, 0) + 1
    return out


# ---------------------------------------------------------------------------
# Мои билеты
# ---------------------------------------------------------------------------

def parse_numbers(text: str, game: Game, when: date | None = None) -> list[int]:
    """Числа билета, введённые вручную: «1 3 10 20 22 28 46» или через запятые."""
    nums = [int(x) for x in re.findall(r"\d+", text)]
    top = game.max_ball(when)
    if len(nums) != game.pick:
        raise ValueError(t("err.count", game=game.title, pick=game.pick, n=len(nums)))
    if len(set(nums)) != len(nums):
        raise ValueError(t("err.dup"))
    bad = [n for n in nums if not 1 <= n <= top]
    if bad:
        raise ValueError(t("err.range", top=top, bad=", ".join(map(str, bad))))
    return sorted(nums)


@dataclass
class TicketResult:
    drawn: bool                 # тираж уже прошёл и есть в данных
    matches: int = 0
    bonus: bool = False
    prize: str = ""             # "jackpot" / "cash" / "free"; пусто — без приза
    maxmillions: int = 0        # сколько MaxMillions/MaxPlus совпало целиком
    amount: int | None = None   # постоянная сумма приза, $; None — делится из фонда

    def text(self, game: Game) -> str:
        if not self.drawn:
            return t("res.waiting")
        out = t("res.matches", m=self.matches, pick=game.pick)
        out += t("res.bonus") if self.bonus else ""
        if self.amount:
            out += " — " + t("prize.fixed", amount=self.amount)
        else:
            out += f" — {t('prize.' + self.prize)}" if self.prize else t("res.no_prize")
        if self.maxmillions:
            out += t("res.mm", n=self.maxmillions)
        return out


def _prize(game: Game, m: int, bonus: bool) -> str:
    """Код приза: jackpot / cash / free; пустая строка — приза нет."""
    if m == game.pick:
        return "jackpot"
    if game.key == "LOTTOMAX":
        if m >= 4 or (m == 3 and bonus):
            return "cash"
        if m == 3:
            return "free"
    else:
        if m >= 3 or (m == 2 and bonus):
            return "cash"
        if m == 2:
            return "free"
    return ""


def prize_amount(game: Game, m: int, bonus: bool) -> int | None:
    """Постоянные призы по официальным таблицам (OLG, Loto-Québec, 2026).

    Lotto Max: 3 из 7 + бонус — 20 $. Lotto 6/49: 3 из 6 — 10 $, 2 из 6 +
    бонус — 5 $. Остальные денежные призы делятся из призового фонда, их
    сумма известна только после тиража (на сайте лотереи).
    """
    if game.key == "LOTTOMAX":
        return 20 if (m == 3 and bonus) else None
    if m == 3:
        return 10
    return 5 if (m == 2 and bonus) else None


def check_ticket(game: Game, numbers: list[int], draw_day: date,
                 mains: list[Draw], extras: list[Draw] = ()) -> TicketResult:
    """Сверка купленного билета с тиражом в день draw_day.

    Совпадения считаются только с основным розыгрышем этого дня; бонусное
    число — для призов вида «5 + бонус». MaxMillions выигрывает лишь при
    полном совпадении всех чисел.
    """
    main = next((d for d in mains if d.when == draw_day), None)
    if main is None:
        return TicketResult(drawn=False)
    t = set(numbers)
    m = len(t & set(main.numbers))
    bonus = main.bonus is not None and main.bonus in t
    mm = sum(1 for d in extras if d.when == draw_day and set(d.numbers) == t)
    return TicketResult(True, m, bonus, _prize(game, m, bonus), mm, prize_amount(game, m, bonus))


def count_draw_rows(text: str) -> int:
    """Сколько разных строк-розыгрышей (дата + номер + последовательность) в CSV.

    Должно равняться «основные + дополнительные» после parse_all. Это
    ловит и потерю строк, и подмену основного розыгрыша дополнительным.
    """
    return _count_keys(text, with_seq=True)


def count_draw_keys(text: str) -> int:
    """Сколько разных основных тиражей (дата + номер) записано в CSV BCLC.

    Нужна для самопроверки при сборке: если parse_all вернул меньше
    основных тиражей, значит какие-то строки отброшены — как случилось,
    когда Lotto Max перешла на 1–52, а программа ещё считала до 50.
    """
    return _count_keys(text, with_seq=False)


def _count_keys(text: str, with_seq: bool) -> int:
    rows = list(csv.reader(io.StringIO(text.lstrip("\ufeff"))))
    if not rows:
        return 0
    header = [h.strip().upper() for h in rows[0]]
    seq_col = next((i for i, h in enumerate(header) if "SEQUENCE" in h), None)
    date_col = next((i for i, h in enumerate(header) if "DATE" in h), None)
    no_col = next((i for i, h in enumerate(header)
                   if "DRAW" in h and ("NUMBER" in h or "NO" in h)
                   and "DRAWN" not in h), None)
    if date_col is None:
        return 0
    keys = set()
    for row in rows[1:]:
        if len(row) > date_col and _parse_date(row[date_col]):
            key = (_parse_date(row[date_col]),
                   row[no_col].strip() if no_col is not None and no_col < len(row) else "")
            if with_seq:
                key += (row[seq_col].strip() if seq_col is not None
                        and seq_col < len(row) else "",)
            keys.add(key)
    return len(keys)


# ---------------------------------------------------------------------------
# Комбинации, которые часто выбирают люди
# ---------------------------------------------------------------------------

def popular_reasons(ticket: list[int], game: Game) -> list[str]:
    """Почему комбинация похожа на те, что выбирают многие.

    Шанс выигрыша от этого не меняется. Меняется другое: если такая
    комбинация выиграет, джекпот делится на всех, кто её купил. Люди
    массово берут дни рождения (1–31), ряды подряд, «лесенки» с равным
    шагом и числа с одной последней цифрой.
    """
    tk = sorted(ticket)
    out = []
    high = sum(1 for n in tk if n > 31)
    if high < 2:
        out.append(t("pop.birthdays"))
    run = best = 1
    for a, b in zip(tk, tk[1:]):
        run = run + 1 if b == a + 1 else 1
        best = max(best, run)
    if best >= 3:
        out.append(t("pop.run", n=best))
    for i in range(len(tk) - 3):
        for j in range(i + 1, len(tk) - 2):
            step = tk[j] - tk[i]
            seq = [tk[i] + k * step for k in range(4)]
            if step > 1 and all(x in tk for x in seq):
                out.append(t("pop.ladder", step=step))
                break
        else:
            continue
        break
    tails = {}
    for n in tk:
        tails[n % 10] = tails.get(n % 10, 0) + 1
    if max(tails.values()) >= 4:
        out.append(t("pop.tail"))
    return out


# ---------------------------------------------------------------------------
# Проверка способов выбора на истории («бэктест»)
# ---------------------------------------------------------------------------

@dataclass
class BacktestRow:
    strategy: str
    tickets: int
    avg_matches: float
    hits3: int          # билетов с 3+ совпадениями
    hits4: int          # с 4+
    expected_avg: float  # сколько в среднем совпало бы у случайного билета
    se: float = 0.0      # обычный разброс среднего (стандартная ошибка, по тиражам)

    @property
    def z(self) -> float:
        """На сколько «разбросов» способ отличается от случайного."""
        return (self.avg_matches - self.expected_avg) / self.se if self.se else 0.0


def backtest(game: Game, draws: list[Draw], strategies: list[str],
             last: int = 300, per_draw: int = 10, seed: int = 1,
             progress=None) -> list[BacktestRow]:
    """Честная проверка: для каждого из последних `last` тиражей строит
    частоты ТОЛЬКО по тиражам до него, генерирует билеты каждым способом и
    считает, сколько чисел совпало с этим тиражом. Будущее не подсматривается.
    """
    rng = random.Random(seed)
    start = max(1, len(draws) - last)
    counts: dict[int, int] = {}
    last_seen: dict[int, int] = {}
    for i, d in enumerate(draws[:start]):
        for n in d.numbers:
            counts[n] = counts.get(n, 0) + 1
            last_seen[n] = i
    acc = {s: [0, 0, 0, 0] for s in strategies}     # билеты, сумма, 3+, 4+
    # Среднее совпадений по каждому тиражу. Разброс считается по ним, а не по
    # билетам: билеты одного способа сильно похожи друг на друга («редкие»
    # почти всегда одни и те же числа), и считать их независимыми — значит
    # занизить разброс втрое и увидеть «улучшение» там, где его нет.
    per_draw_means: dict[str, list[float]] = {s: [] for s in strategies}
    exp_sum = 0.0
    total_steps = len(draws) - start
    for step, i in enumerate(range(start, len(draws))):
        target = draws[i]
        top = game.max_ball(target.when)
        st = Stats(game, draws[:i], top)
        for n in range(1, top + 1):
            c = counts.get(n, 0)
            st.numbers[n] = NumberStat(n, c, c / i,
                                       (i - 1 - last_seen[n]) if n in last_seen else None)
        exp_sum += game.pick * game.pick / top
        win = set(target.numbers)
        for s in strategies:
            got = 0
            tickets_here = generate(st, s, per_draw, rng=rng)
            for t in tickets_here:
                m = len(win & set(t))
                got += m
                a = acc[s]
                a[0] += 1
                a[1] += m
                a[2] += m >= 3
                a[3] += m >= 4
            if tickets_here:
                per_draw_means[s].append(got / len(tickets_here))
        for n in target.numbers:
            counts[n] = counts.get(n, 0) + 1
            last_seen[n] = i
        if progress:
            progress(step + 1, total_steps)
    exp_avg = exp_sum / total_steps if total_steps else 0.0

    def se_of(xs: list[float]) -> float:
        n = len(xs)
        if n < 2:
            return 0.0
        mu = sum(xs) / n
        return math.sqrt(sum((x - mu) ** 2 for x in xs) / (n - 1) / n)

    return [BacktestRow(s, a[0], a[1] / a[0] if a[0] else 0.0, a[2], a[3], exp_avg,
                        se_of(per_draw_means[s]))
            for s, a in acc.items()]
