# Sistema de Información de Docentes

## 📋 Descripción
Aplicación web de control de acceso que permite visualizar información completa de docentes de la Universidad Autónoma de Manizales. El sistema utiliza un formulario de login seguro contra Google Apps Script y Google Sheets como base de datos.

**Arquitectura:**
- **Frontend:** HTML5 + CSS3 + Vanilla JavaScript (GitHub Pages)
- **Backend:** Google Apps Script con validación de credenciales
- **Base de Datos:** Google Sheets con hojas "TEACHERS_INFORMATION" y "USERS_INFORMATION"

---

## 🏗️ Estructura del Proyecto

```
UTC_General/
├── docs/                    # Sitio publicado por GitHub Pages
│   ├── index.html           # Página de login
│   ├── acceso.html          # Selector entre docentes y estudiantes
│   ├── estudiantes.html     # Consulta académica de estudiantes
│   ├── docentes.html        # Página de información de docentes
│   ├── css/                 # Estilos de la web
│   └── js/                  # JavaScript de la web
├── python/                  # Procesamiento de archivos académicos
│   ├── fase_01_archivos.py
│   ├── fase_02_estructura.py
│   ├── fase_03_publicacion.py
│   ├── fase_04_seguimiento.py
│   ├── fase_05_reportes.py
│   └── main.py
├── apps_script/             # Backend de Google Apps Script
│   └── codigo.gs
├── pruebas/                 # Scripts y pruebas exploratorias
├── datos_referencia/        # Archivos de referencia locales
├── config/                  # Configuración local, no publicada
│   └── key.json
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🔄 Flujo de Autenticación

```
┌─────────────┐
│ index.html  │  ← Usuario abre el sitio
└──────┬──────┘
       │
       ▼
┌──────────────────────────────┐
│ Ingresa usuario + contraseña │  ← login.js captura datos
└──────┬───────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ login() en api.js                │
│ Envía POST a Apps Script         │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ Apps Script (codigo.gs)          │
│ - validarUsuario()               │
│ - Compara contra hoja "USERS_INFORMATION" │
└──────┬───────────────────────────┘
       │
       ├─ ✅ Válido → Devuelve array de docentes
       │
       └─ ❌ Inválido → Devuelve { error: "..." }
       │
       ▼
