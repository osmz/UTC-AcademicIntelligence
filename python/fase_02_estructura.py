import pandas as pd
import re
import time
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build

try:
    from .fase_01_archivos import (
        ejecutar_fase_1
    )
except ImportError:
    from fase_01_archivos import (
        ejecutar_fase_1
    )


# ============================================================
# CONFIGURACIÓN
# ============================================================

KEY = str(
    Path(__file__).resolve().parents[1]
    / 'config'
    / 'key.json'
)

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/spreadsheets.readonly'
]


# ============================================================
# AUTENTICACIÓN
# ============================================================

creds = service_account.Credentials.from_service_account_file(
    KEY,
    scopes=SCOPES
)


# ============================================================
# SERVICIOS GOOGLE
# ============================================================

drive = build(
    'drive',
    'v3',
    credentials=creds
)

sheets = build(
    'sheets',
    'v4',
    credentials=creds
)


# ============================================================
# CONSTANTES DE LA ESTRUCTURA DE LA HOJA
# ============================================================

FILA_DOCENTE = 1
FILA_NOMBRE_DOCENTE = 2
FILA_DURACION = 3
FILA_PERIODO = 4
FILA_TIPO_EVALUACION = 5
FILA_ENCABEZADOS = 6

FILA_INICIO_ESTUDIANTES = 7


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def limpiar_texto(valor):
    """
    Convierte un valor a texto limpio.
    """

    if valor is None:
        return ''

    return str(valor).strip()


def es_vacio(valor):
    """
    Determina si una celda está vacía.
    """

    if valor is None:
        return True

    if pd.isna(valor):
        return True

    return str(valor).strip() == ''


def obtener_valor(matriz, fila, columna):
    """
    Obtiene un valor de una matriz evitando errores
    por filas o columnas inexistentes.
    """

    if fila >= len(matriz):
        return ''

    if columna >= len(matriz[fila]):
        return ''

    return limpiar_texto(
        matriz[fila][columna]
    )


def ejecutar_lectura_google(solicitud, intentos=4):

    for intento in range(intentos):

        try:
            return solicitud.execute()

        except Exception as error:

            estado = getattr(
                getattr(error, 'resp', None),
                'status',
                None
            )

            if estado not in {429, 500, 502, 503, 504}:
                raise error

            es_ultimo_intento = intento == intentos - 1

            if es_ultimo_intento:
                raise error

            espera = 30 * (intento + 1)

            print(
                f"Cuota de lectura alcanzada. "
                f"Reintentando en {espera} segundos..."
            )

            time.sleep(
                espera
            )


# ============================================================
# OBTENER HOJAS DEL ARCHIVO
# ============================================================

def obtener_hojas_archivo(id_archivo):

    respuesta = ejecutar_lectura_google(
        sheets.spreadsheets().get(
        spreadsheetId=id_archivo,
        fields='sheets(properties(sheetId,title,index))'
        )
    )

    hojas = []

    for hoja in respuesta.get('sheets', []):

        propiedades = hoja['properties']

        hojas.append({
            'ID_HOJA': propiedades['sheetId'],
            'NOMBRE_HOJA': propiedades['title'],
            'INDICE_HOJA': propiedades['index']
        })

    return pd.DataFrame(hojas)


# ============================================================
# OBTENER INFORMACIÓN DE UNA HOJA
# ============================================================

def leer_hoja(id_archivo, nombre_hoja):

    rango = f"'{nombre_hoja}'"

    respuesta = ejecutar_lectura_google(
        sheets.spreadsheets().values().get(
            spreadsheetId=id_archivo,
            range=rango,
            majorDimension='ROWS'
        )
    )

    valores = respuesta.get(
        'values',
        []
    )

    return valores


# ============================================================
# NORMALIZAR MATRIZ
# ============================================================

