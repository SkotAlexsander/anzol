const $ = (id) => document.getElementById(id);

const elUrl = $("url");
const elBtnBuscar = $("btnBuscar");
const elPrevia = $("previa");
const elMiniatura = $("miniatura");
const elTitulo = $("titulo");
const elMeta = $("meta");
const elBtnVideo = $("btnVideo");
const elBtnAudio = $("btnAudio");
const elProgresso = $("progresso");
const elBarraFill = $("barraFill");
const elProgressoTexto = $("progressoTexto");
const elErro = $("erro");

function mostrarErro(msg) {
  elErro.textContent = msg;
  elErro.classList.remove("oculto");
}

function limparErro() {
  elErro.classList.add("oculto");
  elErro.textContent = "";
}

function formatarDuracao(segundos) {
  if (!segundos) return "";
  const h = Math.floor(segundos / 3600);
  const m = Math.floor((segundos % 3600) / 60);
  const s = Math.floor(segundos % 60);
  const pad = (n) => String(n).padStart(2, "0");
  return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${m}:${pad(s)}`;
}

async function buscar() {
  const url = elUrl.value.trim();
  limparErro();
  elPrevia.classList.add("oculto");
  elProgresso.classList.add("oculto");
  if (!url) {
    mostrarErro("Cole um link primeiro.");
    return;
  }

  elBtnBuscar.disabled = true;
  elBtnBuscar.textContent = "Buscando…";
  try {
    const resp = await fetch("/api/info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const dados = await resp.json();
    if (!resp.ok) throw new Error(dados.erro || "Não consegui buscar esse link.");

    elMiniatura.src = dados.miniatura || "";
    elTitulo.textContent = dados.titulo;
    elMeta.textContent = [dados.site, formatarDuracao(dados.duracao)].filter(Boolean).join(" · ");
    elPrevia.classList.remove("oculto");
  } catch (e) {
    mostrarErro(e.message);
  } finally {
    elBtnBuscar.disabled = false;
    elBtnBuscar.textContent = "Buscar";
  }
}

async function baixar(modo) {
  const url = elUrl.value.trim();
  limparErro();
  elBtnVideo.disabled = true;
  elBtnAudio.disabled = true;
  elProgresso.classList.remove("oculto");
  elBarraFill.style.width = "0%";
  elProgressoTexto.textContent = "Iniciando…";

  try {
    const resp = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url, modo }),
    });
    const dados = await resp.json();
    if (!resp.ok) throw new Error(dados.erro || "Não consegui iniciar o download.");

    await acompanhar(dados.job_id);
  } catch (e) {
    mostrarErro(e.message);
    elProgresso.classList.add("oculto");
  } finally {
    elBtnVideo.disabled = false;
    elBtnAudio.disabled = false;
  }
}

function acompanhar(jobId) {
  return new Promise((resolve, reject) => {
    const intervalo = setInterval(async () => {
      try {
        const resp = await fetch(`/api/status/${jobId}`);
        const job = await resp.json();
        if (!resp.ok) throw new Error(job.erro || "job perdido");

        elBarraFill.style.width = `${job.pct || 0}%`;

        if (job.status === "baixando") {
          elProgressoTexto.textContent = `Baixando… ${job.pct || 0}%`;
        } else if (job.status === "processando") {
          elProgressoTexto.textContent = "Processando (convertendo/juntando áudio e vídeo)…";
        } else if (job.status === "concluido") {
          clearInterval(intervalo);
          elProgressoTexto.textContent = "Concluído — baixando arquivo…";
          window.location.href = `/downloads/${encodeURIComponent(job.filename)}`;
          resolve();
        } else if (job.status === "erro") {
          clearInterval(intervalo);
          reject(new Error(job.erro || "Falha no download."));
        }
      } catch (e) {
        clearInterval(intervalo);
        reject(e);
      }
    }, 800);
  });
}

elBtnBuscar.addEventListener("click", buscar);
elUrl.addEventListener("keydown", (e) => { if (e.key === "Enter") buscar(); });
elBtnVideo.addEventListener("click", () => baixar("video"));
elBtnAudio.addEventListener("click", () => baixar("audio"));
