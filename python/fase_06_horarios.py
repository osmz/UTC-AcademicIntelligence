"""FASE 6: extracción, normalización y publicación de horarios académicos.

El módulo no ejecuta autenticación al importarse. Las funciones de extracción
aceptan servicios de Google opcionales para facilitar diagnóstico y pruebas con
datos locales o servicios simulados.
"""

from __future__ import annotations

import re
import time
import unicodedata
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build


KEY = str(Path(__file__).resolve().parents[1] / 'config' / 'key.json')
CARPETA_RAIZ_ID = '1cHHtW6zsUYJsjlNp_KBspmsKoTNKhBan'
SPREADSHEET_ID = '1LLZJ0N3ZjFn0Wji6ZEFf5J4aQe6c46LbD7iVCMlZ5Yk'

SCOPES_DRIVE = ['https://www.googleapis.com/auth/drive.readonly']
SCOPES_SHEETS = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/spreadsheets',
]
MIME_FOLDER = 'application/vnd.google-apps.folder'
MIME_SHEET = 'application/vnd.google-apps.spreadsheet'

DIAS = {
    'lunes': ('Lunes', 1), 'martes': ('Martes', 2),
    'miercoles': ('Miércoles', 3), 'jueves': ('Jueves', 4),
    'viernes': ('Viernes', 5),
}
PROGRAMAS = {
    'procesos de manufactura':
        ('Técnico Profesional en Procesos de Manufactura', 'TPPM'),
    'diseno ingenieril para la produccion industrial':
        ('Técnico Profesional en Diseño Ingenieril para la Producción Industrial', 'TPDIPI'),
    'mantenimiento mecanico':
        ('Técnico Profesional en Mantenimiento Mecánico', 'TPMM'),
    'control industrial':
        ('Técnico Profesional en Control Industrial', 'TPCI'),
    'programacion de computadores':
        ('Técnico Profesional en Programación de Computadores', 'TPPC'),
}
SEMESTRES_ESPERADOS = {('1', 'TL'): 1, ('1', 'TP'): 3, ('3', 'TL'): 2, ('3', 'TP'): 4}

COLUMNAS_HORARIOS = [
    'ID_REGISTRO', 'AÑO', 'SEMESTRE_ACADEMICO', 'PERIODO',
    'SEMESTRE_DECLARADO', 'NIVEL', 'GRUPO', 'COLEGIOS',
    'COLEGIOS_ORIGINAL', 'PROGRAMA', 'SIGLA_PROGRAMA', 'PROGRAMA_ORIGINAL',
    'SEDE', 'DIA', 'ORDEN_DIA', 'ASIGNATURA', 'ASIGNATURA_ORIGINAL',
    'DOCENTE', 'MONITOR', 'OBSERVACION_MONITOR', 'MONITOR_ORIGINAL', 'AULA',
    'HORA_INICIO', 'HORA_FIN', 'TIPO_HORARIO', 'OBSERVACIONES_HORARIO',
    'VALOR_CELDA_ORIGINAL', 'ID_ARCHIVO', 'NOMBRE_ARCHIVO', 'RUTA_ARCHIVO',
    'ID_HOJA', 'NOMBRE_HOJA', 'FUENTE', 'FECHA_EXTRACCION',
]
COLUMNAS_CALENDARIO = [
    'ID_CALENDARIO', 'AÑO', 'SEMESTRE_ACADEMICO', 'PERIODO', 'NIVEL',
    'SEMESTRE_DECLARADO', 'EVENTO', 'FECHA_INICIO', 'FECHA_FIN',
    'VALOR_ORIGINAL', 'ID_ARCHIVO', 'NOMBRE_ARCHIVO', 'FECHA_EXTRACCION',
]


def limpiar(valor: Any) -> str:
    return '' if valor is None else str(valor).strip()


def clave(valor: Any) -> str:
    texto = unicodedata.normalize('NFKD', limpiar(valor).lower())
    return ''.join(c for c in texto if not unicodedata.combining(c))


def matriz_normalizada(matriz: list[list[Any]]) -> list[list[str]]:
    filas = [[limpiar(v) for v in fila] for fila in matriz]
    ancho = max((len(fila) for fila in filas), default=0)
    return [fila + [''] * (ancho - len(fila)) for fila in filas]


