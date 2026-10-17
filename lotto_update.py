"""Обновление самой программы со страницы выпуска на GitHub.

Откуда: только https://github.com/simafon1-cyber/lotto-generator, выпуск
lottery-latest (открытый репозиторий только с этой программой).
Адрес зашит в код и не меняется настройками.

Как понять, что версия новая: при сборке в программу вкладывается файл
data/version.txt с хешем коммита, а рядом с zip на странице выпуска лежит
файл .sha с хешем той же сборки. Он выкладывается ПОСЛЕ zip, поэтому если
.sha уже новый — zip тоже новый.

Как ставится: zip скачивается во временную папку, его контрольная сумма
сверяется с той, что GitHub показывает для файла (поле digest). Потом
маленький скрипт ждёт, пока программа закроется, меняет папку .app на
новую (старую сохраняет до успешной замены) и запускает программу снова.
Ничего не делается без согласия человека.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

from lotto_data import _ssl_context, bundled_dir

API = "https://api.github.com/repos/simafon1-cyber/lotto-generator/releases/tags/lottery-latest"
UA = {"User-Agent": "LottoGenerator-updater", "Accept": "application/vnd.github+json"}


def arch() -> str:
    return "apple-silicon" if platform.machine() == "arm64" else "intel"


def current_version() -> str:
    try:
        return (bundled_dir() / "version.txt").read_text(encoding="utf-8").strip()
    except OSError:
        return ""          # запуск без сборки — версию не знаем


def app_bundle() -> Path | None:
    """Папка «Lotto Generator.app», если программа запущена из сборки."""
    if not getattr(sys, "frozen", False):
        return None
    exe = Path(sys.executable).resolve()
    for p in exe.parents:
        if p.suffix == ".app":
            return p
    return None


def _get(url: str, timeout: float = 30) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout, context=_ssl_context()) as r:
        return r.read()


def check() -> dict | None:
    """Есть ли новая версия. None — нет; иначе {version, url, digest, size}."""
    release = json.loads(_get(API))
    assets = {a["name"]: a for a in release.get("assets", [])}
    zip_name = f"LottoGenerator-mac-{arch()}.zip"
    sha_name = f"LottoGenerator-mac-{arch()}.sha"
    if zip_name not in assets or sha_name not in assets:
        return None
    latest = _get(assets[sha_name]["browser_download_url"]).decode().strip()
    if not latest or latest == current_version():
        return None
    a = assets[zip_name]
    return {"version": latest, "url": a["browser_download_url"],
            "digest": a.get("digest", ""), "size": a.get("size", 0)}


def verify_digest(payload: bytes, digest: str) -> None:
    """Сверка с контрольной суммой, которую публикует GitHub."""
    if not digest.startswith("sha256:"):
        raise ValueError("GitHub не сообщил контрольную сумму — обновление отменено.")
    got = hashlib.sha256(payload).hexdigest()
    if got != digest.split(":", 1)[1]:
        raise ValueError("Скачанный файл не совпал с контрольной суммой — "
                         "обновление отменено, программа не тронута.")


def download_and_stage(info: dict) -> Path:
    """Скачивает и распаковывает новую версию. Возвращает путь к новой .app."""
    payload = _get(info["url"], timeout=300)
    verify_digest(payload, info["digest"])
    work = Path(tempfile.mkdtemp(prefix="lotto-update-"))
    zpath = work / "new.zip"
    zpath.write_bytes(payload)
    # ditto сохраняет права и подпись .app; zipfile — запасной вариант для тестов.
    if sys.platform == "darwin":
        subprocess.run(["/usr/bin/ditto", "-x", "-k", str(zpath), str(work)], check=True)
    else:
        with zipfile.ZipFile(zpath) as z:
            z.extractall(work)
    apps = [p for p in work.iterdir() if p.suffix == ".app"]
    if len(apps) != 1:
        raise ValueError("В архиве не найдена программа .app — обновление отменено.")
    return apps[0]


SWAP_SCRIPT = """#!/bin/bash
# Ждёт закрытия программы, меняет .app на новую и запускает её.
PID="$1"; OLD="$2"; NEW="$3"
while kill -0 "$PID" 2>/dev/null; do sleep 0.5; done
rm -rf "$OLD.old"
if mv "$OLD" "$OLD.old" && mv "$NEW" "$OLD"; then
    rm -rf "$OLD.old"
else
    [ -d "$OLD.old" ] && [ ! -d "$OLD" ] && mv "$OLD.old" "$OLD"
fi
xattr -dr com.apple.quarantine "$OLD" 2>/dev/null
open "$OLD"
"""


def install_and_restart(new_app: Path, bundle: Path) -> None:
    """Запускает замену после выхода программы. Вызывающий должен закрыть окно."""
    script = new_app.parent / "swap.sh"
    script.write_text(SWAP_SCRIPT, encoding="utf-8")
    subprocess.Popen(["/bin/bash", str(script), str(os.getpid()), str(bundle),
                      str(new_app)], start_new_session=True,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
