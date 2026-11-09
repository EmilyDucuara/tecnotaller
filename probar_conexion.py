
from db import obtener_conexion

try:
    conexion = obtener_conexion()

    if conexion.is_connected():
        print("¡Conexión exitosa con TecnoTaller!")
        print("Base de datos: tecnotaller_v2")

    conexion.close()

except Exception as error:
    print("No se pudo conectar a MySQL.")
    print("Detalle:", error)
