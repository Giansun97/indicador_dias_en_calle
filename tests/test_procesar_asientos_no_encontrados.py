import pandas as pd
from src.procesar_asientos_no_encotrados import procesar_asientos_no_encontrados

def test_procesar_asientos_no_encotrados():
    df_asientos_no_encontrados = pd.read_excel('./tests/test_data/test_asientos_no_encontrados.xlsx')
    df_recibos = pd.read_excel('./tests/test_data/test_detalle_recibos.xlsx')

    df_resultado, asientos_no_encontrados = procesar_asientos_no_encontrados(df_asientos_no_encontrados, df_recibos)
    df_resultado.to_excel('./tests/test_data/test_resultado_asientos_no_encontrados.xlsx', index=False)