def normalizar_matriz(matriz):

    if not matriz:
        return []

    cantidad_columnas = max(
        len(fila)
        for fila in matriz
    )

    matriz_normalizada = []

    for fila in matriz:

        fila_nueva = fila + [
            ''
        ] * (
            cantidad_columnas - len(fila)
        )

        matriz_normalizada.append(
            fila_nueva
        )

    return matriz_normalizada


# ============================================================
# DETECTAR FILA DE ENCABEZADOS
# ============================================================

def detectar_fila_encabezados(matriz):

    for indice, fila in enumerate(matriz):

        valores = [
            limpiar_texto(valor).lower()
            for valor in fila
        ]

        tiene_numero = '#' in valores

        tiene_documento = any(
            'documento' in valor
            for valor in valores
        )

        tiene_estudiante = any(
            'estudiante' in valor
            for valor in valores
        )

        if (
            tiene_numero
            and tiene_documento
            and tiene_estudiante
        ):

            return indice

    raise ValueError(
        'No fue posible detectar la fila de encabezados.'
    )


# ============================================================
# IDENTIFICAR COLUMNAS BASE DEL ESTUDIANTE
# ============================================================

def identificar_columnas_estudiante(encabezados):

    columnas = {}

    for indice, encabezado in enumerate(encabezados):

        texto = limpiar_texto(
            encabezado
        ).lower()

        if texto == '#':
            columnas['NUMERO'] = indice

        elif 'documento' in texto:
            columnas['DOCUMENTO'] = indice

        elif (
            'estudiante' in texto
            or texto == 'nombre'
            or 'nombre' in texto
        ):
            columnas['NOMBRE'] = indice

        elif 'institución educativa' in texto:
            columnas['INSTITUCION'] = indice

        elif (
            'correo institucional' in texto
            or texto == 'correo'
        ):
            columnas['CORREO'] = indice

        elif (
            'teléfono' in texto
            or 'telefono' in texto
        ):
            columnas['TELEFONO'] = indice

        elif texto == 'estado':
            columnas['ESTADO'] = indice

        elif 'asignaturas a repetir' in texto:
            columnas['ASIGNATURAS_A_REPETIR'] = indice

    return columnas


# ============================================================
# DETECTAR SI ES UNA COLUMNA DE OBSERVACIÓN
# ============================================================

def es_columna_observacion(nombre):

    texto = limpiar_texto(
        nombre
    ).lower()

    return (
        texto.startswith('observaciones')
        or texto.startswith('observación')
    )


# ============================================================
# DETECTAR COLUMNAS DE ASIGNATURAS
# ============================================================

def identificar_columnas_academicas(
    matriz,
    encabezados,
    columnas_estudiante
):

    columnas_academicas = []
    asignatura_anterior = None

    for columna, encabezado in enumerate(encabezados):

        nombre = limpiar_texto(
            encabezado
        )

        # ----------------------------------------------------
        # Ignorar columnas personales
        # ----------------------------------------------------

        if columna in columnas_estudiante.values():
            continue

        # ----------------------------------------------------
        # Las observaciones se procesan aparte
        # ----------------------------------------------------

        if es_columna_observacion(nombre):
            continue

        # ----------------------------------------------------
        # Obtener metadatos de las filas superiores
        # ----------------------------------------------------

        docente = obtener_valor(
            matriz,
            FILA_NOMBRE_DOCENTE,
            columna
        )

        duracion = obtener_valor(
            matriz,
            FILA_DURACION,
            columna
        )

        periodo = obtener_valor(
            matriz,
            FILA_PERIODO,
            columna
        )

        tipo_evaluacion = obtener_valor(
            matriz,
            FILA_TIPO_EVALUACION,
            columna
        )

        # ----------------------------------------------------
        # Una asignatura de 16 semanas puede ocupar dos
        # columnas: la segunda conserva el nombre y cambia
        # únicamente sus datos de periodo y evaluación.
        # ----------------------------------------------------

        if (
            nombre == ''
            and asignatura_anterior
            and asignatura_anterior['DURACION'].lower()
            == '16 semanas'
            and periodo != ''
        ):
            nombre = asignatura_anterior['ASIGNATURA']
            docente = asignatura_anterior['DOCENTE']
            duracion = asignatura_anterior['DURACION']

        # ----------------------------------------------------
        # Ignorar columnas sin nombre ni metadatos académicos
        # ----------------------------------------------------

        if nombre == '':
            continue

        # ----------------------------------------------------
        # Una columna académica válida debe tener
        # información académica en las filas superiores
        # ----------------------------------------------------

        tiene_metadatos = any([
            docente != '',
            duracion != '',
            periodo != '',
            tipo_evaluacion != ''
        ])

        if not tiene_metadatos:
            continue

        # ----------------------------------------------------
        # Validar que realmente sea una asignatura
        # ----------------------------------------------------

        if (
            nombre != ''
            and (
                docente != ''
                or duracion != ''
                or periodo != ''
                or tipo_evaluacion != ''
            )
        ):

            asignatura = {

                'COLUMNA': columna,

                'ASIGNATURA': nombre,

                'DOCENTE': docente,

                'DURACION': duracion,

                'PERIODO': periodo,

                'TIPO_EVALUACION':
                    tipo_evaluacion

            }

            columnas_academicas.append(
                asignatura
            )

            asignatura_anterior = asignatura

    return columnas_academicas


