#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Building Native Swift Tools ==="

mkdir -p "$SCRIPT_DIR"

if command -v swiftc >/dev/null 2>&1; then
    echo "[*] Compiling vision_ocr with Apple Vision framework..."
    swiftc -O -o "$SCRIPT_DIR/vision_ocr" "$ROOT_DIR/pipeline/vision_ocr.swift"
    echo "[+] Compiled $SCRIPT_DIR/vision_ocr"

    if [ -f "$ROOT_DIR/render_text.swift" ]; then
        echo "[*] Compiling render_text CoreText shaper..."
        swiftc -O -o "$SCRIPT_DIR/render_text" "$ROOT_DIR/render_text.swift"
        echo "[+] Compiled $SCRIPT_DIR/render_text"
    fi
else
    echo "[!] Warning: swiftc not found. Vision OCR will require macOS Xcode Command Line Tools."
fi

echo "=== Build Complete ==="
