import pandas as pd
from typing import Dict, Tuple
from utils.data_utils import (
    extraer_numero_de_recibo,
    extraer_numero_de_factura,
)

def configurar_pandas() -> None:
    """Configura las opciones de visualización de pandas."""
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)

def cargar_archivos() -> Dict[str, pd.DataFrame]:
    """
    Carga todos los archivos Excel necesarios para el reporte.
    
    Returns:
        Dict[str, pd.DataFrame]: Diccionario con los DataFrames cargados
    """
    print("Leyendo archivos...")
    return {
        'cobranza_recibo': pd.read_excel('./data/cobranza_por_recibo.xlsx', skiprows=1),
        'cobranza_factura': pd.read_excel('./data/cobranza_por_factura.xlsx', skiprows=1),
        'deudores_ventas': pd.read_excel('./data/deudores_por_ventas.xlsx', skiprows=1),
        'diario_movimientos': pd.read_excel('./data/diario_movimientos.xlsx', skiprows=1),
        'mayor_ppi': pd.read_excel('./data/mayor_de_ppis.xlsx', skiprows=2)
    }

def preprocesar_datos(dfs: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Realiza el preprocesamiento inicial de los DataFrames.
    
    Args:
        dfs: Diccionario con los DataFrames originales
    
    Returns:
        Dict[str, pd.DataFrame]: Diccionario con los DataFrames preprocesados
    """
    print("Preprocesando Datos...")
    dfs['cobranza_recibo'] = extraer_numero_de_recibo(dfs['cobranza_recibo'], 'Recibo')
    dfs['cobranza_factura'] = extraer_numero_de_recibo(dfs['cobranza_factura'], 'Comprobante')
    dfs['deudores_ventas'] = extraer_numero_de_recibo(dfs['deudores_ventas'], 'Compr.Rel.')
    dfs['cobranza_factura'] = extraer_numero_de_factura(dfs['cobranza_factura'])
    
    # Conversión de tipos y selección de columnas
    dfs['deudores_ventas'] = dfs['deudores_ventas'][['nro_recibo', 'Asiento']].astype({'Asiento': 'str'})
    dfs['mayor_ppi']['Asiento'] = dfs['mayor_ppi']['Asiento'].astype(str)
    
    return dfs

def crear_reporte_base(dfs: Dict[str, pd.DataFrame]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Crea el reporte base mediante la unión de diferentes DataFrames.
    
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: Reporte base y facturas no encontradas
    """
    print("Creando Reporte Base...")
    reporte = dfs['cobranza_recibo'][['Nombre', 'nro_recibo', 'Pago']]
    
    # Merge con deudores por ventas
    reporte = reporte.merge(
        dfs['deudores_ventas'],
        on='nro_recibo',
        how='left'
    )
    
    # Merge con cobranza por factura
    reporte = reporte.merge(
        dfs['cobranza_factura'][['nro_recibo', 'nro_factura', 'FechaFactura']],
        on='nro_recibo',
        how='left'
    )
    
    # Separar facturas no encontradas
    facturas_no_encontradas = reporte[reporte['nro_factura'].isna()]
    reporte = reporte[reporte['nro_factura'].notna()]
    
    return reporte, facturas_no_encontradas

def procesar_referencias_ppi(reporte: pd.DataFrame, df_mayor_ppi: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Procesa las referencias PPI y calcula días para cobrar.
    
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: Reporte procesado y asientos no encontrados
    """

    print("Procesando Referencias PPI...")

    # Merge con mayor PPI
    reporte = reporte.merge(
        df_mayor_ppi[['Asiento', 'Referencia']],
        on='Asiento',
        how='left'
    )
    
    # Separar asientos no encontrados
    asientos_no_encontrados = reporte[reporte['Referencia'].isna()]
    reporte = reporte[reporte['Referencia'].notna()]
    
    # Procesar referencias
    referencias = reporte['Referencia'].unique()
    df_ppi_referencias = df_mayor_ppi[df_mayor_ppi['Referencia'].isin(referencias)]
    df_haber = df_ppi_referencias[df_ppi_referencias['Haber'].notna()][['Referencia', 'Fecha', 'Haber']]
    
    # Merge final
    reporte = reporte.merge(
        df_haber,
        on='Referencia',
        how='left'
    )
    
    return reporte.query('Haber != 0'), asientos_no_encontrados

def calcular_dias_en_calle(reporte: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula los días en calle y agrupa los resultados.
    
    Returns:
        pd.DataFrame: DataFrame con los cálculos finales
    """

    print("Calculando Días en Calle...")

    # Convertir fechas
    reporte['Fecha'] = pd.to_datetime(reporte['Fecha'])
    reporte['FechaFactura'] = pd.to_datetime(reporte['FechaFactura'])
    
    # Calcular diferencia entre fecha de pago yde factura e importes por días
    reporte['cantidad_de_dias_para_cobrar'] = (reporte['Fecha'] - reporte['FechaFactura']).dt.days
    reporte['importe_por_dias'] = reporte['cantidad_de_dias_para_cobrar'] * reporte['Haber']
    
    # Crear nuevo reporte agrupado por factura, sumando los importes por dia
    df_agrupado = reporte.groupby('nro_factura').agg({
        'importe_por_dias': 'sum',
        'Haber': 'sum',
        'Nombre': 'first',
        'Pago': 'sum',
        'nro_recibo': 'first',
        'Asiento': 'first',
        'Referencia': 'first'
    }).reset_index()
    
    df_agrupado['control_pago_total'] = df_agrupado['Pago'] - df_agrupado['Haber']

    # Calcular días en calle por cada factura
    df_agrupado['cantidad_de_dias_en_calle'] = df_agrupado['importe_por_dias'] / df_agrupado['Haber']
    
    return df_agrupado[['Nombre', 'nro_recibo', 'Haber', 'Pago', 'Asiento', 'nro_factura', 
                        'Referencia', 'cantidad_de_dias_en_calle', 'control_pago_total']]

def guardar_reportes(resultado: pd.DataFrame, reporte_detallado: pd.DataFrame,
                    asientos_no_encontrados: pd.DataFrame, facturas_no_encontradas: pd.DataFrame) -> None:
    """Guarda todos los reportes en un archivo Excel."""
    with pd.ExcelWriter('./data/reporte_dias_en_calle.xlsx') as writer:
        resultado.to_excel(writer, sheet_name='Indicador por Factura', index=False)
        reporte_detallado.to_excel(writer, sheet_name='Detalle del Reporte', index=False)
        asientos_no_encontrados.to_excel(writer, sheet_name='Asientos No Encontrados', index=False)
        facturas_no_encontradas.to_excel(writer, sheet_name='Facturas No Encontradas', index=False)

def main():
    """Función principal que ejecuta el proceso completo."""
    # Configuración inicial
    configurar_pandas()
    
    # Cargar y preprocesar datos
    dfs = cargar_archivos()
    dfs = preprocesar_datos(dfs)
    
    # Crear reporte base
    reporte_base, facturas_no_encontradas = crear_reporte_base(dfs)
    
    # Procesar referencias PPI
    reporte_procesado, asientos_no_encontrados = procesar_referencias_ppi(
        reporte_base, dfs['mayor_ppi']
    )
    
    # Calcular días en calle
    resultado_final = calcular_dias_en_calle(reporte_procesado)
    
    # Guardar resultados
    guardar_reportes(
        resultado_final,
        reporte_procesado,
        asientos_no_encontrados,
        facturas_no_encontradas
    )

if __name__ == "__main__":
    main()