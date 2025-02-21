import streamlit as st
import pandas as pd
import tempfile
import os
from main import (
    preprocesar_datos,
    crear_reporte_base,
    procesar_referencias_ppi,
    calcular_dias_en_calle
)

def configurar_pagina():
    """Configura la página de Streamlit."""
    st.set_page_config(
        page_title="Reporte de Días en Calle",
        page_icon="📊",
        layout="wide"
    )
    st.title("📊 Generador de Reporte de Días en Calle")

def cargar_archivo(key: str, label: str) -> pd.DataFrame | None:
    """
    Permite al usuario cargar un archivo Excel.
    
    Args:
        key: Identificador único para el uploader
        label: Etiqueta que se mostrará al usuario
    
    Returns:
        pd.DataFrame | None: DataFrame con los datos cargados o None si no se cargó archivo
    """
    uploaded_file = st.file_uploader(label, type=['xlsx'], key=key)
    if uploaded_file is not None:
        try:
            if key == 'mayor_ppi':
                return pd.read_excel(uploaded_file, skiprows=2)
            return pd.read_excel(uploaded_file, skiprows=1)
        except Exception as e:
            st.error(f"Error al cargar el archivo {label}: {str(e)}")
            return None
    return None

def verificar_archivos_cargados(archivos: dict) -> bool:
    """
    Verifica que todos los archivos necesarios estén cargados.
    
    Args:
        archivos: Diccionario con los DataFrames
    
    Returns:
        bool: True si todos los archivos están cargados, False en caso contrario
    """
    archivos_faltantes = []
    for nombre, df in archivos.items():
        if df is None:
            archivos_faltantes.append(nombre.replace('_', ' ').title())
    
    if archivos_faltantes:
        st.warning(f"Faltan los siguientes archivos: {', '.join(archivos_faltantes)}")
        return False
    return True

def main():
    configurar_pagina()
    
    # Contenedor para la descripción
    with st.container():
        st.markdown("""
        ### 📋 Instrucciones
        1. Cargue todos los archivos Excel requeridos
        2. Presione el botón 'Generar Reporte'
        3. Descargue el archivo Excel con los resultados
        """)
    
    # Columnas para los file uploaders
    col1, col2 = st.columns(2)
    
    with col1:
        archivos = {
            'cobranza_recibo': cargar_archivo('cobranza_recibo', 'Cobranza por Recibo'),
            'cobranza_factura': cargar_archivo('cobranza_factura', 'Cobranza por Factura'),
            'deudores_ventas': cargar_archivo('deudores_ventas', 'Deudores por Ventas')
        }
    
    with col2:
        archivos.update({
            'diario_movimientos': cargar_archivo('diario_movimientos', 'Diario de Movimientos'),
            'mayor_ppi': cargar_archivo('mayor_ppi', 'Mayor de PPIs')
        })
    
    # Botón para generar reporte
    if st.button('Generar Reporte', type='primary'):
        if verificar_archivos_cargados(archivos):
            with st.spinner('Generando reporte...'):
                try:
                    # Procesar datos
                    dfs = preprocesar_datos(archivos)
                    reporte_base, facturas_no_encontradas = crear_reporte_base(dfs)
                    reporte_procesado, asientos_no_encontrados = procesar_referencias_ppi(
                        reporte_base, dfs['mayor_ppi']
                    )
                    resultado_final = calcular_dias_en_calle(reporte_procesado)
                    
                    # Crear archivo temporal
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp:
                        with pd.ExcelWriter(tmp.name) as writer:
                            resultado_final.to_excel(writer, sheet_name='Indicador por Factura', index=False)
                            reporte_procesado.to_excel(writer, sheet_name='Detalle del Reporte', index=False)
                            asientos_no_encontrados.to_excel(writer, sheet_name='Asientos No Encontrados', index=False)
                            facturas_no_encontradas.to_excel(writer, sheet_name='Facturas No Encontradas', index=False)
                    
                    # Leer el archivo temporal y mostrarlo para descarga
                    with open(tmp.name, 'rb') as f:
                        st.download_button(
                            label="📥 Descargar Reporte",
                            data=f.read(),
                            file_name="reporte_dias_en_calle.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    
                    # Eliminar archivo temporal
                    os.unlink(tmp.name)
                    
                    st.success('¡Reporte generado con éxito!')
                    
                except Exception as e:
                    st.error(f"Error al generar el reporte: {str(e)}")

if __name__ == "__main__":
    main()