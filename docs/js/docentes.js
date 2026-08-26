/**
 * docentes.js - Búsqueda y visualización de docentes
 */

let allDocentes = [];

document.addEventListener("DOMContentLoaded", function () {
  // Verificar si el usuario está logueado
  if (!sessionStorage.getItem("logueado")) {
    window.location.href = "index.html";
    return;
  }

  // Cargar docentes desde sessionStorage
  const docentesJSON = sessionStorage.getItem("docentes");
  if (docentesJSON) {
    allDocentes = JSON.parse(docentesJSON);
  }

  // Elementos del DOM
  const inputBusqueda = document.getElementById("busqueda");
  const btnBuscar = document.getElementById("btnBuscar");
  const btnLimpiar = document.getElementById("btnLimpiar");
  const btnVolverModulos = document.getElementById("btnVolverModulos");
  const btnLogout = document.getElementById("btnLogout");
  const divResultadoContainer = document.getElementById("resultadoContainer");
  const divResultadosMultiplesContainer = document.getElementById("resultadosMultiplesContainer");
  const divListaResultados = document.getElementById("listaResultados");
  const divError = document.getElementById("error");
  const usuario = document.getElementById("usuarioSpan");

  // Mostrar usuario logueado
  const usuarioLogueado = sessionStorage.getItem("usuario");
  if (usuario) {
    usuario.textContent = usuarioLogueado;
  }

  /**
   * Buscar docente
   */
  function buscarDocente() {
    const termino = inputBusqueda.value.trim().toLowerCase();

    if (!termino) {
      divError.style.display = "none";
      divResultadoContainer.style.display = "none";
      divResultadosMultiplesContainer.style.display = "none";
      return;
    }

    const resultados = allDocentes.filter(doc => {
      const nombre = (doc["Nombre Completo"] || "").toLowerCase();
      const numId = (doc["Número de Identificación"] || "").toString().toLowerCase();
      const departamento = (doc["Departamento"] || "").toLowerCase();
      const nombre1 = (doc["Primer Nombre"] || "").toLowerCase();
      const apellido1 = (doc["Primer Apellido"] || "").toLowerCase();

      return (
        nombre.includes(termino) ||
        numId.includes(termino) ||
        departamento.includes(termino) ||
        nombre1.includes(termino) ||
        apellido1.includes(termino)
      );
    });

    if (resultados.length === 0) {
      mostrarError("❌ No se encontró ningún docente con ese criterio");
      divResultadoContainer.style.display = "none";
      divResultadosMultiplesContainer.style.display = "none";
      return;
    }

    // Si hay UN SOLO resultado
    if (resultados.length === 1) {
      divResultadosMultiplesContainer.style.display = "none";
      mostrarDocente(resultados[0]);
      divError.style.display = "none";
      divResultadoContainer.style.display = "block";
      return;
    }

    // Si hay MÚLTIPLES resultados
    mostrarListaResultados(resultados);
    divError.style.display = "none";
    divResultadoContainer.style.display = "none";
  }

  /**
   * Mostrar lista de docentes para seleccionar
   */
  function mostrarListaResultados(resultados) {
    divListaResultados.innerHTML = "";

    resultados.forEach((doc) => {
      const item = document.createElement("div");
      item.style.cssText = `
        background: white;
        border: 2px solid #0069A3;
        border-radius: 6px;
        padding: 15px;
        cursor: pointer;
        transition: all 0.3s;
        display: flex;
        justify-content: space-between;
        align-items: center;
      `;

      item.innerHTML = `
        <div>
          <div style="font-weight: bold; color: #0069A3; font-size: 14px;">${doc["Nombre Completo"] || "—"}</div>
          <div style="color: #666; font-size: 12px;">ID: ${doc["Número de Identificación"] || "—"} | ${doc["Departamento"] || "—"}</div>
          <div style="color: #999; font-size: 11px;">${doc["Cargo"] || "—"}</div>
        </div>
        <button style="
          background: #0069A3;
          color: white;
          border: none;
          padding: 8px 12px;
          border-radius: 4px;
          cursor: pointer;
          font-weight: bold;
        ">Ver</button>
      `;

      item.addEventListener("mouseenter", () => {
        item.style.background = "#e3f2fd";
        item.style.borderColor = "#F4D73B";
        item.style.boxShadow = "0 4px 8px rgba(0, 0, 0, 0.15)";
      });

      item.addEventListener("mouseleave", () => {
        item.style.background = "white";
        item.style.borderColor = "#0069A3";
        item.style.boxShadow = "none";
      });

      item.addEventListener("click", () => {
        mostraDocenteYOcultarLista(doc);
      });

      divListaResultados.appendChild(item);
    });

    divResultadosMultiplesContainer.style.display = "block";
  }

  /**
   * Mostrar docente seleccionado
   */
  function mostraDocenteYOcultarLista(doc) {
    mostrarDocente(doc);
    divResultadosMultiplesContainer.style.display = "none";
    divResultadoContainer.style.display = "block";
    window.scrollTo(0, 0);
  }

  /**
   * Llenar formulario con datos del docente
   */
  function mostrarDocente(doc) {
    // Encabezado y KPIs
    document.getElementById("cargo").textContent = doc["Cargo"] || "—";
    document.getElementById("nombreCompleto").textContent = doc["Nombre Completo"] || "—";

    function formatearAnos(valor) {
      if (!valor && valor !== 0) return "—";
      const str = String(valor).trim();
      if (str === "" || str === "—") return "—";
      return str.toLowerCase().includes("año") ? str : `${str} años`;
    }

    document.getElementById("kpiAnosDocencia").textContent = formatearAnos(doc["Docencia (años)"]);
    document.getElementById("kpiAnosUam").textContent = formatearAnos(doc["UAM (años)"]);
    document.getElementById("kpiAnosInvestigacion").textContent = formatearAnos(doc["Investigacion (años)"]);
    document.getElementById("kpiAnosProfesional").textContent = formatearAnos(doc["Profesional (años)"]);

    // Información Personal
    document.getElementById("tipoId").textContent = doc["Tipo de Identificación"] || "—";
    document.getElementById("numeroId").textContent = doc["Número de Identificación"] || "—";
    document.getElementById("lugarExp").textContent = doc["Lugar de Expedición"] || "—";
    document.getElementById("fechaExp").textContent = formatearFecha(doc["Fecha de Expedición"]);
    document.getElementById("nombre1").textContent = doc["Primer Nombre"] || "—";
    document.getElementById("nombre2").textContent = doc["Segundo Nombre"] || "—";
    document.getElementById("apellido1").textContent = doc["Primer Apellido"] || "—";
    document.getElementById("apellido2").textContent = doc["Segundo Apellido"] || "—";
    document.getElementById("fechaNac").textContent = formatearFecha(doc["Fecha de Nacimiento"]);
    document.getElementById("edad").textContent = doc["Edad"] || "—";
    document.getElementById("contacto").textContent = doc["Número de Contacto"] || "—";
    document.getElementById("rh").textContent = doc["RH"] || "—";
    document.getElementById("genero").textContent = doc["Genero"] || "—";
    document.getElementById("direccion").textContent = doc["Dirección"] || "—";
    document.getElementById("estadoCivil").textContent = doc["Estado civil"] || "—";

    // Información Laboral
    document.getElementById("departamento").textContent = doc["Departamento"] || "—";
    document.getElementById("estadoActual").textContent = doc["Estado actual"] || "—";
    document.getElementById("fechaInicioVinculacion").textContent = formatearFecha(doc["Fecha Inicio Vinculación"]);
    document.getElementById("fechaFinVinculacion").textContent = formatearFecha(doc["Fecha Fin Vinculación"]);
    document.getElementById("fechaNovedad").textContent = formatearFecha(doc["Fecha de la Novedad"]);
    document.getElementById("tiempoPrograma").textContent = doc["Tiempo en el Programa"] || "—";
    document.getElementById("dedicacion").textContent = doc["Dedicación"] || "—";
    document.getElementById("correoIns").textContent = doc["Correo Institucional"] || "—";
    document.getElementById("correoPersonal").textContent = doc["Correo Personal"] || "—";

    // Información de Contratación
    document.getElementById("formaContratacion").textContent = doc["Forma de Contratación (TF-TINDE)"] || doc["Forma de Contratación"] || "—";
    document.getElementById("escalafon").textContent = doc["Escalafón"] || "—";

    // Trayectoria y Experiencia
    document.getElementById("anoTarjetaProf").textContent = doc["Año en el que solicito la tarjeta profesional"] || "—";
    document.getElementById("anoInicioDocente").textContent = doc["Año en el que dio inicio como docente"] || "—";
    document.getElementById("anoInicioInvestigador").textContent = doc["Año en el que dio inicio como investigador"] || "—";
    document.getElementById("anoIngresoUam").textContent = doc["Año en el que ingreso a la UAM como docente"] || "—";
    document.getElementById("anosProfesional").textContent = doc["Profesional (años)"] || "—";
    document.getElementById("anosDocencia").textContent = doc["Docencia (años)"] || "—";
    document.getElementById("anosFormacionPedagogica").textContent = doc["Formacion pedagogica (años)"] || "—";
    document.getElementById("anosInvestigacion").textContent = doc["Investigacion (años)"] || "—";
    document.getElementById("anosUam").textContent = doc["UAM (años)"] || "—";

    // Formación Académica
    document.getElementById("nivelFormacion").textContent = doc["Máximo Nivel de Formación"] || "—";
    document.getElementById("areaConocimiento").textContent = doc["Área de Conocimiento"] || "—";
    document.getElementById("titulo").textContent = doc["Titulo Obtenido"] || "—";
    document.getElementById("institucion").textContent = doc["Institución"] || "—";
    document.getElementById("pais").textContent = doc["Pais"] || "—";
    document.getElementById("tecnologia").textContent = doc["Tecnología"] || "—";
    document.getElementById("fechaTecnologia").textContent = formatearFecha(doc["Fecha Tecnología"]);
    document.getElementById("institucionTecnologia").textContent = doc["Institución Tecnología"] || "—";
    document.getElementById("paisTecnologia").textContent = doc["Pais Tecnología"] || "—";
    document.getElementById("especializacionTecnologia").textContent = doc["Especialización Tecnológica"] || "—";
    document.getElementById("fechaEspecializacionTecnologia").textContent = formatearFecha(doc["Fecha Especialización Tecnológica"]);
    document.getElementById("institucionEspecializacionTecnologia").textContent = doc["Institución Especialización Tecnológica"] || "—";
    document.getElementById("paisEspecializacionTecnologia").textContent = doc["Pais Especialización Tecnológica"] || "—";
    document.getElementById("pregrado").textContent = doc["Pregrado"] || "—";
    document.getElementById("fechaPregrado").textContent = formatearFecha(doc["Fecha Pregrado"]);
    document.getElementById("institucionPregrado").textContent = doc["Institución Pregrado"] || "—";
    document.getElementById("paisPregrado").textContent = doc["Pais Pregrado"] || "—";
    document.getElementById("pregrado2").textContent = doc["Pregrado 2"] || "—";
    document.getElementById("fechaPregrado2").textContent = formatearFecha(doc["Fecha Pregrado 2"]);
    document.getElementById("institucionPregrado2").textContent = doc["Institución Pregrado 2"] || "—";
    document.getElementById("paisPregrado2").textContent = doc["Pais Pregrado 2"] || "—";
    document.getElementById("especializacion").textContent = doc["Especialización"] || "—";
    document.getElementById("fechaEspecializacion").textContent = formatearFecha(doc["Fecha Especialización"]);
    document.getElementById("institucionEspecializacion").textContent = doc["Institución Especialización"] || "—";
    document.getElementById("paisEspecializacion").textContent = doc["Pais Especialización"] || "—";
    document.getElementById("maestria").textContent = doc["Maestría"] || "—";
    document.getElementById("fechaMaestria").textContent = formatearFecha(doc["Fecha Maestría"]);
    document.getElementById("institucionMaestria").textContent = doc["Institución Maestría"] || "—";
    document.getElementById("paisMaestria").textContent = doc["Pais Maestría"] || "—";
    document.getElementById("doctorado").textContent = doc["Doctorado"] || "—";
    document.getElementById("fechaDoctorado").textContent = formatearFecha(doc["Fecha Doctorado"]);
    document.getElementById("institucionDoctorado").textContent = doc["Institución Doctorado"] || "—";
    document.getElementById("paisDoctorado").textContent = doc["Pais Doctorado"] || "—";
  }

  /**
   * Mostrar error
   */
  function mostrarError(mensaje) {
    divError.textContent = mensaje;
    divError.style.display = "block";
  }

  /**
   * Limpiar búsqueda
   */
  function limpiar() {
    inputBusqueda.value = "";
    divError.style.display = "none";
    divResultadoContainer.style.display = "none";
    divResultadosMultiplesContainer.style.display = "none";
    inputBusqueda.focus();
  }

  /**
   * Cerrar sesión
   */
  function logout() {
    sessionStorage.clear();
    window.location.href = "index.html";
  }

  // Event listeners
  btnBuscar.addEventListener("click", buscarDocente);
  btnLimpiar.addEventListener("click", limpiar);
  btnVolverModulos.addEventListener("click", () => {
    window.location.href = "acceso.html";
  });
  btnLogout.addEventListener("click", logout);
  inputBusqueda.addEventListener("keypress", (e) => {
    if (e.key === "Enter") buscarDocente();
  });

  // Enfocar en input de búsqueda al cargar
  inputBusqueda.focus();
});
