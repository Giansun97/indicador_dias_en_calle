import pandas as pd
from src.procesar_referencias_ppi import procesar_referencias_ppi


def procesar_facturas_no_encontradas(
        facturas_no_encontradas: pd.DataFrame,
        df_detalle_recibos: pd.DataFrame,
        cobranza_por_facturas: pd.DataFrame
        ):
    
    # print(df_detalle_recibos[df_detalle_recibos['nro_factura'] == 'FA100-00142458'])
    ## 1) Merge facturas no encontradas con detalle de recibos por nro recibo interno.
    ##  facturas no encontaradas necesito Interno, nro_recibo, Nombre, Pago
    ## detalle de recibos necesito Recibo (es el interno de fact no encontradas), Fecha Comp. y nro_factura
    df_detalle_recibos['nro_recibo'] = df_detalle_recibos['nro_recibo'].astype(int)
    facturas_no_encontradas['Interno'] = facturas_no_encontradas['Interno'].astype(int)

    df_merged = facturas_no_encontradas[['Interno', 'Nombre', 'Pago']].merge(
        df_detalle_recibos[['nro_recibo', 'Fecha Comp.', 'Fecha del Valor', 'nro_factura']],
        left_on='Interno',
        right_on='nro_recibo',
        how='left'
    )

    df_merged = df_merged.merge(
        cobranza_por_facturas[['nro_factura']],
        on='nro_factura',
        how='left'
    )

    # print(df_merged.columns)
    
    # print(df_merged[df_merged['nro_factura'] == 'FA100-00142458'])
    facturas_no_encontradas = df_merged[df_merged['nro_factura'].isna()]
    df_merged = df_merged[df_merged['nro_factura'].notna()]

    return df_merged, facturas_no_encontradas
    


def test_facturas_no_encontradas():

    df_facturas_no_encontradas = pd.read_excel('./tests/test_data/test_facturas_no_encontradas.xlsx')
    df_detalle_recibos = pd.read_excel('./tests/test_data/test_detalle_recibos.xlsx')

    procesar_facturas_no_encontradas(df_facturas_no_encontradas, df_detalle_recibos)