import streamlit as st
import pandas as pd
import tempfile
import os
import plotly.express as px
from test import (
    preprocesar_datos,
    crear_reporte_base,
    procesar_referencias_ppi,
    calcular_dias_en_calle
)

def inicializar_estado():
    """Inicializa las variables de sesión al cargar la aplicación."""
    if 'clientes_seleccionados' not in st.session_state:
        st.session_state.clientes_seleccionados = []
    if 'rango_dias' not in st.session_state:
        st.session_state.rango_dias = (0.0, 0.0)

def pagina_generacion_reporte():
    """Página para generar el reporte inicial"""
    st.title("📊 Generador de Reporte de Días en Calle")
    
    # Instrucciones
    st.markdown("""
    ### 📋 Instrucciones
    1. Cargue todos los archivos Excel requeridos
    2. Presione el botón 'Generar Reporte'
    3. Descargue el archivo de reporte
    """)
    
    # Columnas para los file uploaders
    col1, col2 = st.columns(2)
    
    with col1:
        archivos = {
            'cobranza_recibo': st.file_uploader('Cobranza por Recibo', type=['xlsx'], key='cobranza_recibo'),
            'cobranza_factura': st.file_uploader('Cobranza por Factura', type=['xlsx'], key='cobranza_factura'),
            'detalle_de_recibos': st.file_uploader('Detalle de Recibos', type=['xlsx'], key='detalle_de_recibo')
        }
    
    with col2:
        archivos.update({
            'deudores_ventas': st.file_uploader('Deudores por Ventas', type=['xlsx'], key='deudores_ventas'),
            'mayor_ppi': st.file_uploader('Mayor de PPIs', type=['xlsx'], key='mayor_ppi')
        })
    
    # Convertir archivos a DataFrames
    dfs = {}
    for key, file in archivos.items():
        if file is not None:
            try:
                dfs[key] = pd.read_excel(file)
            except Exception as e:
                st.error(f"Error al cargar {key}: {str(e)}")
    
    # Botón para generar reporte
    if st.button('Generar Reporte', type='primary'):
        # Verificar que todos los archivos estén cargados
        if len(dfs) == 5:
            with st.spinner('Generando reporte...'):
                try:
                    # Procesar datos
                    dfs_procesados = preprocesar_datos(dfs)
                    reporte_base, facturas_no_encontradas = crear_reporte_base(dfs_procesados)
                    reporte_procesado, asientos_no_encontrados = procesar_referencias_ppi(
                        reporte_base, dfs_procesados['mayor_ppi']
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
                            label="📥 Descargar Reporte Completo",
                            data=f.read(),
                            file_name="reporte_dias_en_calle.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    
                    # Eliminar archivo temporal
                    os.unlink(tmp.name)
                    
                except Exception as e:
                    st.error(f"Error al generar el reporte: {str(e)}")
        else:
            st.warning("Por favor, cargue todos los archivos requeridos")

def pagina_analisis_reporte():
    """Página para análisis de reporte descargado"""
    st.title("🔍 Análisis de Reporte de Días en Calle")
    
    # Cargar archivo de reporte
    uploaded_file = st.file_uploader("Cargar Reporte de Días en Calle", type=['xlsx'])
    
    if uploaded_file is not None:
        try:
            # Leer la hoja de Indicador por Factura
            resultado_final = pd.read_excel(uploaded_file, sheet_name='Indicador por Factura')
            
            # Calcular métricas generales
            promedio_dias_calle = resultado_final['cantidad_de_dias_en_calle'].mean()
            total_clientes = resultado_final['Nombre'].nunique()
            total_facturas = len(resultado_final)
            
            # Columnas para métricas principales
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Promedio Días en Calle", f"{promedio_dias_calle:.2f}")
            
            with col2:
                st.metric("Total de Clientes", total_clientes)
            
            with col3:
                st.metric("Total de Facturas", total_facturas)
            
            # Sección de filtros
            st.subheader("Filtros y Visualización")
            
            # Columnas para filtros
            col_filtro1, col_filtro2 = st.columns(2)
            
            with col_filtro1:
                # Selector de cliente
                clientes_seleccionados = st.multiselect(
                    "Seleccionar Clientes", 
                    options=resultado_final['Nombre'].unique().tolist()
                )
            
            with col_filtro2:
                # Rango de días en calle
                min_dias = resultado_final['cantidad_de_dias_en_calle'].min()
                max_dias = resultado_final['cantidad_de_dias_en_calle'].max()
                
                rango_dias = st.slider(
                    "Rango de Días en Calle", 
                    min_value=float(min_dias), 
                    max_value=float(max_dias), 
                    value=(float(min_dias), float(max_dias))
                )
            
            # Aplicar filtros
            df_filtrado = resultado_final.copy()
            
            if clientes_seleccionados:
                df_filtrado = df_filtrado[df_filtrado['Nombre'].isin(clientes_seleccionados)]
            
            df_filtrado = df_filtrado[
                (df_filtrado['cantidad_de_dias_en_calle'] >= rango_dias[0]) & 
                (df_filtrado['cantidad_de_dias_en_calle'] <= rango_dias[1])
            ]
            
            # Visualizaciones
            st.subheader("Días en Calle por Cliente")
            grafico_dias_cliente = px.bar(
                df_filtrado.groupby('Nombre')['cantidad_de_dias_en_calle'].mean().reset_index(), 
                x='Nombre', 
                y='cantidad_de_dias_en_calle',
                title="Promedio de Días en Calle"
            )
            st.plotly_chart(grafico_dias_cliente, use_container_width=True)
            
            # Sección de detalles del cliente
            if clientes_seleccionados:
                st.subheader("Detalles de Clientes Seleccionados")
                
                for cliente in clientes_seleccionados:
                    # Datos específicos del cliente
                    df_cliente = df_filtrado[df_filtrado['Nombre'] == cliente]
                    
                    # Métricas del cliente
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric(f"Días en Calle - {cliente}", 
                                  f"{df_cliente['cantidad_de_dias_en_calle'].mean():.2f}")
                    
                    with col2:
                        st.metric(f"Cantidad Facturas - {cliente}", len(df_cliente))
                    
                    with col3:
                        st.metric(f"Total Factura - {cliente}", 
                                  f"{df_cliente['TotalFactura'].sum():,.2f}")
                    
                    # Tabla de detalles del cliente
                    st.dataframe(df_cliente, hide_index=True)
        
        except Exception as e:
            st.error(f"Error al cargar el archivo: {str(e)}")

def main():
    # Configuración de página
    st.set_page_config(
        page_title="Análisis de Días en Calle",
        page_icon="📊",
        layout="wide"
    )
    
    # Inicializar estado
    inicializar_estado()
    
    # Definir páginas de la aplicación
    pagina = st.sidebar.radio("Seleccionar Página", 
                               ["Generación de Reporte", "Análisis de Reporte"])
    
    # Mostrar la página seleccionada
    if pagina == "Generación de Reporte":
        pagina_generacion_reporte()
    else:
        pagina_analisis_reporte()

if __name__ == "__main__":
    main()