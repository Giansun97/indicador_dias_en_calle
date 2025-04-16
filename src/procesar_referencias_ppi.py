import pandas as pd
from typing import Tuple

def procesar_referencias_ppi(reporte: pd.DataFrame, df_mayor_ppi: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Procesa las referencias PPI y calcula días para cobrar.
    
    Returns:
        Tuple[pd.DataFrame, pd.DataFrame]: Reporte procesado y asientos no encontrados
    """

    print("Procesando Referencias PPI...")
    # Merge con mayor PPI
    reporte = reporte.merge(
        df_mayor_ppi[['Asiento', 'Nombre cuenta', 'Referencia']],
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