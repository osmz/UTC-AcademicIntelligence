from pathlib import Path

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

try:
    from .fase_01_archivos import ejecutar_fase_1
    from .fase_02_estructura import (
        obtener_hojas_archivo,
        procesar_hoja_indice
    )
except ImportError:
    from fase_01_archivos import ejecutar_fase_1
    from fase_02_estructura import (
        obtener_hojas_archivo,
        procesar_hoja_indice
    )


# ============================================================
# CONFIGURACION
# ============================================================

KEY = str(
    Path(__file__).resolve().parents[1]
    / 'config'
    / 'key.json'
)

SPREADSHEET_ID = '1LLZJ0N3ZjFn0Wji6ZEFf5J4aQe6c46LbD7iVCMlZ5Yk'

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/spreadsheets'
]

HOJAS_AUTOMATICAS = {
    'ARCHIVOS': [
        'SEMESTRE',
        'NIVEL',
        'ID_ARCHIVO',
        'NOMBRE_ARCHIVO',
        'URL',
        'TIPO'
    ],
    'ESTUDIANTES': [
        'SEMESTRE',
        'NIVEL',
        'ID_ARCHIVO',
        'NOMBRE_ARCHIVO',
        'ID_HOJA',
        'NUMERO',
        'DOCUMENTO',
        'NOMBRE',
        'INSTITUCION',
        'CORREO',
        'TELEFONO',
        'ESTADO',
        'ASIGNATURAS_A_REPETIR'
    ],
    'ASIGNATURAS': [
        'SEMESTRE',
        'NIVEL',
        'ID_ARCHIVO',
        'NOMBRE_ARCHIVO',
        'ID_HOJA',
        'COLUMNA',
        'ASIGNATURA',
        'DOCENTE',
        'DURACION',
        'PERIODO',
        'TIPO_EVALUACION'
    ],
    'OBSERVACIONES': [
        'SEMESTRE',
        'NIVEL',
        'ID_ARCHIVO',
        'NOMBRE_ARCHIVO',
        'ID_HOJA',
        'NUMERO_ESTUDIANTE',
        'DOCUMENTO',
        'ASIGNATURA',
        'PERIODO',
        'TIPO_EVALUACION',
        'COLUMNA_OBSERVACION',
        'NOMBRE_COLUMNA',
        'OBSERVACION'
    ],
    'NOTAS': [
        'SEMESTRE',
        'NIVEL',
        'ID_ARCHIVO',
        'NOMBRE_ARCHIVO',
        'ID_HOJA',
        'NUMERO_ESTUDIANTE',
        'DOCUMENTO',
        'NOMBRE_ESTUDIANTE',
        'COLUMNA',
        'ASIGNATURA',
        'DOCENTE',
        'DURACION',
        'PERIODO',
        'TIPO_EVALUACION',
        'VALOR_ORIGINAL',
        'NOTA',
        'ESTADO_NOTA'
    ]
}


# ============================================================
# AUTENTICACION Y ESCRITURA
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


def convertir_valor(valor):

    if valor is None or pd.isna(valor):
        return ''

    return valor


def dataframe_a_valores(dataframe, columnas):

    if dataframe.empty:
        return [columnas]

    dataframe = dataframe.reindex(
        columns=columnas,
        fill_value=''
    )

    valores = [columnas]

    for fila in dataframe.itertuples(index=False, name=None):
        valores.append([
            convertir_valor(valor)
            for valor in fila
        ])

    return valores


def actualizar_pestana(servicio, nombre_pestana, dataframe, columnas):

    rango = f"'{nombre_pestana}'"

    servicio.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID,
        range=rango,
        body={}
    ).execute()

    valores = dataframe_a_valores(
        dataframe,
        columnas
    )

    servicio.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{nombre_pestana}'!A1",
        valueInputOption='RAW',
        body={'values': valores}
    ).execute()


# ============================================================
# PROCESAMIENTO DE TODOS LOS ARCHIVOS
# ============================================================

def procesar_archivos(archivos_df):

    estudiantes = []
    asignaturas = []
    observaciones = []
    notas = []

    for archivo in archivos_df.to_dict('records'):

        metadatos_archivo = {
            'SEMESTRE': archivo['SEMESTRE'],
            'NIVEL': archivo['NIVEL'],
            'ID_ARCHIVO': archivo['ID_ARCHIVO'],
            'NOMBRE_ARCHIVO': archivo['NOMBRE_ARCHIVO']
        }

        hojas_df = obtener_hojas_archivo(
            archivo['ID_ARCHIVO']
        )

        hoja_indice = hojas_df[
            hojas_df['INDICE_HOJA'] == 0
        ]

        if hoja_indice.empty:
            print(
                f"Se omite sin hoja indice 0: "
                f"{archivo['NOMBRE_ARCHIVO']}"
            )
            continue

        hoja = hoja_indice.iloc[0]

        resultado = procesar_hoja_indice(
            archivo['ID_ARCHIVO'],
            hoja['NOMBRE_HOJA'],
            metadatos_archivo,
            hoja['ID_HOJA']
        )

        estudiantes_df, asignaturas_df, observaciones_df, notas_df = resultado

        estudiantes.append(estudiantes_df)
        asignaturas.append(asignaturas_df)
        observaciones.append(observaciones_df)
        notas.append(notas_df)

    return (
        pd.concat(estudiantes, ignore_index=True)
        if estudiantes else pd.DataFrame(),
        pd.concat(asignaturas, ignore_index=True)
        if asignaturas else pd.DataFrame(),
        pd.concat(observaciones, ignore_index=True)
        if observaciones else pd.DataFrame(),
        pd.concat(notas, ignore_index=True)
        if notas else pd.DataFrame()
    )


# ============================================================
# FASE 3 - PUBLICACION
# ============================================================

def publicar_dataframes(
    servicio,
    archivos_df,
    estudiantes_df,
    asignaturas_df,
    observaciones_df,
    notas_df
):

    actualizar_pestana(
        servicio,
        'ARCHIVOS',
        archivos_df,
        HOJAS_AUTOMATICAS['ARCHIVOS']
    )

    actualizar_pestana(
        servicio,
        'ESTUDIANTES',
        estudiantes_df,
        HOJAS_AUTOMATICAS['ESTUDIANTES']
    )

    actualizar_pestana(
        servicio,
        'ASIGNATURAS',
        asignaturas_df,
        HOJAS_AUTOMATICAS['ASIGNATURAS']
    )

    actualizar_pestana(
        servicio,
        'OBSERVACIONES',
        observaciones_df,
        HOJAS_AUTOMATICAS['OBSERVACIONES']
    )

    actualizar_pestana(
        servicio,
        'NOTAS',
        notas_df,
        HOJAS_AUTOMATICAS['NOTAS']
    )


def ejecutar_fase_3():

    archivos_df = ejecutar_fase_1()

    estudiantes_df, asignaturas_df, observaciones_df, notas_df = (
        procesar_archivos(archivos_df)
    )

    servicio = obtener_servicio_sheets()

    publicar_dataframes(
        servicio,
        archivos_df,
        estudiantes_df,
        asignaturas_df,
        observaciones_df,
        notas_df
    )

    print('Publicacion completada.')
    print(f"Archivos: {len(archivos_df)}")
    print(f"Estudiantes: {len(estudiantes_df)}")
    print(f"Asignaturas: {len(asignaturas_df)}")
    print(f"Observaciones: {len(observaciones_df)}")
    print(f"Notas: {len(notas_df)}")


if __name__ == '__main__':
    ejecutar_fase_3()
