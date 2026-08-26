from pathlib import Path

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

try:
    from .fase_01_archivos import ejecutar_fase_1
    from .fase_03_publicacion import (
        SPREADSHEET_ID,
        procesar_archivos,
        actualizar_pestana
    )
except ImportError:
    from fase_01_archivos import ejecutar_fase_1
    from fase_03_publicacion import (
        SPREADSHEET_ID,
        procesar_archivos,
        actualizar_pestana
    )


# ============================================================
# CONFIGURACION
# ============================================================

KEY = str(
    Path(__file__).resolve().parents[1]
    / 'config'
    / 'key.json'
)

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/spreadsheets'
]

COLUMNAS_SEGUIMIENTO = [
    'SEMESTRE',
    'NIVEL',
    'ID_ARCHIVO',
    'NOMBRE_ARCHIVO',
    'DOCENTE',
    'ASIGNATURA',
    'DURACION',
    'PERIODO',
    'TIPO_EVALUACION',
    'ESTADO',
    'TOTAL_ESTUDIANTES',
    'CANTIDAD_NOTAS',
    'APROBADOS',
    'REPROBADOS',
    'VACIOS',
    'NA'
]

COLUMNAS_AGRUPACION = [
    'SEMESTRE',
    'NIVEL',
    'ID_ARCHIVO',
    'NOMBRE_ARCHIVO',
    'DOCENTE',
    'ASIGNATURA',
    'DURACION',
    'PERIODO',
    'TIPO_EVALUACION'
]


# ============================================================
# AUTENTICACION
# ============================================================

def obtener_servicio_sheets():

    creds = service_account.Credentials.from_service_account_file(
        KEY,
        scopes=SCOPES
    )

    return build(
        'sheets',
        'v4',
        credentials=creds
    )


def asegurar_pestana_seguimiento(servicio):

    respuesta = servicio.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID,
        fields='sheets(properties(title))'
    ).execute()

    nombres = {
        hoja['properties']['title']
        for hoja in respuesta.get('sheets', [])
    }

    if 'SEGUIMIENTO' not in nombres:
        servicio.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                'requests': [{
                    'addSheet': {
                        'properties': {
                            'title': 'SEGUIMIENTO'
                        }
                    }
                }]
            }
        ).execute()


# ============================================================
# CALCULAR SEGUIMIENTO
# ============================================================

def calcular_estado(cantidad_notas, vacios, cantidad_na):

    if cantidad_notas == 0 and cantidad_na == 0:
        return 'SIN NOTAS'

    if vacios > 0:
        return 'INCOMPLETO'

    return 'COMPLETO'


def construir_seguimiento_df(notas_df):

    if notas_df.empty:
        return pd.DataFrame(columns=COLUMNAS_SEGUIMIENTO)

    registros = []

    for claves, grupo in notas_df.groupby(
        COLUMNAS_AGRUPACION,
        dropna=False,
        sort=False
    ):

        datos = dict(zip(COLUMNAS_AGRUPACION, claves))

        cantidad_notas = int(
            grupo['NOTA'].notna().sum()
        )

        aprobados = int(
            (grupo['ESTADO_NOTA'] == 'APROBADA').sum()
        )

        reprobados = int(
            (grupo['ESTADO_NOTA'] == 'REPROBADA').sum()
        )

        vacios = int(
            (grupo['ESTADO_NOTA'] == 'VACIA').sum()
        )

        cantidad_na = int(
            (grupo['ESTADO_NOTA'] == 'NA').sum()
        )

        datos.update({
            'ESTADO': calcular_estado(
                cantidad_notas,
                vacios,
                cantidad_na
            ),
            'TOTAL_ESTUDIANTES': int(
                grupo['NUMERO_ESTUDIANTE'].nunique()
            ),
            'CANTIDAD_NOTAS': cantidad_notas,
            'APROBADOS': aprobados,
            'REPROBADOS': reprobados,
            'VACIOS': vacios,
            'NA': cantidad_na
        })

        registros.append(datos)

    return pd.DataFrame(
        registros,
        columns=COLUMNAS_SEGUIMIENTO
    )


# ============================================================
# FASE 4
# ============================================================

def ejecutar_fase_4():

    archivos_df = ejecutar_fase_1()

    (
        estudiantes_df,
        asignaturas_df,
        observaciones_df,
        notas_df
    ) = procesar_archivos(archivos_df)

    seguimiento_df = construir_seguimiento_df(
        notas_df
    )

    servicio = obtener_servicio_sheets()

    asegurar_pestana_seguimiento(
        servicio
    )

    actualizar_pestana(
        servicio,
        'SEGUIMIENTO',
        seguimiento_df,
        COLUMNAS_SEGUIMIENTO
    )

    print('Seguimiento publicado.')
    print(f'Registros: {len(seguimiento_df)}')

    return seguimiento_df


if __name__ == '__main__':
    ejecutar_fase_4()
