// 1️⃣ Obtener docentes (tu lógica original)
function obtenerDocentes() {
  const sheet = SpreadsheetApp
    .getActiveSpreadsheet()
    .getSheetByName("TEACHERS_INFORMATION");

  if (!sheet) {
    throw new Error("No existe la hoja TEACHERS_INFORMATION");
  }

  const values = sheet.getDataRange().getValues();
  const headers = values.shift();

  return values.map(row => {
    let obj = {};
    headers.forEach((h, i) => obj[h] = row[i] || "");
    return obj;
  });
}

function obtenerTabla(nombreHoja) {
  const sheet = SpreadsheetApp
    .getActiveSpreadsheet()
    .getSheetByName(nombreHoja);

  if (!sheet) {
    return [];
  }

  const values = sheet.getDataRange().getValues();

  if (values.length === 0) {
    return [];
  }

  const headers = values.shift();

  return values.map(row => {
    const registro = {};
    headers.forEach((header, index) => {
      registro[header] = row[index] ?? "";
    });
    return registro;
  });
}

function obtenerInformacionAcademica() {
  return {
    estudiantes: obtenerTabla("ESTUDIANTES"),
    asignaturas: obtenerTabla("ASIGNATURAS"),
    notas: obtenerTabla("NOTAS"),
    observaciones: obtenerTabla("OBSERVACIONES"),
    seguimiento: obtenerTabla("SEGUIMIENTO")
  };
}

// 2️⃣ Validar usuario y clave
function validarUsuario(usuario, clave) {
  const sheet = SpreadsheetApp
    .getActiveSpreadsheet()
    .getSheetByName("USERS_INFORMATION");

  const data = sheet.getDataRange().getValues();
  data.shift();

  // 🧪 DEBUG: Mostrar qué está buscando
  Logger.log("Buscando usuario: [" + usuario + "] clave: [" + clave + "]");
  Logger.log("Datos en sheet: " + JSON.stringify(data));

  return data.some(row => {
    // Convertir a string, trim, lowercase
    const usuarioSheet = String(row[0]).trim();
    const claveSheet = String(row[1]).trim();
    
    Logger.log("Comparando: [" + usuarioSheet + "] con [" + usuario + "]");
    
    return (
      usuarioSheet === String(usuario).trim()
      && claveSheet === String(clave).trim()
    );
  });
}

// 3️⃣ ÚNICO punto de entrada
function doPost(e) {
  const params = JSON.parse(e.postData.contents);

  const autorizado = validarUsuario(
    params.usuario,
    params.clave
  );

  if (!autorizado) {
    return ContentService
      .createTextOutput(
        JSON.stringify({ error: "Credenciales inválidas" })
      )
      .setMimeType(ContentService.MimeType.JSON);
  }

  const informacionAcademica = obtenerInformacionAcademica();

  return ContentService
    .createTextOutput(
      JSON.stringify({
        docentes: obtenerDocentes(),
        estudiantes: informacionAcademica.estudiantes,
        asignaturas: informacionAcademica.asignaturas,
        notas: informacionAcademica.notas,
        observaciones: informacionAcademica.observaciones,
        seguimiento: informacionAcademica.seguimiento
      })
    )
    .setMimeType(ContentService.MimeType.JSON);
}