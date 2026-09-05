# Anzol

Baixador de vídeo e áudio que roda na sua máquina, com janela própria. Cola o link,
escolhe a qualidade, o arquivo cai numa pasta. Por baixo é o
[yt-dlp](https://github.com/yt-dlp/yt-dlp) — os mesmos milhares de sites que ele
suporta, sem a linha de comando.

Python + Flask + pywebview. Sem conta, sem servidor, sem telemetria: o que sai da sua
máquina é o pedido ao site do vídeo, e nada mais.

![feito com Python](https://img.shields.io/badge/Python-3.10%2B-4f7cff)
![licença MIT](https://img.shields.io/badge/licen%C3%A7a-MIT-38c172)

---

## O que ele faz

- **Prévia antes de baixar** — título, miniatura, duração e de que site veio.
- **Qualidade à escolha** — melhor disponível, 1080p, 720p, 480p, MP3 192kbps ou o
  áudio original sem reconverter.
- **Playlist inteira** — quando o link é de playlist, ele avisa quantos itens tem e
  deixa você decidir entre só aquele vídeo ou a lista toda, numerada em ordem.
- **Progresso de verdade** — porcentagem, tamanho, velocidade e quanto falta.
- **Cancelar no meio** — para o download e apaga os pedaços incompletos.
- **A pasta do lado** — lista o que já foi baixado, com link, tamanho, botão de apagar
  e um atalho para abrir a pasta no explorador de arquivos.
- **Erro em português** — "Vídeo privado", "Vídeo bloqueado no seu país", "O site pediu
  para desacelerar" no lugar do despejo técnico do yt-dlp.

## Como rodar

```bash
pip install -r requirements.txt

python desktop.py     # janela própria (no Windows: pythonw desktop.py, sem console)
python app.py         # ou no navegador, em http://127.0.0.1:8137
```

No Windows há também o **`Anzol.cmd`**: duplo clique e pronto.

O `ffmpeg` precisa estar no PATH para MP4 e MP3 — é ele que junta a faixa de vídeo com
a de áudio e que converte para MP3. Sem ffmpeg o app continua funcionando, só que a
interface esconde essas opções e deixa o áudio original (M4A), que não precisa dele.

Os arquivos vão para `downloads/`, ao lado do código. A porta padrão é a `8137` e sai
da variável `ANZOL_PORTA`; se ela estiver ocupada, o app pega outra livre em vez de
morrer com traceback.

## Requisitos

- Python 3.10 ou mais novo
- `pip install -r requirements.txt` → `flask`, `yt-dlp`, `pywebview`
- `ffmpeg` no PATH (opcional, mas é o que libera MP4 e MP3)
- No Windows, o `pywebview` usa o **Edge WebView2**, que já vem com Windows 10/11
  atualizado

## Testes

```bash
pip install pytest
pytest testes -q
```

São 67 testes e nenhum toca a rede: eles cobrem formatação, a tradução dos erros do
yt-dlp, a escolha do arquivo final, a limpeza de fragmentos, a validação das rotas e o
portão que recusa pedido de fora do loopback.

## Como é por dentro

```text
nucleo.py     o motor: fila de trabalhos, opções do yt-dlp, tradução de erro
app.py        a casca HTTP: rotas, validação, o portão do loopback
desktop.py    a janela nativa em cima do mesmo Flask
static/       a interface (HTML, CSS e JS puros — sem framework, sem build)
testes/       pytest
```

Três decisões que valem explicação:

**O arquivo final vem do yt-dlp, não de um `glob()`.** Num merge o yt-dlp deixa
`vídeo.f251.webm` e `vídeo.f616.mp4` ao lado do `.mp4` pronto. Procurar por nome pode
entregar o fragmento no lugar do vídeo — é o que acontecia antes. Agora o app lê
`requested_downloads` do próprio yt-dlp, que diz o que de fato ficou pronto, e varre as
sobras depois.

**Cada trabalho nasce com um prefixo no nome e perde o prefixo no fim.** Durante o
download o prefixo é o que deixa a faxina saber o que é deste trabalho e o que é de
outro rodando ao mesmo tempo; quando termina, o arquivo é renomeado para o nome limpo
(e ganha `(2)` se já existir um igual, em vez de sobrescrever).

**O servidor só atende o loopback.** Confere o endereço de origem e o cabeçalho `Host`
— o segundo bloqueia o truque de apontar um domínio de fora para 127.0.0.1. É um app de
uma máquina só; não foi feito para ficar exposto na rede, e o servidor de
desenvolvimento do Flask não é o servidor certo para isso.

## Limites conhecidos

- Cancelar durante a **extração** (antes do primeiro byte) só tem efeito quando o
  download começa — o yt-dlp não oferece ponto de interrupção nessa fase. São alguns
  segundos, não trava.
- Site com paywall, DRM ou que exija login não foi testado. Vídeo com restrição de
  idade tende a falhar sem cookies.
- Playlist com item quebrado continua: o item falha, o resto baixa.
- Nada é apagado sozinho da pasta `downloads/`.

## Licença e crédito

Código sob licença MIT. O trabalho pesado é do
[yt-dlp](https://github.com/yt-dlp/yt-dlp) (Unlicense) — este projeto é só a interface.

Baixar conteúdo protegido por direito autoral sem permissão é problema de quem baixa,
não da ferramenta. Respeite os termos de uso de cada site.