┌──────────────────────────────────┐
│ login.js recibe respuesta         │
│ - Si OK: Guarda en sessionStorage │
│ - Redirige a docentes.html        │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│ docentes.html                    │
│ - Carga docentes de session      │
│ - Muestra buscador               │
│ - Botón "Cerrar Sesión"          │
└──────────────────────────────────┘
```

---

## 📁 Descripción de Archivos

### `docs/index.html` - Página de Login
**Responsabilidad:** Autenticación del usuario
- Formulario con campos: Usuario y Contraseña
- Validación de campos (no vacíos)
- Muestra estado de carga mientras se valida
- Mensaje de error si credenciales son inválidas
- Estilos responsivos y seguros

### `docs/docentes.html` - Página de Docentes
**Responsabilidad:** Búsqueda y visualización
- Buscador por: nombre, cédula, departamento
- Muestra lista si hay múltiples coincidencias
- Perfil completo en 4 secciones:
  - 👤 **Información Personal** (ID, nombres, apellidos, edad, etc.)
  - 💼 **Información Laboral** (departamento, cargo, correos, etc.)
       - 📋 **Información de Contratación** (forma de contratación y escalafón)
       - 🎓 **Formación Académica** con 2 niveles de visualización:
              - Resumen: máximo nivel, área, título, institución, país
              - 📖 Detalle de Formación: tecnología, especialización tecnológica, pregrado, pregrado 2, especialización, maestría y doctorado (cada uno con fecha, institución y país)
- Botón "Cerrar Sesión" que borra datos y vuelve a login

### `css/styles.css` - Estilos Generales
**Responsabilidad:** Diseño visual de ambas páginas
- **Login:** Centrado, tarjeta moderna, colores institucionales
- **Docentes:** Contenedor flexible, grid responsivo
- **Colores:** #0069A3 (azul institucional), #F4D73B (amarillo)
- **Tipografía:** Arial, estilos claros y legibles
- **Responsive:** Adapta a móvil, tablet y desktop

### `js/api.js` - Comunicación con Backend
**Responsabilidad:** Conectar frontend ↔ Apps Script
- `login(usuario, clave)` → Valida credenciales, retorna docentes
- `formatearFecha(fechaISO)` → Convierte yyyy-mm-dd a yyyy/mm/dd
- Errores claros si hay problemas de conexión

### `js/login.js` - Lógica del Login
**Responsabilidad:** Manejar el formulario de autenticación
- Captura el evento `submit` del formulario
- Valida que usuario y clave no estén vacíos
- Llama a `login()` de api.js
- Si es exitoso: Guarda datos en `sessionStorage` y redirige
- Si falla: Muestra el error y permite reintentar

### `js/docentes.js` - Lógica de Búsqueda
**Responsabilidad:** Búsqueda y visualización de docentes
- Verifica si usuario está autenticado (redirige a login si no)
- Carga docentes desde `sessionStorage`
- Busca por: nombre completo, cédula, departamento, primer nombre, apellido
- Muestra lista si encuentra múltiples coincidencias
- Renderiza perfil completo al seleccionar docente
- Botón "Logout" que borra sesión

### `apps_script/codigo.gs` - Backend en Google Apps Script
**Responsabilidad:** Validación segura de credenciales y datos
- `obtenerDocentes()` → Lee hoja "TEACHERS_INFORMATION" y retorna JSON
- `validarUsuario(usuario, clave)` → Busca en hoja "USERS_INFORMATION"
- `doPost(e)` → Punto de entrada, valida y retorna docentes o error

---

## 🔐 Estructura de Google Sheets

### Hoja "TEACHERS_INFORMATION"
Contiene información de los docentes. Ejemplo de columnas:
```
Nombre Completo | Número de Identificación | Cargo | Departamento | ...
XXXX XXXXX      | XXXXXXXX                 | Prof  | Ingeniería   | ...
```

**Campos destacados:**
- **Información Personal:** Identificación, nombres, nacimiento, contacto, dirección, estado civil
- **Información Laboral:** Departamento, estado actual, fechas de vinculación, dedicación, correos
- **Información de Contratación:** Forma de Contratación, Escalafón
- **Formación Académica (Resumen):** Máximo Nivel de Formación, Área de Conocimiento, Titulo Obtenido, Institución, Pais
- **Formación Académica (Detalle):**
       - Tecnología, Fecha Tecnología, Institución Tecnología, Pais Tecnología
       - Especialización Tecnológica, Fecha Especialización Tecnológica, Institución Especialización Tecnológica, Pais Especialización Tecnológica
       - Pregrado, Fecha Pregrado, Institución Pregrado, Pais Pregrado
       - Pregrado 2, Fecha Pregrado 2, Institución Pregrado 2, Pais Pregrado 2
       - Especialización, Fecha Especialización, Institución Especialización, Pais Especialización
       - Maestría, Fecha Maestría, Institución Maestría, Pais Maestría
       - Doctorado, Fecha Doctorado, Institución Doctorado, Pais Doctorado

### Hoja "USERS_INFORMATION"
Contiene credenciales autorizadas:
```
Usuario  | Contraseña   | rol
---------|--------------|----------
XXX      | XXXXX        | Coordinador
XXXXX    | XXXXX        | Coordinador
XXXX     | XXXXX        | Coordinador
```

---

## 🚀 Cómo Usar

### Para Usuarios Finales
1. Abre `docs/index.html` en el navegador
2. Ingresa usuario y contraseña (ej: `XXX` / `XXXXX`)
3. Haz clic en "Iniciar Sesión"
4. Usa el buscador para encontrar docentes
5. Haz clic en "Cerrar Sesión" para salir

### Para Desarrolladores

#### Probar en Local
```bash
# Instalar dependencias Python
pip install -r requirements.txt

# Ejecutar la fase 1
python python/fase_01_archivos.py

# Ejecutar la fase 2
python python/fase_02_estructura.py