def _ejecutar_drive(solicitud, intentos: int = 4):
    for intento in range(intentos):
        try:
            return solicitud.execute()
        except Exception as error:
            estado = getattr(getattr(error, 'resp', None), 'status', None)
            if estado not in {429, 500, 502, 503, 504} or intento == intentos - 1:
                raise
            espera = 2 ** intento
            print(f'Error temporal de Drive ({estado}). Reintentando en {espera} s...')
            time.sleep(espera)


def _listar(drive_service, parent_id: str) -> list[dict[str, Any]]:
    elementos = []
    token = None
    while True:
        solicitud = drive_service.files().list(
            q=f"'{parent_id}' in parents and trashed = false",
            fields='nextPageToken,files(id,name,mimeType,webViewLink)',
            pageSize=1000, pageToken=token,
        )
        respuesta = _ejecutar_drive(solicitud)
        elementos.extend(respuesta.get('files', []))
        token = respuesta.get('nextPageToken')
        if not token:
            return elementos


def _recorrer(drive_service, folder_id: str, path: str, alertas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    encontrados = []
    try:
        elementos = _listar(drive_service, folder_id)
    except Exception as error:
        estado = getattr(getattr(error, 'resp', None), 'status', '')
        alertas.append({
            'TIPO_ALERTA': 'DRIVE_CARPETA_NO_LEIBLE',
            'CARPETA_ID': folder_id,
            'RUTA': path or '/',
            'DETALLE': f'HTTP {estado}' if estado else str(error),
        })
        print(f'No se pudo leer la carpeta {path or "/"}; se continúa.')
        return encontrados
    for elemento in elementos:
        actual = f'{path}/{elemento["name"]}'
        if elemento.get('mimeType') == MIME_FOLDER:
            encontrados.extend(_recorrer(drive_service, elemento['id'], actual, alertas))
        elif elemento.get('mimeType') == MIME_SHEET:
            encontrados.append({**elemento, 'RUTA_ARCHIVO': actual})
    return encontrados


def metadatos_desde_ruta(archivo: dict[str, Any]) -> dict[str, Any]:
    ruta = limpiar(archivo.get('RUTA_ARCHIVO'))
    partes = [p.strip() for p in ruta.split('/') if p.strip()]
    semestre = next((p for p in partes if re.fullmatch(r'\d{4}-\d+', p)), '')
    match = re.fullmatch(r'(\d{4})-(\d+)', semestre)
    nivel = next((p.upper() for p in partes if p.upper() in {'TL', 'TP'}), '')
    nombre = limpiar(archivo.get('name') or archivo.get('NOMBRE_ARCHIVO'))
    declarado = extraer_semestre_declarado(nombre)
    periodo = match.group(2) if match else ''
    anio = match.group(1) if match else ''
    esperado = SEMESTRES_ESPERADOS.get((periodo, nivel))
    alertas = []
    if not match:
        alertas.append('RUTA_SIN_SEMESTRE_ACADEMICO')
    if not nivel:
        alertas.append('RUTA_SIN_NIVEL')
    if not declarado:
        alertas.append('NOMBRE_SIN_SEMESTRE_DECLARADO')
    elif esperado is not None and declarado != str(esperado):
        alertas.append('SEMESTRE_DECLARADO_INCONSISTENTE')
    return {
        'AÑO': anio, 'PERIODO': periodo, 'SEMESTRE_ACADEMICO': semestre,
        'NIVEL': nivel, 'SEMESTRE_DECLARADO': declarado or '',
        'ID_ARCHIVO': limpiar(archivo.get('id') or archivo.get('ID_ARCHIVO')),
        'NOMBRE_ARCHIVO': nombre, 'RUTA_ARCHIVO': ruta, 'ALERTAS': alertas,
    }


def extraer_semestre_declarado(nombre: str) -> str:
    encontrado = re.search(r'\b([1-4])(?:er|ro|do|to)?\.?\s*sem', nombre.lower())
    return encontrado.group(1) if encontrado else ''


def localizar_archivos_horarios(drive_service, carpeta_raiz_id=CARPETA_RAIZ_ID) -> dict[str, Any]:
    alertas: list[dict[str, Any]] = []
    archivos = _recorrer(drive_service, carpeta_raiz_id, '', alertas)
    candidatos = [
        archivo for archivo in archivos
        if metadatos_desde_ruta(archivo)['SEMESTRE_ACADEMICO']
        and 'horario' in clave(archivo.get('name'))
    ]
    agrupados: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for archivo in candidatos:
        datos = metadatos_desde_ruta(archivo)
        clave_archivo = (datos['SEMESTRE_ACADEMICO'], datos['NIVEL'], datos['SEMESTRE_DECLARADO'])
        agrupados.setdefault(clave_archivo, []).append(archivo)
    esperados = []
    for semestre, periodo in [('2026-1', '1'), ('2026-3', '3')]:
        for nivel in ('TL', 'TP'):
            esperados.append((semestre, nivel, str(SEMESTRES_ESPERADOS[(periodo, nivel)])))
    seleccionados = []
    for identidad in esperados:
        opciones = agrupados.get(identidad, [])
        if len(opciones) == 0:
            alertas.append({'TIPO_ALERTA': 'ARCHIVO_FALTANTE', 'CLAVE': identidad})
        elif len(opciones) > 1:
            alertas.append({'TIPO_ALERTA': 'ARCHIVOS_DUPLICADOS', 'CLAVE': identidad,
                            'ARCHIVOS': [a.get('name', '') for a in opciones]})
        seleccionados.extend(opciones[:1])
    for archivo in seleccionados:
        archivo['_METADATOS'] = metadatos_desde_ruta(archivo)
    return {'archivos': seleccionados, 'candidatos': candidatos, 'alertas': alertas}


def obtener_hojas(sheets_service, id_archivo: str) -> list[dict[str, Any]]:
    respuesta = sheets_service.spreadsheets().get(
        spreadsheetId=id_archivo,
        fields='sheets(properties(sheetId,title,index))',
    ).execute()
    return [h['properties'] for h in respuesta.get('sheets', [])]


def leer_hoja(sheets_service, id_archivo: str, nombre_hoja: str) -> list[list[Any]]:
    respuesta = sheets_service.spreadsheets().values().get(
        spreadsheetId=id_archivo, range=f"'{nombre_hoja}'", majorDimension='ROWS',
    ).execute()
    return matriz_normalizada(respuesta.get('values', []))


def _dia(valor: Any) -> tuple[str, int] | None:
    return DIAS.get(clave(valor).replace(' ', ''))


def detectar_estructura(matriz: list[list[str]]) -> dict[str, Any]:
    filas_dia = []
    for indice, fila in enumerate(matriz[:8]):
        cantidad = sum(_dia(valor) is not None for valor in fila)
        if cantidad:
            filas_dia.append((cantidad, indice))
    if not filas_dia:
        return {'fila_dias': None, 'fila_encabezados': None, 'columnas': {},
                'alertas': ['ESTRUCTURA_COLUMNAS_INESPERADA']}
    fila_dias = max(filas_dia)[1]
    fila_encabezados = min((i for i in range(fila_dias + 1, min(len(matriz), 8))), default=fila_dias)
    dias = list(matriz[fila_dias])
    ultimo = None
    for i, valor in enumerate(dias):
        if _dia(valor):
            ultimo = _dia(valor)
        elif ultimo:
            dias[i] = ultimo[0]
    columnas = {}
    encabezados = matriz[fila_encabezados]
    roles = {'asignatura': 'ASIGNATURA', 'materia': 'ASIGNATURA',
             'docente': 'DOCENTE', 'profesor': 'DOCENTE', 'monitor': 'MONITOR'}
    for indice, valor in enumerate(encabezados):
        rol = roles.get(clave(valor))
        if rol and _dia(dias[indice]):
            columnas[indice] = (_dia(dias[indice])[0], _dia(dias[indice])[1], rol)
    alertas = []
    if not columnas:
        alertas.append('ESTRUCTURA_COLUMNAS_INESPERADA')
    return {'fila_dias': fila_dias, 'fila_encabezados': fila_encabezados,
            'fila_datos': fila_encabezados + 1, 'columnas': columnas, 'alertas': alertas}


def normalizar_programa(texto: Any) -> dict[str, str]:
    original = limpiar(texto)
    encontrado = next((v for k, v in PROGRAMAS.items() if k in clave(original)), None)
    if encontrado:
        return {'PROGRAMA': encontrado[0], 'SIGLA_PROGRAMA': encontrado[1], 'PROGRAMA_ORIGINAL': original}
    return {'PROGRAMA': '', 'SIGLA_PROGRAMA': '', 'PROGRAMA_ORIGINAL': original}


def normalizar_colegios(texto: Any) -> tuple[str, str]:
    original = limpiar(texto)
    partes = [p.strip() for p in re.split(r'\s+-\s+', original) if p.strip()]
    return ' | '.join(dict.fromkeys(partes)), original


def separar_grupo_colegios(texto: Any) -> tuple[str, str, str]:
    original = limpiar(texto)
    grupo = re.match(r'^\s*(grupo\s*\d+)\s*(?:\r?\n|[-:])\s*(.*)$', original, flags=re.I | re.S)
    if not grupo:
        return original, original, ''

    colegios = grupo.group(2).strip()
    lineas = []
    programas = []
    for linea in re.split(r'\r?\n', colegios):
        linea = linea.strip()
        programa = next((nombre for nombre in PROGRAMAS if clave(nombre) in clave(linea)), None)
        if programa:
            programas.append(linea)
        elif linea:
            lineas.append(linea)
    colegios = ' - '.join(linea for linea in lineas if linea)
    return grupo.group(1).strip(), colegios, ' / '.join(programas)


def _partes_relacionadas(valor: Any) -> list[str]:
    return [p.strip() for p in re.split(r'\s*/\s*', limpiar(valor)) if p.strip()]


def extraer_aula_y_observacion(asignatura: str) -> tuple[str, str, str]:
    original = limpiar(asignatura)
    observacion = ''
    coincidencia_observacion = re.search(r'\s+(HASTA\s+.+)$', original, flags=re.I)
    base = original
    if coincidencia_observacion:
        observacion = coincidencia_observacion.group(1).strip()
        base = original[:coincidencia_observacion.start()].strip()
    aula = ''
    coincidencias = list(re.finditer(r'\(([^()]*)\)', base))
    if coincidencias and re.fullmatch(r'[A-Za-z]?[- ]?\d{2,3}(?:-\d{2,3})?', coincidencias[-1].group(1).strip()):
        aula = coincidencias[-1].group(1).strip()
        base = base[:coincidencias[-1].start()].strip() + base[coincidencias[-1].end():].strip()
    return base.strip(), aula, observacion


def extraer_horas(texto: str) -> tuple[str, str, str, str]:
    original = limpiar(texto)
    patron = r'(\d{1,2})(?::(\d{2}))?\s*(?:([ap])\.?m?\.?\s*)?A\s*(\d{1,2})(?::(\d{2}))?\s*(?:([ap])\.?m?\.?)?'
    encontrado = re.search(patron, original, flags=re.I)
    if not encontrado:
        return '14:00', '18:00', 'GENERAL', ''
    h1, m1, mer1, h2, m2, mer2 = encontrado.groups()
    def convertir(hora: str, minutos: str, meridiano: str) -> str:
        valor = int(hora)
        if meridiano and meridiano.lower() == 'p' and valor < 12:
            valor += 12
        if meridiano and meridiano.lower() == 'a' and valor == 12:
            valor = 0
        if not meridiano and 1 <= valor <= 7:
            valor += 12
        return f'{valor:02d}:{int(minutos or 0):02d}'
    return convertir(h1, m1, mer1), convertir(h2, m2, mer2), 'ESPECIFICO', original


def normalizar_monitor(valor: Any) -> tuple[str, str, str]:
    original = limpiar(valor)
    observacion = ''
    match = re.search(r'\(([^()]*)\)', original)
    if match and not re.fullmatch(r'[A-Za-z]?[- ]?\d{2,3}(?:-\d{2,3})?', match.group(1).strip()):
        observacion = match.group(1).strip()
        nombre = (original[:match.start()] + original[match.end():]).strip()
    else:
        nombre = original
    return nombre, observacion, original


def _relacionar(asignaturas: list[str], docentes: list[str], alertas: list[dict[str, Any]], contexto: str) -> list[tuple[str, str]]:
    if len(docentes) == 1:
        return [(asignatura, docentes[0]) for asignatura in asignaturas]
    if len(asignaturas) == len(docentes):
        return list(zip(asignaturas, docentes))
    if len(asignaturas) == 1 and len(docentes) > 1:
        alertas.append({'TIPO_ALERTA': 'MULTIPLES_DOCENTES_PARA_UNA_ASIGNATURA', 'CONTEXTO': contexto})
        return [(asignaturas[0], docente) for docente in docentes]
    alertas.append({'TIPO_ALERTA': 'CORRESPONDENCIA_ASIGNATURA_DOCENTE_AMBIGUA', 'CONTEXTO': contexto})
    return [(asignatura, docentes[0] if docentes else '') for asignatura in asignaturas]


def _fecha(valor: str) -> str:
    meses = {
        'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4,
        'mayo': 5, 'junio': 6, 'julio': 7, 'agosto': 8,
        'septiembre': 9, 'setiembre': 9, 'octubre': 10,
        'noviembre': 11, 'diciembre': 12,
    }
    texto = clave(valor)
    nombrada = re.search(r'\b(\d{1,2})[- ]([a-z]+)[- ](\d{4})\b', texto)
    if nombrada and nombrada.group(2) in meses:
        return f'{nombrada.group(3)}-{meses[nombrada.group(2)]:02d}-{int(nombrada.group(1)):02d}'
    for patron in (r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b', r'\b(\d{4})-(\d{2})-(\d{2})\b'):
        match = re.search(patron, valor)
        if match:
            partes = match.groups()
            if len(partes[0]) == 4:
                return '-'.join(partes)
            return f'{partes[2]}-{int(partes[1]):02d}-{int(partes[0]):02d}'
    return ''


def extraer_calendario(matriz: list[list[str]], metadatos: dict[str, Any], fecha_extraccion: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    registros, alertas = [], []
    if not matriz:
        return registros, alertas
    fila = matriz[0]
    for i, valor in enumerate(fila):
        texto = limpiar(valor)
        if not texto or not re.search(r'(inicio|fin|recuperaci|clases|asignaturas)', clave(texto)):
            continue
        siguiente = fila[i + 1] if i + 1 < len(fila) else ''
        original = f'{texto}: {siguiente}'.strip(': ')
        fechas = re.findall(
            r'\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}-\d{2}-\d{2}|'
            r'\d{1,2}[- ](?:enero|febrero|marzo|abril|mayo|junio|julio|'
            r'agosto|septiembre|setiembre|octubre|noviembre|diciembre)[- ]\d{4}',
            original,
            flags=re.I,
        )
        if not fechas:
            alertas.append({'TIPO_ALERTA': 'FECHA_NO_INTERPRETABLE', 'VALOR': original})
            continue
        convertidas = [_fecha(f) for f in fechas]
        registro = {**{k: metadatos.get(k, '') for k in ('AÑO', 'SEMESTRE_ACADEMICO', 'PERIODO', 'NIVEL', 'SEMESTRE_DECLARADO')},
                          'EVENTO': texto, 'FECHA_INICIO': convertidas[0], 'FECHA_FIN': convertidas[-1],
                          'VALOR_ORIGINAL': original, 'ID_ARCHIVO': metadatos['ID_ARCHIVO'],
                  'NOMBRE_ARCHIVO': metadatos['NOMBRE_ARCHIVO'], 'FECHA_EXTRACCION': fecha_extraccion}
        registro['ID_CALENDARIO'] = f"{metadatos['ID_ARCHIVO']}:{i}"
        registros.append(registro)
    return registros, alertas


def procesar_hoja(matriz: list[list[Any]], metadatos: dict[str, Any], hoja: dict[str, Any], fecha_extraccion: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    matriz = matriz_normalizada(matriz)
    estructura = detectar_estructura(matriz)
    alertas = [{'TIPO_ALERTA': alerta, 'ARCHIVO': metadatos['NOMBRE_ARCHIVO']} for alerta in estructura['alertas']]
    contenido_inicial = ' '.join(' '.join(fila) for fila in matriz[:8])
    if metadatos['SEMESTRE_ACADEMICO'] and metadatos['SEMESTRE_ACADEMICO'] in contenido_inicial:
        pass
    elif re.search(r'\b\d{4}-\d+\b', contenido_inicial):
        alertas.append({'TIPO_ALERTA': 'SEMESTRE_RUTA_DIFERENTE_CONTENIDO', 'ARCHIVO': metadatos['NOMBRE_ARCHIVO']})
    nivel_interno = next((nivel for nivel in ('TL', 'TP') if re.search(rf'\b{nivel}\b', contenido_inicial, flags=re.I)), '')
    if nivel_interno and metadatos['NIVEL'] and nivel_interno != metadatos['NIVEL']:
        alertas.append({'TIPO_ALERTA': 'NIVEL_RUTA_DIFERENTE_CONTENIDO', 'ARCHIVO': metadatos['NOMBRE_ARCHIVO']})
    calendarios, alertas_cal = extraer_calendario(matriz, metadatos, fecha_extraccion)
    alertas.extend(alertas_cal)
    registros = []
    programa_actual = {'PROGRAMA': '', 'SIGLA_PROGRAMA': '', 'PROGRAMA_ORIGINAL': ''}
    fila_datos = estructura.get('fila_datos') or 4
    grupo_actual = ''
    sede_actual = ''
    for numero_fila, fila in enumerate(matriz[fila_datos:], start=fila_datos + 1):
        texto_fila = ' | '.join(fila)
        grupo_texto = fila[1] if len(fila) > 1 else ''
        grupo_detectado, colegios_detectados, programa_texto = separar_grupo_colegios(grupo_texto)
        programa = normalizar_programa(programa_texto or texto_fila)
        if programa['PROGRAMA']:
            programa_actual = programa
        grupo_celda = grupo_texto
        sede_celda = fila[2] if len(fila) > 2 else ''
        if grupo_celda:
            grupo_actual = grupo_celda
        if sede_celda:
            sede_actual = sede_celda
        grupo, colegios_celda, programa_celda = separar_grupo_colegios(grupo_actual)
        if programa_celda:
            programa_actual = normalizar_programa(programa_celda)
        sede = sede_actual
        if not grupo and not any(fila[indice] for indice in estructura['columnas']):
            continue
        colegios, colegios_original = normalizar_colegios(colegios_celda)
        if any(fila[indice] for indice in estructura['columnas']) and not programa_actual['PROGRAMA']:
            alertas.append({'TIPO_ALERTA': 'PROGRAMA_NO_DETERMINADO', 'FILA': numero_fila})
        for columna, (dia, orden, rol) in estructura['columnas'].items():
            if rol != 'ASIGNATURA' or columna >= len(fila) or not fila[columna]:
                continue
            asignaturas = _partes_relacionadas(fila[columna])
            docentes = _partes_relacionadas(fila[columna + 1]) if columna + 1 < len(fila) else []
            monitores = _partes_relacionadas(fila[columna + 2]) if columna + 2 < len(fila) else []
            relaciones = _relacionar(asignaturas, docentes, alertas, f'{metadatos["NOMBRE_ARCHIVO"]}:{numero_fila}:{dia}')
            if len(monitores) > 1 and len(monitores) != len(asignaturas):
                alertas.append({'TIPO_ALERTA': 'MULTIPLES_MONITORES_AMBIGUOS', 'FILA': numero_fila})
            for posicion, (asignatura_original, docente) in enumerate(relaciones):
                asignatura, aula, observacion_horario = extraer_aula_y_observacion(asignatura_original)
                inicio, fin, tipo, valor_hora = extraer_horas(asignatura_original)
                monitor_original = monitores[posicion] if len(monitores) == len(asignaturas) and posicion < len(monitores) else (monitores[0] if len(monitores) == 1 else '')
                monitor, observacion_monitor, monitor_original = normalizar_monitor(monitor_original)
                registro = {**metadatos, **programa_actual, 'GRUPO': grupo,
                            'COLEGIOS': colegios, 'COLEGIOS_ORIGINAL': colegios_original, 'SEDE': sede,
                            'DIA': dia, 'ORDEN_DIA': orden, 'ASIGNATURA': asignatura,
                            'ASIGNATURA_ORIGINAL': asignatura_original, 'DOCENTE': docente,
                            'MONITOR': monitor, 'OBSERVACION_MONITOR': observacion_monitor,
                            'MONITOR_ORIGINAL': monitor_original, 'AULA': aula,
                            'HORA_INICIO': inicio, 'HORA_FIN': fin, 'TIPO_HORARIO': tipo,
                            'OBSERVACIONES_HORARIO': observacion_horario or valor_hora,
                            'VALOR_CELDA_ORIGINAL': fila[columna], 'ID_HOJA': hoja.get('sheetId', ''),
                            'NOMBRE_HOJA': hoja.get('title', ''), 'FUENTE': 'Google Drive / Google Sheets',
                            'FECHA_EXTRACCION': fecha_extraccion}
                registro['ID_REGISTRO'] = f"{metadatos['ID_ARCHIVO']}:{hoja.get('sheetId', '')}:{numero_fila}:{columna}:{posicion}"
                registros.append(registro)
    return registros, calendarios + alertas


def extraer_fase6(drive_service, sheets_service, carpeta_raiz_id=CARPETA_RAIZ_ID) -> dict[str, Any]:
    fecha_extraccion = date.today().isoformat()
    localizacion = localizar_archivos_horarios(drive_service, carpeta_raiz_id)
    horarios, calendario, alertas = [], [], list(localizacion['alertas'])
    for archivo in localizacion['archivos']:
        metadatos = archivo['_METADATOS']
        alertas.extend({'TIPO_ALERTA': a, 'ARCHIVO': metadatos['NOMBRE_ARCHIVO']} for a in metadatos['ALERTAS'])
        hojas = obtener_hojas(sheets_service, metadatos['ID_ARCHIVO'])
        if not hojas:
            alertas.append({'TIPO_ALERTA': 'ARCHIVO_SIN_HOJAS', 'ARCHIVO': metadatos['NOMBRE_ARCHIVO']})
            continue
        for hoja in hojas:
            matriz = leer_hoja(sheets_service, metadatos['ID_ARCHIVO'], hoja['title'])
            registros, secundarios = procesar_hoja(matriz, metadatos, hoja, fecha_extraccion)
            horarios.extend(registros)
            calendario.extend(row for row in secundarios if 'EVENTO' in row)
            alertas.extend(row for row in secundarios if 'TIPO_ALERTA' in row)
    for indice, registro in enumerate(horarios, start=1):
        registro['ID_REGISTRO'] = registro.get('ID_REGISTRO') or str(indice)
    horarios_df = pd.DataFrame(horarios).reindex(columns=COLUMNAS_HORARIOS, fill_value='')
    calendario_df = pd.DataFrame(calendario).reindex(columns=COLUMNAS_CALENDARIO, fill_value='')
    return {'horarios': horarios_df, 'calendario': calendario_df, 'alertas': alertas,
            'localizacion': localizacion}


def construir_diagnostico(resultado: dict[str, Any]) -> dict[str, Any]:
    horarios = resultado['horarios']
    calendario = resultado['calendario']
    return {
        'ARCHIVOS_ESPERADOS': 4,
        'ARCHIVOS_ENCONTRADOS': len(resultado['localizacion']['archivos']),
        'ARCHIVOS_FALTANTES': sum(a.get('TIPO_ALERTA') == 'ARCHIVO_FALTANTE' for a in resultado['alertas']),
        'ARCHIVOS_DUPLICADOS': sum(a.get('TIPO_ALERTA') == 'ARCHIVOS_DUPLICADOS' for a in resultado['alertas']),
        'GRUPOS_ENCONTRADOS': int(horarios['GRUPO'].replace('', pd.NA).nunique()) if not horarios.empty else 0,
        'REGISTROS_GENERADOS': len(horarios),
        'ASIGNATURAS_IDENTIFICADAS': int(horarios['ASIGNATURA'].replace('', pd.NA).nunique()) if not horarios.empty else 0,
        'DOCENTES_IDENTIFICADOS': int(horarios['DOCENTE'].replace('', pd.NA).nunique()) if not horarios.empty else 0,
        'MONITORES_IDENTIFICADOS': int(horarios['MONITOR'].replace('', pd.NA).nunique()) if not horarios.empty else 0,
        'AULAS_IDENTIFICADAS': int(horarios['AULA'].replace('', pd.NA).nunique()) if not horarios.empty else 0,
        'REGISTROS_HORARIO_ESPECIFICO': int((horarios['TIPO_HORARIO'] == 'ESPECIFICO').sum()) if not horarios.empty else 0,
        'REGISTROS_HORARIO_GENERAL': int((horarios['TIPO_HORARIO'] == 'GENERAL').sum()) if not horarios.empty else 0,
        'CASOS_MULTIPLES_ASIGNATURAS': sum('/' in limpiar(v) for v in horarios.get('ASIGNATURA_ORIGINAL', [])),
        'CASOS_MULTIPLES_DOCENTES': sum(a.get('TIPO_ALERTA') == 'MULTIPLES_DOCENTES_PARA_UNA_ASIGNATURA' for a in resultado['alertas']),
        'FECHAS_EXTRAIDAS': len(calendario),
        'INCONSISTENCIAS_DETECTADAS': len(resultado['alertas']),
        'ALERTAS': resultado['alertas'],
    }


def diagnosticoFase6(drive_service=None, sheets_service=None, carpeta_raiz_id=CARPETA_RAIZ_ID) -> dict[str, Any]:
    drive_service = drive_service or obtener_servicio_drive()
    sheets_service = sheets_service or obtener_servicio_sheets()
    resultado = extraer_fase6(drive_service, sheets_service, carpeta_raiz_id)
    diagnostico = construir_diagnostico(resultado)
    print(pd.Series({k: v for k, v in diagnostico.items() if k != 'ALERTAS'}).to_string())
    return diagnostico


def obtener_servicio_drive():
    credenciales = service_account.Credentials.from_service_account_file(KEY, scopes=SCOPES_DRIVE)
    return build('drive', 'v3', credentials=credenciales)


def obtener_servicio_sheets():
    credenciales = service_account.Credentials.from_service_account_file(KEY, scopes=SCOPES_SHEETS)
    return build('sheets', 'v4', credentials=credenciales)


def asegurar_pestanas(servicio) -> None:
    existentes = servicio.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID, fields='sheets(properties(title))',
    ).execute().get('sheets', [])
    nombres = {hoja['properties']['title'] for hoja in existentes}
    solicitudes = [{'addSheet': {'properties': {'title': nombre}}}
                   for nombre in ('HORARIOS', 'CALENDARIO_ACADEMICO') if nombre not in nombres]
    if solicitudes:
        servicio.spreadsheets().batchUpdate(spreadsheetId=SPREADSHEET_ID, body={'requests': solicitudes}).execute()


def _valor_sheets(valor: Any) -> Any:
    if valor is None or (not isinstance(valor, (str, int, float, bool)) and pd.isna(valor)):
        return ''
    if isinstance(valor, (datetime, date)):
        return valor.isoformat()
    return valor


def actualizar_pestana_fase6(servicio, nombre: str, dataframe: pd.DataFrame, columnas: list[str]) -> None:
    servicio.spreadsheets().values().clear(spreadsheetId=SPREADSHEET_ID, range=f"'{nombre}'", body={}).execute()
    valores = [columnas] + [[_valor_sheets(v) for v in fila]
                             for fila in dataframe.reindex(columns=columnas, fill_value='').itertuples(index=False, name=None)]
    servicio.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID, range=f"'{nombre}'!A1", valueInputOption='RAW', body={'values': valores},
    ).execute()


def ejecutarFase6(drive_service=None, sheets_service=None, carpeta_raiz_id=CARPETA_RAIZ_ID) -> dict[str, Any]:
    drive_service = drive_service or obtener_servicio_drive()
    sheets_service = sheets_service or obtener_servicio_sheets()
    resultado = extraer_fase6(drive_service, sheets_service, carpeta_raiz_id)
    diagnostico = construir_diagnostico(resultado)
    asegurar_pestanas(sheets_service)
    actualizar_pestana_fase6(sheets_service, 'HORARIOS', resultado['horarios'], COLUMNAS_HORARIOS)
    actualizar_pestana_fase6(sheets_service, 'CALENDARIO_ACADEMICO', resultado['calendario'], COLUMNAS_CALENDARIO)
    print(f"FASE 6 publicada. Horarios: {len(resultado['horarios'])}; Calendario: {len(resultado['calendario'])}; Alertas: {len(resultado['alertas'])}")
    return {'horarios': resultado['horarios'], 'calendario': resultado['calendario'], 'diagnostico': diagnostico}


ejecutar_fase_6 = ejecutarFase6


if __name__ == '__main__':
    ejecutarFase6()