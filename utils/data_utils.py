import pandas as pd

def extraer_numero_de_recibo(df: pd.DataFrame, nombre_columna_recibo: str) -> pd.DataFrame:
    """
    Extrae el número de recibo de la columna Recibo y lo agrega a una nueva columna llamada nro_recibo.
    """
    df['nro_recibo'] = df[nombre_columna_recibo].str.extract(r'REC\s*-?\s*(\d+)')
    return df


def extraer_numero_de_factura(df: pd.DataFrame) -> pd.DataFrame:
    df['nro_factura'] = df['Factura'].str.slice(start=2, stop=22)
    return df
