
from getpass import getpass
from werkzeug.security import generate_password_hash
from db import obtener_conexion


def crear_superadmin():
    conexion = None
    cursor = None

    try:
        correo = input("Correo del superadministrador: ").strip().lower()
        nombre = input("Nombre del superadministrador: ").strip()
        contrasena = getpass("Crea una contraseña: ")
        confirmar = getpass("Confirma la contraseña: ")

        if not correo or not nombre or not contrasena:
            print("Error: todos los campos son obligatorios.")
            return

        if contrasena != confirmar:
            print("Error: las contraseñas no coinciden.")
            return

        if len(contrasena) < 12:
            print("La contraseña debe tener al menos 12 caracteres.")
            return

        conexion = obtener_conexion()
        cursor = conexion.cursor()

        cursor.execute(
            "SELECT id_usuario FROM usuario WHERE correo = %s",
            (correo,)
        )

        if cursor.fetchone():
            print("Ya existe un usuario con ese correo.")
            return

        cursor.execute(
            """
            INSERT INTO usuario
                (id_taller, nombre, correo, contrasena_hash, rol, estado)
            VALUES
                (NULL, %s, %s, %s, 'superadmin', 'activo')
            """,
            (nombre, correo, generate_password_hash(contrasena))
        )

        conexion.commit()
        print("¡Superadministrador creado correctamente!")

    except Exception as error:
        if conexion is not None:
            conexion.rollback()
        print("No se pudo crear la cuenta.")
        print("Detalle:", error)

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None and conexion.is_connected():
            conexion.close()


if __name__ == "__main__":
    crear_superadmin()
