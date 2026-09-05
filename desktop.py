"""Baixador de Vídeo — app de desktop (janela nativa sobre o mesmo Flask).

Roda o servidor Flask numa thread em segundo plano e abre uma janela do
sistema (pywebview) apontando pra ele — sem aba de navegador, sem terminal
visível quando lançado com pythonw.
"""
from __future__ import annotations

import threading

import webview

from app import app

PORTA = 8137


def _rodar_servidor():
    app.run(host="127.0.0.1", port=PORTA, debug=False, use_reloader=False)


def main():
    thread = threading.Thread(target=_rodar_servidor, daemon=True)
    thread.start()

    webview.create_window(
        "Baixador de Vídeo",
        f"http://127.0.0.1:{PORTA}",
        width=920,
        height=680,
        min_size=(560, 420),
    )
    webview.start()


if __name__ == "__main__":
    main()
