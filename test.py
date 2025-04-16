import pandas as pd
from typing import Dict, Tuple
from src.procesar_asientos_no_encotrados import procesar_asientos_no_encontrados
from src.procesar_facturas_no_encontradas import test_facturas_no_encontradas, procesar_facturas_no_encontradas
from utils.data_utils import (
    extraer_numero_de_recibo,
    extraer_numero_de_factura,
)
from src.procesar_referencias_ppi import procesar_referencias_ppi


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
        'cobranza_recibo': pd.read_excel('./data/para_pruebas/cobranza_por_recibo.xlsx'),
        'cobranza_factura': pd.read_excel('./data/para_pruebas/cobranza_por_factura.xlsx'),
        'deudores_ventas': pd.read_excel('./data/para_pruebas/deudores_por_ventas.xlsx'),
        'mayor_ppi': pd.read_excel('./data/para_pruebas/COBROS TOTALES (PPI y CHEQUES).xlsx'),
        'detalle_de_recibos': pd.read_excel('./data/para_pruebas/Analisis financiero de cobranza por detalle de recibo.xlsx')
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
    dfs['cobranza_factura'] = extraer_numero_de_factura(dfs['cobranza_factura'], 'Factura')
    dfs['detalle_de_recibos'] = extraer_numero_de_factura(dfs['detalle_de_recibos'], 'Comprobante')
    dfs['detalle_de_recibos'] = extraer_numero_de_recibo(dfs['detalle_de_recibos'], 'Valor')
    
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
    reporte = dfs['cobranza_recibo'][['Nombre', 'Interno', 'nro_recibo', 'Pago']]
    
    print(f"Cantidad de filas en reporte: {reporte.shape[0]}")
    
    

    # Merge cobranza por recibos con deudores por ventas por el numero de recibo
    reporte = reporte.merge(
        dfs['deudores_ventas'],
        on='nro_recibo',
        how='left'
    )

    print(f"Cantidad de filas en reporte con deudores por venta: {reporte.shape[0]}")
    
    # Merge reporte con cobranzas por factura por el numero de recibo
    reporte = reporte.merge(
        dfs['cobranza_factura'][['nro_recibo', 'nro_factura', 'FechaFactura']],
        on='nro_recibo',
        how='left'
    )

    print(f"Cantidad de filas en reporte con cobranza por factura: {reporte.shape[0]}")
    
    # Separar facturas no encontradas
    facturas_no_encontradas = reporte[reporte['nro_factura'].isna()]
    reporte = reporte[reporte['nro_factura'].notna()]
    
    return reporte, facturas_no_encontradas


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
    
    # Calcular diferencia entre fecha de pago y de factura e importes por días
    reporte['cantidad_de_dias_para_cobrar'] = (reporte['Fecha'] - reporte['FechaFactura']).dt.days
    reporte['importe_por_dias'] = reporte['cantidad_de_dias_para_cobrar'] * reporte['Haber']
    
    # Calcular el pago total por número de recibo
    pagos_por_recibo = reporte.groupby('nro_recibo')['Pago'].first().reset_index()
    
    # Crear nuevo reporte agrupado por factura
    df_agrupado = reporte.groupby('nro_factura').agg({
        'importe_por_dias': 'sum',
        'Haber': 'sum',
        'Nombre': 'first',
        'nro_recibo': 'first',
        'Asiento': 'first',
        'Referencia': 'first'
    }).reset_index()
    
    # # Merge con los pagos por recibo
    df_agrupado = df_agrupado.merge(pagos_por_recibo, on='nro_recibo', how='left')

    # Calcular control de pago total
    df_agrupado['control_pago_total'] = df_agrupado['Pago'] - df_agrupado['Haber']

    # Calcular días en calle por cada factura
    df_agrupado['cantidad_de_dias_en_calle'] = df_agrupado['importe_por_dias'] / df_agrupado['Haber']
    
    df_agrupado.rename(
        columns={
            'Haber': 'TotalFactura'
            }, inplace=True)
    
    return df_agrupado[['Nombre', 'nro_recibo', 'TotalFactura', 'Pago', 'Asiento', 'nro_factura', 
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

    # Procesar facturas no encontradas
    facturas_encontradas, facturas_no_encontradas_final = procesar_facturas_no_encontradas(
        facturas_no_encontradas,
        dfs['detalle_de_recibos'],
        dfs['cobranza_factura']
    )

    # Procesar asientos no encontrados
    df_resultado, asientos_no_encontrados = procesar_asientos_no_encontrados(
        asientos_no_encontrados,
        dfs['detalle_de_recibos']
    )

    # Renombrar 'Pago_x' a 'Pago' en df_resultado para que coincida con reporte_procesado
    df_resultado.rename(columns={
        'Fecha del Valor': 'Fecha'}, inplace=True)
    
    
    facturas_encontradas.rename(
        columns={
            'Fecha Comp.': 'FechaFactura',
            'Fecha del Valor': 'Fecha',
            'Total': 'Haber'
            }, inplace=True)

    # print("INFO DF RESLUTADO")
    # print(len(df_resultado))
    # print(df_resultado.head())

    # print("INFO REPORTE PROCESADO")
    # print(len(reporte_procesado))
    # print(reporte_procesado.head())

    # print("INFO FACTURAS ENCONTRADAS")
    # print(len(facturas_encontradas))
    # print(facturas_encontradas.head())

    # print("-----   ------   -----")

    # print(df_resultado.columns)
    # print(reporte_procesado.columns)
    # print(facturas_encontradas.columns)

    # print(df_resultado[df_resultado['nro_recibo'] == '00084859'])
    # print(reporte_procesado[reporte_procesado['nro_recibo'] == '00084859'])

    # # Concatenar los DataFrames
    reporte_concatenado = pd.concat([df_resultado, reporte_procesado, facturas_encontradas], ignore_index=True)
    
    reporte_concatenado = reporte_concatenado[reporte_concatenado['Haber'].notna()]

    resultado_final = calcular_dias_en_calle(reporte_concatenado)
    
    # Guardar resultados
    guardar_reportes(
        resultado_final,
        reporte_concatenado,
        asientos_no_encontrados,
        facturas_no_encontradas_final
    )


if __name__ == "__main__":
    main()
    # test_facturas_no_encontradas()