import pandas as pd

def procesar_asientos_no_encontrados(asientos_no_encontrados, detalle_de_recibos):
    # Realizar el merge entre ambas tablas usando 'nro_factura' y 'Comprobante' como claves
    df_merged = asientos_no_encontrados.merge(
        detalle_de_recibos[['nro_factura', 'Fecha del Valor', 'Pago']],
        on="nro_factura",
        how="left"
    )


    # df_merged.to_excel('test.xlsx')
    # Cambiar el nombre de la columna Pago_y a Haber
    # df_merged.to_excel("test.xlsx")
    
    
    # Hacer merge con el dataframe original para agregar las columnas Fecha y Pago
    resultado_final = asientos_no_encontrados[['nro_factura']].merge(
        df_merged,
        on="nro_factura",
        how="left"
    )

    resultado_final = resultado_final.rename(columns={"Pago_y": "Haber"})
    resultado_final = resultado_final.rename(columns={"Pago_x": "Pago"})

    # Filtrar los registros que NO tienen un valor en 'Haber' (no se encontraron)
    df_asientos_no_encontrados = resultado_final[resultado_final["Haber"].isna()]

    # Filtrar los registros que sí tienen un valor en 'Haber' (se encontraron en detalle_de_recibos)
    resultado_final = resultado_final.dropna(subset=["Haber"])

    # Opcional: Resetear los índices
    resultado_final = resultado_final.reset_index(drop=True)

    df_asientos_no_encontrados = df_asientos_no_encontrados.reset_index(drop=True)

    return resultado_final, df_asientos_no_encontrados