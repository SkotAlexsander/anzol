"""Anzol — a casca HTTP.

Um Flask que serve a interface e expõe o motor de `nucleo.py`. Escuta só em
127.0.0.1: é um app de uma máquina só, não um serviço.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys

from flask import Flask, jsonify, request, send_from_directory

import nucleo

PORTA_PADRAO = int(os.environ.get("ANZOL_PORTA", "8137"))
DOWNLOADS_DIR = nucleo.DOWNLOADS_DIR

app = Flask(__name__, static_folder="static", static_url_path="")

#: quem pode falar com a API — o app é local, e ponto
LOOPBACK = {"127.0.0.1", "::1", "localhost"}


@app.before_request
def _so_da_propria_maquina():
    """Recusa qualquer chamada que não venha do loopback.

    Sem isso, um app que alguém exponha por engano (mudando o host no `run`)
    viraria um baixador aberto na rede. O `Host` também é conferido: bloqueia
    o truque de apontar um domínio de fora para 127.0.0.1 (DNS rebinding).
    """
    if request.remote_addr not in LOOPBACK:
        return jsonify({"erro": "Acesso permitido só da própria máquina."}), 403
    host = (request.host or "").rsplit(":", 1)[0].strip("[]")
    if host not in LOOPBACK:
        return jsonify({"erro": "Host não confiável."}), 403
    return None


def _corpo() -> dict:
    """JSON do pedido, tolerante: sem Content-Type o Flask levantaria 415."""
    return request.get_json(silent=True) or {}


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.get("/api/saude")
def api_saude():
    import yt_dlp

    return jsonify(
        {
            "ffmpeg": nucleo.ffmpeg_disponivel(),
            "ytdlp": yt_dlp.version.__version__,
            "pasta": str(DOWNLOADS_DIR),
            "modos": [
                {
                    "id": chave,
                    "rotulo": receita["rotulo"],
                    "precisaFfmpeg": chave in nucleo.MODOS_COM_FFMPEG,
                }
                for chave, receita in nucleo.MODOS.items()
            ],
        }
    )


@app.post("/api/info")
def api_info():
    url = str(_corpo().get("url", "")).strip()
    if not url:
        return jsonify({"erro": "Cole um link primeiro."}), 400
    try:
        return jsonify(nucleo.extrair_info(url))
    except Exception as exc:  # noqa: BLE001 — o motivo real vale mais que um 500 mudo
        return jsonify({"erro": nucleo.traduzir_erro(str(exc))}), 400


@app.post("/api/download")
def api_download():
    dados = _corpo()
    url = str(dados.get("url", "")).strip()
    modo = str(dados.get("modo", "video"))
    playlist = bool(dados.get("playlist", False))

    if not url:
        return jsonify({"erro": "Cole um link primeiro."}), 400
    if modo not in nucleo.MODOS:
        return jsonify({"erro": "Qualidade desconhecida."}), 400
    if modo in nucleo.MODOS_COM_FFMPEG and not nucleo.ffmpeg_disponivel():
        return jsonify(
            {"erro": "Esta opção precisa do ffmpeg no PATH. Sem ele, só o áudio original (M4A)."}
        ), 400

    return jsonify({"job_id": nucleo.iniciar_download(url, modo, playlist)})


@app.get("/api/status/<job_id>")
def api_status(job_id: str):
    job = nucleo.ler_job(job_id)
    if not job:
        return jsonify({"erro": "Este download saiu da memória do app."}), 404
    job.pop("terminou_em", None)
    return jsonify(job)


@app.post("/api/cancelar/<job_id>")
def api_cancelar(job_id: str):
    if not nucleo.cancelar_job(job_id):
        return jsonify({"erro": "Já tinha terminado."}), 409
    return jsonify({"ok": True})


@app.get("/api/arquivos")
def api_arquivos():
    """O que está na pasta hoje — inclusive de sessões anteriores."""
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    itens = [
        {"nome": p.name, "tamanho": p.stat().st_size, "quando": p.stat().st_mtime}
        for p in DOWNLOADS_DIR.iterdir()
        if p.is_file() and p.name != ".gitkeep" and not nucleo.eh_fragmento(p.name)
    ]
    itens.sort(key=lambda i: i["quando"], reverse=True)
    return jsonify({"arquivos": itens})


@app.post("/api/apagar")
def api_apagar():
    nome = nucleo.nome_seguro(str(_corpo().get("nome", "")))
    if not nome:
        return jsonify({"erro": "Nome de arquivo inválido."}), 400
    alvo = (DOWNLOADS_DIR / nome).resolve()
    if alvo.parent != DOWNLOADS_DIR.resolve() or not alvo.is_file():
        return jsonify({"erro": "Esse arquivo não está na pasta de downloads."}), 404
    alvo.unlink()
    return jsonify({"ok": True})


@app.post("/api/abrir-pasta")
def api_abrir_pasta():
    """Abre a pasta no explorador de arquivos do sistema."""
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if sys.platform == "win32":
            os.startfile(DOWNLOADS_DIR)  # noqa: S606 — caminho é constante do app
        elif sys.platform == "darwin":
            subprocess.run(["open", str(DOWNLOADS_DIR)], check=False)
        else:
            subprocess.run(["xdg-open", str(DOWNLOADS_DIR)], check=False)
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": f"Não consegui abrir a pasta: {exc}"}), 500
    return jsonify({"ok": True})


@app.get("/downloads/<path:nome>")
def baixar_arquivo(nome: str):
    return send_from_directory(DOWNLOADS_DIR, nome, as_attachment=True)


def escolher_porta(preferida: int = PORTA_PADRAO) -> int:
    """A porta preferida, ou uma livre qualquer se ela estiver ocupada.

    Evita o traceback de `Address already in use` quando sobrou uma instância
    antiga rodando.
    """
    for porta in (preferida, 0):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", porta))
                return s.getsockname()[1]
            except OSError:
                continue
    return preferida


def main() -> None:
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    porta = escolher_porta()
    if not nucleo.ffmpeg_disponivel():
        print("aviso: ffmpeg não encontrado no PATH — MP4 e MP3 vão ficar indisponíveis.")
    print(f"Anzol em http://127.0.0.1:{porta}  (Ctrl+C para parar)")
    app.run(host="127.0.0.1", port=porta, debug=False)


if __name__ == "__main__":
    main()
