
from getpass import getpass
from werkzeug.security import generate_password_hash
from db import obtener_conexion


def cambiar_contrasena():
    conexion = None
    cursor = None

    try:
        correo = input("Correo de la cuenta: ").strip().lower()
        nueva_contrasena = getpass("Nueva contraseña: ")
        confirmar = getpass("Confirma la nueva contraseña: ")

        if not correo or not nueva_contrasena:
            print("Error: todos los campos son obligatorios.")
            return

        if nueva_contrasena != confirmar:
            print("Error: las contraseñas no coinciden.")
            return

        if len(nueva_contrasena) < 8:
            print("Error: usa al menos 8 caracteres.")
            return

        conexion = obtener_conexion()
        cursor = conexion.cursor()

        cursor.execute(
            """
            UPDATE usuario
            SET contrasena_hash = %s
            WHERE correo = %s
              AND estado = 'activo'
            """,
            (
                generate_password_hash(nueva_contrasena),
                correo
            )
        )

        if cursor.rowcount == 0:
            conexion.rollback()
            print("No se encontró una cuenta activa con ese correo.")
            return

        conexion.commit()
        print("¡Contraseña actualizada correctamente!")

    except Exception as error:
        if conexion is not None:
            conexion.rollback()

        print("No se pudo cambiar la contraseña.")
        print("Detalle:", error)

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None and conexion.is_connected():
            conexion.close()


if __name__ == "__main__":
    cambiar_contrasena()