# Ejecutar la publicación de fases 1 y 2 en Google Sheets
python -m python.fase_03_publicacion

# Calcular y publicar el seguimiento de notas
python -m python.fase_04_seguimiento

# Generar recordatorios y reporte de estudiantes reprobados
python -m python.fase_05_reportes

# Ejecutar todo el flujo usando una sola lectura de cada archivo origen
python -m python.main

# Abrir docs/index.html en el navegador
# (O usar un servidor local como Live Server de VS Code)
```

### GitHub Pages

Configura GitHub Pages para publicar la rama principal desde la carpeta `/docs`.
El archivo `docs/index.html` será la página de entrada del sitio.

La fase 3 actualiza las pestañas `ARCHIVOS`, `ESTUDIANTES`, `ASIGNATURAS`,
`OBSERVACIONES` y `NOTAS` del Spreadsheet de destino. La pestaña `DOCENTES`
no se modifica porque sus datos se cargan manualmente.

La fase 4 calcula y actualiza la pestaña `SEGUIMIENTO` a partir de `NOTAS`.
La fase 5 calcula y actualiza `RECORDATORIOS` y `REPORTE_ESTUDIANTES`.
El comando `python -m python.main` ejecuta el flujo completo reutilizando los
DataFrames en memoria. Las lecturas de los archivos origen no se repiten entre
las fases 3, 4 y 5.

#### Actualizar Docentes o Usuarios
1. Edita la hoja correspondiente en Google Sheets
2. Apps Script leerá automáticamente los cambios
3. Los cambios aparecen en la siguiente búsqueda

#### Agregar Nuevos Campos
1. Agrega la columna en Google Sheet
2. El código leerá automáticamente (usa nombres exactos de columnas)
3. Agrega el campo visual en `docs/docentes.html`
4. Mapea el campo en `docs/js/docentes.js` con el nombre exacto del encabezado

---

## ⚠️ Notas Importantes

### Validación de Credenciales
- Las credenciales se validan en **Apps Script** (servidor)
- Nunca se guarda la contraseña en el navegador
- Se usa `sessionStorage` solo para la sesión actual (se borra al cerrar tab)

### Nombres de Columnas
- Deben ser **exactos** (mayúsculas/minúsculas)
- Si cambias una columna en Google Sheet, actualiza `js/docentes.js` (mapeo)
- Verifica tildes y caracteres especiales: por ejemplo `Escalafón`, `Tecnología`, `Especialización Tecnológica`

### Espacios en Blanco
- El código usa `.trim()` para eliminar espacios accidentales
- Válido para usuario: `"XXX"` o `" XXX "`

### Tipos de Datos
- Las contraseñas en Google Sheet se guardan como **texto** (no números)
- Si una contraseña es `XXXX`, escribe `XXXX` (como texto)

---

## 🔧 Debugging

### Ver Logs de Apps Script
1. Abre Apps Script en Google Drive
2. Ve a **Ejecuciones** y abre la ejecución más reciente
3. Usa `Logger.log()` para ver qué validación está fallando

### Ver Datos en sessionStorage
En el navegador, abre **DevTools** (F12):
```javascript
console.log(sessionStorage.getItem("docentes"));
console.log(sessionStorage.getItem("usuario"));
```

### Errores Comunes
| Error | Causa | Solución |
|-------|-------|----------|
| "Credenciales inválidas" | Usuario o clave incorrectos | Verifica la hoja "USERS_INFORMATION" en Google Sheet |
| Página en blanco después de login | sessionStorage vacío | Verifica que Apps Script devuelva JSON válido |
| Búsqueda sin resultados | Campo de búsqueda vacío | Intenta con un nombre o cédula |

---

## 📊 Próximos Pasos

- ✅ Sistema de autenticación
- ✅ Búsqueda de docentes
- ✅ Visualización de perfil completo
- ⬜ Exportar información a PDF
- ⬜ Historial de búsquedas
- ⬜ Roles de usuario (admin, coordinador, etc.)

---

## 📧 Contacto

Para reportar errores o solicitar mejoras, contacta al equipo de desarrollo.

**Versión:** 2.1
**Última actualización:** Mayo 2026

