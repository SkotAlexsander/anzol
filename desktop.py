"""Anzol — janela própria, sem navegador e sem console.

Sobe o mesmo Flask numa thread de fundo e abre a interface numa janela do
sistema (pywebview; no Windows, motor Edge WebView2). Fechar a janela encerra
o processo e libera a porta.

    pythonw desktop.py
"""
from __future__ import annotations

import threading

import webview

import nucleo
from app import app, escolher_porta


def _servir(porta: int) -> None:
    app.run(host="127.0.0.1", port=porta, debug=False, use_reloader=False)


def main() -> None:
    nucleo.DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    porta = escolher_porta()

    threading.Thread(target=_servir, args=(porta,), daemon=True).start()

    webview.create_window(
        "Anzol",
        f"http://127.0.0.1:{porta}",
        width=960,
        height=760,
        min_size=(560, 480),
    )
    webview.start()


if __name__ == "__main__":
    main()
