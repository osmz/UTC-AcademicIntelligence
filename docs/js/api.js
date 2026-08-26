/**
 * api.js - Comunicación con Google Apps Script
 */

//const API_URL = "https://script.google.com/macros/s/AKfycbwmj8qm20Du1kDdr6PX-kr3TX5y6PwuKTkCk36fT5sRpypzaIi6nAJe7PMfpDJ_trw/exec";
const API_URL = "https://script.google.com/macros/s/AKfycbyJBHCrl8RWe4kNA0iYSeauKLKePPDuh_Y0Jo4Mc2a0CnHnrrAjfyksdyomIz8t1M-g/exec";

/**
 * login() - Valida usuario y contraseña contra Apps Script
 */
async function login(usuario, clave) {
  try {
    const response = await fetch(API_URL, {
      method: "POST",
      body: JSON.stringify({
        usuario,
        clave
      })
    });

    if (!response.ok) {
      throw new Error("Error al conectar con el servidor");
    }

    const data = await response.json();

    // Si el servidor retorna un error
    if (data.error) {
      throw new Error(data.error);
    }

    // Acepta tanto la respuesta antigua (arreglo) como la nueva (objeto).
    const informacion = Array.isArray(data)
      ? { docentes: data }
      : data;

    return {
      success: true,
      docentes: informacion.docentes || [],
      estudiantes: informacion.estudiantes || [],
      asignaturas: informacion.asignaturas || [],
      notas: informacion.notas || [],
      observaciones: informacion.observaciones || [],
      seguimiento: informacion.seguimiento || []
    };

  } catch (err) {
    console.error("❌ Error en login:", err);
    return {
      success: false,
      error: err.message || "Error desconocido"
    };
  }
}

/**
 * formatearFecha() - Convierte fecha ISO a formato yyyy/mm/dd
 */
function formatearFecha(fechaISO) {
  if (!fechaISO) return "—";
  try {
    const fecha = new Date(fechaISO);
    const year = fecha.getFullYear();
    const mes = String(fecha.getMonth() + 1).padStart(2, '0');
    const dia = String(fecha.getDate()).padStart(2, '0');
    return `${dia}/${mes}/${year}`;
  } catch (e) {
    return fechaISO;
  }
}
