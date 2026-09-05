"""O que dá para provar sem rede: formatação, tradução de erro, escolha do
arquivo final, varredura de sobras e o ciclo de vida de um trabalho."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import nucleo  # noqa: E402


# ──────────────────────────────────────────────────────────────── formatação ──

@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        (None, ""),
        (0, ""),
        (-5, ""),
        (512, "512 B"),
        (1024, "1,0 KB"),
        (1536, "1,5 KB"),
        (1024 * 1024 * 3.5, "3,5 MB"),
        (1024**3, "1,0 GB"),
    ],
)
def test_formatar_bytes(entrada, esperado):
    assert nucleo.formatar_bytes(entrada) == esperado


@pytest.mark.parametrize(
    ("entrada", "esperado"),
    [
        (None, ""),
        (0, ""),
        (9, "0:09"),
        (75, "1:15"),
        (600, "10:00"),
        (3672, "1:01:12"),
    ],
)
def test_formatar_duracao(entrada, esperado):
    assert nucleo.formatar_duracao(entrada) == esperado


# ─────────────────────────────────────────────────────────── tradução de erro ──

def test_traduzir_erro_reconhece_video_privado():
    bruto = "ERROR: [youtube] abc123: Private video. Sign in if you've been granted access"
    assert nucleo.traduzir_erro(bruto).startswith("Vídeo privado")


def test_traduzir_erro_reconhece_geo_bloqueio():
    bruto = "ERROR: The uploader has not made this video available in your country"
    assert "bloqueado no seu país" in nucleo.traduzir_erro(bruto)


def test_traduzir_erro_reconhece_video_sumido():
    bruto = "ERROR: [youtube] BaW_jenozKc: This video is unavailable"
    assert "indisponível" in nucleo.traduzir_erro(bruto)


def test_traduzir_erro_tira_extrator_e_id_do_texto_desconhecido():
    bruto = "ERROR: [genericsite] xJ8k2mQ0: aconteceu uma coisa nova"
    assert nucleo.traduzir_erro(bruto) == "aconteceu uma coisa nova"


def test_traduzir_erro_limpa_prefixo_e_cor_quando_nao_conhece():
    bruto = "\x1b[0;31mERROR:\x1b[0m algo bem específico que ninguém previu"
    assert nucleo.traduzir_erro(bruto) == "algo bem específico que ninguém previu"


def test_traduzir_erro_vazio_nao_devolve_string_vazia():
    assert nucleo.traduzir_erro("") == "Falhou sem dizer por quê."


# ─────────────────────────────────────────────────── qual é o arquivo final ──

def test_arquivos_finais_pega_o_merge_e_nao_os_fragmentos():
    info = {
        "title": "Um vídeo",
        "requested_downloads": [{"filepath": "/d/abc.Um vídeo [x1].mp4"}],
    }
    assert nucleo.arquivos_finais(info) == ["/d/abc.Um vídeo [x1].mp4"]


def test_arquivos_finais_desce_na_playlist():
    info = {
        "_type": "playlist",
        "entries": [
            {"requested_downloads": [{"filepath": "/d/abc.1 - um.mp4"}]},
            None,  # item que falhou com ignoreerrors
            {"requested_downloads": [{"filepath": "/d/abc.2 - dois.mp4"}]},
        ],
    }
    assert nucleo.arquivos_finais(info) == ["/d/abc.1 - um.mp4", "/d/abc.2 - dois.mp4"]


def test_arquivos_finais_aceita_info_vazia():
    assert nucleo.arquivos_finais({}) == []
    assert nucleo.arquivos_finais(None) == []


@pytest.mark.parametrize(
    "nome",
    [
        "abc.Tron [id].f251.webm",
        "abc.Tron [id].f616.mp4",
        "abc.Tron [id].temp.mp4",
        "abc.Tron [id].mp4.part",
        "abc.Tron [id].mp4.ytdl",
        "abc.Tron [id].mp4.part-Frag1",
    ],
)
def test_eh_fragmento_reconhece_sobra(nome):
    assert nucleo.eh_fragmento(nome)


@pytest.mark.parametrize("nome", ["abc.Tron [id].mp4", "abc.Musica [id].mp3", "video.f.mp4"])
def test_eh_fragmento_nao_marca_arquivo_bom(nome):
    assert not nucleo.eh_fragmento(nome)


def test_varrer_sobras_apaga_fragmento_e_preserva_o_resto(tmp_path):
    bom = tmp_path / "job1.video [x].mp4"
    frag = tmp_path / "job1.video [x].f251.webm"
    de_outro = tmp_path / "job2.outro [y].f140.m4a"
    for p in (bom, frag, de_outro):
        p.write_bytes(b"x")

    nucleo._varrer_sobras(tmp_path, "job1", {bom.name})

    assert bom.exists()
    assert not frag.exists()
    assert de_outro.exists(), "não pode encostar em arquivo de outro trabalho"


def test_sem_prefixo_tira_o_job_do_nome(tmp_path):
    arquivo = tmp_path / "job1.Um vídeo [x].mp4"
    arquivo.write_bytes(b"x")
    assert nucleo._sem_prefixo(arquivo, "job1").name == "Um vídeo [x].mp4"


def test_sem_prefixo_nao_atropela_arquivo_existente(tmp_path):
    (tmp_path / "Um vídeo [x].mp4").write_bytes(b"antigo")
    novo = tmp_path / "job1.Um vídeo [x].mp4"
    novo.write_bytes(b"novo")

    destino = nucleo._sem_prefixo(novo, "job1")

    assert destino.name == "Um vídeo [x] (2).mp4"
    assert (tmp_path / "Um vídeo [x].mp4").read_bytes() == b"antigo"


def test_sem_prefixo_ignora_nome_de_outro_job(tmp_path):
    arquivo = tmp_path / "job2.Um vídeo [x].mp4"
    assert nucleo._sem_prefixo(arquivo, "job1") == arquivo


# ─────────────────────────────────────────────────────────── nome de arquivo ──

@pytest.mark.parametrize("nome", ["../segredo.txt", "..\\segredo.txt", "/etc/passwd", "C:\\x", "", ".."])
def test_nome_seguro_barra_travessia(nome):
    assert nucleo.nome_seguro(nome) is None


def test_nome_seguro_aceita_nome_comum():
    assert nucleo.nome_seguro("abc.Um vídeo [x1].mp4") == "abc.Um vídeo [x1].mp4"


# ───────────────────────────────────────────────────────────── opções do ydl ──

def test_opcoes_de_video_pedem_mp4_e_um_item_so(tmp_path):
    opts = nucleo._opcoes("job1", "video", playlist=False, pasta=tmp_path)
    assert opts["merge_output_format"] == "mp4"
    assert opts["noplaylist"] is True
    assert opts["ignoreerrors"] is False
    assert opts["outtmpl"].startswith(str(tmp_path))
    assert "playlist_index" not in opts["outtmpl"]


def test_opcoes_de_playlist_numeram_e_toleram_item_quebrado(tmp_path):
    opts = nucleo._opcoes("job1", "video", playlist=True, pasta=tmp_path)
    assert opts["noplaylist"] is False
    assert opts["ignoreerrors"] is True
    assert "playlist_index" in opts["outtmpl"]


def test_opcoes_de_mp3_pedem_o_pos_processador(tmp_path):
    opts = nucleo._opcoes("job1", "mp3", playlist=False, pasta=tmp_path)
    assert opts["postprocessors"][0]["key"] == "FFmpegExtractAudio"
    assert opts["postprocessors"][0]["preferredcodec"] == "mp3"


def test_opcoes_nao_compartilham_o_pos_processador_entre_jobs(tmp_path):
    a = nucleo._opcoes("job1", "mp3", playlist=False, pasta=tmp_path)
    b = nucleo._opcoes("job2", "mp3", playlist=False, pasta=tmp_path)
    a["postprocessors"][0]["preferredquality"] = "64"
    assert b["postprocessors"][0]["preferredquality"] == "192"


def test_todo_modo_da_interface_tem_rotulo_e_formato():
    for chave, receita in nucleo.MODOS.items():
        assert receita["rotulo"], chave
        assert receita["format"], chave


# ─────────────────────────────────────────────────────────── ciclo do trabalho ──

def test_job_nasce_zerado_e_e_lido_por_copia():
    job_id = nucleo.criar_job("https://exemplo/x", "video")
    job = nucleo.ler_job(job_id)
    assert job["status"] == "iniciando"
    assert job["pct"] == 0.0
    job["status"] = "mexido"
    assert nucleo.ler_job(job_id)["status"] == "iniciando", "ler_job devolve cópia"


def test_ler_job_desconhecido_e_none():
    assert nucleo.ler_job("nao-existe") is None


def test_cancelar_marca_e_nao_cancela_duas_vezes():
    job_id = nucleo.criar_job("https://exemplo/x", "video")
    assert nucleo.cancelar_job(job_id) is True
    nucleo._atualizar(job_id, status="cancelado", terminou_em=nucleo._agora())
    assert nucleo.cancelar_job(job_id) is False


def test_gancho_de_progresso_calcula_porcentagem_e_velocidade():
    job_id = nucleo.criar_job("https://exemplo/x", "video")
    gancho = nucleo._gancho_progresso(job_id)
    gancho(
        {
            "status": "downloading",
            "downloaded_bytes": 512,
            "total_bytes": 2048,
            "speed": 1024,
            "eta": 12,
            "info_dict": {"title": "Um vídeo"},
        }
    )
    job = nucleo.ler_job(job_id)
    assert job["pct"] == 25.0
    assert job["status"] == "baixando"
    assert job["velocidade"] == 1024
    assert job["eta"] == 12
    assert job["titulo"] == "Um vídeo"


def test_gancho_de_progresso_aborta_quando_cancelado():
    job_id = nucleo.criar_job("https://exemplo/x", "video")
    gancho = nucleo._gancho_progresso(job_id)
    nucleo.cancelar_job(job_id)
    with pytest.raises(nucleo.CanceladoPeloUsuario):
        gancho({"status": "downloading", "downloaded_bytes": 1, "total_bytes": 2})


def test_job_vencido_e_esquecido():
    job_id = nucleo.criar_job("https://exemplo/x", "video")
    nucleo._atualizar(
        job_id, status="concluido", terminou_em=nucleo._agora() - nucleo.VALIDADE_JOB_S - 1
    )
    nucleo.criar_job("https://exemplo/y", "video")  # criar dispara a faxina
    assert nucleo.ler_job(job_id) is None
