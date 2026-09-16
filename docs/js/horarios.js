const DIAS_HORARIO = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"];
let todosLosHorarios = [];
let calendario = [];
let filtros = {};

window.addEventListener("DOMContentLoaded", async function () {
  if (!sessionStorage.getItem("logueado")) {
    window.location.href = "index.html";
    return;
  }

  document.getElementById("usuarioSpan").textContent = sessionStorage.getItem("usuario") || "—";
  document.getElementById("btnVolverModulos").addEventListener("click", () => window.location.href = "acceso.html");
  document.getElementById("btnLogout").addEventListener("click", cerrarSesion);
  document.getElementById("btnBuscarGlobal").addEventListener("click", buscarGlobal);
  document.getElementById("busquedaGlobal").addEventListener("keydown", event => {
    if (event.key === "Enter") buscarGlobal();
  });
  document.getElementById("btnLimpiarFiltros").addEventListener("click", limpiarFiltros);

  todosLosHorarios = await leerSegura("horarios");
  calendario = await leerSegura("calendarioAcademico");
  if (!todosLosHorarios.length) {
    mostrarEstado("No hay horarios cargados. Ejecuta la FASE 6 para actualizar los datos.");
  }
  poblarFiltros();
  document.querySelectorAll(".schedule-filter-grid select").forEach(select => select.addEventListener("change", aplicarFiltros));
  aplicarFiltros();
});

async function leerSegura(nombre) {
  try { return await leerColeccion(nombre); } catch (error) { console.error(error); return []; }
}

function valoresUnicos(registros, campo) {
  return [...new Set(registros.map(registro => String(registro[campo] || "").trim()).filter(Boolean))].sort((a, b) => a.localeCompare(b, "es"));
}

function llenarSelect(id, valores, textoInicial) {
  const select = document.getElementById(id);
  const valorActual = select.value;
  select.innerHTML = `<option value="">${textoInicial}</option>` + valores.map(valor => `<option value="${escapeHtml(valor)}">${escapeHtml(valor)}</option>`).join("");
  if (valores.includes(valorActual)) select.value = valorActual;
}

function poblarFiltros() {
  llenarSelect("filtroSemestre", valoresUnicos(todosLosHorarios, "SEMESTRE_ACADEMICO"), "Todos los semestres");
  llenarSelect("filtroNivel", valoresUnicos(todosLosHorarios, "NIVEL"), "Todos los niveles");
  llenarSelect("filtroPrograma", valoresUnicos(todosLosHorarios, "PROGRAMA"), "Todos los programas");
  llenarSelect("filtroGrupo", valoresUnicos(todosLosHorarios, "GRUPO"), "Todos los grupos");
  llenarSelect("filtroSede", valoresUnicos(todosLosHorarios, "SEDE"), "Todas las sedes");
}

function filtrosActuales() {
  return {
    SEMESTRE_ACADEMICO: document.getElementById("filtroSemestre").value,
    NIVEL: document.getElementById("filtroNivel").value,
    PROGRAMA: document.getElementById("filtroPrograma").value,
    GRUPO: document.getElementById("filtroGrupo").value,
    SEDE: document.getElementById("filtroSede").value
  };
}

function aplicarFiltros() {
  filtros = filtrosActuales();
  const registros = todosLosHorarios.filter(registro => Object.entries(filtros).every(([campo, valor]) => !valor || registro[campo] === valor));
  renderizarResumen(registros);
  renderizarHorario(registros);
  renderizarCalendario(filtros.SEMESTRE_ACADEMICO);
}

function renderizarResumen(registros) {
  const resumen = document.getElementById("resumenHorarios");
  const docentes = new Set(registros.map(r => r.DOCENTE).filter(Boolean)).size;
  const grupos = new Set(registros.map(r => r.GRUPO).filter(Boolean)).size;
  const aulas = new Set(registros.map(r => r.AULA).filter(Boolean)).size;
  resumen.innerHTML = [["Clases", registros.length], ["Docentes", docentes], ["Grupos", grupos], ["Aulas", aulas]].map(([label, valor]) => `<div class="schedule-stat"><span>${label}</span><strong>${valor}</strong></div>`).join("");
}

