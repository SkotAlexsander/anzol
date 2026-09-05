# Baixador de Vídeo

App web local que usa o [yt-dlp](https://github.com/yt-dlp/yt-dlp) (instalado via
PyPI — o mesmo projeto que estava em `A:\Programas\yt-dlp-master`, só que pelo canal
oficial em vez de compilar a pasta baixada) pra baixar vídeo ou áudio de milhares de
sites, com uma interface simples no navegador.

## O que é o `yt-dlp`

Downloader de vídeo/áudio de linha de comando, código aberto (Unlicense), fork
mantido do `youtube-dl`. Suporta YouTube e milhares de outros sites
(ver `supportedsites.md` no repo original). Não tem nada suspeito no código —
mantenedores reais, release assinada com chave pública própria.

## Como rodar

**App de desktop (recomendado)** — janela própria, sem navegador, sem console:

- Atalho na Área de Trabalho: **`Baixador de Vídeo.lnk`** — dá duplo clique.
- Ou manualmente: `pythonw desktop.py` (usa `pythonw`, não `python`, pra não abrir console).

Sobe o mesmo Flask numa thread em segundo plano e abre a interface numa janela nativa
(`pywebview`, motor Edge WebView2 no Windows). Fecha a janela → o processo encerra e a
porta libera sozinha.

**Modo navegador** (debug ou se preferir uma aba):

```bat
cd 10-projetos\baixador-video
python app.py
```

Abre em **http://127.0.0.1:8137**.

## Como usar

1. Cola o link do vídeo → **Buscar** (mostra título, miniatura e duração).
2. **Baixar vídeo (MP4)** — junta a melhor faixa de vídeo + áudio via `ffmpeg`.
3. **Baixar áudio (MP3)** — extrai só o áudio, 192kbps.
4. Barra de progresso acompanha em tempo real; ao terminar, o navegador baixa
   o arquivo sozinho.

## Dependências

- Python 3.12 (já instalado nesta máquina)
- `pip install flask yt-dlp pywebview` (já feito)
- `ffmpeg` no PATH (já instalado — 8.1.2, usado pela skill `transcrever-audio`)
- Windows: `pywebview` usa o **Edge WebView2**, que já vem com o Windows 10/11 atualizado

## Limitações conhecidas

- Servidor de desenvolvimento do Flask (`debug=False`), pensado pra uso local,
  não pra expor na internet.
- Um job de download por vez por navegador; downloads concorrentes de vários
  usuários funcionam (cada um tem seu `job_id`), mas não há fila nem limite —
  não é feito pra multiusuário sério.
- Arquivos ficam em `downloads/` (fora do git) e não são apagados sozinhos.
- Não testado contra sites com paywall/DRM nem geo-bloqueio.
