document.addEventListener("DOMContentLoaded", function () {
  if (!sessionStorage.getItem("logueado")) {
    window.location.href = "index.html";
    return;
  }

  let estudiantes = leer("estudiantes");
  const notas = leer("notas");
  const observaciones = leer("observaciones");
  const seguimiento = leer("seguimiento");
  const input = document.getElementById("busquedaEstudiante");
  const filtroSemestre = document.getElementById("filtroSemestre");
  const filtroDocumento = document.getElementById("filtroDocumento");
  const filtroCorreo = document.getElementById("filtroCorreo");
  const filtroNivel = document.getElementById("filtroNivel");
  const filtroEstado = document.getElementById("filtroEstado");
  const filtroAsignatura = document.getElementById("filtroAsignatura");
  const filtroDocente = document.getElementById("filtroDocente");
  const error = document.getElementById("errorEstudiante");
  const lista = document.getElementById("listaEstudiantes");
  const items = document.getElementById("itemsEstudiantes");
  const perfil = document.getElementById("perfilEstudiante");
  const estadoDatos = document.getElementById("estadoDatosEstudiante");

  if (!estudiantes.length && notas.length) {
    estudiantes = construirEstudiantesDesdeNotas(notas);
  }

  if (!estudiantes.length) {
    estadoDatos.textContent = "No se cargaron datos de estudiantes. Verifica que Apps Script esté desplegado con las pestañas ESTUDIANTES y NOTAS actualizadas.";
    estadoDatos.hidden = false;
  }

  document.getElementById("usuarioSpan").textContent = sessionStorage.getItem("usuario") || "—";
  document.getElementById("btnLogout").addEventListener("click", cerrarSesion);
  document.getElementById("btnVolverModulos").addEventListener("click", function () {
    window.location.href = "acceso.html";
  });
  document.getElementById("btnBuscarEstudiante").addEventListener("click", buscar);
  document.getElementById("btnLimpiarEstudiante").addEventListener("click", limpiar);
  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter") buscar();
  });

  [filtroDocumento, filtroCorreo].forEach(function (campo) {
    campo.addEventListener("keydown", function (event) {
      if (event.key === "Enter") buscar();
    });
  });

  poblarFiltros();

  function leer(nombre) {
    try {
      return JSON.parse(sessionStorage.getItem(nombre) || "[]");
    } catch (exception) {
      return [];
    }
  }

  function construirEstudiantesDesdeNotas(registrosNotas) {
    const vistos = new Set();
    return registrosNotas.reduce(function (resultado, nota) {
      const identificador = clave(nota);
      if (vistos.has(identificador)) return resultado;
      vistos.add(identificador);
      resultado.push({
        ID_ARCHIVO: nota.ID_ARCHIVO,
        ID_HOJA: nota.ID_HOJA,
        SEMESTRE: nota.SEMESTRE,
        NIVEL: nota.NIVEL,
        NOMBRE_ARCHIVO: nota.NOMBRE_ARCHIVO,
        NUMERO: nota.NUMERO_ESTUDIANTE,
        DOCUMENTO: nota.DOCUMENTO,
        NOMBRE: nota.NOMBRE_ESTUDIANTE,
        ESTADO: "—"
      });
      return resultado;
    }, []);
  }

  function texto(valor) {
    return valor === null || valor === undefined || valor === "" ? "—" : String(valor);
  }

  function escapar(valor) {
    return String(valor || "").replace(/[&<>"']/g, function (caracter) {
      return {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"}[caracter];
    });
  }

  function clave(estudiante) {
    return [estudiante.ID_ARCHIVO, estudiante.ID_HOJA, estudiante.DOCUMENTO].join("|");
  }

  function buscar() {
    const termino = input.value.trim().toLowerCase();
    const documento = filtroDocumento.value.trim().toLowerCase();
    const correo = filtroCorreo.value.trim().toLowerCase();
    const resultados = estudiantes.filter(function (estudiante) {
      const textoCoincide = !termino || String(estudiante.NOMBRE || "").toLowerCase().includes(termino);
      const documentoCoincide = !documento || String(estudiante.DOCUMENTO || "").toLowerCase().includes(documento);
      const correoCoincide = !correo || String(estudiante.CORREO || "").toLowerCase().includes(correo);
      const notasEstudiante = notas.filter(function (nota) {
        return clave(nota) === clave(estudiante);
      });
      const asignaturaCoincide = !filtroAsignatura.value || notasEstudiante.some(function (nota) {
        return nota.ASIGNATURA === filtroAsignatura.value;
      });
      const docenteCoincide = !filtroDocente.value || notasEstudiante.some(function (nota) {
        return nota.DOCENTE === filtroDocente.value;
      });
      return textoCoincide
        && documentoCoincide
        && correoCoincide
        && (!filtroSemestre.value || estudiante.SEMESTRE === filtroSemestre.value)
        && (!filtroNivel.value || estudiante.NIVEL === filtroNivel.value)
        && (!filtroEstado.value || estudiante.ESTADO === filtroEstado.value)
        && asignaturaCoincide
        && docenteCoincide;
    });
    error.hidden = resultados.length > 0;
    error.textContent = resultados.length ? "" : "No se encontró ningún estudiante con esos filtros.";
    perfil.hidden = true;
    lista.hidden = resultados.length === 0;
    items.innerHTML = resultados.map(function (estudiante) {
      return `<button class="student-result" type="button" data-key="${escapar(clave(estudiante))}"><strong>${escapar(estudiante.NOMBRE)}</strong><span>${escapar(estudiante.DOCUMENTO)} · ${escapar(estudiante.SEMESTRE)} · ${escapar(estudiante.NIVEL)}</span><small>${escapar(estudiante.NOMBRE_ARCHIVO)}</small></button>`;
    }).join("");
    items.querySelectorAll(".student-result").forEach(function (item) {
      item.addEventListener("click", function () {
        mostrar(estudiantes.find(function (estudiante) { return clave(estudiante) === item.dataset.key; }));
      });
    });
    document.getElementById("contadorEstudiantes").textContent = `${resultados.length} perfil${resultados.length === 1 ? "" : "es"} encontrado${resultados.length === 1 ? "" : "s"}`;
    if (resultados.length === 1) mostrar(resultados[0]);
  }

  function limpiar() {
    input.value = "";
    filtroDocumento.value = "";
    filtroCorreo.value = "";
    filtroSemestre.value = "";
    filtroNivel.value = "";
    filtroEstado.value = "";
    filtroAsignatura.value = "";
    filtroDocente.value = "";
    lista.hidden = true;
    perfil.hidden = true;
    error.hidden = true;
    items.innerHTML = "";
    input.focus();
  }

  function poblarFiltros() {
    llenar(filtroSemestre, valoresUnicos(estudiantes, "SEMESTRE"), "Todos los semestres");
    llenar(filtroNivel, valoresUnicos(estudiantes, "NIVEL"), "Todos los niveles");
    llenar(filtroEstado, valoresUnicos(estudiantes, "ESTADO"), "Todos los estados");
    llenar(filtroAsignatura, valoresUnicos(notas, "ASIGNATURA"), "Todas las asignaturas");
    llenar(filtroDocente, valoresUnicos(notas, "DOCENTE"), "Todos los docentes");
  }

  function valoresUnicos(registros, campo) {
    return [...new Set(registros.map(function (registro) {
      return registro[campo];
    }).filter(Boolean))].sort();
  }

  function llenar(selector, valores, textoInicial) {
    selector.innerHTML = `<option value="">${textoInicial}</option>`;
    valores.forEach(function (valor) {
      selector.insertAdjacentHTML("beforeend", `<option value="${escapar(valor)}">${escapar(valor)}</option>`);
    });
  }

  function mostrar(estudiante) {
    lista.hidden = true;
    perfil.hidden = false;
    const identificador = clave(estudiante);
    const notasPerfil = notas.filter(function (nota) { return clave(nota) === identificador; });
    const observacionesPerfil = observaciones.filter(function (observacion) { return clave(observacion) === identificador; });
    const seguimientos = seguimiento.filter(function (fila) { return fila.ID_ARCHIVO === estudiante.ID_ARCHIVO; });
    const aprobadas = notasPerfil.filter(function (nota) { return nota.ESTADO_NOTA === "APROBADA"; }).length;
    const reprobadas = notasPerfil.filter(function (nota) { return nota.ESTADO_NOTA === "REPROBADA"; }).length;
    const pendientes = notasPerfil.filter(function (nota) { return nota.ESTADO_NOTA === "VACIA" || nota.ESTADO_NOTA === "NA"; }).length;

    document.getElementById("identidadEstudiante").innerHTML = `<div><span class="eyebrow">Perfil académico</span><h2>${escapar(estudiante.NOMBRE)}</h2><p>${escapar(estudiante.DOCUMENTO)} · ${escapar(estudiante.NOMBRE_ARCHIVO)}</p></div><span class="status-pill">${escapar(estudiante.ESTADO)}</span>`;
    document.getElementById("metricasEstudiante").innerHTML = [["Asignaturas", notasPerfil.length], ["Aprobadas", aprobadas], ["Reprobadas", reprobadas], ["Pendientes", pendientes]].map(function (metrica) { return `<div class="metric"><span>${metrica[0]}</span><strong>${metrica[1]}</strong></div>`; }).join("");
    document.getElementById("contextoEstudiante").innerHTML = [["Nivel académico", estudiante.NIVEL], ["Semestre", estudiante.SEMESTRE], ["Programa / grupo", estudiante.NOMBRE_ARCHIVO], ["Número", estudiante.NUMERO], ["Documento", estudiante.DOCUMENTO], ["Institución", estudiante.INSTITUCION], ["Correo", estudiante.CORREO], ["Teléfono", estudiante.TELEFONO], ["Estado", estudiante.ESTADO], ["Asignaturas a repetir", estudiante.ASIGNATURAS_A_REPETIR]].map(function (dato) { return `<div class="info-item"><span>${dato[0]}</span><strong>${escapar(texto(dato[1]))}</strong></div>`; }).join("");
    document.getElementById("historialEstudiante").innerHTML = seguimientos.length ? seguimientos.map(function (fila) { return `<div class="timeline-item"><strong>${escapar(fila.SEMESTRE)} · ${escapar(fila.NIVEL)}</strong><span>${escapar(fila.NOMBRE_ARCHIVO)}</span></div>`; }).join("") : "<p>No hay historial disponible.</p>";
    document.getElementById("notasEstudiante").innerHTML = notasPerfil.map(function (nota) { return `<tr><td><strong>${escapar(nota.ASIGNATURA)}</strong><small>${escapar(nota.DURACION)}</small></td><td>${escapar(nota.DOCENTE)}</td><td>${escapar(nota.SEMESTRE)}</td><td>${escapar(nota.PERIODO)} · ${escapar(nota.TIPO_EVALUACION)}</td><td class="grade">${escapar(nota.VALOR_ORIGINAL || "—")}</td><td><span class="grade-status status-${String(nota.ESTADO_NOTA).toLowerCase()}">${escapar(nota.ESTADO_NOTA)}</span></td></tr>`; }).join("");
    document.getElementById("observacionesEstudiante").innerHTML = observacionesPerfil.length ? observacionesPerfil.map(function (observacion) { return `<article><strong>${escapar(observacion.ASIGNATURA)}</strong><p>${escapar(observacion.OBSERVACION)}</p></article>`; }).join("") : "<p>No hay observaciones registradas.</p>";
  }

  function cerrarSesion() {
    sessionStorage.clear();
    window.location.href = "index.html";
  }
});
