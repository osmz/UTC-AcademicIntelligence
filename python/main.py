from fase_01_archivos import ejecutar_fase_1
from fase_03_publicacion import (
    HOJAS_AUTOMATICAS,
    obtener_servicio_sheets,
    procesar_archivos,
    publicar_dataframes,
    actualizar_pestana
)
from fase_04_seguimiento import (
    COLUMNAS_SEGUIMIENTO,
    asegurar_pestana_seguimiento,
    construir_seguimiento_df
)
from fase_05_reportes import (
    COLUMNAS_RECORDATORIOS,
    COLUMNAS_REPORTE_ESTUDIANTES,
    asegurar_pestanas_reportes,
    construir_recordatorios_df,
    construir_reporte_estudiantes_df,
    leer_pestana
)


# ============================================================
# FLUJO COMPLETO
# ============================================================

def ejecutar_flujo_completo():

    print('FASE 1 - Inventario de archivos')
    archivos_df = ejecutar_fase_1()

    print('FASE 2 - Lectura y procesamiento')
    (
        estudiantes_df,
        asignaturas_df,
        observaciones_df,
        notas_df
    ) = procesar_archivos(archivos_df)

    servicio = obtener_servicio_sheets()

    print('PUBLICACION - Datos base')
    publicar_dataframes(
        servicio,
        archivos_df,
        estudiantes_df,
        asignaturas_df,
        observaciones_df,
        notas_df
    )

    print('FASE 4 - Seguimiento')
    seguimiento_df = construir_seguimiento_df(
        notas_df
    )

    asegurar_pestana_seguimiento(
        servicio
    )

    actualizar_pestana(
        servicio,
        'SEGUIMIENTO',
        seguimiento_df,
        COLUMNAS_SEGUIMIENTO
    )

    print('FASE 5 - Reportes')
    docentes_df = leer_pestana(
        servicio,
        'DOCENTES'
    )

    recordatorios_df = construir_recordatorios_df(
        seguimiento_df,
        docentes_df
    )

    reporte_estudiantes_df = construir_reporte_estudiantes_df(
        notas_df
    )

    asegurar_pestanas_reportes(
        servicio
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

    print('Flujo completo publicado.')
    print(f'Archivos: {len(archivos_df)}')
    print(f'Estudiantes: {len(estudiantes_df)}')
    print(f'Asignaturas: {len(asignaturas_df)}')
    print(f'Observaciones: {len(observaciones_df)}')
    print(f'Notas: {len(notas_df)}')
    print(f'Seguimiento: {len(seguimiento_df)}')
    print(f'Recordatorios: {len(recordatorios_df)}')
    print(f'Reporte estudiantes: {len(reporte_estudiantes_df)}')

    return {
        'archivos': archivos_df,
        'estudiantes': estudiantes_df,
        'asignaturas': asignaturas_df,
        'observaciones': observaciones_df,
        'notas': notas_df,
        'seguimiento': seguimiento_df,
        'recordatorios': recordatorios_df,
        'reporte_estudiantes': reporte_estudiantes_df
    }


if __name__ == '__main__':
    ejecutar_flujo_completo()