# ============================================================
# CONSTRUIR DATAFRAME DE ESTUDIANTES
# ============================================================

def construir_estudiantes_df(
    matriz,
    columnas_estudiante,
    metadatos_archivo,
    id_hoja
):

    registros = []

    for fila_indice in range(
        FILA_INICIO_ESTUDIANTES,
        len(matriz)
    ):

        fila = matriz[fila_indice]

        # ----------------------------------------------------
        # Número del estudiante
        # ----------------------------------------------------

        numero = ''

        if 'NUMERO' in columnas_estudiante:

            numero = obtener_valor(
                matriz,
                fila_indice,
                columnas_estudiante['NUMERO']
            )

        # ----------------------------------------------------
        # Si no existe número, ignoramos la fila
        # ----------------------------------------------------

        if numero == '':
            continue

        registro = {

            'SEMESTRE':
                metadatos_archivo['SEMESTRE'],

            'NIVEL':
                metadatos_archivo['NIVEL'],

            'ID_ARCHIVO':
                metadatos_archivo['ID_ARCHIVO'],

            'NOMBRE_ARCHIVO':
                metadatos_archivo['NOMBRE_ARCHIVO'],

            'ID_HOJA':
                id_hoja,

            'NUMERO':
                numero
        }

        # ----------------------------------------------------
        # Agregar columnas personales
        # ----------------------------------------------------

        for nombre_columna, indice_columna \
                in columnas_estudiante.items():

            if nombre_columna == 'NUMERO':
                continue

            registro[nombre_columna] = obtener_valor(
                matriz,
                fila_indice,
                indice_columna
            )

        registros.append(
            registro
        )

    return pd.DataFrame(
        registros
    )


# ============================================================
# CONSTRUIR DATAFRAME DE ASIGNATURAS
# ============================================================

def construir_asignaturas_df(
    columnas_academicas,
    metadatos_archivo,
    id_hoja
):

    registros = []

    for asignatura in columnas_academicas:

        registros.append({

            'SEMESTRE':
                metadatos_archivo['SEMESTRE'],

            'NIVEL':
                metadatos_archivo['NIVEL'],

            'ID_ARCHIVO':
                metadatos_archivo['ID_ARCHIVO'],

            'NOMBRE_ARCHIVO':
                metadatos_archivo['NOMBRE_ARCHIVO'],

            'ID_HOJA':
                id_hoja,

            'COLUMNA':
                asignatura['COLUMNA'],

            'ASIGNATURA':
                asignatura['ASIGNATURA'],

            'DOCENTE':
                asignatura['DOCENTE'],

            'DURACION':
                asignatura['DURACION'],

            'PERIODO':
                asignatura['PERIODO'],

            'TIPO_EVALUACION':
                asignatura['TIPO_EVALUACION']

        })

    return pd.DataFrame(
        registros
    )


