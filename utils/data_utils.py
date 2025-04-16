import pandas as pd

def extraer_numero_de_recibo(df: pd.DataFrame, nombre_columna_recibo: str) -> pd.DataFrame:
    df['nro_recibo'] = df[nombre_columna_recibo].astype(str).str.extract(r'REC\s*-?\s*(\d+)')
    df = df.dropna(subset=['nro_recibo'])
    return df



def extraer_numero_de_factura(df: pd.DataFrame, columna) -> pd.DataFrame:
    df['nro_factura'] = df[columna].str.slice(start=2, stop=22)
    return df
