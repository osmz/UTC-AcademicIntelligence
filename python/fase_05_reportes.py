from pathlib import Path
from urllib.parse import quote

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

try:
    from .fase_03_publicacion import (
        SPREADSHEET_ID,
        actualizar_pestana
    )
except ImportError:
    from fase_03_publicacion import (
        SPREADSHEET_ID,
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
    'https://www.googleapis.com/auth/spreadsheets'
]

COLUMNAS_DOCENTES = [
    'DOCENTE',
    'INDICADOR',
    'NUMERO',
    'TELEFONO_WHATSAPP'
]

COLUMNAS_RECORDATORIOS = [
    'SEMESTRE',
    'NIVEL',
    'DOCENTE',
    'INDICADOR',
    'NUMERO',
    'TELEFONO_WHATSAPP',
    'NOMBRE_ARCHIVO',
    'ASIGNATURA',
    'PERIODO',
    'TIPO_EVALUACION',
    'ESTADO',
    'MENSAJE',
    'LINK_WHATSAPP',
    'VALIDACION'
]

COLUMNAS_REPORTE_ESTUDIANTES = [
    'SEMESTRE',
    'NIVEL',
    'DOCUMENTO',
    'NOMBRE_ESTUDIANTE',
    'ASIGNATURA',
    'NOTA',
    'DOCENTE',
    'NOMBRE_ARCHIVO',
    'PERIODO',
    'TIPO_EVALUACION'
]


# ============================================================
# LECTURA
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


def leer_pestana(servicio, nombre_pestana):

    respuesta = servicio.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{nombre_pestana}'"
    ).execute()

    valores = respuesta.get('values', [])

    if not valores:
        return pd.DataFrame()

    encabezados = valores[0]
    filas = valores[1:]

    return pd.DataFrame(
        filas,
        columns=encabezados
    )


def asegurar_pestanas_reportes(servicio):

    respuesta = servicio.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID,
        fields='sheets(properties(title))'
    ).execute()

    existentes = {
        hoja['properties']['title']
        for hoja in respuesta.get('sheets', [])
    }

    solicitudes = []

    for nombre in ['RECORDATORIOS', 'REPORTE_ESTUDIANTES']:

        if nombre not in existentes:
            solicitudes.append({
                'addSheet': {
                    'properties': {
                        'title': nombre
                    }
                }
            })

    if solicitudes:
        servicio.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={'requests': solicitudes}
        ).execute()


# ============================================================
# RECORDATORIOS
# ============================================================

def construir_mensaje(docente, archivo, asignatura, estado, tipo):

    return (
        f"Hola {docente}, se identifico que en el archivo {archivo} "
        f"la materia {asignatura} presenta estado {estado} en el "
        f"registro de notas ({tipo}). Por favor revisar y completar "
        f"el cargue correspondiente."
    )


def construir_recordatorios_df(seguimiento_df, docentes_df):

    if seguimiento_df.empty or docentes_df.empty:
        return pd.DataFrame(columns=COLUMNAS_RECORDATORIOS)

    pendientes = seguimiento_df[
        seguimiento_df['ESTADO'].isin(['SIN NOTAS', 'INCOMPLETO'])
    ].copy()

    docentes = docentes_df.reindex(
        columns=COLUMNAS_DOCENTES,
        fill_value=''
    ).copy()

    pendientes = pendientes.merge(
        docentes,
        on='DOCENTE',
        how='left'
    )

    registros = []

    for fila in pendientes.to_dict('records'):

        docente = str(fila.get('DOCENTE', '')).strip()
        archivo = str(fila.get('NOMBRE_ARCHIVO', '')).strip()
        asignatura = str(fila.get('ASIGNATURA', '')).strip()
        estado = str(fila.get('ESTADO', '')).strip()
        tipo = str(fila.get('TIPO_EVALUACION', '')).strip()
        telefono = str(fila.get('TELEFONO_WHATSAPP', '')).strip()

        mensaje = construir_mensaje(
            docente,
            archivo,
            asignatura,
            estado,
            tipo
        )

        link = ''

        if telefono:
            link = (
                f'https://wa.me/{telefono}?text='
                f'{quote(mensaje)}'
            )

        registros.append({
            'SEMESTRE': fila.get('SEMESTRE', ''),
            'NIVEL': fila.get('NIVEL', ''),
            'DOCENTE': docente,
            'INDICADOR': fila.get('INDICADOR', ''),
            'NUMERO': fila.get('NUMERO', ''),
            'TELEFONO_WHATSAPP': telefono,
            'NOMBRE_ARCHIVO': archivo,
            'ASIGNATURA': asignatura,
            'PERIODO': fila.get('PERIODO', ''),
            'TIPO_EVALUACION': tipo,
            'ESTADO': estado,
            'MENSAJE': mensaje,
            'LINK_WHATSAPP': link,
            'VALIDACION': 'OK' if telefono else 'SIN TELEFONO'
        })

    return pd.DataFrame(
        registros,
        columns=COLUMNAS_RECORDATORIOS
    )


# ============================================================
# REPORTE DE ESTUDIANTES
# ============================================================

def construir_reporte_estudiantes_df(notas_df):

    if notas_df.empty:
        return pd.DataFrame(columns=COLUMNAS_REPORTE_ESTUDIANTES)

    reporte = notas_df[
        notas_df['ESTADO_NOTA'] == 'REPROBADA'
    ].copy()

    return reporte.rename(
        columns={'NOMBRE_ARCHIVO': 'NOMBRE_ARCHIVO'}
    ).reindex(
        columns=COLUMNAS_REPORTE_ESTUDIANTES,
        fill_value=''
    ).reset_index(drop=True)


# ============================================================
# FASE 5
# ============================================================

def ejecutar_fase_5():

    servicio = obtener_servicio_sheets()

    asegurar_pestanas_reportes(
        servicio
    )

    seguimiento_df = leer_pestana(
        servicio,
        'SEGUIMIENTO'
    )

    docentes_df = leer_pestana(
        servicio,
        'DOCENTES'
    )

    notas_df = leer_pestana(
        servicio,
        'NOTAS'
    )

    recordatorios_df = construir_recordatorios_df(
        seguimiento_df,
        docentes_df
    )

    reporte_estudiantes_df = construir_reporte_estudiantes_df(
        notas_df
    )

    actualizar_pestana(
        servicio,
        'RECORDATORIOS',
        recordatorios_df,
        COLUMNAS_RECORDATORIOS
    )

    actualizar_pestana(
        servicio,
        'REPORTE_ESTUDIANTES',
        reporte_estudiantes_df,
        COLUMNAS_REPORTE_ESTUDIANTES
    )

    print('Reportes publicados.')
    print(f'Recordatorios: {len(recordatorios_df)}')
    print(f'Estudiantes reprobados: {len(reporte_estudiantes_df)}')

    return recordatorios_df, reporte_estudiantes_df


if __name__ == '__main__':
    ejecutar_fase_5()