
from getpass import getpass
from werkzeug.security import generate_password_hash
from db import obtener_conexion


def crear_administrador():
    conexion = None
    cursor = None

    try:
        correo = input("Correo del administrador: ").strip().lower()
        nombre = input("Nombre del administrador: ").strip()
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

        # Verificar que exista el taller de prueba.
        cursor.execute(
            """
            SELECT id_taller
            FROM taller
            WHERE id_taller = %s
              AND estado = 'activo'
            """,
            (1,)
        )

        if cursor.fetchone() is None:
            print("Error: no existe el taller activo con ID 1.")
            return

        # Evitar correos duplicados.
        cursor.execute(
            "SELECT id_usuario FROM usuario WHERE correo = %s",
            (correo,)
        )

        if cursor.fetchone():
            print("Ya existe un usuario con ese correo.")
            return

        # Crear administrador vinculado al taller 1.
        cursor.execute(
            """
            INSERT INTO usuario
                (id_taller, nombre, correo, contrasena_hash, rol, estado)
            VALUES
                (%s, %s, %s, %s, 'administrador', 'activo')
            """,
            (
                1,
                nombre,
                correo,
                generate_password_hash(contrasena)
            )
        )

        conexion.commit()
        print("¡Administrador del taller creado correctamente!")

    except Exception as error:
        if conexion is not None:
            conexion.rollback()

        print("No se pudo crear el administrador.")
        print("Detalle:", error)

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None and conexion.is_connected():
            conexion.close()


if __name__ == "__main__":
    crear_administrador()
