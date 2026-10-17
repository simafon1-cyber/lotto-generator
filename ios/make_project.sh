#!/bin/bash
# Собирает готовый проект Xcode для iPhone в папку $1.
# Нужна программа XcodeGen (brew install xcodegen). Запускается сборкой на GitHub.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="$1"
export BUILD_NUMBER="${BUILD_NUMBER:-1}"
rm -rf "$out"
mkdir -p "$out/web"
cp "$here/ContentView.swift" "$here/LottoGeneratorApp.swift" "$here/project.yml" "$out/"
cp -R "$here/Assets.xcassets" "$out/"
cp "$here/AppIcon-1024.png" "$out/Assets.xcassets/AppIcon.appiconset/"
cp "$here/../web/"* "$out/web/"
cp "$here/TESTFLIGHT.md" "$out/КАК_ОТПРАВИТЬ_В_TESTFLIGHT.md"
(cd "$out" && xcodegen generate)
echo "Проект готов: $out/LottoGenerator.xcodeproj (сборка № $BUILD_NUMBER)"