function renderizarHorario(registros) {
  const tabla = document.getElementById("tablaHorario");
  document.getElementById("contadorClases").textContent = `${registros.length} clase${registros.length === 1 ? "" : "s"}`;
  const contexto = [filtros.SEMESTRE_ACADEMICO, filtros.NIVEL, filtros.PROGRAMA, filtros.GRUPO].filter(Boolean).join(" · ");
  document.getElementById("tituloHorario").textContent = contexto || "Todos los horarios";
  if (!registros.length) {
    tabla.innerHTML = '<div class="empty-state">No hay clases para los filtros seleccionados.</div>';
    return;
  }
  const grupos = agruparPorGrupo(registros);
  tabla.innerHTML = `<table class="schedule-table"><thead><tr><th class="group-number-heading">N.º</th><th>Información del grupo</th><th class="campus-heading">Sede</th>${DIAS_HORARIO.map(dia => `<th>${abreviarDia(dia)}</th>`).join("")}</tr></thead><tbody>${grupos.map((grupo, indice) => `<tr><th class="group-number">${numeroGrupo(grupo.registros[0], indice + 1)}</th><td class="group-information">${informacionGrupo(grupo.registros)}</td><td class="group-campus">${escapeHtml(grupo.registros[0].SEDE || "—")}</td>${DIAS_HORARIO.map(dia => `<td class="day-cell">${tarjetasDelDia(grupo.registros.filter(registro => registro.DIA === dia)) || '<span class="empty-slot">—</span>'}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  activarScrollHorizontalHorario();
}

function activarScrollHorizontalHorario() {
  const contenedor = document.getElementById("tablaHorario");
  if (contenedor.dataset.scrollActivo) return;
  contenedor.dataset.scrollActivo = "true";
  contenedor.addEventListener("wheel", function (evento) {
    if (contenedor.scrollWidth <= contenedor.clientWidth) return;
    if (Math.abs(evento.deltaY) <= Math.abs(evento.deltaX)) return;
    contenedor.scrollLeft += evento.deltaY;
    evento.preventDefault();
  }, { passive: false });
}

function agruparPorGrupo(registros) {
  const grupos = new Map();
  registros.forEach(registro => {
    const claveGrupo = [
      registro.SEMESTRE_ACADEMICO,
      registro.NIVEL,
      registro.GRUPO,
      registro.PROGRAMA || registro.PROGRAMA_ORIGINAL,
      registro.SEDE,
      registro.COLEGIOS
    ].join("|");
    if (!grupos.has(claveGrupo)) grupos.set(claveGrupo, []);
    grupos.get(claveGrupo).push(registro);
  });
  return [...grupos.values()].map(registrosGrupo => ({ registros: registrosGrupo }));
}

function numeroGrupo(registro, respaldo) {
  const encontrado = String(registro.GRUPO || "").match(/grupo\s*(\d+)/i);
  return encontrado ? encontrado[1] : respaldo;
}

function abreviarDia(dia) {
  return ({ Lunes: "LUN", Martes: "MAR", "Miércoles": "MIÉ", Jueves: "JUE", Viernes: "VIE" })[dia] || dia;
}

function informacionGrupo(registros) {
  const primero = registros[0] || {};
  const colegios = [...new Set(registros.map(registro => registro.COLEGIOS).filter(Boolean))].join(" · ");
  const programas = [...new Map(registros.map(registro => [registro.PROGRAMA || registro.PROGRAMA_ORIGINAL, registro])).values()];
  return `<div class="group-summary"><strong class="group-name">${escapeHtml(primero.GRUPO || "Grupo sin nombre")}</strong><span class="group-schools">${escapeHtml(colegios || "Colegios no registrados")}</span><div class="program-stack">${programas.map(registro => `<article class="program-card ${clasePrograma(registro)}"><strong>${escapeHtml(registro.PROGRAMA || registro.PROGRAMA_ORIGINAL || "Programa no registrado")}</strong>${registro.SIGLA_PROGRAMA ? `<span>${escapeHtml(registro.SIGLA_PROGRAMA)}</span>` : ""}</article>`).join("")}</div></div>`;
}

function clasePrograma(registro) {
  const sigla = String(registro.SIGLA_PROGRAMA || "").toUpperCase();
  return ["TPPM", "TPDIPI", "TPMM", "TPCI", "TPPC"].includes(sigla) ? `program-${sigla.toLowerCase()}` : "program-default";
}

function tarjetasDelDia(registros) {
  const grupos = new Map();
  registros.sort((primero, segundo) => franja(primero).localeCompare(franja(segundo)));
  registros.forEach(registro => {
    const partesId = String(registro.ID_REGISTRO || "").split(":");
    const claveFuente = partesId.length > 1 ? partesId.slice(0, -1).join(":") : registro.VALOR_CELDA_ORIGINAL || registro.ASIGNATURA_ORIGINAL;
    if (!grupos.has(claveFuente)) grupos.set(claveFuente, []);
    grupos.get(claveFuente).push(registro);
  });
  return [...grupos.values()].map(secuencia => secuencia.length > 1 ? tarjetaSecuencia(secuencia) : tarjetaClase(secuencia[0])).join("");
}

function franja(registro) {
  return `${registro.HORA_INICIO || "14:00"} - ${registro.HORA_FIN || "18:00"}`;
}

function tarjetaSecuencia(registros) {
  return `<article class="sequence-card"><div class="sequence-track" aria-hidden="true"></div><div class="sequence-items">${registros.map((registro, indice) => tarjetaClase(registro, indice === 0 ? "PRIMERO" : "DESPUÉS")).join("")}</div></article>`;
}

function tarjetaClase(registro, etiqueta = "") {
  return `<article class="class-card ${clasePrograma(registro)}"><div class="class-card-heading"><span class="class-time">${escapeHtml(franja(registro))}</span>${etiqueta ? `<span class="sequence-label">${etiqueta}</span>` : ""}</div><strong>${escapeHtml(registro.ASIGNATURA || "Asignatura sin nombre")}</strong>${registro.SIGLA_PROGRAMA ? `<span class="class-program">${escapeHtml(registro.SIGLA_PROGRAMA)}</span>` : ""}<span>${escapeHtml(registro.DOCENTE || "Docente pendiente")}</span>${registro.AULA ? `<span>Aula ${escapeHtml(registro.AULA)}</span>` : ""}${registro.MONITOR ? `<span>Monitor: ${escapeHtml(registro.MONITOR)}</span>` : ""}${registro.OBSERVACIONES_HORARIO ? `<small>${escapeHtml(registro.OBSERVACIONES_HORARIO)}</small>` : ""}</article>`;
}

function buscarGlobal() {
  const termino = document.getElementById("busquedaGlobal").value.trim().toLocaleLowerCase("es");
  const campo = document.getElementById("tipoBusqueda").value;
  const resultados = todosLosHorarios.filter(registro => {
    if (!termino) return false;
    const campos = campo ? [campo] : ["DOCENTE", "MONITOR", "ASIGNATURA", "AULA", "GRUPO", "SEDE", "PROGRAMA", "SEMESTRE_ACADEMICO"];
    return campos.some(nombre => String(registro[nombre] || "").toLocaleLowerCase("es").includes(termino));
  });
  const contenedor = document.getElementById("resultadosGlobales");
  contenedor.hidden = false;
  if (!resultados.length) {
    contenedor.innerHTML = '<div class="empty-state">No se encontraron coincidencias.</div>';
    return;
  }
  const grupos = new Map();
  resultados.forEach(registro => {
    const clave = [registro.DOCENTE, registro.ASIGNATURA, registro.AULA, registro.GRUPO, registro.SEMESTRE_ACADEMICO].join("|");
    if (!grupos.has(clave)) grupos.set(clave, registro);
  });
  contenedor.innerHTML = `<div class="global-result-count">${resultados.length} registros encontrados</div>` + [...grupos.values()].slice(0, 60).map(registro => `<button class="global-result" type="button" data-id="${escapeHtml(registro.ID_REGISTRO)}"><strong>${escapeHtml(registro.ASIGNATURA || "Sin asignatura")}</strong><span>${escapeHtml(registro.DOCENTE || "Sin docente")} · ${escapeHtml(registro.DIA || "Sin día")} · ${escapeHtml(registro.HORA_INICIO || "14:00")} - ${escapeHtml(registro.HORA_FIN || "18:00")}</span><small>${escapeHtml([registro.GRUPO, registro.AULA, registro.SEMESTRE_ACADEMICO].filter(Boolean).join(" · "))}</small></button>`).join("");
  contenedor.querySelectorAll(".global-result").forEach(boton => boton.addEventListener("click", () => enfocarResultado(boton.dataset.id)));
}

function enfocarResultado(id) {
  const registro = todosLosHorarios.find(item => item.ID_REGISTRO === id);
  if (!registro) return;
  document.getElementById("filtroSemestre").value = registro.SEMESTRE_ACADEMICO || "";
  document.getElementById("filtroNivel").value = registro.NIVEL || "";
  document.getElementById("filtroPrograma").value = registro.PROGRAMA || "";
  document.getElementById("filtroGrupo").value = registro.GRUPO || "";
  document.getElementById("filtroSede").value = registro.SEDE || "";
  aplicarFiltros();
  document.getElementById("tablaHorario").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderizarCalendario(semestre) {
  const eventos = calendario.filter(evento => !semestre || evento.SEMESTRE_ACADEMICO === semestre);
  document.getElementById("tituloCalendario").textContent = semestre ? `Eventos de ${semestre}` : "Eventos del semestre";
  document.getElementById("calendarioAcademico").innerHTML = eventos.length ? eventos.map(evento => `<article class="calendar-event"><strong>${escapeHtml(evento.EVENTO || "Evento académico")}</strong><span>${formatearFecha(evento.FECHA_INICIO)}${evento.FECHA_FIN && evento.FECHA_FIN !== evento.FECHA_INICIO ? ` a ${formatearFecha(evento.FECHA_FIN)}` : ""}</span><small>${escapeHtml(evento.VALOR_ORIGINAL || "")}</small></article>`).join("") : '<div class="empty-state">No hay eventos para el semestre seleccionado.</div>';
}

function limpiarFiltros() {
  document.querySelectorAll(".schedule-filter-grid select").forEach(select => select.value = "");
  document.getElementById("busquedaGlobal").value = "";
  document.getElementById("resultadosGlobales").hidden = true;
  aplicarFiltros();
}

function mostrarEstado(texto) {
  const estado = document.getElementById("estadoHorarios");
  estado.textContent = texto;
  estado.hidden = false;
}

function cerrarSesion() {
  sessionStorage.clear();
  limpiarColecciones().finally(() => window.location.href = "index.html");
}

function escapeHtml(valor) {
  return String(valor).replace(/[&<>'"]/g, caracter => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[caracter]));
}

function formatearFecha(fecha) {
  if (!fecha) return "Fecha pendiente";
  const partes = fecha.split("-");
  return partes.length === 3 ? `${partes[2]}/${partes[1]}/${partes[0]}` : fecha;
}