# ============================================================
# CONSTRUIR DATAFRAME DE OBSERVACIONES
# ============================================================

def construir_observaciones_df(
    matriz,
    encabezados,
    columnas_estudiante,
    metadatos_archivo,
    id_hoja,
    columnas_academicas
):

    registros = []

    # --------------------------------------------------------
    # Crear mapa de columnas académicas
    # --------------------------------------------------------

    mapa_asignaturas = {

        item['COLUMNA']: item

        for item in columnas_academicas

    }

    # --------------------------------------------------------
    # Recorrer encabezados
    # --------------------------------------------------------

    for columna, encabezado in enumerate(encabezados):

        nombre_observacion = limpiar_texto(
            encabezado
        )

        if not es_columna_observacion(
            nombre_observacion
        ):
            continue

        # ----------------------------------------------------
        # Intentar identificar asignatura desde el encabezado
        # ----------------------------------------------------

        asignatura = ''

        periodo = ''

        tipo_evaluacion = ''

        texto = nombre_observacion.lower()

        # ----------------------------------------------------
        # Observaciones Parciales de:
        # ----------------------------------------------------

        if 'parciales de:' in texto:

            posicion = texto.find(
                'parciales de:'
            )

            asignatura = nombre_observacion[
                posicion + len('parciales de:')
            ].strip()

            tipo_evaluacion = 'Parciales'

            periodo = '1'

        # ----------------------------------------------------
        # Observaciones Finales de:
        # ----------------------------------------------------

        elif 'finales de:' in texto:

            posicion = texto.find(
                'finales de:'
            )

            asignatura = nombre_observacion[
                posicion + len('finales de:')
            ].strip()

            tipo_evaluacion = 'Finales'

            periodo = '2'

        # ----------------------------------------------------
        # Observaciones de:
        # ----------------------------------------------------

        elif 'observaciones de:' in texto:

            posicion = texto.find(
                'observaciones de:'
            )

            asignatura = nombre_observacion[
                posicion + len('observaciones de:')
            ].strip()

        # ----------------------------------------------------
        # Buscar coincidencia con asignaturas
        # ----------------------------------------------------

        asignatura_encontrada = None

        for item in columnas_academicas:

            if (
                item['ASIGNATURA'].strip().lower()
                == asignatura.strip().lower()
            ):

                asignatura_encontrada = item
                break

        # ----------------------------------------------------
        # Si es una observación genérica, tomar metadatos
        # de la asignatura correspondiente
        # ----------------------------------------------------

        if asignatura_encontrada:

            if periodo == '':

                periodo = (
                    asignatura_encontrada['PERIODO']
                )

            if tipo_evaluacion == '':

                tipo_evaluacion = (
                    asignatura_encontrada[
                        'TIPO_EVALUACION'
                    ]
                )

        # ----------------------------------------------------
        # Recorrer estudiantes
        # ----------------------------------------------------

        for fila_indice in range(
            FILA_INICIO_ESTUDIANTES,
            len(matriz)
        ):

            numero = obtener_valor(
                matriz,
                fila_indice,
                columnas_estudiante.get(
                    'NUMERO',
                    -1
                )
            )

            if numero == '':
                continue

            documento = obtener_valor(
                matriz,
                fila_indice,
                columnas_estudiante.get(
                    'DOCUMENTO',
                    -1
                )
            )

            observacion = obtener_valor(
                matriz,
                fila_indice,
                columna
            )

            # ------------------------------------------------
            # Solo registrar observaciones con contenido
            # ------------------------------------------------

            if observacion == '':
                continue

            registros.append({

                'SEMESTRE':
                    metadatos_archivo['SEMESTRE'],

                'NIVEL':
                    metadatos_archivo['NIVEL'],

                'ID_ARCHIVO':
                    metadatos_archivo['ID_ARCHIVO'],

                'NOMBRE_ARCHIVO':
                    metadatos_archivo['NOMBRE_ARCHIVO'],

                'ID_HOJA':
                    id_hoja,

                'NUMERO_ESTUDIANTE':
                    numero,

                'DOCUMENTO':
                    documento,

                'ASIGNATURA':
                    asignatura,

                'PERIODO':
                    periodo,

                'TIPO_EVALUACION':
                    tipo_evaluacion,

                'COLUMNA_OBSERVACION':
                    columna,

                'NOMBRE_COLUMNA':
                    nombre_observacion,

                'OBSERVACION':
                    observacion

            })

    return pd.DataFrame(
        registros
    )


