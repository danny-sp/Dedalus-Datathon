import os
import sqlite3

import pandas as pd

DB_NAME = "hospital.db"
DATA_DIR = "data"


def main():
    print(f"Iniciando la carga de datos en {DB_NAME}...")
    conn = sqlite3.connect(DB_NAME)

    archivos_csv = [
        "cohorte_alergias.csv",
        "cohorte_condiciones.csv",
        "cohorte_encuentros.csv",
        "cohorte_medicationes.csv",
        "cohorte_pacientes.csv",
        "cohorte_procedimientos.csv",
    ]

    for archivo in archivos_csv:
        ruta_csv = os.path.join(DATA_DIR, archivo)
        if os.path.exists(ruta_csv):
            print(f"Procesando {archivo}...")
            df = pd.read_csv(ruta_csv)

            nombre_tabla = archivo.replace("cohorte_", "").replace(".csv", "")

            df.to_sql(nombre_tabla, conn, if_exists="replace", index=False)
            print(f"  Tabla '{nombre_tabla}' creada con {len(df)} registros.")
        else:
            print(f"  Archivo no encontrado: {ruta_csv}")

    conn.close()
    print(f"\nBase de datos '{DB_NAME}' creada con éxito.")


if __name__ == "__main__":
    main()
