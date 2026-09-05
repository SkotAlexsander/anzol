"""Baixador de Vídeo — app web local sobre o yt-dlp.

Roda um servidor Flask na própria máquina. A pasta downloads/ recebe os arquivos.
"""
from __future__ import annotations

import re
import threading
import uuid
from pathlib import Path

import yt_dlp
from flask import Flask, jsonify, request, send_from_directory

BASE_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
DOWNLOADS_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder="static", static_url_path="")

# jobs em memória: {job_id: {"status": ..., "pct": float, "filename": str|None, "erro": str|None}}
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


def _sanitizar_nome(nome: str) -> str:
    nome = re.sub(r'[\\/:*?"<>|]', "_", nome)
    return nome.strip()[:150] or "arquivo"


def _extrair_info(url: str) -> dict:
    opts = {"quiet": True, "no_warnings": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
    if "entries" in info:
        # playlist: usa o primeiro item pra pré-visualização
        info = info["entries"][0]
    return {
        "titulo": info.get("title") or "(sem título)",
        "duracao": info.get("duration"),
        "miniatura": info.get("thumbnail"),
        "site": info.get("extractor_key"),
    }


def _progresso_hook(job_id: str):
    def hook(d: dict):
        with JOBS_LOCK:
            job = JOBS.get(job_id)
            if not job:
                return
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                baixado = d.get("downloaded_bytes") or 0
                job["pct"] = round(100 * baixado / total, 1) if total else job.get("pct", 0)
                job["status"] = "baixando"
            elif d["status"] == "finished":
                job["status"] = "processando"
                job["pct"] = 100.0
    return hook


def _rodar_download(job_id: str, url: str, modo: str):
    saida = str(DOWNLOADS_DIR / f"{job_id}.%(title).150s.%(ext)s")
    opts = {
        "outtmpl": saida,
        "progress_hooks": [_progresso_hook(job_id)],
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    if modo == "audio":
        opts["format"] = "bestaudio/best"
        opts["postprocessors"] = [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
        ]
    else:
        opts["format"] = "bestvideo*+bestaudio/best"
        opts["merge_output_format"] = "mp4"

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])
        # acha o arquivo gerado (prefixo job_id)
        candidatos = list(DOWNLOADS_DIR.glob(f"{job_id}.*"))
        with JOBS_LOCK:
            if candidatos:
                JOBS[job_id]["status"] = "concluido"
                JOBS[job_id]["filename"] = candidatos[0].name
            else:
                JOBS[job_id]["status"] = "erro"
                JOBS[job_id]["erro"] = "Download terminou mas o arquivo não foi encontrado."
    except Exception as exc:  # noqa: BLE001 — reporta qualquer falha do yt-dlp pro usuário
        with JOBS_LOCK:
            JOBS[job_id]["status"] = "erro"
            JOBS[job_id]["erro"] = str(exc)


@app.get("/")
def index():
    return app.send_static_file("index.html")


@app.post("/api/info")
def api_info():
    url = (request.json or {}).get("url", "").strip()
    if not url:
        return jsonify({"erro": "URL vazia."}), 400
    try:
        return jsonify(_extrair_info(url))
    except Exception as exc:  # noqa: BLE001
        return jsonify({"erro": str(exc)}), 400


@app.post("/api/download")
def api_download():
    data = request.json or {}
    url = data.get("url", "").strip()
    modo = data.get("modo", "video")
    if not url:
        return jsonify({"erro": "URL vazia."}), 400
    if modo not in ("video", "audio"):
        return jsonify({"erro": "Modo inválido."}), 400

    job_id = uuid.uuid4().hex[:12]
    with JOBS_LOCK:
        JOBS[job_id] = {"status": "iniciando", "pct": 0.0, "filename": None, "erro": None}

    thread = threading.Thread(target=_rodar_download, args=(job_id, url, modo), daemon=True)
    thread.start()
    return jsonify({"job_id": job_id})


@app.get("/api/status/<job_id>")
def api_status(job_id: str):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
    if not job:
        return jsonify({"erro": "job desconhecido"}), 404
    return jsonify(job)


@app.get("/downloads/<path:filename>")
def baixar_arquivo(filename: str):
    return send_from_directory(DOWNLOADS_DIR, filename, as_attachment=True)


if __name__ == "__main__":
    print(f"Baixador de Vídeo rodando em http://127.0.0.1:8137")
    app.run(host="127.0.0.1", port=8137, debug=False)