# ============================================================
# NORMALIZAR NOTAS
# ============================================================

def normalizar_nota(valor):

    valor_original = limpiar_texto(valor)

    if valor_original == '':
        return None, 'VACIA'

    valor_mayusculas = valor_original.upper().replace(
        ' ',
        ''
    )

    if valor_mayusculas in {'N/A', 'N.A'}:
        return None, 'NA'

    try:
        nota = float(
            valor_original.replace(',', '.')
        )
    except ValueError:
        return None, 'INVALIDA'

    estado = (
        'APROBADA'
        if nota >= 3.0
        else 'REPROBADA'
    )

    return nota, estado


# ============================================================
# CONSTRUIR DATAFRAME DE NOTAS
# ============================================================

def construir_notas_df(
    matriz,
    columnas_estudiante,
    metadatos_archivo,
    id_hoja,
    columnas_academicas
):

    registros = []

    for fila_indice in range(
        FILA_INICIO_ESTUDIANTES,
        len(matriz)
    ):

        numero = obtener_valor(
            matriz,
            fila_indice,
            columnas_estudiante.get(
                'NUMERO',
                -1
            )
        )

        if numero == '':
            continue

        documento = obtener_valor(
            matriz,
            fila_indice,
            columnas_estudiante.get(
                'DOCUMENTO',
                -1
            )
        )

        nombre_estudiante = obtener_valor(
            matriz,
            fila_indice,
            columnas_estudiante.get(
                'NOMBRE',
                -1
            )
        )

        for asignatura in columnas_academicas:

            valor_original = obtener_valor(
                matriz,
                fila_indice,
                asignatura['COLUMNA']
            )

            nota, estado_nota = normalizar_nota(
                valor_original
            )

            registros.append({

                'SEMESTRE':
                    metadatos_archivo['SEMESTRE'],

                'NIVEL':
                    metadatos_archivo['NIVEL'],

                'ID_ARCHIVO':
                    metadatos_archivo['ID_ARCHIVO'],

                'NOMBRE_ARCHIVO':
                    metadatos_archivo['NOMBRE_ARCHIVO'],

                'ID_HOJA':
                    id_hoja,

                'NUMERO_ESTUDIANTE':
                    numero,

                'DOCUMENTO':
                    documento,

                'NOMBRE_ESTUDIANTE':
                    nombre_estudiante,

                'COLUMNA':
                    asignatura['COLUMNA'],

                'ASIGNATURA':
                    asignatura['ASIGNATURA'],

                'DOCENTE':
                    asignatura['DOCENTE'],

                'DURACION':
                    asignatura['DURACION'],

                'PERIODO':
                    asignatura['PERIODO'],

                'TIPO_EVALUACION':
                    asignatura['TIPO_EVALUACION'],

                'VALOR_ORIGINAL':
                    valor_original,

                'NOTA':
                    nota,

                'ESTADO_NOTA':
                    estado_nota

            })

    return pd.DataFrame(
        registros
    )


# ============================================================
# PROCESAR HOJA ÍNDICE 0
# ============================================================

