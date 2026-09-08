/**
 * storage.js - Almacenamiento de colecciones grandes usando IndexedDB
 * sessionStorage tiene un límite de ~5-10MB; con los datos de dos semestres
 * (miles de notas/observaciones) esa cuota se excede, por eso las colecciones
 * pesadas se guardan en IndexedDB en lugar de sessionStorage.
 */
const DB_NOMBRE = "academic_intelligence_db";
const DB_VERSION = 1;
const STORE_NOMBRE = "colecciones";

function abrirDB() {
  return new Promise((resolve, reject) => {
    const solicitud = indexedDB.open(DB_NOMBRE, DB_VERSION);
    solicitud.onupgradeneeded = () => {
      solicitud.result.createObjectStore(STORE_NOMBRE);
    };
    solicitud.onsuccess = () => resolve(solicitud.result);
    solicitud.onerror = () => reject(solicitud.error);
  });
}

async function guardarColeccion(nombre, valor) {
  const db = await abrirDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NOMBRE, "readwrite");
    tx.objectStore(STORE_NOMBRE).put(valor, nombre);
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

async function leerColeccion(nombre) {
  const db = await abrirDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NOMBRE, "readonly");
    const solicitud = tx.objectStore(STORE_NOMBRE).get(nombre);
    solicitud.onsuccess = () => resolve(solicitud.result || []);
    solicitud.onerror = () => reject(solicitud.error);
  });
}

async function limpiarColecciones() {
  const db = await abrirDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_NOMBRE, "readwrite");
    tx.objectStore(STORE_NOMBRE).clear();
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}
