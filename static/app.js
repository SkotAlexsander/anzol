const $ = (id) => document.getElementById(id);

const el = {
  form: $("formBusca"),
  url: $("url"),
  btnBuscar: $("btnBuscar"),
  avisoFfmpeg: $("avisoFfmpeg"),
  previa: $("previa"),
  miniatura: $("miniatura"),
  titulo: $("titulo"),
  meta: $("meta"),
  rotuloPlaylist: $("rotuloPlaylist"),
  chkPlaylist: $("chkPlaylist"),
  textoPlaylist: $("textoPlaylist"),
  modo: $("modo"),
  btnBaixar: $("btnBaixar"),
  progresso: $("progresso"),
  barraFill: $("barraFill"),
  progressoTexto: $("progressoTexto"),
  btnCancelar: $("btnCancelar"),
  erro: $("erro"),
  secaoArquivos: $("secaoArquivos"),
  listaArquivos: $("listaArquivos"),
  btnPasta: $("btnPasta"),
  rodapeInfo: $("rodapeInfo"),
};

const CHAVE_MODO = "anzol:modo";
let jobAtual = null;
let temFfmpeg = true;

// ───────────────────────────────────────────────────────────────── ajudantes ──

async function api(caminho, opcoes = {}) {
  const resp = await fetch(caminho, {
    headers: { "Content-Type": "application/json" },
    ...opcoes,
  });
  let dados = {};
  try {
    dados = await resp.json();
  } catch {
    throw new Error("O app respondeu algo que não é JSON. Ele ainda está rodando?");
  }
  if (!resp.ok) throw new Error(dados.erro || "Deu errado e o app não disse por quê.");
  return dados;
}

const postar = (caminho, corpo) =>
  api(caminho, { method: "POST", body: JSON.stringify(corpo || {}) });

function mostrarErro(msg) {
  el.erro.textContent = msg;
  el.erro.classList.remove("oculto");
}

function limparErro() {
  el.erro.classList.add("oculto");
  el.erro.textContent = "";
}

