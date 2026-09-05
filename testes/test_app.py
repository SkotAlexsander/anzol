"""A casca HTTP: validação de entrada, o portão do loopback e o caminho de arquivo."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app as aplicacao  # noqa: E402
import nucleo  # noqa: E402


@pytest.fixture()
def cliente(tmp_path, monkeypatch):
    monkeypatch.setattr(aplicacao, "DOWNLOADS_DIR", tmp_path)
    monkeypatch.setattr(nucleo, "DOWNLOADS_DIR", tmp_path)
    aplicacao.app.config.update(TESTING=True)
    return aplicacao.app.test_client()


def test_saude_lista_os_modos(cliente):
    dados = cliente.get("/api/saude").get_json()
    assert isinstance(dados["ffmpeg"], bool)
    assert {"video", "mp3", "m4a"} <= {m["id"] for m in dados["modos"]}
    assert any(m["precisaFfmpeg"] for m in dados["modos"])


def test_pedido_de_fora_do_loopback_e_recusado(cliente):
    resp = cliente.get("/api/saude", environ_overrides={"REMOTE_ADDR": "192.168.0.9"})
    assert resp.status_code == 403


def test_host_de_dominio_estranho_e_recusado(cliente):
    resp = cliente.get("/api/saude", headers={"Host": "malicioso.example.com"})
    assert resp.status_code == 403


def test_info_sem_url_reclama_em_portugues(cliente):
    resp = cliente.post("/api/info", json={"url": "  "})
    assert resp.status_code == 400
    assert "Cole um link" in resp.get_json()["erro"]


def test_corpo_sem_content_type_nao_derruba_a_rota(cliente):
    resp = cliente.post("/api/info", data="não é json")
    assert resp.status_code == 400
    assert "erro" in resp.get_json()


def test_download_com_modo_inventado_e_recusado(cliente):
    resp = cliente.post("/api/download", json={"url": "https://x/y", "modo": "8k-holograma"})
    assert resp.status_code == 400
    assert "Qualidade desconhecida" in resp.get_json()["erro"]


def test_download_sem_ffmpeg_explica_a_alternativa(cliente, monkeypatch):
    monkeypatch.setattr(nucleo, "ffmpeg_disponivel", lambda: False)
    resp = cliente.post("/api/download", json={"url": "https://x/y", "modo": "video"})
    assert resp.status_code == 400
    assert "ffmpeg" in resp.get_json()["erro"]


def test_status_de_job_desconhecido_e_404(cliente):
    resp = cliente.get("/api/status/naoexiste")
    assert resp.status_code == 404


def test_cancelar_job_que_nao_existe_e_409(cliente):
    assert cliente.post("/api/cancelar/naoexiste").status_code == 409


def test_arquivos_lista_o_que_esta_na_pasta_e_esconde_fragmento(cliente, tmp_path):
    (tmp_path / "abc.Um vídeo [x].mp4").write_bytes(b"1234")
    (tmp_path / "abc.Um vídeo [x].f251.webm").write_bytes(b"1")
    (tmp_path / ".gitkeep").write_bytes(b"")

    nomes = [a["nome"] for a in cliente.get("/api/arquivos").get_json()["arquivos"]]
    assert nomes == ["abc.Um vídeo [x].mp4"]


def test_apagar_remove_o_arquivo(cliente, tmp_path):
    alvo = tmp_path / "abc.Um vídeo [x].mp4"
    alvo.write_bytes(b"1234")

    assert cliente.post("/api/apagar", json={"nome": alvo.name}).status_code == 200
    assert not alvo.exists()


def test_apagar_nao_sai_da_pasta(cliente, tmp_path):
    fora = tmp_path.parent / "importante.txt"
    fora.write_text("não me apague")

    resp = cliente.post("/api/apagar", json={"nome": "../importante.txt"})
    assert resp.status_code == 400
    assert fora.exists()


def test_escolher_porta_devolve_alguma_porta_utilizavel():
    assert 1 <= aplicacao.escolher_porta(0) <= 65535