def procesar_hoja_indice(
    id_archivo,
    nombre_hoja,
    metadatos_archivo,
    id_hoja
):

    print(
        f"\n{'=' * 90}"
    )

    print(
        f"PROCESANDO HOJA ÍNDICE 0: "
        f"{nombre_hoja}"
    )

    print(
        f"{'=' * 90}"
    )

    # --------------------------------------------------------
    # Leer hoja
    # --------------------------------------------------------

    matriz = leer_hoja(
        id_archivo,
        nombre_hoja
    )

    matriz = normalizar_matriz(
        matriz
    )

    if not matriz:

        raise ValueError(
            'La hoja no contiene información.'
        )

    # --------------------------------------------------------
    # Detectar encabezados
    # --------------------------------------------------------

    fila_encabezados = detectar_fila_encabezados(
        matriz
    )

    print(
        f"Fila de encabezados detectada: "
        f"{fila_encabezados}"
    )

    encabezados = matriz[
        fila_encabezados
    ]

    # --------------------------------------------------------
    # Identificar columnas personales
    # --------------------------------------------------------

    columnas_estudiante = \
        identificar_columnas_estudiante(
            encabezados
        )

    print(
        "\nCOLUMNAS DE ESTUDIANTES:"
    )

    for nombre, indice in \
            columnas_estudiante.items():

        print(
            f"  {nombre}: columna {indice}"
        )

    # --------------------------------------------------------
    # Identificar columnas académicas
    # --------------------------------------------------------

    columnas_academicas = \
        identificar_columnas_academicas(
            matriz,
            encabezados,
            columnas_estudiante
        )

    print(
        "\nCOLUMNAS ACADÉMICAS:"
    )

    for item in columnas_academicas:

        print(
            f"  {item['COLUMNA']} -> "
            f"{item['ASIGNATURA']} | "
            f"{item['DOCENTE']} | "
            f"{item['DURACION']} | "
            f"Periodo {item['PERIODO']} | "
            f"{item['TIPO_EVALUACION']}"
        )

    # --------------------------------------------------------
    # Crear DataFrame estudiantes
    # --------------------------------------------------------

    estudiantes_df = construir_estudiantes_df(
        matriz,
        columnas_estudiante,
        metadatos_archivo,
        id_hoja
    )

    # --------------------------------------------------------
    # Crear DataFrame asignaturas
    # --------------------------------------------------------

    asignaturas_df = construir_asignaturas_df(
        columnas_academicas,
        metadatos_archivo,
        id_hoja
    )

    # --------------------------------------------------------
    # Crear DataFrame observaciones
    # --------------------------------------------------------

    observaciones_df = construir_observaciones_df(
        matriz,
        encabezados,
        columnas_estudiante,
        metadatos_archivo,
        id_hoja,
        columnas_academicas
    )

    notas_df = construir_notas_df(
        matriz,
        columnas_estudiante,
        metadatos_archivo,
        id_hoja,
        columnas_academicas
    )

    return (
        estudiantes_df,
        asignaturas_df,
        observaciones_df,
        notas_df
    )


# ============================================================
# FASE 2
# ============================================================