function formatarDuracao(segundos) {
  if (!segundos) return "";
  const h = Math.floor(segundos / 3600);
  const m = Math.floor((segundos % 3600) / 60);
  const s = Math.floor(segundos % 60);
  const pad = (n) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

function formatarBytes(n) {
  if (!n) return "";
  const u = ["B", "KB", "MB", "GB", "TB"];
  let i = 0;
  let v = n;
  while (v >= 1024 && i < u.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(i === 0 ? 0 : 1).replace(".", ",")} ${u[i]}`;
}

function formatarEta(segundos) {
  if (segundos === null || segundos === undefined) return "";
  if (segundos < 60) return `${Math.round(segundos)}s`;
  const m = Math.floor(segundos / 60);
  const s = Math.round(segundos % 60);
  return `${m}min ${String(s).padStart(2, "0")}s`;
}

// ─────────────────────────────────────────────────────────────────── arranque ──

async function carregarSaude() {
  try {
    const saude = await api("/api/saude");
    temFfmpeg = saude.ffmpeg;
    el.avisoFfmpeg.classList.toggle("oculto", temFfmpeg);

    const salvo = localStorage.getItem(CHAVE_MODO);
    el.modo.innerHTML = "";
    for (const m of saude.modos) {
      if (m.precisaFfmpeg && !temFfmpeg) continue;
      const opcao = document.createElement("option");
      opcao.value = m.id;
      opcao.textContent = m.rotulo;
      el.modo.appendChild(opcao);
    }
    if (salvo && [...el.modo.options].some((o) => o.value === salvo)) el.modo.value = salvo;

    el.rodapeInfo.textContent = `yt-dlp ${saude.ytdlp} · ${saude.pasta}`;
  } catch (e) {
    mostrarErro(e.message);
  }
}

async function carregarArquivos() {
  try {
    const { arquivos } = await api("/api/arquivos");
    el.secaoArquivos.classList.toggle("oculto", arquivos.length === 0);
    el.listaArquivos.innerHTML = "";

    for (const arq of arquivos) {
      const item = document.createElement("li");

      const link = document.createElement("a");
      link.href = `/downloads/${encodeURIComponent(arq.nome)}`;
      link.textContent = arq.nome;
      link.title = arq.nome;

      const tamanho = document.createElement("span");
      tamanho.className = "tamanho";
      tamanho.textContent = formatarBytes(arq.tamanho);

      const apagar = document.createElement("button");
      apagar.className = "link perigo";
      apagar.type = "button";
      apagar.textContent = "apagar";
      apagar.addEventListener("click", async () => {
        if (!confirm(`Apagar "${link.textContent}" do disco?`)) return;
        try {
          await postar("/api/apagar", { nome: arq.nome });
          await carregarArquivos();
        } catch (e) {
          mostrarErro(e.message);
        }
      });

      item.append(link, tamanho, apagar);
      el.listaArquivos.appendChild(item);
    }
  } catch (e) {
    mostrarErro(e.message);
  }
}

// ────────────────────────────────────────────────────────────────────── busca ──

async function buscar(evento) {
  evento?.preventDefault();
  const url = el.url.value.trim();
  limparErro();
  el.previa.classList.add("oculto");
  el.progresso.classList.add("oculto");
  if (!url) return mostrarErro("Cole um link primeiro.");

  el.btnBuscar.disabled = true;
  el.btnBuscar.textContent = "Buscando…";
  try {
    const dados = await postar("/api/info", { url });

    el.miniatura.hidden = !dados.miniatura;
    if (dados.miniatura) el.miniatura.src = dados.miniatura;
    el.titulo.textContent = dados.titulo;
    el.meta.textContent = [
      dados.site,
      formatarDuracao(dados.duracao),
      dados.aoVivo ? "ao vivo" : "",
    ]
      .filter(Boolean)
      .join(" · ");

    if (dados.playlist) {
      el.rotuloPlaylist.classList.remove("oculto");
      el.textoPlaylist.textContent = `Baixar a playlist inteira — ${dados.playlist.total} itens`;
      el.chkPlaylist.checked = false;
    } else {
      el.rotuloPlaylist.classList.add("oculto");
      el.chkPlaylist.checked = false;
    }

    el.previa.classList.remove("oculto");
  } catch (e) {
    mostrarErro(e.message);
  } finally {
    el.btnBuscar.disabled = false;
    el.btnBuscar.textContent = "Buscar";
  }
}

// ───────────────────────────────────────────────────────────────────── baixar ──

function textoDoProgresso(job) {
  const partes = [];
  if (job.itens && job.itens > 1) partes.push(`item ${job.item || 1}/${job.itens}`);

  if (job.status === "baixando") {
    partes.push(`${job.pct || 0}%`);
    if (job.total) partes.push(`${formatarBytes(job.baixado)} de ${formatarBytes(job.total)}`);
    if (job.velocidade) partes.push(`${formatarBytes(job.velocidade)}/s`);
    if (job.eta) partes.push(`faltam ${formatarEta(job.eta)}`);
    return `Baixando… ${partes.join(" · ")}`;
  }
  if (job.status === "processando") return "Convertendo e juntando áudio com vídeo…";
  if (job.status === "cancelando") return "Cancelando…";
  return "Iniciando…";
}

function acompanhar(jobId) {
  return new Promise((resolve, reject) => {
    const relogio = setInterval(async () => {
      try {
        const job = await api(`/api/status/${jobId}`);
        el.barraFill.style.width = `${job.pct || 0}%`;
        el.progressoTexto.textContent = textoDoProgresso(job);

        if (job.status === "concluido") {
          clearInterval(relogio);
          const n = job.arquivos.length;
          el.progressoTexto.textContent =
            n === 1 ? "Pronto — está na pasta e na lista abaixo." : `Pronto — ${n} arquivos.`;
          el.barraFill.classList.add("pronto");
          resolve(job);
        } else if (job.status === "cancelado") {
          clearInterval(relogio);
          el.progresso.classList.add("oculto");
          resolve(job);
        } else if (job.status === "erro") {
          clearInterval(relogio);
          reject(new Error(job.erro || "Falhou no meio do caminho."));
        }
      } catch (e) {
        clearInterval(relogio);
        reject(e);
      }
    }, 700);
  });
}

async function baixar() {
  const url = el.url.value.trim();
  const modo = el.modo.value;
  limparErro();
  localStorage.setItem(CHAVE_MODO, modo);

  el.btnBaixar.disabled = true;
  el.btnCancelar.hidden = false;
  el.progresso.classList.remove("oculto");
  el.barraFill.classList.remove("pronto");
  el.barraFill.style.width = "0%";
  el.progressoTexto.textContent = "Iniciando…";

  try {
    const { job_id } = await postar("/api/download", {
      url,
      modo,
      playlist: el.chkPlaylist.checked,
    });
    jobAtual = job_id;
    await acompanhar(job_id);
    await carregarArquivos();
  } catch (e) {
    mostrarErro(e.message);
    el.progresso.classList.add("oculto");
  } finally {
    jobAtual = null;
    el.btnBaixar.disabled = false;
    el.btnCancelar.hidden = true;
  }
}

async function cancelar() {
  if (!jobAtual) return;
  try {
    await postar(`/api/cancelar/${jobAtual}`);
    el.progressoTexto.textContent = "Cancelando…";
  } catch (e) {
    mostrarErro(e.message);
  }
}

// ─────────────────────────────────────────────────────────────────────── liga ──

el.form.addEventListener("submit", buscar);
el.btnBaixar.addEventListener("click", baixar);
el.btnCancelar.addEventListener("click", cancelar);
el.btnPasta.addEventListener("click", () => postar("/api/abrir-pasta").catch((e) => mostrarErro(e.message)));

el.btnCancelar.hidden = true;
carregarSaude();
carregarArquivos();
