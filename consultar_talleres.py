
from db import obtener_conexion

conexion = None
cursor = None

try:
    conexion = obtener_conexion()
    cursor = conexion.cursor()

    cursor.execute("SELECT COUNT(*) FROM taller")
    resultado = cursor.fetchone()

    print("Conexión correcta.")
    print("Cantidad de talleres registrados:", resultado[0])

except Exception as error:
    print("Ocurrió un error:", error)

finally:
    if cursor is not None:
        cursor.close()

    if conexion is not None and conexion.is_connected():
        conexion.close()