def ejecutar_fase_2():

    # ========================================================
    # FASE 1
    # ========================================================

    archivos_df = ejecutar_fase_1()

    if archivos_df.empty:

        print(
            'No existen archivos para procesar.'
        )

        return (
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame()
        )

    # ========================================================
    # SELECCIONAR UN ÚNICO ARCHIVO
    # ========================================================

    archivo = archivos_df.iloc[0]

    metadatos_archivo = {

        'SEMESTRE':
            archivo['SEMESTRE'],

        'NIVEL':
            archivo['NIVEL'],

        'ID_ARCHIVO':
            archivo['ID_ARCHIVO'],

        'NOMBRE_ARCHIVO':
            archivo['NOMBRE_ARCHIVO']

    }

    print(
        "\n" + "=" * 90
    )

    print(
        "FASE 2 - LECTURA DE ARCHIVO"
    )

    print(
        "=" * 90
    )

    print(
        f"\nArchivo seleccionado:"
    )

    print(
        f"  Semestre: "
        f"{metadatos_archivo['SEMESTRE']}"
    )

    print(
        f"  Nivel: "
        f"{metadatos_archivo['NIVEL']}"
    )

    print(
        f"  Nombre: "
        f"{metadatos_archivo['NOMBRE_ARCHIVO']}"
    )

    print(
        f"  ID: "
        f"{metadatos_archivo['ID_ARCHIVO']}"
    )

    # ========================================================
    # OBTENER HOJA ÍNDICE 0
    # ========================================================

    hojas_df = obtener_hojas_archivo(
        metadatos_archivo['ID_ARCHIVO']
    )

    print(
        "\n" + "=" * 90
    )

    print(
        "DATAFRAME DE HOJAS"
    )

    print(
        "=" * 90
    )

    print(
        hojas_df.to_string(
            index=False
        )
    )

    hoja_indice = hojas_df[
        hojas_df['INDICE_HOJA'] == 0
    ]

    if hoja_indice.empty:

        raise ValueError(
            'No se encontró la hoja con índice 0.'
        )

    hoja = hoja_indice.iloc[0]

    # ========================================================
    # PROCESAR ÚNICAMENTE ÍNDICE 0
    # ========================================================

    (
        estudiantes_df,
        asignaturas_df,
        observaciones_df,
        notas_df
    ) = procesar_hoja_indice(

        metadatos_archivo['ID_ARCHIVO'],

        hoja['NOMBRE_HOJA'],

        metadatos_archivo,

        hoja['ID_HOJA']
    )

    return (
        estudiantes_df,
        asignaturas_df,
        observaciones_df,
        notas_df
    )


# ============================================================
# EJECUCIÓN
# ============================================================

if __name__ == '__main__':

    (
        estudiantes_df,
        asignaturas_df,
        observaciones_df,
        notas_df
    ) = ejecutar_fase_2()

    # ========================================================
    # ESTUDIANTES
    # ========================================================

    print(
        "\n" + "=" * 90
    )

    print(
        "DATAFRAME DE ESTUDIANTES"
    )

    print(
        "=" * 90
    )

    if estudiantes_df.empty:

        print(
            "No se encontraron estudiantes."
        )

    else:

        print(
            estudiantes_df.to_string(
                index=False
            )
        )

    # ========================================================
    # ASIGNATURAS
    # ========================================================

    print(
        "\n" + "=" * 90
    )

    print(
        "DATAFRAME DE ASIGNATURAS"
    )

    print(
        "=" * 90
    )

    if asignaturas_df.empty:

        print(
            "No se encontraron asignaturas."
        )

    else:

        print(
            asignaturas_df.to_string(
                index=False
            )
        )

    # ========================================================
    # OBSERVACIONES
    # ========================================================

    print(
        "\n" + "=" * 90
    )

    print(
        "DATAFRAME DE OBSERVACIONES"
    )

    print(
        "=" * 90
    )

    if observaciones_df.empty:

        print(
            "No se encontraron observaciones."
        )

    else:

        print(
            observaciones_df.to_string(
                index=False
            )
        )

    # ========================================================
    # NOTAS
    # ========================================================

    print(
        "\n" + "=" * 90
    )

    print(
        "DATAFRAME DE NOTAS"
    )

    print(
        "=" * 90
    )

    if notas_df.empty:

        print(
            "No se encontraron notas."
        )

    else:

        print(
            notas_df.to_string(
                index=False
            )
        )

    # ========================================================
    # RESUMEN
    # ========================================================

    print(
        "\n" + "=" * 90
    )

    print(
        "RESUMEN FASE 2"
    )

    print(
        "=" * 90
    )

    print(
        f"Estudiantes: "
        f"{len(estudiantes_df)}"
    )

    print(
        f"Asignaturas: "
        f"{len(asignaturas_df)}"
    )

    print(
        f"Observaciones: "
        f"{len(observaciones_df)}"
    )

    print(
        f"Notas: "
        f"{len(notas_df)}"
    )