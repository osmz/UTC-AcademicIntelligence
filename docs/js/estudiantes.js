document.addEventListener("DOMContentLoaded", async function () {
  if (!sessionStorage.getItem("logueado")) {
    window.location.href = "index.html";
    return;
  }

  let estudiantes = await leer("estudiantes");
  const notas = await leer("notas");
  const observaciones = await leer("observaciones");
  const seguimiento = await leer("seguimiento");
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
  const consultaIndividual = document.getElementById("consultaIndividual");
  const consultaGrupo = document.getElementById("consultaGrupo");
  const resultadoGrupo = document.getElementById("resultadoGrupo");
  const filtroGrupoSemestre = document.getElementById("filtroGrupoSemestre");
  const filtroGrupoNivel = document.getElementById("filtroGrupoNivel");
  const filtroGrupoNombre = document.getElementById("filtroGrupoNombre");

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
  document.querySelectorAll(".student-mode-card").forEach(function (tarjeta) {
    tarjeta.addEventListener("click", function () { cambiarModo(tarjeta.dataset.modo); });
    tarjeta.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") cambiarModo(tarjeta.dataset.modo);
    });
  });
  filtroGrupoSemestre.addEventListener("change", poblarFiltrosGrupo);
  filtroGrupoNivel.addEventListener("change", poblarFiltrosGrupo);
  filtroGrupoNombre.addEventListener("change", function () {
    document.getElementById("btnConsultarGrupo").disabled = !filtroGrupoNombre.value;
  });
  document.getElementById("btnConsultarGrupo").addEventListener("click", consultarGrupo);
  document.getElementById("btnLimpiarGrupo").addEventListener("click", limpiarGrupo);
  document.getElementById("btnCerrarObservacion").addEventListener("click", cerrarObservacion);
  document.querySelector("[data-cerrar-observacion]").addEventListener("click", cerrarObservacion);
  input.addEventListener("keydown", function (event) {
    if (event.key === "Enter") buscar();
  });

  [filtroDocumento, filtroCorreo].forEach(function (campo) {
    campo.addEventListener("keydown", function (event) {
      if (event.key === "Enter") buscar();
    });
  });

  poblarFiltros();
  poblarSemestresGrupo();
  cambiarModo("seleccion");

  async function leer(nombre) {
    try {
      return await leerColeccion(nombre);
    } catch (exception) {
      return [];
    }
  }

  function construirEstudiantesDesdeNotas(registrosNotas) {
    const vistos = new Set();
    return registrosNotas.reduce(function (resultado, nota) {
      const identificador = claveEstudiante(nota);
      if (vistos.has(identificador)) return resultado;
      vistos.add(identificador);
      resultado.push({
        ID_ARCHIVO: nota.ID_ARCHIVO,
        ID_HOJA: nota.ID_HOJA,
        SEMESTRE: nota.SEMESTRE,
        NIVEL: nota.NIVEL,
        PROGRAMA: nota.PROGRAMA || nota.NIVEL || "",
        SEMESTRE_ACADEMICO: nota.SEMESTRE_ACADEMICO || "",
        SEMESTRE_DECLARADO: nota.SEMESTRE_DECLARADO || "",
        DIAGNOSTICO_SEMESTRE: nota.DIAGNOSTICO_SEMESTRE || "",
        NOMBRE_ARCHIVO: nota.NOMBRE_ARCHIVO,
        NUMERO: nota.NUMERO_ESTUDIANTE,
        DOCUMENTO: nota.DOCUMENTO,
        NOMBRE: nota.NOMBRE_ESTUDIANTE,
        CORREO: nota.CORREO || "",
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

  function claveEstudiante(registro) {
    const documento = String(registro.DOCUMENTO || "").trim();
    const nombre = String(registro.NOMBRE || registro.NOMBRE_ESTUDIANTE || "").trim().toLowerCase();
    const archivo = String(registro.ID_ARCHIVO || "").trim();
    const hoja = String(registro.ID_HOJA || "").trim();

    if (documento) return "doc:" + documento;
    if (nombre) return "nombre:" + nombre;
    return "archivo:" + archivo + ":" + hoja;
  }

  function coincidePersona(primero, segundo) {
    const documentoA = String((primero && (primero.DOCUMENTO || primero.DOCUMENTO_ESTUDIANTE)) || "").trim();
    const documentoB = String((segundo && (segundo.DOCUMENTO || segundo.DOCUMENTO_ESTUDIANTE)) || "").trim();

    if (documentoA && documentoB && documentoA === documentoB) {
      return true;
    }

    const nombreA = String((primero && (primero.NOMBRE || primero.NOMBRE_ESTUDIANTE)) || "").trim().toLowerCase();
    const nombreB = String((segundo && (segundo.NOMBRE || segundo.NOMBRE_ESTUDIANTE)) || "").trim().toLowerCase();

    return !!nombreA && !!nombreB && nombreA === nombreB;
  }

  function agruparEstudiantes(registros) {
    const mapa = new Map();

    registros.forEach(function (registro) {
      const key = claveEstudiante(registro);
      if (!mapa.has(key)) {
        mapa.set(key, {
          key: key,
          nombre: String(registro.NOMBRE || registro.NOMBRE_ESTUDIANTE || "Estudiante").trim(),
          documento: String(registro.DOCUMENTO || "").trim(),
          registros: []
        });
      }
      mapa.get(key).registros.push(registro);
    });

    return Array.from(mapa.values()).map(function (grupo) {
      const semestres = [...new Set(grupo.registros.map(function (registro) {
        return registro.SEMESTRE;
      }).filter(Boolean))].sort(function (a, b) {
        return ordenarSemestres(a, b);
      });

      return Object.assign(grupo, { semestres: semestres });
    });
  }

  function numeroAcademicoPeriodo(periodo) {
    const match = String(periodo || "").match(/(\d{4})-(\d+)/);
    if (!match) return null;

    const year = parseInt(match[1], 10);
    const period = parseInt(match[2], 10);

    if (period === 1) return 1;
    if (period === 3) return 2;

    return null;
  }

  function ordenSemestreAcademico(periodo) {
    const valor = numeroAcademicoPeriodo(periodo);
    if (valor !== null) return valor;
    return parseInt(String(periodo || "").match(/(\d+)/g)?.slice(-1)[0] || "0", 10);
  }

  function ordenarSemestres(semestreA, semestreB) {
    return ordenSemestreAcademico(semestreA) - ordenSemestreAcademico(semestreB);
  }

  function buscar() {
    const termino = input.value.trim().toLowerCase();
    const documento = filtroDocumento.value.trim().toLowerCase();
    const correo = filtroCorreo.value.trim().toLowerCase();
    const grupos = agruparEstudiantes(estudiantes);
    const resultados = grupos.filter(function (grupo) {
      const coincidencias = grupo.registros.some(function (registro) {
        const textoCoincide = !termino || String(registro.NOMBRE || "").toLowerCase().includes(termino);
        const documentoCoincide = !documento || String(registro.DOCUMENTO || "").toLowerCase().includes(documento);
        const correoCoincide = !correo || String(registro.CORREO || "").toLowerCase().includes(correo);
        const notasEstudiante = notas.filter(function (nota) {
          return coincidePersona(nota, registro);
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
          && (!filtroSemestre.value || registro.SEMESTRE === filtroSemestre.value)
          && (!filtroNivel.value || registro.NIVEL === filtroNivel.value)
          && (!filtroEstado.value || registro.ESTADO === filtroEstado.value)
          && asignaturaCoincide
          && docenteCoincide;
      });

      return coincidencias;
    });

    error.hidden = resultados.length > 0;
    error.textContent = resultados.length ? "" : "No se encontró ningún estudiante con esos filtros.";
    perfil.hidden = true;
    lista.hidden = resultados.length === 0;
    items.innerHTML = resultados.map(function (grupo) {
      const semestres = grupo.semestres.length ? grupo.semestres.slice(0, 3).join(" · ") : "Sin historial";
      return `<button class="student-result" type="button" data-key="${escapar(grupo.key)}"><strong>${escapar(grupo.nombre)}</strong><span>${escapar(grupo.documento || "Sin documento" )} · ${escapar(semestres)}</span><small>${escapar(grupo.registros.map(function (registro) { return registro.NOMBRE_ARCHIVO || registro.NOMBRE || "Grupo"; }).filter(Boolean).slice(0, 2).join(" / "))}</small></button>`;
    }).join("");
    items.querySelectorAll(".student-result").forEach(function (item) {
      item.addEventListener("click", function () {
        const estudiante = grupos.find(function (grupo) { return grupo.key === item.dataset.key; });
        if (estudiante) mostrar(estudiante);
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

  function convertirNumeroSemestre(registro) {
    const declarado = parseInt(registro && registro.SEMESTRE_ACADEMICO, 10);
    if (declarado >= 1 && declarado <= 4) return declarado;

    const periodo = String(registro && (registro.SEMESTRE || registro.PERIODO) || "").trim();
    const programa = String(registro && (registro.PROGRAMA || registro.NIVEL) || "").trim().toUpperCase();
    const match = periodo.match(/\d{4}-(1|3)/);
    if (!match) return null;

    const reglas = {
      "1-TL": 1,
      "1-TP": 3,
      "3-TL": 2,
      "3-TP": 4
    };

    return reglas[`${match[1]}-${programa}`] || null;
  }

  function nombreSemestre(numero) {
    const mapa = { 1: "1er semestre", 2: "2do semestre", 3: "3er semestre", 4: "4to semestre" };
    return mapa[numero] || `${numero} semestre`;
  }

  function resumenSemestre(registrosSemestre) {
    const asignaturas = new Set(registrosSemestre.map(function (registro) {
      return registro.ASIGNATURA;
    }).filter(Boolean));

    return {
      asignaturas: asignaturas.size,
      aprobadas: registrosSemestre.filter(function (registro) { return registro.ESTADO_NOTA === "APROBADA"; }).length,
      reprobadas: registrosSemestre.filter(function (registro) { return registro.ESTADO_NOTA === "REPROBADA"; }).length,
      sinNotas: registrosSemestre.filter(function (registro) { return registro.ESTADO_NOTA === "VACIA" || registro.ESTADO_NOTA === "NA"; }).length
    };
  }

  function construirHistorialSemestres(registros) {
    const semestres = [1, 2, 3, 4];
    const periodosDisponibles = registros.map(function (registro) {
      return String(registro.SEMESTRE || registro.PERIODO || "").trim();
    }).filter(Boolean);

    const baseYear = periodosDisponibles.length ? Math.min.apply(null, periodosDisponibles.map(function (periodo) {
      const match = periodo.match(/(\d{4})-(\d+)/);
      return match ? parseInt(match[1], 10) : 2026;
    })) : 2026;

    const periodosPorSemestre = {
      1: `${baseYear}-1`,
      2: `${baseYear}-3`,
      3: `${baseYear + 1}-1`,
      4: `${baseYear + 1}-3`
    };

    const numerosDisponibles = registros.map(function (nota) {
      return convertirNumeroSemestre(nota);
    }).filter(function (valor) {
      return valor !== null;
    });

    const primerSemestreDisponible = numerosDisponibles.length ? Math.min.apply(null, numerosDisponibles) : null;
    const ultimoSemestreDisponible = numerosDisponibles.length ? Math.max.apply(null, numerosDisponibles) : 0;

    return semestres.map(function (numeroSemestre) {
      const semestrePeriodo = periodosPorSemestre[numeroSemestre] || "—";
      const registrosDeSemestre = registros.filter(function (registro) {
        const numero = convertirNumeroSemestre(registro);
        return numero === numeroSemestre;
      });
      const hayInfo = registrosDeSemestre.length > 0;
      const grupos = [...new Set(registrosDeSemestre.map(function (registro) {
        return registro.NOMBRE_ARCHIVO || registro.ASIGNATURA || "Grupo";
      }).filter(Boolean))];

      if (hayInfo) {
        const resumen = resumenSemestre(registrosDeSemestre);
        const periodoReal = String(registrosDeSemestre[0].SEMESTRE || registrosDeSemestre[0].PERIODO || semestrePeriodo).trim();
        return {
          numero: numeroSemestre,
          estado: numeroSemestre === ultimoSemestreDisponible ? "actual" : "cursado",
          etiqueta: numeroSemestre === ultimoSemestreDisponible ? "Semestre actual" : "Cursado",
          titulo: `${nombreSemestre(numeroSemestre)}`,
          detalle: `${periodoReal}${grupos.length ? ` · ${grupos.join(" / ")}` : ""}`,
          resumen: resumen,
          mensaje: ""
        };
      }

      if (primerSemestreDisponible !== null && numeroSemestre < primerSemestreDisponible) {
        return {
          numero: numeroSemestre,
          estado: "historico",
          etiqueta: "Sin datos históricos",
          titulo: `${nombreSemestre(numeroSemestre)}`,
          detalle: `${semestrePeriodo} · Información histórica no disponible`,
          resumen: null,
          mensaje: "Información histórica no disponible"
        };
      }

      if (primerSemestreDisponible !== null && numeroSemestre > ultimoSemestreDisponible) {
        return {
          numero: numeroSemestre,
          estado: "no-cursado",
          etiqueta: "No cursado",
          titulo: `${nombreSemestre(numeroSemestre)}`,
          detalle: `${semestrePeriodo} · No cursado aún`,
          resumen: null,
          mensaje: "No cursado aún"
        };
      }

      if (primerSemestreDisponible === null) {
        return {
          numero: numeroSemestre,
          estado: "no-cursado",
          etiqueta: "No cursado",
          titulo: `${nombreSemestre(numeroSemestre)}`,
          detalle: `${semestrePeriodo} · No cursado aún`,
          resumen: null,
          mensaje: "No cursado aún"
        };
      }

      return {
        numero: numeroSemestre,
        estado: "historico",
        etiqueta: "Sin datos históricos",
        titulo: `${nombreSemestre(numeroSemestre)}`,
        detalle: `${semestrePeriodo} · Información histórica no disponible`,
        resumen: null,
        mensaje: "Información histórica no disponible"
      };
    });
  }

  function docenteObservacion(observacion, notasPerfil) {
    if (observacion && observacion.DOCENTE) {
      return observacion.DOCENTE;
    }

    const asignatura = String(observacion.ASIGNATURA || "").trim();
    const periodo = String(observacion.PERIODO || "").trim();
    const semestre = String(observacion.SEMESTRE || "").trim();

    const semi = notasPerfil.filter(function (nota) {
      const coincideAsignatura = !asignatura || String(nota.ASIGNATURA || "").trim().toLowerCase() === asignatura.toLowerCase();
      const coincidePeriodo = !periodo || String(nota.PERIODO || "").trim() === periodo;
      const coincideSemestre = !semestre || String(nota.SEMESTRE || "").trim() === semestre;
      return coincideAsignatura && coincidePeriodo && coincideSemestre && nota.DOCENTE;
    });

    if (semi.length) return semi[0].DOCENTE;

    const asignaturaMatch = notasPerfil.filter(function (nota) {
      return !asignatura || String(nota.ASIGNATURA || "").trim().toLowerCase() === asignatura.toLowerCase();
    });

    if (asignaturaMatch.length && asignaturaMatch[0].DOCENTE) return asignaturaMatch[0].DOCENTE;

    return "Información no disponible";
  }

  function construirNotasPorSemestre(registros) {
    const grupos = new Map();

    registros.forEach(function (nota) {
      const numero = convertirNumeroSemestre(nota);
      const clave = numero === null ? "sin-semestre" : String(numero);
      if (!grupos.has(clave)) {
        grupos.set(clave, []);
      }
      grupos.get(clave).push(nota);
    });

    return Array.from(grupos.entries()).sort(function (a, b) {
      if (a[0] === "sin-semestre") return 1;
      if (b[0] === "sin-semestre") return -1;
      return parseInt(a[0], 10) - parseInt(b[0], 10);
    }).map(function ([semestre, items]) {
      const numero = semestre === "sin-semestre" ? null : parseInt(semestre, 10);
      return {
        semestre: numero,
        titulo: numero === null ? "Semestre no disponible" : nombreSemestre(numero),
        registros: items
      };
    });
  }

  function generarEnlaceLista(idArchivo) {
    if (!idArchivo) {
      return "#";
    }

    return "https://docs.google.com/spreadsheets/d/" + encodeURIComponent(idArchivo.trim());
  }

  function periodoTarjeta(item) {
    return String(item.detalle || "").split(" · ")[0] || "—";
  }

  function construirObservacionesPorSemestre(historia, observacionesPerfil) {
    return historia.map(function (item) {
      const registrosSemestre = observacionesPerfil.filter(function (observacion) {
        return convertirNumeroSemestre(observacion) === item.numero;
      });

      let mensaje = "";
      if (item.estado === "no-cursado") {
        mensaje = "Semestre no cursado aún";
      } else if (item.estado === "historico") {
        mensaje = item.mensaje || "Información histórica no disponible";
      } else if (!registrosSemestre.length) {
        mensaje = "Sin observaciones registradas en este semestre";
      }

      return {
        numero: item.numero,
        titulo: item.titulo,
        periodo: periodoTarjeta(item),
        registros: registrosSemestre,
        mensaje: mensaje
      };
    });
  }

  function mostrar(estudiante) {
    lista.hidden = true;
    perfil.hidden = false;

    const registroPrincipal = estudiante.registros[0] || {};
    const notasPerfil = notas.filter(function (nota) {
      return coincidePersona(nota, registroPrincipal);
    });
    const observacionesPerfil = observaciones.filter(function (observacion) {
      return coincidePersona(observacion, registroPrincipal);
    });
    const historia = construirHistorialSemestres(notasPerfil);
    const aprobadas = notasPerfil.filter(function (nota) { return nota.ESTADO_NOTA === "APROBADA"; }).length;
    const reprobadas = notasPerfil.filter(function (nota) { return nota.ESTADO_NOTA === "REPROBADA"; }).length;
    const pendientes = notasPerfil.filter(function (nota) { return nota.ESTADO_NOTA === "VACIA" || nota.ESTADO_NOTA === "NA"; }).length;
    const nombreCompleto = String(registroPrincipal.NOMBRE || estudiante.nombre || "Estudiante").trim();
    const documentoCompleto = String(registroPrincipal.DOCUMENTO || estudiante.documento || "—").trim();
    const archivoPrincipal = String(registroPrincipal.NOMBRE_ARCHIVO || "Grupo académico").trim();
    const semestresListado = estudiante.semestres.length ? estudiante.semestres.join(" · ") : "Sin historial";

    document.getElementById("identidadEstudiante").innerHTML = `<div><span class="eyebrow">Perfil académico</span><h2>${escapar(nombreCompleto)}</h2><p>${escapar(documentoCompleto)} · ${escapar(semestresListado)}</p></div><span class="status-pill">${escapar(archivoPrincipal)}</span>`;
    document.getElementById("metricasEstudiante").innerHTML = [["Asignaturas", notasPerfil.length], ["Aprobadas", aprobadas], ["Reprobadas", reprobadas], ["Pendientes", pendientes]].map(function (metrica) { return `<div class="metric"><span>${metrica[0]}</span><strong>${metrica[1]}</strong></div>`; }).join("");
    document.getElementById("contextoEstudiante").innerHTML = [["Nivel académico", registroPrincipal.NIVEL], ["Semestre", registroPrincipal.SEMESTRE], ["Programa / grupo", registroPrincipal.NOMBRE_ARCHIVO], ["Número", registroPrincipal.NUMERO], ["Documento", registroPrincipal.DOCUMENTO], ["Institución", registroPrincipal.INSTITUCION], ["Correo", registroPrincipal.CORREO], ["Teléfono", registroPrincipal.TELEFONO], ["Estado", registroPrincipal.ESTADO], ["Asignaturas a repetir", registroPrincipal.ASIGNATURAS_A_REPETIR]].map(function (dato) { return `<div class="info-item"><span>${dato[0]}</span><strong>${escapar(texto(dato[1]))}</strong></div>`; }).join("");

    document.getElementById("historialEstudiante").innerHTML = historia.map(function (item) {
      const contenido = item.resumen ? `<div class="semester-summary"><h4>Resumen académico</h4><ul><li>Asignaturas cursadas: ${item.resumen.asignaturas}</li><li>Aprobadas: ${item.resumen.aprobadas}</li><li>Reprobadas: ${item.resumen.reprobadas}</li><li>Sin notas: ${item.resumen.sinNotas}</li></ul></div>` : `<div class="semester-summary empty"><p>${escapar(item.mensaje)}</p></div>`;
      return `<div class="semester-card semester-${item.estado}"><div class="semester-card-header"><strong>${escapar(item.titulo)}</strong><span class="semester-badge">${escapar(item.etiqueta)}</span></div><p>${escapar(item.detalle)}</p>${contenido}</div>`;
    }).join("");

    const notasPorSemestre = construirNotasPorSemestre(notasPerfil);
    document.getElementById("notasEstudiante").innerHTML = notasPorSemestre.map(function (bloque) {
      const rows = bloque.registros.map(function (nota) {
        const idArchivo = nota.ID_ARCHIVO || "";
        const tipoNota = nota.TIPO_EVALUACION || "Información no disponible";
        return `<tr><td><strong>${escapar(nota.ASIGNATURA || "Sin asignatura")}</strong><small>${escapar(nota.DURACION || "Sin semanas")}</small></td><td>${escapar(nota.DOCENTE || "Información no disponible")}</td><td>${escapar(nota.SEMESTRE || "—")}</td><td>${escapar(nota.PERIODO || "—")}</td><td>${escapar(tipoNota)}</td><td class="grade">${escapar(nota.VALOR_ORIGINAL || "—")}</td><td><span class="grade-status status-${String(nota.ESTADO_NOTA || "VACIA").toLowerCase()}">${escapar(nota.ESTADO_NOTA || "Sin nota")}</span></td><td>${idArchivo ? `<a class="list-link" href="${generarEnlaceLista(idArchivo)}" target="_blank" rel="noopener noreferrer" title="Ir a la lista" aria-label="Ir a la lista">📋</a>` : "Sin enlace"}</td></tr>`;
      }).join("");

      return `<div class="semester-performance"><div class="semester-performance-header"><h3>${escapar(bloque.titulo)}</h3></div><div class="table-wrap"><table><thead><tr><th>Asignatura</th><th>Docente</th><th>Semestre</th><th>Periodo</th><th>Tipo</th><th>Nota</th><th>Estado</th><th>Lista</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
    }).join("") || "<p>No hay notas registradas.</p>";

    const observacionesPorSemestre = construirObservacionesPorSemestre(historia, observacionesPerfil);
    document.getElementById("observacionesEstudiante").innerHTML = observacionesPorSemestre.map(function (bloque) {
      const cuerpo = bloque.registros.length ? bloque.registros.map(function (observacion) {
        const docente = docenteObservacion(observacion, notasPerfil);
        const contexto = observacion.SEMESTRE ? `${escapar(observacion.SEMESTRE)}${observacion.PERIODO ? ` · ${escapar(observacion.PERIODO)}` : ""}` : "Semestre no disponible";
        const nombreAsignatura = observacion.ASIGNATURA || "Asignatura no disponible";
        return `<article><div class="observation-meta"><strong>${escapar(nombreAsignatura)}</strong><span>${escapar(contexto)}</span></div><p class="observation-teacher"><strong>Docente:</strong> ${escapar(docente)}</p><p>${escapar(observacion.OBSERVACION || "Sin observación registrada.")}</p></article>`;
      }).join("") : `<p>${escapar(bloque.mensaje)}</p>`;

      return `<div class="semester-performance"><div class="semester-performance-header"><h3>${escapar(bloque.titulo)} – ${escapar(bloque.periodo)}</h3></div><div class="observation-list">${cuerpo}</div></div>`;
    }).join("");
  }

  function cambiarModo(modo) {
    const esGrupo = modo === "grupo";
    const esIndividual = modo === "individual";
    consultaIndividual.hidden = !esIndividual;
    consultaGrupo.hidden = !esGrupo;
    resultadoGrupo.hidden = true;
    lista.hidden = true;
    perfil.hidden = true;
    document.querySelectorAll(".student-mode-card").forEach(function (tarjeta) {
      tarjeta.classList.toggle("student-mode-card-active", tarjeta.dataset.modo === modo);
    });
  }

  function registrosGrupo() {
    return estudiantes.filter(function (registro) {
      return registro.ID_ARCHIVO || registro.NOMBRE_ARCHIVO;
    });
  }

  function valorGrupo(registro, campo) {
    return String(registro[campo] || "").trim();
  }

  function nombreGrupoDesdeRegistro(registro) {
    return valorGrupo(registro, "NOMBRE_ARCHIVO");
  }

  function opcionesGrupo(filtros) {
    return registrosGrupo().filter(function (registro) {
      return (!filtros.semestre || valorGrupo(registro, "SEMESTRE") === filtros.semestre || valorGrupo(registro, "SEMESTRE_ACADEMICO") === filtros.semestre)
        && (!filtros.nivel || valorGrupo(registro, "NIVEL") === filtros.nivel);
    });
  }

  function valoresGrupo(registros, campo) {
    return [...new Set(registros.map(function (registro) { return valorGrupo(registro, campo); }).filter(Boolean))].sort(function (a, b) {
      return a.localeCompare(b, "es");
    });
  }

  function llenarGrupo(selector, valores, texto, deshabilitado) {
    const valorActual = selector.value;
    selector.innerHTML = `<option value="">${texto}</option>`;
    valores.forEach(function (valor) {
      selector.insertAdjacentHTML("beforeend", `<option value="${escapar(valor)}">${escapar(valor)}</option>`);
    });
    selector.disabled = deshabilitado;
    if (valores.includes(valorActual)) selector.value = valorActual;
  }

  function poblarSemestresGrupo() {
    const semestres = valoresGrupo(registrosGrupo(), "SEMESTRE").filter(function (valor) {
      return /^\d{4}-(?:1|3)$/.test(valor);
    });
    llenarGrupo(filtroGrupoSemestre, semestres, "Selecciona un semestre", false);
  }

  function poblarFiltrosGrupo() {
    const semestre = filtroGrupoSemestre.value;
    const contextoSemestre = opcionesGrupo({ semestre: semestre });
    llenarGrupo(filtroGrupoNivel, valoresGrupo(contextoSemestre, "NIVEL"), "Selecciona un nivel", !semestre);
    const nivel = filtroGrupoNivel.value;
    const contextoNivel = opcionesGrupo({ semestre: semestre, nivel: nivel });
    const grupos = [...new Set(contextoNivel.map(nombreGrupoDesdeRegistro).filter(Boolean))].sort(function (primero, segundo) {
      const numeroPrimero = parseInt(primero.match(/grupo\s+(\d+)/i)?.[1] || "0", 10);
      const numeroSegundo = parseInt(segundo.match(/grupo\s+(\d+)/i)?.[1] || "0", 10);
      return numeroPrimero - numeroSegundo || primero.localeCompare(segundo, "es");
    });
    llenarGrupo(filtroGrupoNombre, grupos, "Selecciona un grupo y programa", !nivel);
    document.getElementById("btnConsultarGrupo").disabled = true;
  }

  function mismoSemestre(registro, semestre) {
    return valorGrupo(registro, "SEMESTRE_ACADEMICO") === semestre || valorGrupo(registro, "SEMESTRE") === semestre;
  }

  function consultarGrupo() {
    const miembros = registrosGrupo().filter(function (registro) {
      return mismoSemestre(registro, filtroGrupoSemestre.value)
        && valorGrupo(registro, "NIVEL") === filtroGrupoNivel.value
        && nombreGrupoDesdeRegistro(registro) === filtroGrupoNombre.value;
    });
    if (!miembros.length) return;
    const fuentes = new Set(miembros.map(function (registro) {
      return valorGrupo(registro, "ID_ARCHIVO") + "|" + valorGrupo(registro, "ID_HOJA");
    }));
    const notasGrupo = notas.filter(function (nota) {
      return fuentes.has(valorGrupo(nota, "ID_ARCHIVO") + "|" + valorGrupo(nota, "ID_HOJA"));
    });
    const observacionesGrupo = observaciones.filter(function (observacion) {
      return fuentes.has(valorGrupo(observacion, "ID_ARCHIVO") + "|" + valorGrupo(observacion, "ID_HOJA"));
    });
    renderizarGrupo(miembros[0], miembros, notasGrupo, observacionesGrupo);
  }

  function renderizarGrupo(grupo, miembros, notasGrupo, observacionesGrupo) {
    const estudiantesGrupo = agruparEstudiantes(miembros).sort(function (a, b) { return a.nombre.localeCompare(b.nombre, "es"); });
    const materias = [...new Map(notasGrupo.map(function (nota) {
      return [String(nota.ASIGNATURA || "Sin asignatura"), nota];
    })).values()];
    document.getElementById("resumenGrupo").innerHTML = `<div><span class="eyebrow">Grupo seleccionado</span><h2>${escapar(grupo.NOMBRE_ARCHIVO || "Grupo académico")}</h2><p>${escapar([grupo.PROGRAMA, grupo.NIVEL, grupo.SEMESTRE_ACADEMICO || grupo.SEMESTRE].filter(Boolean).join(" · "))}</p></div><strong>${estudiantesGrupo.length} estudiantes</strong>`;
    const encabezadoMaterias = materias.map(function (materia) { return `<th colspan="2">${escapar(materia.ASIGNATURA || "Sin asignatura")}</th>`; }).join("");
    const subencabezadoMaterias = materias.map(function () { return "<th>Nota</th><th>Obs.</th>"; }).join("");
    const filas = estudiantesGrupo.map(function (estudiante, indice) {
      const registro = estudiante.registros[0] || {};
      const notasEstudiante = notasGrupo.filter(function (nota) { return coincidePersona(nota, registro); });
      const observacionesEstudiante = observacionesGrupo.filter(function (observacion) { return coincidePersona(observacion, registro); });
      const celdas = materias.map(function (materia) {
        const nota = notasEstudiante.find(function (item) { return item.ASIGNATURA === materia.ASIGNATURA && item.VALOR_ORIGINAL; })
          || notasEstudiante.find(function (item) { return item.ASIGNATURA === materia.ASIGNATURA; });
        const observacion = observacionesEstudiante.find(function (item) { return item.ASIGNATURA === materia.ASIGNATURA; });
        const valorNota = nota && (nota.VALOR_ORIGINAL || nota.NOTA || nota.ESTADO_NOTA) ? (nota.VALOR_ORIGINAL || nota.NOTA || nota.ESTADO_NOTA) : "—";
        return `<td class="group-grade">${escapar(valorNota)}</td><td>${observacion && observacion.OBSERVACION ? `<button class="observation-button" type="button" data-observacion="${escapar(JSON.stringify({ estudiante: estudiante.nombre, materia: materia.ASIGNATURA, docente: observacion.DOCENTE, texto: observacion.OBSERVACION }))}" title="Ver observación" aria-label="Ver observación">👁</button>` : "—"}</td>`;
      }).join("");
      const enlace = registro.ID_ARCHIVO ? `<a class="list-link" href="${generarEnlaceLista(registro.ID_ARCHIVO)}" target="_blank" rel="noopener noreferrer" title="Ir a la lista" aria-label="Ir a la lista">📋</a>` : "—";
      return `<tr><td>${indice + 1}</td><td><strong>${escapar(estudiante.nombre)}</strong><small>${escapar(estudiante.documento || "Sin documento")}</small></td>${celdas}<td>${enlace}</td></tr>`;
    }).join("");
    document.getElementById("tablaGrupoWrap").innerHTML = `<table class="group-table"><thead><tr><th rowspan="2">N.º</th><th rowspan="2">Nombre</th>${encabezadoMaterias}<th rowspan="2">Acciones</th></tr><tr>${subencabezadoMaterias}</tr></thead><tbody>${filas || `<tr><td colspan="${3 + materias.length * 2}">No hay estudiantes para este grupo.</td></tr>`}</tbody></table>`;
    resultadoGrupo.hidden = false;
    activarScrollHorizontal();
    resultadoGrupo.querySelectorAll(".observation-button").forEach(function (boton) {
      boton.addEventListener("click", function () { abrirObservacion(JSON.parse(boton.dataset.observacion)); });
    });
  }

  function activarScrollHorizontal() {
    const contenedor = document.getElementById("tablaGrupoWrap");
    if (contenedor.dataset.scrollActivo) return;
    contenedor.dataset.scrollActivo = "true";
    contenedor.addEventListener("wheel", function (evento) {
      if (contenedor.scrollWidth <= contenedor.clientWidth) return;
      if (Math.abs(evento.deltaY) <= Math.abs(evento.deltaX)) return;
      contenedor.scrollLeft += evento.deltaY;
      evento.preventDefault();
    }, { passive: false });
  }

  function limpiarGrupo() {
    filtroGrupoSemestre.value = "";
    filtroGrupoNivel.value = "";
    filtroGrupoNombre.value = "";
    poblarFiltrosGrupo();
    resultadoGrupo.hidden = true;
  }

  function abrirObservacion(datos) {
    document.getElementById("tituloObservacion").textContent = datos.materia || "Observación";
    document.getElementById("contenidoObservacion").innerHTML = `<p><strong>Estudiante:</strong> ${escapar(datos.estudiante)}</p><p><strong>Docente:</strong> ${escapar(datos.docente || "Información no disponible")}</p><p class="observation-modal-text">${escapar(datos.texto)}</p>`;
    document.getElementById("modalObservacion").hidden = false;
  }

  function cerrarObservacion() {
    document.getElementById("modalObservacion").hidden = true;
  }

  function cerrarSesion() {
    sessionStorage.clear();
    limpiarColecciones().finally(function () {
      window.location.href = "index.html";
    });
  }
});
