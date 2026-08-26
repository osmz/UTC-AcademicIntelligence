import re
from pathlib import Path
import pandas as pd

from google.oauth2 import service_account
from googleapiclient.discovery import build


# ============================================================
# CONFIGURACIÓN
# ============================================================

KEY = str(
    Path(__file__).resolve().parents[1]
    / 'config'
    / 'key.json'
)

# ID DE LA CARPETA MAESTRA 2026
CARPETA_RAIZ_ID = '1cHHtW6zsUYJsjlNp_KBspmsKoTNKhBan'

# Niveles académicos válidos
NIVELES_VALIDOS = {'TL', 'TP'}

# Patrón válido para semestres
# Ejemplos:
# 2026-1
# 2026-3
# 2027-1
# 2027-3
PATRON_SEMESTRE = r'^\d{4}-\d+$'

SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly'
]


# ============================================================
# AUTENTICACIÓN Y CONEXIÓN CON GOOGLE DRIVE
# ============================================================

def obtener_servicio_drive():

    creds = service_account.Credentials.from_service_account_file(
        KEY,
        scopes=SCOPES
    )

    return build(
        'drive',
        'v3',
        credentials=creds
    )


# Crear conexión a Google Drive
drive = obtener_servicio_drive()


# ============================================================
# OBTENER ELEMENTOS DE UNA CARPETA
# ============================================================

def obtener_elementos(carpeta_id):

    elementos = []

    page_token = None

    while True:

        resultado = drive.files().list(
            q=f"'{carpeta_id}' in parents and trashed = false",
            fields=(
                "nextPageToken, "
                "files(id, name, mimeType, webViewLink)"
            ),
            pageSize=1000,
            pageToken=page_token
        ).execute()

        elementos.extend(
            resultado.get('files', [])
        )

        page_token = resultado.get(
            'nextPageToken'
        )

        if not page_token:
            break

    return elementos


# ============================================================
# OBTENER CARPETAS
# ============================================================

def obtener_carpetas(carpeta_id):

    elementos = obtener_elementos(
        carpeta_id
    )

    return [
        elemento
        for elemento in elementos
        if elemento['mimeType']
        == 'application/vnd.google-apps.folder'
    ]


# ============================================================
# VALIDAR SI UNA CARPETA ES UN SEMESTRE
# ============================================================

def es_semestre(nombre):

    return bool(
        re.match(
            PATRON_SEMESTRE,
            nombre
        )
    )


# ============================================================
# OBTENER SEMESTRES VÁLIDOS
# ============================================================

def obtener_semestres(carpeta_raiz_id):

    carpetas = obtener_carpetas(
        carpeta_raiz_id
    )

    semestres = []

    for carpeta in carpetas:

        nombre = carpeta['name']

        if es_semestre(nombre):

            semestres.append(carpeta)

    return semestres


# ============================================================
# OBTENER NIVELES ACADÉMICOS VÁLIDOS
# ============================================================

def obtener_niveles(carpeta_semestre_id):

    carpetas = obtener_carpetas(
        carpeta_semestre_id
    )

    niveles = []

    for carpeta in carpetas:

        nombre = carpeta['name'].strip().upper()

        if nombre in NIVELES_VALIDOS:

            niveles.append({

                'id': carpeta['id'],

                'name': nombre

            })

    return niveles


# ============================================================
# OBTENER ARCHIVOS DE GRUPO
# ============================================================

def obtener_archivos_grupo(carpeta_id):

    elementos = obtener_elementos(
        carpeta_id
    )

    archivos = []

    for elemento in elementos:

        nombre = elemento['name']

        # Ignorar carpetas
        if elemento['mimeType'] == \
                'application/vnd.google-apps.folder':

            continue

        # Solo archivos cuyo nombre comienza por "Grupo"
        if nombre.startswith('Grupo'):

            archivos.append(elemento)

    return archivos


# ============================================================
# FASE 1
# ============================================================

def ejecutar_fase_1():

    registros = []

    # --------------------------------------------------------
    # 1. Obtener únicamente semestres válidos
    # --------------------------------------------------------

    semestres = obtener_semestres(
        CARPETA_RAIZ_ID
    )

    print("\nSEMESTRES VÁLIDOS ENCONTRADOS:")

    for semestre in semestres:

        print(
            f"  - {semestre['name']}"
        )

    # --------------------------------------------------------
    # 2. Recorrer cada semestre
    # --------------------------------------------------------

    for semestre in semestres:

        semestre_id = semestre['id']

        semestre_nombre = semestre['name']

        # ----------------------------------------------------
        # 3. Buscar únicamente TL y TP
        # ----------------------------------------------------

        niveles = obtener_niveles(
            semestre_id
        )

        print(
            f"\n{semestre_nombre}:"
        )

        for nivel in niveles:

            nivel_id = nivel['id']

            nivel_nombre = nivel['name']

            print(
                f"  - Nivel encontrado: {nivel_nombre}"
            )

            # ------------------------------------------------
            # 4. Buscar archivos Grupo
            # ------------------------------------------------

            archivos = obtener_archivos_grupo(
                nivel_id
            )

            print(
                f"    Archivos encontrados: "
                f"{len(archivos)}"
            )

            # ------------------------------------------------
            # 5. Registrar archivos
            # ------------------------------------------------

            for archivo in archivos:

                registros.append({

                    'SEMESTRE':
                        semestre_nombre,

                    'NIVEL':
                        nivel_nombre,

                    'ID_ARCHIVO':
                        archivo['id'],

                    'NOMBRE_ARCHIVO':
                        archivo['name'],

                    'URL':
                        archivo.get(
                            'webViewLink',
                            (
                                'https://drive.google.com/open?id='
                                + archivo['id']
                            )
                        ),

                    'TIPO':
                        archivo['mimeType']

                })

    # ========================================================
    # CREAR DATAFRAME
    # ========================================================

    archivos_df = pd.DataFrame(
        registros
    )

    # ========================================================
    # ORDENAR
    # ========================================================

    if not archivos_df.empty:

        archivos_df = archivos_df.sort_values(
            by=[
                'SEMESTRE',
                'NIVEL',
                'NOMBRE_ARCHIVO'
            ]
        ).reset_index(
            drop=True
        )

    return archivos_df


# ============================================================
# EJECUTAR
# ============================================================

if __name__ == '__main__':

    archivos_df = ejecutar_fase_1()

    # ========================================================
    # MOSTRAR RESULTADO
    # ========================================================

    print("\n" + "=" * 90)

    print(
        "FASE 1 - INVENTARIO DE ARCHIVOS"
    )

    print("=" * 90)

    if archivos_df.empty:

        print(
            "No se encontraron archivos de grupos."
        )

    else:

        print(
            archivos_df.to_string(
                index=False
            )
        )

    # ========================================================
    # RESUMEN
    # ========================================================

    print("\n" + "=" * 90)

    print("RESUMEN")

    print("=" * 90)

    print(
        f"Total archivos: "
        f"{len(archivos_df)}"
    )

    if not archivos_df.empty:

        print(
            f"Semestres: "
            f"{archivos_df['SEMESTRE'].nunique()}"
        )

        print(
            f"Niveles: "
            f"{archivos_df['NIVEL'].nunique()}"
        )

        print("\nArchivos por semestre:")

        print(
            archivos_df
            .groupby('SEMESTRE')
            .size()
            .to_string()
        )

        print("\nArchivos por nivel:")

        print(
            archivos_df
            .groupby('NIVEL')
            .size()
            .to_string()
        )