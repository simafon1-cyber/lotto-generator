"""Где лежат данные и как их обновить из интернета.

Источник — официальные файлы лотереи BCLC (Британская Колумбия) с полной
историей тиражей Lotto 6/49 (с 1982 года) и Lotto Max (с 2009 года).
"""

from __future__ import annotations

import io
import json
import os
import ssl
import sys
import urllib.request
import zipfile
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path

from i18n import t
from lotto_core import GAMES, LOTTO_MAX_52_FROM, Game, count_draw_keys, count_draw_rows, parse_all, parse_csv

SOURCE_URL = "https://www.playnow.com/resources/documents/downloadable-numbers/{key}.zip"
APP_NAME = "LottoGenerator"


# Как часто проверять новые тиражи, пока программа открыта.
UPDATE_EVERY = timedelta(hours=3)

# Официальные сайты, где продают Lotto Max и Lotto 6/49 (по провинции
# проживания). Покупку программа НЕ делает — только открывает сайт.
# Ключ — код провинции, название на нужном языке — в переводах prov.<код>.
PROVINCES = {
    "ON": "https://www.olg.ca/",
    "BC": "https://www.playnow.com/",
    "MB": "https://www.playnow.com/",
    "AB": "https://www.playalberta.ca/",
    "QC": "https://loteries.lotoquebec.com/",
    "ATL": "https://www.alc.ca/",
    "SK": "https://www.wclc.com/",
}
DEFAULT_PROVINCE = "ON"
# Как провинция хранилась в настройках до перевода на три языка.
_OLD_PROVINCE_NAMES = {
    "Онтарио (OLG)": "ON", "Британская Колумбия (PlayNow)": "BC", "Манитоба (PlayNow)": "MB",
    "Альберта (PlayAlberta)": "AB", "Квебек (Loto-Québec)": "QC",
    "Атлантические провинции (ALC)": "ATL", "Саскачеван (WCLC, онлайн-продаж нет)": "SK",
}


def province_code(saved) -> str:
    """Код провинции из настроек; старые русские названия тоже понимает."""
    if saved in PROVINCES:
        return saved
    return _OLD_PROVINCE_NAMES.get(saved, DEFAULT_PROVINCE)


