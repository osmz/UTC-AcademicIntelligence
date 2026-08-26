import pandas as pd
from googleapiclient.discovery import build
from google.oauth2 import service_account


# ============================================================
# 1. CONFIGURACIÓN
# ============================================================

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

KEY = 'key.json'

SPREADSHEET_ID = '1LLZJ0N3ZjFn0Wji6ZEFf5J4aQe6c46LbD7iVCMlZ5Yk'

RANGE = 'Jenny!A1:M43'


# ============================================================
# 2. AUTENTICACIÓN CON GOOGLE
# ============================================================

creds = service_account.Credentials.from_service_account_file(
    KEY,
    scopes=SCOPES
)


# ============================================================
# 3. CONEXIÓN CON GOOGLE SHEETS
# ============================================================

service = build(
    'sheets',
    'v4',
    credentials=creds
)

sheet = service.spreadsheets()


# ============================================================
# 4. LEER INFORMACIÓN DE GOOGLE SHEETS
# ============================================================

result = sheet.values().get(
    spreadsheetId=SPREADSHEET_ID,
    range=RANGE
).execute()

values = result.get('values', [])


if not values:
    raise ValueError("No se encontraron datos en la hoja.")


# ============================================================
# 5. IDENTIFICAR LAS FILAS IMPORTANTES
# ============================================================

# Índices Python:
#
# 0 → título
# 1 → "Docente"
# 2 → nombre docente
# 3 → duración
# 4 → número
# 5 → evaluación
# 6 → encabezados
# 7 → primer estudiante

fila_docente = values[2]
fila_duracion = values[3]
fila_numero = values[4]
fila_evaluacion = values[5]
fila_encabezados = values[6]


# ============================================================
# 6. COMPLETAR LOS VALORES VACÍOS DE LOS METADATOS
# ============================================================

def rellenar_hacia_derecha(fila):
    """
    Si una celda está vacía, conserva el último valor encontrado.

    Ejemplo:

    ['Fernando Escobar Gomez', '', 'Juan Diego Villamil Sierra']

    se convierte en:

    ['Fernando Escobar Gomez',
     'Fernando Escobar Gomez',
     'Juan Diego Villamil Sierra']
    """

    resultado = []
    ultimo_valor = ''

    for valor in fila:

        if valor != '':
            ultimo_valor = valor

        resultado.append(ultimo_valor)

    return resultado


docentes = rellenar_hacia_derecha(fila_docente)
duraciones = rellenar_hacia_derecha(fila_duracion)


# ============================================================
# 7. CONSTRUIR DATAFRAME DE ASIGNATURAS
# ============================================================

# La fila de encabezados puede tener celdas vacías
# porque una asignatura puede ocupar varias columnas.
#
# Ejemplo:
#
# Cálculo Integral | '' | Automatismos PLC
#
# Debemos interpretar:
#
# Cálculo Integral | Cálculo Integral | Automatismos PLC

asignaturas_nombres = rellenar_hacia_derecha(
    fila_encabezados[7:]
)

asignaturas = []

for posicion, asignatura in enumerate(asignaturas_nombres):

    # Índice real de la columna en Google Sheets
    i = posicion + 7

    asignaturas.append({
        'columna': i,
        'asignatura': asignatura.strip(),
        'docente': docentes[i].strip(),
        'duracion': duraciones[i].strip(),
        'periodo': f"Periodo {fila_numero[i]}",
        'evaluacion': fila_evaluacion[i].strip()
    })


asignaturas_df = pd.DataFrame(asignaturas)


# ============================================================
# 8. CONSTRUIR DATAFRAME DE ESTUDIANTES
# ============================================================

datos_estudiantes = values[7:]

estudiantes_df = pd.DataFrame(
    datos_estudiantes,
    columns=fila_encabezados
)


# ============================================================
# 9. MOSTRAR RESULTADOS
# ============================================================

print("\n" + "=" * 70)
print("DATAFRAME DE ASIGNATURAS")
print("=" * 70)

print(asignaturas_df.to_string(index=False))


print("\n" + "=" * 70)
print("DATAFRAME DE ESTUDIANTES")
print("=" * 70)

print(estudiantes_df.to_string(index=False))


print("\n" + "=" * 70)
print("RESUMEN")
print("=" * 70)

print("Cantidad de estudiantes:", len(estudiantes_df))
print("Cantidad de columnas de estudiantes:", len(estudiantes_df.columns))
print("Cantidad de registros de asignaturas:", len(asignaturas_df))