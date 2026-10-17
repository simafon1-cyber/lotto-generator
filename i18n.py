"""Переводы интерфейса: русский, английский, французский.

Все фразы — в web/i18n.json; этот же файл читает веб-версия (iPhone), так
что тексты на Mac и на телефоне не расходятся. Язык хранится в настройках
программы (ключ "lang").
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

LANGS = ("ru", "en", "fr")
DEFAULT = "ru"


def _path() -> Path:
    # В собранной программе файл лежит рядом с данными, иначе — в web/.
    base = getattr(sys, "_MEIPASS", None)
    if base and (Path(base) / "i18n.json").is_file():
        return Path(base) / "i18n.json"
    return Path(__file__).resolve().parent / "web" / "i18n.json"


STRINGS: dict[str, dict[str, str]] = json.loads(_path().read_text(encoding="utf-8"))
_lang = DEFAULT


def set_lang(lang: str) -> None:
    global _lang
    _lang = lang if lang in LANGS else DEFAULT


def lang() -> str:
    return _lang


def t(key: str, **kw) -> str:
    """Фраза на текущем языке; {имя} подставляются из kw.

    Если фразы нет в выбранном языке — берётся русская, а если нет и её —
    сам ключ: интерфейс не падает из-за пропущенного перевода (а тест
    test_i18n следит, чтобы пропусков не было).
    """
    text = STRINGS.get(_lang, {}).get(key) or STRINGS[DEFAULT].get(key) or key
    return text.format(**kw) if kw else text


def d(day: date) -> str:
    """Дата в принятом для языка виде: 20.10.2026 / 2026-10-20 / 20/10/2026."""
    return day.strftime(t("fmt.date"))


def num(x: float, digits: int = 2) -> str:
    """Число с разделителем, принятым в языке (во французском — запятая)."""
    s = f"{x:.{digits}f}"
    return s.replace(".", ",") if _lang == "fr" else s


def write_js(target: Path | None = None) -> Path:
    """web/i18n.js — тот же словарь для веб-версии (работает и без сети)."""
    target = target or Path(__file__).resolve().parent / "web" / "i18n.js"
    target.write_text("// Создано из i18n.json командой: python3 i18n.py — не править вручную.\n"
                      "window.I18N = " + json.dumps(STRINGS, ensure_ascii=False, sort_keys=True)
                      + ";\n", encoding="utf-8")
    return target


if __name__ == "__main__":
    print(write_js())
