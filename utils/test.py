import pandas as pd
from utils.data_utils import extraer_numero_de_recibo, extraer_numero_de_factura
from utils.data_utils import procesar_movimientos_contables, crear_id_unico

# configuracion
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)

# lectura de los archivos
print("Leyendo archivos...")
df_cobranza_por_recibo = pd.read_excel('./data/cobranza_por_recibo.xlsx', skiprows=1)
df_cobranza_por_factura = pd.read_excel('./data/cobranza_por_factura.xlsx', skiprows=1)
df_deudores_por_ventas = pd.read_excel('./data/deudores_por_ventas.xlsx', skiprows=1)
df_diario_movimientos = pd.read_excel('./data/diario_movimientos.xlsx', skiprows=1)
df_mayor_de_ppi = pd.read_excel('./data/mayor_de_ppis.xlsx', skiprows=2)

## extraigo el número de recibo y lo agrego a una nueva columna llamada nro_recibo
df_cobranza_por_recibo = extraer_numero_de_recibo(df_cobranza_por_recibo, 'Recibo')
df_cobranza_por_factura = extraer_numero_de_recibo(df_cobranza_por_factura, 'Comprobante')

df_deudores_por_ventas = extraer_numero_de_recibo(df_deudores_por_ventas, 'Compr.Rel.')

## extraigo el número de factura y lo agrego a una nueva columna llamada nro_factura
df_cobranza_por_factura = extraer_numero_de_factura(df_cobranza_por_factura)

## ARMADO DE REPORTE FINAL

# convierto la columna Asiento a string
df_deudores_por_ventas = df_deudores_por_ventas[['nro_recibo', 'Asiento']].astype({'Asiento': 'str'})
reporte_final = df_cobranza_por_recibo[['Nombre', 'nro_recibo', 'Pago']]

## mergeo reporte_final con df_deudores_por_ventas por la columna nro_recibo
reporte_final = reporte_final.merge(
    df_deudores_por_ventas,
    on='nro_recibo',
    how='left'
)

## mergeo reporte_final con df_deudores_por_ventas por la columna nro_recibo
reporte_final = reporte_final.merge(
    df_cobranza_por_factura[['nro_recibo', 'nro_factura', 'FechaFactura']],
    on='nro_recibo',
    how='left'
)

## crear un nuevo DataFrame con aquellas facturas que no se encontraron en df_cobranza_por_factura
df_facturas_no_encontradas = reporte_final[reporte_final['nro_factura'].isna()]

## eliminar las facturas no encontradas de reporte_final
reporte_final = reporte_final[reporte_final['nro_factura'].notna()]

df_mayor_de_ppi['Asiento'] = df_mayor_de_ppi['Asiento'].astype(str)

## mergeo reporte_final con df_mayor_de_ppi para obtener la columna Referencia
reporte_final = reporte_final.merge(
    df_mayor_de_ppi[['Asiento', 'Referencia']],
    on='Asiento',
    how='left'
)

## crear un nuevo DataFrame con aquellos Asientos que no se encontraron en df_mayor_de_ppi
df_asientos_no_encontrados = reporte_final[reporte_final['Referencia'].isna()]

## eliminar los Asientos no encontrados de reporte_final
reporte_final = reporte_final[reporte_final['Referencia'].notna()]

## obtengo todos los registros de df_mayor_de_ppi que tengan el mismo número de Referencia
referencias = reporte_final['Referencia'].unique()
df_ppi_referencias = df_mayor_de_ppi[df_mayor_de_ppi['Referencia'].isin(referencias)]

## filtra df_ppi_referencias para obtener las filas donde la columna Haber tiene un valor no nulo
df_haber = df_ppi_referencias[df_ppi_referencias['Haber'].notna()][['Referencia', 'Fecha', 'Haber']]

## mergeo reporte_final con df_haber para agregar la fecha del movimiento
reporte_final = reporte_final.merge(
    df_haber,
    on='Referencia',
    how='left'
)

## eliminar las filas que tienen 0 en la columna Haber
reporte_final = reporte_final[reporte_final['Haber'] != 0]

## convierto las columnas Fecha y FechaFactura a tipo datetime
reporte_final['Fecha'] = pd.to_datetime(reporte_final['Fecha'])
reporte_final['FechaFactura'] = pd.to_datetime(reporte_final['FechaFactura'])

## calculo la diferencia de días entre Fecha y FechaFactura
reporte_final['cantidad_de_dias_para_cobrar'] = (reporte_final['Fecha'] - reporte_final['FechaFactura']).dt.days

## multiplico la diferencia de días por el importe en la columna Haber
reporte_final['importe_por_dias'] = reporte_final['cantidad_de_dias_para_cobrar'] * reporte_final['Haber']


## agrupo por nro_factura y calculo la suma de importe_por_dias
df_agrupado = reporte_final.groupby('nro_factura').agg({
    'importe_por_dias': 'sum',
    'Nombre': 'first',
    'Pago': 'first',
    'nro_recibo': 'first',
    'Asiento': 'first',
    'Referencia': 'first'
}).reset_index()

## calculo la cantidad de días en la calle
df_agrupado['cantidad_de_dias_en_calle'] = df_agrupado['importe_por_dias'] / df_agrupado['Pago']

## selecciono las columnas necesarias
df_resultado = df_agrupado[['Nombre', 'nro_recibo', 'Pago', 'Asiento', 'nro_factura', 'Referencia', 'cantidad_de_dias_en_calle']]

# Guardar todos los DataFrames en un solo archivo Excel con diferentes hojas
with pd.ExcelWriter('./data/reporte_dias_en_calle.xlsx') as writer:
    df_resultado.to_excel(writer, sheet_name='Indicador por Factura', index=False)
    reporte_final.to_excel(writer, sheet_name='Detalle del Reporte', index=False)
    df_asientos_no_encontrados.to_excel(writer, sheet_name='Asientos No Encontrados', index=False)
    df_facturas_no_encontradas.to_excel(writer, sheet_name='Facturas No Encontradas', index=False)
    