def bundled_dir() -> Path:
    """Папка с данными, вложенными в приложение при сборке."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / "data"


def user_dir() -> Path:
    """Папка, куда приложение сохраняет свежескачанные данные и билеты."""
    if os.environ.get("LOTTO_DATA_DIR"):        # для самопроверки при сборке
        return Path(os.environ["LOTTO_DATA_DIR"])
    if sys.platform == "darwin":
        p = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        p = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_NAME
    return p


def csv_path(game: Game, folder: Path) -> Path:
    return folder / f"{game.key}.csv"


def load_text(game: Game) -> tuple[str, Path] | None:
    """Самый свежий из доступных файлов: сначала скачанный, потом вложенный."""
    for folder in (user_dir(), bundled_dir()):
        p = csv_path(game, folder)
        if p.is_file():
            return p.read_text(encoding="utf-8", errors="replace"), p
    return None


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # во вложенном Python на Mac своих сертификатов нет
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def download_csv(game: Game, timeout: float = 60) -> str:
    """Скачивает zip с историей и возвращает текст CSV внутри него."""
    req = urllib.request.Request(
        SOURCE_URL.format(key=game.key),
        headers={"User-Agent": "Mozilla/5.0 (Macintosh) LottoGenerator/1.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
        payload = r.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as z:
        names = [n for n in z.namelist() if n.lower().endswith(".csv")]
        if not names:
            raise ValueError(f"В архиве {game.key}.zip нет CSV-файла")
        return z.read(names[0]).decode("utf-8-sig", errors="replace")


def save_checked(game: Game, text: str, folder: Path) -> int:
    """Сохраняет CSV, только если он разбирается и в нём достаточно тиражей.

    Возвращает число тиражей. Битый файл не затирает рабочий.
    """
    draws = parse_csv(text, game)
    if len(draws) < game.min_draws:
        raise ValueError(t("data.short", game=game.title, n=len(draws), min=game.min_draws))
    folder.mkdir(parents=True, exist_ok=True)
    target = csv_path(game, folder)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(target)
    return len(draws)


def needs_update(last: datetime | None, now: datetime) -> bool:
    return last is None or now - last >= UPDATE_EVERY or now < last


def _state_path() -> Path:
    return user_dir() / "settings.json"


def load_settings() -> dict:
    try:
        return json.loads(_state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_settings(**changes) -> None:
    state = load_settings()
    state.update(changes)
    try:
        user_dir().mkdir(parents=True, exist_ok=True)
        _state_path().write_text(json.dumps(state, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
    except OSError:
        pass  # настройки — удобство, не повод падать


def last_update() -> datetime | None:
    try:
        return datetime.fromisoformat(load_settings()["last_update"])
    except (KeyError, ValueError, TypeError):
        return None


def _tickets_path() -> Path:
    return user_dir() / "my_tickets.json"


def load_tickets() -> list[dict]:
    """Купленные билеты: {game, numbers, bought, draw} (даты — ГГГГ-ММ-ДД)."""
    try:
        items = json.loads(_tickets_path().read_text(encoding="utf-8"))
        return [t for t in items if isinstance(t, dict) and "numbers" in t]
    except (OSError, ValueError):
        return []


def save_tickets(items: list[dict]) -> None:
    """Сохраняет атомарно: при сбое записи старый список не портится."""
    user_dir().mkdir(parents=True, exist_ok=True)
    target = _tickets_path()
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(target)


# Цена одной линии (7 или 6 чисел) в канадских долларах на 2026 год
# (OLG, BCLC, Loto-Québec): Lotto Max — 6 $ за игру из 4 линий,
# Lotto 6/49 — 3 $ за линию. До тиража 14.04.2026 Lotto Max стоил 5 $ за 3 линии.
LINE_PRICE = {"LOTTOMAX": 1.5, "649": 3.0}
LOTTO_MAX_OLD_LINE = 5 / 3


def line_price(game_key: str, draw: str = "") -> float:
    """Цена линии на тираж draw (ГГГГ-ММ-ДД); пустая дата — нынешняя цена."""
    if game_key == "LOTTOMAX" and draw and draw < LOTTO_MAX_52_FROM.isoformat():
        return LOTTO_MAX_OLD_LINE
    return LINE_PRICE.get(game_key, 0.0)


def ticket_cost(t: dict) -> float:
    return float(t.get("cost", line_price(t.get("game"), str(t.get("draw", "")))))


def money_summary(items: list[dict], today: date) -> dict:
    """Потрачено и выиграно: за эту неделю (с понедельника), месяц и всего."""
    week_start = today - timedelta(days=today.weekday())
    out = {"week": 0.0, "month": 0.0, "total": 0.0, "won": 0.0, "won_month": 0.0}
    for t in items:
        try:
            bought = date.fromisoformat(t["bought"])
        except (KeyError, ValueError):
            continue
        cost = ticket_cost(t)
        won = float(t.get("won", 0) or 0)
        out["total"] += cost
        out["won"] += won
        if bought >= week_start:
            out["week"] += cost
        if (bought.year, bought.month) == (today.year, today.month):
            out["month"] += cost
            out["won_month"] += won
    return out


def weekly_limit() -> float:
    try:
        return max(0.0, float(load_settings().get("weekly_limit", 0)))
    except (TypeError, ValueError):
        return 0.0


def over_limit(items: list[dict], today: date, extra: float = 0.0) -> bool:
    """Выйдет ли неделя за лимит с учётом ещё `extra` долларов. 0 — лимита нет."""
    lim = weekly_limit()
    return lim > 0 and money_summary(items, today)["week"] + extra > lim + 1e-9


def set_won(item: dict, amount: float) -> None:
    """Записывает выигрыш, который человек увидел на сайте или в кассе."""
    if amount < 0:
        raise ValueError(t("err.neg_won"))
    items = load_tickets()
    for tk in items:
        if tk == item:
            tk["won"] = round(amount, 2)
            save_tickets(items)
            return
    raise ValueError(t("err.ticket_gone"))


def notify(title: str, text: str) -> None:
    """Уведомление в углу экрана Mac. На других системах — ничего."""
    if sys.platform != "darwin":
        return
    esc = lambda x: x.replace("\\", "\\\\").replace('"', '\\"')  # noqa: E731
    try:
        subprocess.run(["/usr/bin/osascript", "-e",
                        f'display notification "{esc(text)}" with title "{esc(title)}"'],
                       timeout=10, capture_output=True)
    except (OSError, subprocess.SubprocessError):
        pass


def add_tickets(game_key: str, tickets: list[list[int]], bought: str,
                draw: str) -> int:
    """Добавляет билеты; тот же билет на тот же тираж второй раз не пишется."""
    items = load_tickets()
    have = {(t["game"], tuple(t["numbers"]), t["draw"]) for t in items}
    added = 0
    for nums in tickets:
        key = (game_key, tuple(sorted(nums)), draw)
        if key in have:
            continue
        have.add(key)
        items.append({"game": game_key, "numbers": sorted(nums),
                      "bought": bought, "draw": draw,
                      "cost": line_price(game_key, draw)})
        added += 1
    if added:
        save_tickets(items)
    return added


def import_tickets(incoming: list) -> int:
    """Добавляет билеты из файла другого устройства (тот же формат).

    Тот же билет на тот же тираж второй раз не пишется; цена и записанный
    выигрыш переносятся. Битые записи пропускаются.
    """
    items = load_tickets()
    have = {(t["game"], tuple(t["numbers"]), t["draw"]) for t in items}
    added = 0
    for t in incoming if isinstance(incoming, list) else []:
        try:
            game, nums, draw = t["game"], sorted(int(x) for x in t["numbers"]), str(t["draw"])
            date.fromisoformat(draw)
        except (KeyError, TypeError, ValueError):
            continue
        if game not in LINE_PRICE or (game, tuple(nums), draw) in have:
            continue
        have.add((game, tuple(nums), draw))
        rec = {"game": game, "numbers": nums, "bought": str(t.get("bought") or draw),
               "draw": draw, "cost": float(t.get("cost", line_price(game, draw)))}
        if t.get("won"):
            rec["won"] = float(t["won"])
        items.append(rec)
        added += 1
    if added:
        save_tickets(items)
    return added


def remove_ticket(item: dict) -> None:
    items = load_tickets()
    if item in items:
        items.remove(item)
        save_tickets(items)


def update_all(folder: Path | None = None) -> dict[str, tuple[bool, str]]:
    """Обновляет все игры. Итог по каждой: (успех, текст для человека)."""
    folder = folder or user_dir()
    report = {}
    for game in GAMES.values():
        try:
            n = save_checked(game, download_csv(game), folder)
            report[game.title] = (True, t("data.ok", n=n))
        except Exception as e:  # сеть, формат — показываем, но не падаем
            report[game.title] = (False, t("data.fail", e=e))
    if folder == user_dir() and all(ok for ok, _ in report.values()):
        save_settings(last_update=datetime.now().isoformat(timespec="seconds"))
    return report


if __name__ == "__main__":
    # Используется при сборке: python lotto_data.py <папка>
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else bundled_dir()
    for game in GAMES.values():
        text = download_csv(game)
        print(f"--- {game.key}: первые строки ---")
        print("\n".join(text.splitlines()[:4]))
        n = save_checked(game, text, out)
        draws, extra = parse_all(text, game)
        keys = count_draw_keys(text)
        print(f"  основных тиражей в файле: {keys}, прочитано: {len(draws)}, "
              f"допрозыгрышей: {len(extra)}")
        rows = count_draw_rows(text)
        print(f"  строк-розыгрышей в файле: {rows}, прочитано: {len(draws) + len(extra)}")
        if keys != len(draws) or rows != len(draws) + len(extra):
            raise SystemExit(f"{game.title}: прочитано не всё (тиражей {len(draws)} из "
                             f"{keys}, строк {len(draws) + len(extra)} из {rows}) — "
                             "правила игры изменились? Сборка остановлена.")
        if game.key == "LOTTOMAX":
            new = [d for d in draws if d.when >= LOTTO_MAX_52_FROM]
            hi = sum(1 for d in new for x in d.numbers if x > 50)
            print(f"  тиражей по правилам 1–52: {len(new)}, из них чисел 51/52: {hi}")
        print(f"{game.title}: тиражей {n}, с {draws[0].when} по {draws[-1].when}")
        print(f"  последний: {draws[-1].numbers} бонус {draws[-1].bonus}")
