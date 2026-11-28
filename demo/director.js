/* Director de la demo NextGen DevSecOps: reloj con pausa y velocidad, subtítulos, foco, lupa, cursor,
   slides y barra de control. Lo inyecta el runner con add_init_script; vive en un único shadow root
   abierto colgado de <html>, así la consola no cambia. Los estilos llegan en window.__DIRECTOR_CSS. */
(() => {
  "use strict";
  if (window.top !== window || window.__director) return;

  const VELOCIDADES = [0.75, 1, 1.25];
  const EXPO = "cubic-bezier(0.16, 1, 0.3, 1)";
  const RESERVA_ABAJO = 196; // franja inferior para subtítulos y barra
  const reducido = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

  const est = {
    activo: false,
    velocidad: 1,
    pausado: false,
    pasoAPaso: false,
    accionando: false,
    terminado: false,
    escenas: [],
    indice: -1,
    frontera: false,
    total: 0,
  };
  const ui = {};

  /* ---------- Reloj: tiempo de contenido que solo corre sin pausa ---------- */
  const reloj = { timers: new Set(), handle: 0, ultimo: performance.now(), transcurrido: 0, escenaDesde: 0, tic: 0 };

  function avanzar() {
    const ahora = performance.now();
    if (!est.pausado) {
      const dt = (ahora - reloj.ultimo) / 1000;
      reloj.transcurrido += dt;
      for (const t of reloj.timers) t.restante -= dt * est.velocidad;
    }
    reloj.ultimo = ahora;
  }

  function programar() {
    clearTimeout(reloj.handle);
    if (est.pausado || !reloj.timers.size) return;
    let menor = Infinity;
    for (const t of reloj.timers) menor = Math.min(menor, t.restante);
    reloj.handle = setTimeout(vencer, Math.max(0, (menor / est.velocidad) * 1000));
  }

  function vencer() {
    avanzar();
    for (const t of [...reloj.timers]) if (t.restante <= 0.001) cerrarTimer(t);
    programar();
  }

  function cerrarTimer(t) {
    if (reloj.timers.delete(t)) t.resolver();
  }

  // Espera `segundos` de contenido: a 1,25× pasa en 0,8 s reales por segundo y en pausa no avanza.
  function temporizador(segundos) {
    avanzar();
    const t = { restante: Math.max(0, segundos), resolver: null };
    t.promesa = new Promise((r) => { t.resolver = r; });
    t.cortar = () => { cerrarTimer(t); programar(); };
    t.ajustar = (delta) => { avanzar(); t.restante += delta; programar(); };
    reloj.timers.add(t);
    programar();
    return t;
  }
  const pausa = (segundos) => temporizador(segundos).promesa;

  const esperasDePausa = [];
  const sinPausa = () => (est.pausado && !est.terminado ? new Promise((r) => esperasDePausa.push(r)) : Promise.resolve());

  /* ---------- Estado público y eventos hacia Python ---------- */
  function estadoPublico() {
    avanzar();
    return {
      velocidad: est.velocidad,
      pausado: est.pausado,
      pasoAPaso: est.pasoAPaso,
      terminado: est.terminado,
      transcurrido_s: Math.round(reloj.transcurrido * 1000) / 1000,
    };
  }

  function emitir(tipo) {
    const fn = window.__demoEvento;
    if (typeof fn !== "function") return;
    try {
      Promise.resolve(fn({ tipo, ...estadoPublico() })).catch(() => {});
    } catch {
      /* el runner ya no escucha */
    }
  }

  function fijarPausa(valor) {
    if (est.pausado === valor) return;
    avanzar();
    est.pausado = valor;
    reloj.ultimo = performance.now();
    if (linea && linea.clip) {
      if (valor) linea.clip.pause();
      else linea.clip.play().catch(linea.degradar);
    }
    programar();
    if (!valor) esperasDePausa.splice(0).forEach((r) => r());
    ui.host?.toggleAttribute("data-pausado", valor);
    pintarBarra();
    emitir("estado");
  }

  function fijarVelocidad(v) {
    if (!(v > 0) || v === est.velocidad) return;
    avanzar();
    est.velocidad = v;
    reloj.ultimo = performance.now();
    if (linea && linea.clip) linea.clip.playbackRate = v;
    ui.host?.style.setProperty("--v", String(v));
    programar();
    pintarBarra();
    emitir("estado");
  }

  // Fuera del menú (el ensayo corre a 6×) la primera pulsación vuelve a una velocidad del menú.
  function pasoVelocidad(dir) {
    const v = est.velocidad;
    const i = VELOCIDADES.indexOf(v);
    let destino;
    if (i >= 0) destino = VELOCIDADES[Math.min(VELOCIDADES.length - 1, Math.max(0, i + dir))];
    else if (dir > 0) destino = VELOCIDADES.find((x) => x > v) ?? VELOCIDADES[VELOCIDADES.length - 1];
    else destino = [...VELOCIDADES].reverse().find((x) => x < v) ?? VELOCIDADES[0];
    fijarVelocidad(destino);
  }

  function alternarPaso() {
    est.pasoAPaso = !est.pasoAPaso;
    if (!est.pasoAPaso && liberarFrontera) siguiente();
    pintarBarra();
    emitir("estado");
  }

  let armadoTerminar = -Infinity;
  function pedirTerminar() {
    const ahora = performance.now();
    if (ahora - armadoTerminar > 2500) {
      armadoTerminar = ahora;
      aviso("Pulsa Q otra vez para terminar la demo");
      return;
    }
    armadoTerminar = -Infinity;
    est.terminado = true;
    aviso("Terminando la demo y restaurando el entorno…");
    emitir("terminar");
    // Python puede estar esperando un turno en pausa, una frontera o una línea: se libera todo.
    esperasDePausa.splice(0).forEach((r) => r());
    if (liberarFrontera) {
      const liberar = liberarFrontera;
      liberarFrontera = null;
      liberar();
    }
    if (corte) corte.terminar();
    if (linea) linea.terminar();
  }

  /* ---------- Líneas, esperas y «Siguiente» ---------- */
  let linea = null; // la línea que suena: {clip, respaldo, terminar, degradar}
  let corte = null; // lo que «Siguiente» corta: la línea o el esperar en curso
  let liberarFrontera = null;

  function decir(texto, url, duracion) {
    montar();
    if (est.terminado) return Promise.resolve();
    if (linea) linea.terminar();
    if (!url) mostrarSubtitulo(String(texto ?? "")); // con voz, solo la voz
    const dur = Math.max(0, Number(duracion) || 0);
    return new Promise((resolver) => {
      const actual = { clip: null, respaldo: temporizador(url ? dur + 2 : dur), degradar: () => {} };
      let hecho = false;
      actual.terminar = () => {
        if (hecho) return;
        hecho = true;
        actual.respaldo.cortar();
        const clip = actual.clip;
        actual.clip = null;
        if (clip) {
          clip.pause();
          clip.removeAttribute("src");
          clip.load();
        }
        if (linea === actual) linea = null;
        if (corte === actual) corte = null;
        retirarSubtitulo();
        resolver();
      };
      actual.respaldo.promesa.then(actual.terminar);
      if (url) {
        const clip = new Audio(url);
        clip.preservesPitch = true;
        clip.playbackRate = est.velocidad;
        // Sin audio (404, formato o autoplay bloqueado) la línea dura lo que dice el guion.
        actual.degradar = () => {
          if (hecho || !actual.clip) return;
          actual.clip = null;
          actual.respaldo.ajustar(-2);
          mostrarSubtitulo(String(texto ?? "")); // sin audio, que la línea no quede muda
        };
        clip.addEventListener("ended", actual.terminar);
        clip.addEventListener("error", actual.degradar);
        actual.clip = clip;
        if (!est.pausado) clip.play().catch(actual.degradar);
      }
      linea = actual;
      corte = actual;
    });
  }

  function esperar(ms) {
    if (est.terminado) return Promise.resolve();
    const t = temporizador((Math.max(0, Number(ms) || 0)) / 1000);
    const propio = { terminar: t.cortar };
    corte = propio;
    return t.promesa.then(() => {
      if (corte === propio) corte = null;
    });
  }

  function siguiente() {
    if (liberarFrontera) {
      const liberar = liberarFrontera;
      liberarFrontera = null;
      liberar();
      return;
    }
    if (corte) corte.terminar();
  }

  async function turno() {
    montar();
    accionar(false);
    const enfocado = document.activeElement;
    // Que Espacio, N o Q del presentador no acaben escritos en la nota que el guion acaba de teclear.
    if (esEditable(enfocado)) enfocado.blur();
    await sinPausa();
    if (est.terminado || !est.frontera) return;
    est.frontera = false;
    if (!est.pasoAPaso) return;
    await new Promise((r) => {
      liberarFrontera = r;
      pintarBarra();
    });
    pintarBarra();
    await sinPausa();
  }

  function escena(indice) {
    montar();
    avanzar();
    est.indice = Number(indice);
    reloj.escenaDesde = reloj.transcurrido;
    est.frontera = est.indice > 0;
    pintarBarra();
  }

  function iniciar({ escenas = [], velocidad = 1, pasoAPaso = false, total_s = 0 } = {}) {
    montar();
    est.escenas = escenas.map((e) => ({ id: e.id, titulo: e.titulo || e.id, dur: Number(e.dur_s) || 0 }));
    est.velocidad = Number(velocidad) > 0 ? Number(velocidad) : 1;
    est.pasoAPaso = Boolean(pasoAPaso);
    est.pausado = false;
    est.terminado = false;
    est.indice = -1;
    est.frontera = false;
    est.total = total_s;
    reloj.transcurrido = 0;
    reloj.escenaDesde = 0;
    reloj.ultimo = performance.now();
    est.activo = true;
    ui.host.style.setProperty("--v", String(est.velocidad));
    ui.host.removeAttribute("data-pausado");
    construirMarcas();
    mostrarBarra();
    clearInterval(reloj.tic);
    reloj.tic = setInterval(pintarProgreso, 500);
    return estadoPublico();
  }

  function total(valor) {
    est.total = valor;
    pintarProgreso();
  }

  function totalActual() {
    const t = est.total;
    if (typeof t === "number") return t;
    if (t && typeof t === "object") return Number(t[String(est.velocidad)] ?? t["1"] ?? Object.values(t)[0]) || 0;
    return 0;
  }

  /* ---------- Teclado: fase de captura; los campos de texto quedan para quien escribe ---------- */
  const TEXTO = new Set(["text", "search", "email", "number", "password", "tel", "url", "date", "datetime-local", "month", "time", "week"]);
  function esEditable(el) {
    if (!el || el.nodeType !== 1) return false;
    if (el.isContentEditable) return true;
    return el.tagName === "TEXTAREA" || (el.tagName === "INPUT" && TEXTO.has(el.type));
  }

  const alternarPausa = () => fijarPausa(!est.pausado);
  const TECLAS = {
    " ": alternarPausa, k: alternarPausa, K: alternarPausa,
    ArrowRight: siguiente, n: siguiente, N: siguiente,
    "<": () => pasoVelocidad(-1), "-": () => pasoVelocidad(-1),
    ">": () => pasoVelocidad(1), "+": () => pasoVelocidad(1),
    p: alternarPaso, P: alternarPaso,
    q: pedirTerminar, Q: pedirTerminar,
  };

  window.addEventListener("keydown", (e) => {
    if (!est.activo || e.metaKey || e.ctrlKey || e.altKey) return;
    const accion = TECLAS[e.key];
    if (!accion || esEditable(e.composedPath()[0])) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    if (!e.repeat) accion();
  }, true);

  window.addEventListener("mousemove", () => {
    if (est.activo && !est.accionando) mostrarBarra();
  }, { capture: true, passive: true });

  /* ---------- Montaje del shadow root ---------- */
  const MONOGRAMA = '<svg class="monograma" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="7" fill="#182f5c"/><path d="M9.5 22.5V9.5L20.5 22.5V10" fill="none" stroke="#7c9df0" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/><path d="M20.5 10L24.5 6" fill="none" stroke="#29c5f6" stroke-width="2.2" stroke-linecap="round"/><circle cx="9.5" cy="22.5" r="2.6" fill="#ffffff"/><circle cx="9.5" cy="9.5" r="2.6" fill="#ffffff"/><circle cx="20.5" cy="22.5" r="2.6" fill="#ffffff"/><circle cx="20.5" cy="10" r="4.8" fill="#29c5f6" fill-opacity="0.28"/><circle cx="20.5" cy="10" r="2.7" fill="#29c5f6"/><circle cx="24.5" cy="6" r="1.5" fill="#29c5f6"/></svg>';

  const ICONOS = {
    pausa: '<rect x="6.5" y="5" width="3.8" height="14" rx="1.2"/><rect x="13.7" y="5" width="3.8" height="14" rx="1.2"/>',
    seguir: '<path d="M8 5.6v12.8a.8.8 0 0 0 1.2.7l10-6.4a.8.8 0 0 0 0-1.4l-10-6.4A.8.8 0 0 0 8 5.6z"/>',
    siguiente: '<path d="M5.5 6.1v11.8a.7.7 0 0 0 1.1.6l8.6-5.9a.7.7 0 0 0 0-1.2L6.6 5.5a.7.7 0 0 0-1.1.6z"/><path d="M18.5 5.5v13"/>',
    paso: '<path d="M4 18.5h4.5V14H13V9.5h4.5V5H20"/>',
    terminar: '<rect x="6" y="6" width="12" height="12" rx="2.2"/>',
    ok: '<circle cx="12" cy="12" r="9"/><path d="m8.2 12.3 2.6 2.6 5-5.4"/>',
    falla: '<circle cx="12" cy="12" r="9"/><path d="m9 9 6 6M15 9l-6 6"/>',
    alerta: '<path d="M10.3 4.2 2.9 17.1A2 2 0 0 0 4.6 20h14.8a2 2 0 0 0 1.7-2.9L13.7 4.2a2 2 0 0 0-3.4 0z"/><path d="M12 9.5v4.2M12 16.9v.1"/>',
    flecha: '<path d="M4 12h15M13.5 6.5 19 12l-5.5 5.5"/>',
  };
  const iconoSvg = (nombre) => `<svg class="ico" viewBox="0 0 24 24" aria-hidden="true">${ICONOS[nombre]}</svg>`;
  const CURSOR = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4.5 2.5v16.7l4.6-4.3 3.2 6.7 2.9-1.3-3.1-6.6 6.3-.3z" fill="#ffffff" stroke="#081c3a" stroke-width="1.5" stroke-linejoin="round"/></svg>';

  const BASE = `
    <div class="velo-foco" hidden><div class="foco"></div><p class="etiqueta foco-etiqueta" hidden></p></div>
    <div class="velo-lupa"></div>
    <figure class="lupa" hidden><figcaption class="etiqueta" hidden></figcaption></figure>
    <section class="slide" hidden></section>
    <p class="subtitulos" aria-live="polite"><span class="linea"></span></p>
    <div class="cursor" hidden>${CURSOR}</div>
    <p class="envivo" hidden><span class="punto"></span><span><b>En vivo:</b> <span class="envivo-texto"></span></span></p>
    <p class="aviso" role="status" hidden></p>
    <div class="barra" role="toolbar" aria-label="Control de la demo">
      <span class="estado-chip" hidden></span>
      <button type="button" tabindex="-1" class="b-pausa" aria-keyshortcuts="Space K"></button>
      <button type="button" tabindex="-1" class="b-siguiente" aria-label="Siguiente (→)" title="Siguiente (→)" aria-keyshortcuts="ArrowRight N">${iconoSvg("siguiente")}</button>
      <span class="sep"></span>
      <div class="velocidades" role="group" aria-label="Velocidad">
        <button type="button" tabindex="-1" data-v="0.75" title="Más lento (&lt;)">0,75×</button>
        <button type="button" tabindex="-1" data-v="1">1×</button>
        <button type="button" tabindex="-1" data-v="1.25" title="Más rápido (&gt;)">1,25×</button>
      </div>
      <button type="button" tabindex="-1" class="b-paso" aria-label="Paso a paso (P)" title="Paso a paso (P)" aria-keyshortcuts="P">${iconoSvg("paso")}</button>
      <span class="sep"></span>
      <div class="progreso"><span class="escena"></span><span class="tiempo"></span><div class="pista"><div class="relleno"></div></div></div>
      <span class="sep"></span>
      <button type="button" tabindex="-1" class="b-terminar" aria-label="Terminar (Q dos veces)" title="Terminar (Q dos veces)" aria-keyshortcuts="Q">${iconoSvg("terminar")}</button>
    </div>`;

  function montar() {
    if (ui.host) return;
    const host = document.createElement("demo-director");
    host.id = "demo-director";
    host.style.cssText = "position:fixed;inset:0;z-index:2147483647;pointer-events:none;display:block";
    const sombra = host.attachShadow({ mode: "open" });
    sombra.innerHTML = BASE;
    const css = String(window.__DIRECTOR_CSS || "");
    try {
      const hoja = new CSSStyleSheet();
      hoja.replaceSync(css);
      sombra.adoptedStyleSheets = [hoja];
    } catch {
      const estilo = document.createElement("style");
      estilo.textContent = css;
      sombra.prepend(estilo);
    }
    const $ = (sel) => sombra.querySelector(sel);
    Object.assign(ui, {
      host, sombra,
      veloFoco: $(".velo-foco"), foco: $(".foco"), focoEtiqueta: $(".foco-etiqueta"),
      veloLupa: $(".velo-lupa"), lupa: $(".lupa"), lupaImg: document.createElement("img"), lupaEtiqueta: $(".lupa .etiqueta"),
      slide: $(".slide"), subtitulos: $(".subtitulos"), linea: $(".linea"), cursor: $(".cursor"),
      envivo: $(".envivo"), envivoTexto: $(".envivo-texto"), aviso: $(".aviso"),
      barra: $(".barra"), chip: $(".estado-chip"), bPausa: $(".b-pausa"), bPaso: $(".b-paso"),
      escena: $(".escena"), tiempo: $(".tiempo"), pista: $(".pista"), relleno: $(".relleno"),
      ultimoMostrar: 0, barraEncima: false,
    });
    ui.lupaImg.alt = "";
    ui.lupa.prepend(ui.lupaImg);
    (document.documentElement || document.body).appendChild(host);

    // La barra y las slides no dejan pasar clics ni rueda a la consola.
    for (const capa of [ui.barra, ui.slide]) {
      for (const tipo of ["click", "mousedown", "pointerdown", "dblclick"]) capa.addEventListener(tipo, (e) => e.stopPropagation());
      capa.addEventListener("wheel", (e) => e.preventDefault(), { passive: false });
    }
    ui.barra.addEventListener("mousedown", (e) => e.preventDefault()); // los botones nunca toman el foco
    ui.barra.addEventListener("pointerenter", () => { ui.barraEncima = true; pintarBarra(); });
    ui.barra.addEventListener("pointerleave", () => { ui.barraEncima = false; mostrarBarra(); });
    ui.barra.addEventListener("click", (e) => {
      const boton = e.target.closest("button");
      if (!boton) return;
      if (boton.dataset.v) fijarVelocidad(Number(boton.dataset.v));
      else if (boton === ui.bPausa) alternarPausa();
      else if (boton.classList.contains("b-siguiente")) siguiente();
      else if (boton === ui.bPaso) alternarPaso();
      else if (boton.classList.contains("b-terminar")) pedirTerminar();
    });
    pintarBarra();
  }

  /* ---------- Barra de control ---------- */
  let ocultarBarraEn = 0;
  function mostrarBarra() {
    if (!ui.barra) return;
    ui.ultimoMostrar = performance.now();
    clearTimeout(ocultarBarraEn);
    ocultarBarraEn = setTimeout(pintarBarra, 3050);
    pintarBarra();
  }

  function accionar(valor) {
    est.accionando = valor;
    pintarBarra();
  }

  function pintarBarra() {
    if (!ui.barra) return;
    const fija = est.pausado || Boolean(liberarFrontera);
    const reciente = performance.now() - ui.ultimoMostrar < 3000 || ui.barraEncima;
    ui.barra.toggleAttribute("data-oculta", est.accionando ? !fija : !(fija || reciente));
    ui.barra.toggleAttribute("data-inerte", est.accionando);
    const iconoPausa = est.pausado ? "seguir" : "pausa";
    if (ui.bPausa.dataset.icono !== iconoPausa) {
      ui.bPausa.dataset.icono = iconoPausa;
      ui.bPausa.innerHTML = iconoSvg(iconoPausa);
    }
    const etiquetaPausa = est.pausado ? "Seguir (Espacio)" : "Pausa (Espacio)";
    ui.bPausa.setAttribute("aria-label", etiquetaPausa);
    ui.bPausa.title = etiquetaPausa;
    ui.bPaso.setAttribute("aria-pressed", String(est.pasoAPaso));
    for (const b of ui.barra.querySelectorAll("[data-v]")) b.setAttribute("aria-pressed", String(Number(b.dataset.v) === est.velocidad));
    const chip = liberarFrontera ? "Pulsa → para seguir" : est.pausado ? "En pausa" : "";
    ui.chip.textContent = chip;
    ui.chip.hidden = !chip;
    pintarProgreso();
  }

  function pesosEscenas() {
    const n = est.escenas.length || 1;
    const suma = est.escenas.reduce((a, e) => a + e.dur, 0);
    return est.escenas.map((e) => (suma > 0 ? e.dur / suma : 1 / n));
  }

  function construirMarcas() {
    ui.pista.querySelectorAll(".marca").forEach((m) => m.remove());
    let acumulado = 0;
    for (const peso of pesosEscenas().slice(0, -1)) {
      acumulado += peso;
      const marca = document.createElement("span");
      marca.className = "marca";
      marca.style.left = `${(acumulado * 100).toFixed(2)}%`;
      ui.pista.append(marca);
    }
  }

  const mmss = (s) => {
    const t = Math.max(0, Math.round(s));
    return `${String(Math.floor(t / 60)).padStart(2, "0")}:${String(t % 60).padStart(2, "0")}`;
  };

  function pintarProgreso() {
    if (!ui.barra || !est.activo) return;
    avanzar();
    const n = est.escenas.length;
    const i = est.indice;
    const actual = est.escenas[i];
    const numero = document.createElement("b");
    numero.textContent = n ? `${Math.max(1, i + 1)}/${n}` : "";
    ui.escena.replaceChildren(numero, actual ? ` · ${actual.titulo}` : "");
    const pesos = pesosEscenas();
    let fraccion = 0;
    if (i >= 0) {
      fraccion = pesos.slice(0, i).reduce((a, b) => a + b, 0);
      if (actual && actual.dur > 0) {
        fraccion += (pesos[i] || 0) * Math.min(1, ((reloj.transcurrido - reloj.escenaDesde) * est.velocidad) / actual.dur);
      }
    }
    ui.relleno.style.width = `${(Math.min(1, fraccion) * 100).toFixed(2)}%`;
    const t = totalActual();
    ui.tiempo.textContent = t > 0 ? `${mmss(reloj.transcurrido)} / ${mmss(t)}` : mmss(reloj.transcurrido);
  }

  /* ---------- Subtítulos ---------- */
  let retiroSubtitulo = 0;
  function mostrarSubtitulo(texto) {
    clearTimeout(retiroSubtitulo);
    const yaVisible = ui.subtitulos.hasAttribute("data-visible");
    ui.linea.textContent = texto;
    ui.subtitulos.hidden = !texto;
    ui.subtitulos.setAttribute("data-visible", "");
    if (yaVisible && !reducido()) ui.linea.animate([{ opacity: 0.1 }, { opacity: 1 }], { duration: 260 / est.velocidad, easing: "ease-out" });
  }

  function retirarSubtitulo() {
    clearTimeout(retiroSubtitulo);
    retiroSubtitulo = setTimeout(() => ui.subtitulos.removeAttribute("data-visible"), 700);
  }

  /* ---------- Avisos ---------- */
  let retiroAviso = 0;
  function aviso(texto) {
    montar();
    clearTimeout(retiroAviso);
    ui.aviso.textContent = String(texto ?? "");
    ui.aviso.hidden = !texto;
    if (texto) retiroAviso = setTimeout(() => { ui.aviso.hidden = true; }, 3600);
  }

  function enVivo(texto) {
    montar();
    ui.envivoTexto.textContent = texto ? String(texto) : "";
    ui.envivo.hidden = !texto;
  }

  /* ---------- Foco: recorte que sigue en vivo al objetivo ---------- */
  const foco = { els: [], desde: null, t0: 0, dur: 0, raf: 0, rect: null };
  const MARGEN_FOCO = 10;
  const lerp = (a, b, k) => a + (b - a) * k;

  function rectDe(els) {
    let x1 = Infinity, y1 = Infinity, x2 = -Infinity, y2 = -Infinity;
    for (const el of els) {
      if (!el.isConnected) continue;
      const r = el.getBoundingClientRect();
      if (!r.width && !r.height) continue;
      x1 = Math.min(x1, r.left);
      y1 = Math.min(y1, r.top);
      x2 = Math.max(x2, r.right);
      y2 = Math.max(y2, r.bottom);
    }
    if (x1 === Infinity) return null;
    return { x: x1 - MARGEN_FOCO, y: y1 - MARGEN_FOCO, w: x2 - x1 + 2 * MARGEN_FOCO, h: y2 - y1 + 2 * MARGEN_FOCO };
  }

  function rectEstable(els, minimoMs) {
    return new Promise((resolver) => {
      const t0 = performance.now();
      let previo = null;
      let quietos = 0;
      const mirar = () => {
        const r = rectDe(els);
        const igual = r && previo && Math.abs(r.x - previo.x) < 0.5 && Math.abs(r.y - previo.y) < 0.5;
        quietos = igual ? quietos + 1 : 0;
        previo = r;
        const pasado = performance.now() - t0;
        if ((quietos >= 4 && pasado >= minimoMs) || pasado > 1600) resolver();
        else requestAnimationFrame(mirar);
      };
      requestAnimationFrame(mirar);
    });
  }

  async function llevarALaVista(els) {
    const r = rectDe(els);
    if (!r) return;
    const visible = r.y >= 8 && r.y + r.h <= innerHeight - RESERVA_ABAJO;
    if (visible) return;
    els[0].scrollIntoView({ behavior: reducido() ? "auto" : "smooth", block: r.h > innerHeight * 0.6 ? "start" : "center" });
    await rectEstable(els, 180);
  }

  function esquivar(r) {
    const tapaAbajo = r.y + r.h > innerHeight - RESERVA_ABAJO;
    const tapaArriba = r.y < 170;
    ui.subtitulos.dataset.posicion = tapaAbajo && !tapaArriba ? "arriba" : "abajo";
  }

  function colocarEtiqueta(r) {
    const e = ui.focoEtiqueta;
    if (e.hidden) return;
    const ancho = e.offsetWidth;
    const x = Math.min(Math.max(12, r.x), innerWidth - ancho - 12);
    const y = r.y > 56 ? r.y - e.offsetHeight - 10 : r.y + r.h + 10;
    e.style.transform = `translate(${x}px, ${y}px)`;
  }

  function seguirFoco(ahora) {
    const vivo = rectDe(foco.els);
    if (vivo) {
      let r = vivo;
      if (foco.desde) {
        const t = foco.dur ? Math.min(1, (ahora - foco.t0) / foco.dur) : 1;
        const k = t >= 1 ? 1 : 1 - Math.pow(2, -10 * t);
        r = { x: lerp(foco.desde.x, vivo.x, k), y: lerp(foco.desde.y, vivo.y, k), w: lerp(foco.desde.w, vivo.w, k), h: lerp(foco.desde.h, vivo.h, k) };
        if (t >= 1) foco.desde = null;
      }
      foco.rect = r;
      const s = ui.foco.style;
      s.transform = `translate(${r.x}px, ${r.y}px)`;
      s.width = `${r.w}px`;
      s.height = `${r.h}px`;
      colocarEtiqueta(r);
      esquivar(r);
    }
    foco.raf = requestAnimationFrame(seguirFoco);
  }

  async function enfocar(selector, opciones = {}) {
    montar();
    if (!selector) {
      apagarFoco();
      return true;
    }
    let els;
    try {
      els = [...document.querySelectorAll(selector)];
    } catch {
      return false;
    }
    els = els.filter((el) => {
      const r = el.getBoundingClientRect();
      return r.width > 0 || r.height > 0;
    });
    if (!els.length) return false;
    await llevarALaVista(els);
    const yaVisible = ui.veloFoco.hasAttribute("data-visible") && foco.rect;
    foco.desde = yaVisible ? { ...foco.rect } : null;
    foco.els = els;
    foco.t0 = performance.now();
    foco.dur = (reducido() ? 0 : 560) / est.velocidad;
    const etiqueta = opciones && opciones.etiqueta ? String(opciones.etiqueta) : "";
    ui.focoEtiqueta.textContent = etiqueta;
    ui.focoEtiqueta.hidden = !etiqueta;
    ui.veloFoco.hidden = false;
    if (!foco.raf) foco.raf = requestAnimationFrame(seguirFoco);
    requestAnimationFrame(() => ui.veloFoco.setAttribute("data-visible", ""));
    await pausa(yaVisible ? 0.56 : 0.32);
    return true;
  }

  function apagarFoco() {
    ui.veloFoco.removeAttribute("data-visible");
    ui.subtitulos.dataset.posicion = "abajo";
    const els = foco.els;
    setTimeout(() => {
      if (foco.els !== els) return; // otro foco llegó mientras se apagaba
      cancelAnimationFrame(foco.raf);
      foco.raf = 0;
      foco.els = [];
      foco.rect = null;
      ui.veloFoco.hidden = true;
    }, 360 / est.velocidad);
  }

  /* ---------- Lupa: la captura de Python, ampliada con FLIP ---------- */
  let lupaActual = null;
  async function lupa(dataUrl, rect, opciones = {}) {
    montar();
    if (!dataUrl) return cerrarLupa();
    if (lupaActual) await cerrarLupa();
    const r = { x: Number(rect.x), y: Number(rect.y), w: Number(rect.width), h: Number(rect.height) };
    if (!(r.w > 0 && r.h > 0)) return false;
    const arriba = 48;
    const altoUtil = innerHeight - RESERVA_ABAJO - arriba;
    // Hasta 2× dentro del 70 % del viewport; un elemento más ancho se muestra a 1:1 y solo encoge si no cabe.
    const encaje = Math.min((innerWidth * 0.7) / r.w, Math.min(innerHeight * 0.7, altoUtil) / r.h);
    const tope = Math.min((innerWidth - 48) / r.w, altoUtil / r.h);
    const s = Math.min(2, Math.max(1, encaje), tope);
    const w = r.w * s;
    const h = r.h * s;
    const x = (innerWidth - w) / 2;
    const y = arriba + Math.max(0, (altoUtil - h) / 2);
    ui.lupaImg.src = dataUrl;
    await ui.lupaImg.decode().catch(() => {});
    const etiqueta = opciones && opciones.etiqueta ? String(opciones.etiqueta) : "";
    ui.lupaEtiqueta.textContent = etiqueta;
    ui.lupaEtiqueta.hidden = !etiqueta;
    Object.assign(ui.lupa.style, { left: `${x}px`, top: `${y}px`, width: `${w}px` });
    ui.lupaImg.style.height = `${h}px`;
    ui.lupa.getAnimations().forEach((a) => a.cancel());
    ui.lupa.hidden = false;
    ui.veloLupa.setAttribute("data-visible", "");
    const desde = `translate(${r.x - x}px, ${r.y - y}px) scale(${1 / s})`;
    const dur = (reducido() ? 200 : 640) / est.velocidad;
    lupaActual = { desde, dur };
    const cuadros = reducido()
      ? [{ opacity: 0 }, { opacity: 1 }]
      : [{ transform: desde, opacity: 0.35 }, { transform: "none", opacity: 1 }];
    await ui.lupa.animate(cuadros, { duration: dur, easing: EXPO, fill: "both" }).finished.catch(() => {});
    return true;
  }

  async function cerrarLupa() {
    if (!lupaActual) return true;
    const { desde, dur } = lupaActual;
    lupaActual = null;
    ui.veloLupa.removeAttribute("data-visible");
    const cuadros = reducido()
      ? [{ opacity: 1 }, { opacity: 0 }]
      : [{ transform: "none", opacity: 1 }, { transform: desde, opacity: 0 }];
    await ui.lupa.animate(cuadros, { duration: dur * 0.75, easing: "cubic-bezier(0.7, 0, 0.84, 0)", fill: "both" }).finished.catch(() => {});
    ui.lupa.hidden = true;
    ui.lupa.getAnimations().forEach((a) => a.cancel());
    return true;
  }

  /* ---------- Cursor falso: llega antes que el clic real de Playwright ---------- */
  const puntero = { x: null, y: null };
  async function cursor(x, y) {
    montar();
    accionar(true);
    const destino = { x: Number(x), y: Number(y) };
    const desde = puntero.x == null ? { x: destino.x + 160, y: destino.y + 110 } : { x: puntero.x, y: puntero.y };
    ui.cursor.hidden = false;
    const distancia = Math.hypot(destino.x - desde.x, destino.y - desde.y);
    const dur = (reducido() ? 1 : Math.min(900, Math.max(600, 520 + distancia * 0.35))) / est.velocidad;
    ui.cursor.getAnimations().forEach((a) => a.cancel());
    const anim = ui.cursor.animate(
      [{ transform: `translate(${desde.x}px, ${desde.y}px)` }, { transform: `translate(${destino.x}px, ${destino.y}px)` }],
      { duration: dur, easing: "cubic-bezier(0.45, 0, 0.2, 1)", fill: "forwards" },
    );
    puntero.x = destino.x;
    puntero.y = destino.y;
    await anim.finished.catch(() => {});
    ui.cursor.style.transform = `translate(${destino.x}px, ${destino.y}px)`;
    anim.cancel();
    return true;
  }

  function clic() {
    montar();
    if (puntero.x == null) return;
    const onda = document.createElement("span");
    onda.className = "onda";
    onda.style.left = `${puntero.x}px`;
    onda.style.top = `${puntero.y}px`;
    ui.sombra.append(onda);
    const dur = 560 / est.velocidad;
    onda.animate([{ transform: "scale(0.3)", opacity: 0.95 }, { transform: "scale(2.2)", opacity: 0 }], { duration: dur, easing: EXPO, fill: "forwards" })
      .finished.catch(() => {}).then(() => onda.remove());
    ui.cursor.querySelector("svg").animate([{ transform: "scale(1)" }, { transform: "scale(0.86)" }, { transform: "scale(1)" }], { duration: 220 / est.velocidad });
  }

  /* ---------- Slides ---------- */
  function h(tag, props, ...hijos) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(props || {})) {
      if (v == null || v === false) continue;
      if (k === "class") el.className = v;
      else if (k === "style") el.style.cssText = v;
      else el.setAttribute(k, v === true ? "" : String(v));
    }
    for (const hijo of hijos.flat()) {
      if (hijo == null || hijo === false || hijo === "") continue;
      el.append(hijo instanceof Node ? hijo : document.createTextNode(String(hijo)));
    }
    return el;
  }

  function desdeMarcado(marcado, clase) {
    const t = document.createElement("template");
    t.innerHTML = marcado.trim();
    const el = t.content.firstElementChild;
    if (clase) el.classList.add(clase);
    return el;
  }
  const icono = (nombre) => desdeMarcado(iconoSvg(nombre));
  const monograma = (clase) => desdeMarcado(MONOGRAMA, clase);
  const TONO_ICONO = { pass: "ok", fail: "falla", warn: "alerta" };

  function caja(titulo, detalle, rol) {
    return h("div", { class: "caja", "data-rol": rol }, h("b", {}, titulo), detalle && h("small", {}, detalle));
  }
  function conector(tipo) {
    const trazos = {
      abre: ["M0 50 C50 50 50 16.67 100 16.67", "M0 50 H100", "M0 50 C50 50 50 83.33 100 83.33"],
      cierra: ["M0 16.67 C50 16.67 50 50 100 50", "M0 50 H100", "M0 83.33 C50 83.33 50 50 100 50"],
      recto: ["M0 50 H100"],
    }[tipo];
    return desdeMarcado(`<svg class="conector" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">${trazos.map((d) => `<path d="${d}"/>`).join("")}</svg>`);
  }

  const PLANTILLAS = {
    portada: ({ titulo, subtitulo }) => h("div", { class: "s-portada" },
      monograma("entra"),
      h("h1", { class: "entra" }, titulo),
      h("p", { class: "bajada entra" }, subtitulo),
      h("div", { class: "riel", "aria-hidden": "true" }, Array.from({ length: 8 }, (_, e) => h("span", { class: "nodo", style: `--e:${e}` })))),

    pregunta: ({ pregunta, fuentes = [], remate }) => h("div", { class: "s-pregunta" },
      h("h1", { class: "entra" }, pregunta),
      fuentes.length > 0 && h("ul", { class: "islas", style: `--n:${fuentes.length}` },
        fuentes.map((f) => h("li", { class: "entra" }, h("span", { class: "nodo" }), h("span", { class: "nombre" }, f)))),
      h("p", { class: "remate entra" }, remate)),

    caso: ({ regla, entregas = [] }) => h("div", { class: "s-caso" },
      h("h1", { class: "entra" }, regla),
      h("div", { class: "entregas" }, entregas.map((e) => h("div", { class: "entrega entra", "data-tono": e.tono },
        h("p", { class: "version" }, TONO_ICONO[e.tono] && icono(TONO_ICONO[e.tono]), h("span", {}, e.version)),
        h("p", { class: "escenario" }, h("span", { class: "rotulo" }, "Escenario:"), " ", e.escenario))))),

    maf: ({ titulo = "Los agentes investigan; la política decide" }) => h("div", { class: "s-maf" },
      h("h1", { class: "entra" }, titulo),
      h("div", { class: "grafo entra" },
        caja("Recolector de evidencia", "Huella SHA-256 de cada artefacto"),
        conector("abre"),
        h("div", { class: "agentes" },
          caja("QA de renovaciones", "Agente en Azure AI Foundry"),
          caja("Seguridad y operación", "Agente en Azure AI Foundry"),
          caja("SRE, analítica y gobierno", "Agente en Azure AI Foundry")),
        conector("cierra"),
        caja("Política REN-001.v2", "Determinista: emite el dictamen", "politica"),
        conector("recto"),
        caja("Aprobación humana", "Antes de crear la tarea en Azure Boards", "humano")),
      h("p", { class: "pie entra" }, "Microsoft Agent Framework: tres ramas en paralelo que se reúnen antes del dictamen, con un punto de control para la decisión humana.")),

    etapas: ({ etapas = [], titulo = "Ocho etapas, una sola trazabilidad" }) => h("div", { class: "s-etapas" },
      h("h1", { class: "entra" }, titulo),
      h("div", { class: "mapa" },
        h("div", { class: "intercambio", "aria-hidden": "true" }, h("span", {}, "Núcleo determinista")),
        h("ol", {}, etapas.map((nombre, e) => h("li", { class: "estacion", "data-linea": e < 4 ? "devsec" : "cloudops", style: `--e:${e}` },
          h("span", { class: "anillo" }, String(e + 1)),
          h("span", { class: "nombre" }, nombre))))),
      h("div", { class: "leyenda entra", style: "--i:11" },
        h("span", { class: "l-devsec" }, "Línea DevSec · Código y evidencia"),
        h("span", { class: "l-cloudops" }, "Línea CloudOps · Nube y gobierno"))),

    gobernanza: ({ pasos = [], titulo = "Ninguna tarea entra al backlog sin una decisión humana" }) => h("div", { class: "s-gobernanza" },
      h("h1", { class: "entra" }, titulo),
      h("ol", { class: "flujo" }, pasos.map((p) => {
        const paso = typeof p === "string" ? { texto: p } : p || {};
        return h("li", { class: "entra", "data-destacar": Boolean(paso.destacar) }, h("span", { class: "nodo" }), h("span", {}, paso.texto));
      }))),

    cierre: ({ tesis = [], cta }) => h("div", { class: "s-cierre" },
      h("ul", { class: "tesis" }, tesis.map((t) => h("li", { class: "entra" }, h("span", { class: "nodo" }), h("p", {}, t)))),
      cta && h("p", { class: "cta entra" }, icono("flecha"), h("span", {}, cta))),
  };

  async function slide(plantilla, datos) {
    montar();
    const fabrica = PLANTILLAS[plantilla];
    if (!fabrica) throw new Error(`Plantilla de slide desconocida: ${plantilla}`);
    const contenido = fabrica(datos || {});
    const piezas = plantilla === "portada" ? [contenido] : [h("div", { class: "membrete", "aria-hidden": "true" }, monograma(), "NextGen DevSecOps Assessment"), contenido];
    ui.slide.replaceChildren(...piezas);
    ui.slide.dataset.plantilla = plantilla;
    ui.slide.querySelectorAll(".entra").forEach((el, i) => {
      if (!el.style.getPropertyValue("--i")) el.style.setProperty("--i", String(i));
    });
    ui.cursor.hidden = true;
    ui.slide.removeAttribute("data-sale");
    ui.slide.hidden = false;
    await new Promise((r) => requestAnimationFrame(r));
    ui.slide.setAttribute("data-visible", "");
    await pausa(0.6);
    return true;
  }

  async function ocultarSlide() {
    montar();
    if (ui.slide.hidden) return true;
    ui.slide.removeAttribute("data-visible");
    ui.slide.setAttribute("data-sale", "");
    await pausa(0.4);
    ui.slide.hidden = true;
    ui.slide.removeAttribute("data-sale");
    ui.slide.replaceChildren();
    return true;
  }

  window.__director = Object.freeze({
    iniciar,
    escena,
    turno,
    decir,
    esperar,
    foco: enfocar,
    lupa,
    cursor,
    clic,
    slide,
    ocultarSlide,
    enVivo,
    aviso,
    pausar: () => fijarPausa(true),
    total,
    estado: estadoPublico,
  });
})();
