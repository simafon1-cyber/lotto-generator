"""Готовит data.json для веб-приложения (iPhone) из файлов BCLC.

Запуск: python build_web_data.py <папка с 649.csv и LOTTOMAX.csv> <выходной data.json>
Сверка «каждая строка файла прочитана» — та же, что при сборке для Mac.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from lotto_core import GAMES, count_draw_keys, count_draw_rows, parse_all


def build(folder: Path) -> dict:
    out = {"updated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
           "games": {}}
    for g in GAMES.values():
        text = (folder / f"{g.key}.csv").read_text(encoding="utf-8")
        main, extra = parse_all(text, g)
        if (count_draw_keys(text) != len(main)
                or count_draw_rows(text) != len(main) + len(extra)):
            raise SystemExit(f"{g.title}: прочитано не всё — сборка остановлена.")
        out["games"][g.key] = {
            "title": g.title,
            "pick": g.pick,
            # [дата, [числа], бонус]
            "draws": [[d.when.isoformat(), list(d.numbers), d.bonus] for d in main],
            # [дата, [числа]] — MaxMillions / MaxPlus
            "extras": [[d.when.isoformat(), list(d.numbers)] for d in extra],
        }
        print(f"{g.title}: основных {len(main)}, дополнительных {len(extra)}")
    return out


if __name__ == "__main__":
    data = build(Path(sys.argv[1]))
    Path(sys.argv[2]).write_text(json.dumps(data, separators=(",", ":")), encoding="utf-8")
