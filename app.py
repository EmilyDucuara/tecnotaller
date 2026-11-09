
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime, timedelta
import secrets
import hashlib
import os
from flask_mail import Mail, Message
from db import obtener_conexion

app = Flask(__name__)

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = os.environ.get("TECNOTALLER_EMAIL")
app.config["MAIL_PASSWORD"] = os.environ.get("TECNOTALLER_EMAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("TECNOTALLER_EMAIL")

mail = Mail(app)


# Clave temporal para las sesiones durante el desarrollo.
# Más adelante la guardaremos de forma segura en una variable de entorno.

import os

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
)

def requiere_rol(*roles_permitidos):
    """Comprueba que el usuario haya iniciado sesión y tenga un rol autorizado."""
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    if session.get("rol") not in roles_permitidos:
        return "No tienes permiso para acceder a este módulo.", 403

    if session.get("id_taller") is None:
        return "No tienes un taller asignado.", 403

    return None


@app.route("/")
def inicio():
    return render_template("index.html")

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT id_usuario, id_taller, nombre, rol, estado
            FROM usuario
            WHERE correo = %s
            LIMIT 1
        """, ("enducuara@soy.sena.edu.co",))

        usuario = cursor.fetchone()

        if (
            usuario is None
            or usuario["rol"] != "superadmin"
            or usuario["estado"] != "activo"
        ):
            return "La cuenta de superadministrador no está disponible.", 403

        # Crear la sesión del superadministrador.
        session.clear()
        session["id_usuario"] = usuario["id_usuario"]
        session["id_taller"] = usuario["id_taller"]
        session["nombre"] = usuario["nombre"]
        session["rol"] = usuario["rol"]

        return redirect(url_for("panel"))

    except Exception:
        app.logger.exception("Error en el acceso automático.")
        return "No fue posible iniciar el acceso automático.", 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None and conexion.is_connected():
            conexion.close()


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    correo = request.form.get("correo", "").strip().lower()
    contrasena = request.form.get("contrasena", "")

    if not correo:
        return render_template(
            "login.html",
            error="Por favor, ingresa tu correo electrónico."
        )

    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id_usuario,
                id_taller,
                nombre,
                correo,
                contrasena_hash,
                rol,
                estado
            FROM usuario
            WHERE correo = %s
            """,
            (correo,)
        )

        usuario = cursor.fetchone()

        # Verificar que la cuenta exista y esté activa.
        if usuario is None or usuario["estado"] != "activo":
            return render_template(
                "login.html",
                error="Correo o contraseña incorrectos, o cuenta inactiva."
            )

        
        
      # Todos los usuarios deben ingresar su contraseña.
        if not contrasena or not check_password_hash(
            usuario["contrasena_hash"], contrasena
        ):
            return render_template(
                "login.html",
                error="Correo o contraseña incorrectos, o cuenta inactiva."
            )


        # Crear la sesión.
        session.clear()
        session["id_usuario"] = usuario["id_usuario"]
        session["id_taller"] = usuario["id_taller"]
        session["nombre"] = usuario["nombre"]
        session["rol"] = usuario["rol"]

        return redirect(url_for("panel"))

    except Exception:
        app.logger.exception("Error durante el inicio de sesión.")
        return render_template(
            "login.html",
            error="No fue posible iniciar sesión. Inténtalo nuevamente."
        ), 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None and conexion.is_connected():
            conexion.close()




@app.route("/panel")
def panel():
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    conexion = None
    cursor = None
    nombre_taller = None

    try:
        if session.get("id_taller") is not None:
            conexion = obtener_conexion()
            cursor = conexion.cursor(dictionary=True)

            cursor.execute(
                """
                SELECT nombre
                FROM taller
                WHERE id_taller = %s
                """,
                (session["id_taller"],)
            )

            taller = cursor.fetchone()

            if taller:
                nombre_taller = taller["nombre"]

        return render_template(
            "panel.html",
            nombre_taller=nombre_taller
        )

    except Exception:
        app.logger.exception("Error al cargar el panel.")
        return "No fue posible cargar el panel.", 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None and conexion.is_connected():
            conexion.close()






@app.route("/registro", methods=["GET", "POST"])
def registro():
    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        if request.method == "GET":
            cursor.execute("""
                SELECT id_taller, nombre
                FROM taller
                WHERE estado = 'activo'
                ORDER BY nombre ASC
            """)
            talleres = cursor.fetchall()

            return render_template(
                "registro.html",
                talleres=talleres
            )

        nombre = request.form.get("nombre", "").strip()
        correo = request.form.get("correo", "").strip().lower()
        id_taller = request.form.get("id_taller", "").strip()
        contrasena = request.form.get("contrasena", "")
        confirmar_contrasena = request.form.get(
            "confirmar_contrasena", ""
        )

        error = None

        if not nombre or not correo or not id_taller or not contrasena:
            error = "Completa todos los campos obligatorios."
        elif len(nombre) > 100:
            error = "El nombre no puede superar los 100 caracteres."
        elif len(correo) > 150:
            error = "El correo es demasiado largo."
        elif len(contrasena) < 8:
            error = "La contraseña debe tener al menos 8 caracteres."
        elif contrasena != confirmar_contrasena:
            error = "Las contraseñas no coinciden."

        if error:
            cursor.execute("""
                SELECT id_taller, nombre
                FROM taller
                WHERE estado = 'activo'
                ORDER BY nombre ASC
            """)
            talleres = cursor.fetchall()

            return render_template(
                "registro.html",
                error=error,
                talleres=talleres
            )

        # Validar que el taller exista y esté activo.
        try:
            id_taller = int(id_taller)
        except ValueError:
            id_taller = None

        cursor.execute("""
            SELECT id_taller
            FROM taller
            WHERE id_taller = %s
              AND estado = 'activo'
        """, (id_taller,))

        taller = cursor.fetchone()

        if not taller:
            cursor.execute("""
                SELECT id_taller, nombre
                FROM taller
                WHERE estado = 'activo'
                ORDER BY nombre ASC
            """)
            talleres = cursor.fetchall()

            return render_template(
                "registro.html",
                error="Selecciona un taller válido y activo.",
                talleres=talleres
            )

        # Comprobar que el correo no esté registrado.
        cursor.execute("""
            SELECT id_usuario
            FROM usuario
            WHERE LOWER(correo) = %s
            LIMIT 1
        """, (correo,))

        if cursor.fetchone():
            cursor.execute("""
                SELECT id_taller, nombre
                FROM taller
                WHERE estado = 'activo'
                ORDER BY nombre ASC
            """)
            talleres = cursor.fetchall()

            return render_template(
                "registro.html",
                error="Este correo ya tiene una cuenta registrada.",
                talleres=talleres
            )

        # Cifrar la contraseña antes de guardarla.
        contrasena_hash = generate_password_hash(contrasena)

        cursor.execute("""
            INSERT INTO usuario (
                id_taller,
                nombre,
                correo,
                contrasena_hash,
                rol,
                estado
            )
            VALUES (%s, %s, %s, %s, 'administrador', 'activo')
        """, (
            id_taller,
            nombre,
            correo,
            contrasena_hash
        ))

        conexion.commit()

        return render_template(
            "login.html",
            mensaje="Cuenta creada correctamente. Ya puedes iniciar sesión."
        )

    except Exception:
        if conexion is not None:
            conexion.rollback()

        app.logger.exception("Error al registrar una cuenta.")

        return render_template(
            "registro.html",
            error="No fue posible crear la cuenta. Revisa la terminal.",
            talleres=talleres if "talleres" in locals() else []
        ), 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None and conexion.is_connected():
            conexion.close()



@app.route("/clientes", methods=["GET", "POST"])
def clientes():
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    if session.get("rol") not in [
        "administrador", "asesor", "recepcionista", "superadmin"
    ]:
        return "No tienes permiso para acceder a este módulo.", 403

    id_taller = session.get("id_taller")

    # Por seguridad, el superadministrador todavía no gestiona
    # clientes directamente desde este módulo.
    if id_taller is None:
        return "Selecciona un taller para gestionar sus clientes.", 403

    conexion = None
    cursor = None
    mensaje = None
    error = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        if request.method == "POST":
            nombre = request.form.get("nombre", "").strip()
            tipo_documento = request.form.get("tipo_documento", "CC").strip()
            documento = request.form.get("documento", "").strip()
            telefono = request.form.get("telefono", "").strip() or None
            correo = request.form.get("correo", "").strip().lower() or None
            direccion = request.form.get("direccion", "").strip() or None
            

            if not nombre or not documento:
                error = "El nombre y el documento son obligatorios."
            else:
                # Evitar duplicar el documento dentro del mismo taller.
                cursor.execute(
                 """
                 SELECT id_cliente
                 FROM cliente
                 WHERE id_taller = %s
                 AND tipo_documento = %s
                 AND documento = %s
                 """,
                 (id_taller, tipo_documento, documento)
                )

                if cursor.fetchone():
                    error = "Ya existe un cliente con ese documento."
                else:
                    cursor.execute(
                    """
                INSERT INTO cliente
                      (id_taller, nombre, tipo_documento, documento,
                       telefono, correo, direccion)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                     id_taller,
                     nombre,
                     tipo_documento,
                     documento,
                     telefono,
                     correo,
                     direccion
    )
)
                    conexion.commit()
                    return redirect(url_for("clientes", guardado="1"))

        buscar = request.args.get("buscar", "").strip()

        if buscar:
            cursor.execute(
                """
                SELECT id_cliente, nombre, tipo_documento, documento, telefono, correo
                FROM cliente
                WHERE id_taller = %s
                  AND (nombre LIKE %s OR documento LIKE %s)
                ORDER BY nombre
                """,
                (id_taller, f"%{buscar}%", f"%{buscar}%")
            )
        else:
            cursor.execute(
                """
                SELECT id_cliente, nombre, tipo_documento, documento, telefono, correo
                FROM cliente
                WHERE id_taller = %s
                ORDER BY nombre
                """,
                (id_taller,)
            )

        lista_clientes = cursor.fetchall()

        if request.args.get("guardado") == "1":
            mensaje = "Cliente registrado correctamente."

        return render_template(
            "clientes.html",
            clientes=lista_clientes,
            buscar=buscar,
            mensaje=mensaje,
            error=error
        )

    except Exception:
        if conexion is not None:
            conexion.rollback()

        app.logger.exception("Error en el módulo de clientes.")
        return "No fue posible procesar la solicitud. Revisa la consola del servidor.", 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None and conexion.is_connected():
            conexion.close()

            
@app.route("/vehiculos", methods=["GET", "POST"])
def vehiculos():
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    if session.get("rol") not in [
        "administrador", "asesor", "recepcionista", "superadmin"
    ]:
        return "No tienes permiso para acceder a este módulo.", 403

    id_taller = session.get("id_taller")

    if id_taller is None:
        return "Selecciona un taller para gestionar sus vehículos.", 403

    conexion = None
    cursor = None
    mensaje = None
    error = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        if request.method == "POST":
            id_cliente = request.form.get("id_cliente", "").strip()
            placa = request.form.get("placa", "").strip().upper()
            marca = request.form.get("marca", "").strip()
            modelo = request.form.get("modelo", "").strip()
            anio_texto = request.form.get("anio", "").strip()
            color = request.form.get("color", "").strip() or None

            if not id_cliente or not placa or not marca or not modelo:
                error = "Completa el cliente, la placa, la marca y el modelo."
            else:
                try:
                    id_cliente = int(id_cliente)
                    anio = int(anio_texto) if anio_texto else None

                    if anio is not None and not 1886 <= anio <= 2155:
                        error = "Ingresa un año válido entre 1886 y 2155."

                except ValueError:
                    error = "El cliente o el año ingresado no son válidos."

                if error is None:
                    cursor.execute(
                        """
                        SELECT id_cliente
                        FROM cliente
                        WHERE id_cliente = %s AND id_taller = %s
                        """,
                        (id_cliente, id_taller)
                    )

                    if cursor.fetchone() is None:
                        error = "Selecciona un cliente válido de tu taller."

                if error is None:
                    cursor.execute(
                        """
                        SELECT id_vehiculo
                        FROM vehiculo
                        WHERE id_taller = %s AND placa = %s
                        """,
                        (id_taller, placa)
                    )

                    if cursor.fetchone():
                        error = "Ya existe un vehículo con esa placa en este taller."

                if error is None:
                    cursor.execute(
                        """
                        INSERT INTO vehiculo
                            (id_taller, id_cliente, placa, marca, modelo, anio, color)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            id_taller, id_cliente, placa,
                            marca, modelo, anio, color
                        )
                    )
                    conexion.commit()
                    return redirect(url_for("vehiculos", guardado="1"))

        cursor.execute(
            """
            SELECT id_cliente, nombre, tipo_documento, documento
            FROM cliente
            WHERE id_taller = %s
            ORDER BY nombre
            """,
            (id_taller,)
        )
        lista_clientes = cursor.fetchall()

        cursor.execute(
            """
            SELECT
                v.id_vehiculo,
                v.placa,
                v.marca,
                v.modelo,
                v.anio,
                v.color,
                c.nombre AS nombre_cliente,
                c.tipo_documento,
                c.documento
            FROM vehiculo v
            INNER JOIN cliente c
                ON c.id_cliente = v.id_cliente
                AND c.id_taller = v.id_taller
            WHERE v.id_taller = %s
            ORDER BY v.placa
            """,
            (id_taller,)
        )
        lista_vehiculos = cursor.fetchall()

        if request.args.get("guardado") == "1":
            mensaje = "Vehículo registrado correctamente."

        return render_template(
            "vehiculos.html",
            clientes=lista_clientes,
            vehiculos=lista_vehiculos,
            mensaje=mensaje,
            error=error
        )

    except Exception:
        if conexion is not None:
            conexion.rollback()

        app.logger.exception("Error en el módulo de vehículos.")
        return "No fue posible procesar la solicitud. Revisa la consola del servidor.", 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None and conexion.is_connected():
            conexion.close()


@app.route("/mecanicos", methods=["GET", "POST"])
def mecanicos():
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    if session.get("rol") not in [
        "administrador", "asesor", "recepcionista", "superadmin"
    ]:
        return "No tienes permiso para acceder a este módulo.", 403

    id_taller = session.get("id_taller")

    if id_taller is None:
        return "Selecciona un taller para gestionar sus mecánicos.", 403

    conexion = None
    cursor = None
    mensaje = None
    error = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        if request.method == "POST":
            nombre = request.form.get("nombre", "").strip()
            documento = request.form.get("documento", "").strip()
            telefono = request.form.get("telefono", "").strip() or None
            especialidad = request.form.get("especialidad", "").strip() or None
            estado = request.form.get("estado", "activo").strip()

            if not nombre or not documento:
                error = "El nombre y el documento son obligatorios."
            elif estado not in ["activo", "inactivo"]:
                error = "Selecciona un estado válido."

            if error is None:
                cursor.execute(
                    """
                    SELECT id_mecanico
                    FROM mecanico
                    WHERE id_taller = %s AND documento = %s
                    """,
                    (id_taller, documento)
                )

                if cursor.fetchone():
                    error = "Ya existe un mecánico con ese documento en este taller."

            if error is None:
                cursor.execute(
                    """
                    INSERT INTO mecanico
                        (id_taller, nombre, documento, telefono,
                         especialidad, estado)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        id_taller, nombre, documento, telefono,
                        especialidad, estado
                    )
                )
                conexion.commit()
                return redirect(url_for("mecanicos", guardado="1"))

        buscar = request.args.get("buscar", "").strip()

        if buscar:
            cursor.execute(
                """
                SELECT id_mecanico, nombre, documento, telefono,
                       especialidad, estado
                FROM mecanico
                WHERE id_taller = %s
                  AND (nombre LIKE %s
                       OR documento LIKE %s
                       OR especialidad LIKE %s)
                ORDER BY nombre
                """,
                (
                    id_taller,
                    f"%{buscar}%",
                    f"%{buscar}%",
                    f"%{buscar}%"
                )
            )
        else:
            cursor.execute(
                """
                SELECT id_mecanico, nombre, documento, telefono,
                       especialidad, estado
                FROM mecanico
                WHERE id_taller = %s
                ORDER BY nombre
                """,
                (id_taller,)
            )

        lista_mecanicos = cursor.fetchall()

        if request.args.get("guardado") == "1":
            mensaje = "Mecánico registrado correctamente."

        return render_template(
            "mecanicos.html",
            mecanicos=lista_mecanicos,
            buscar=buscar,
            mensaje=mensaje,
            error=error
        )

    except Exception:
        if conexion is not None:
            conexion.rollback()

        app.logger.exception("Error en el módulo de mecánicos.")
        return "No fue posible procesar la solicitud. Revisa la consola del servidor.", 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None and conexion.is_connected():
            conexion.close()

  
@app.route("/ordenes", methods=["GET", "POST"])
def ordenes():
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    if session.get("rol") not in [
        "administrador", "asesor", "recepcionista", "superadmin"
    ]:
        return "No tienes permiso para acceder a este módulo.", 403

    id_taller = session.get("id_taller")

    if id_taller is None:
        return "Selecciona un taller para gestionar sus órdenes.", 403

    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    mensaje = ""
    error = ""

    try:
        if request.method == "POST":
            id_vehiculo = request.form.get("id_vehiculo", "").strip()
            id_mecanico = request.form.get("id_mecanico", "").strip()
            estado = request.form.get("estado", "recibida")
            kilometraje = request.form.get("kilometraje", "").strip()
            observaciones = request.form.get("observaciones", "").strip()

            estados_validos = [
                "recibida", "diagnostico", "en_reparacion",
                "esperando_repuesto", "finalizada", "entregada",
                "cancelada"
            ]

            if not id_vehiculo:
                error = "Selecciona un vehículo."
            elif estado not in estados_validos:
                error = "Selecciona un estado válido."
            else:
                cursor.execute("""
                    SELECT id_vehiculo
                    FROM vehiculo
                    WHERE id_vehiculo = %s AND id_taller = %s
                """, (id_vehiculo, id_taller))

                if not cursor.fetchone():
                    error = "El vehículo no pertenece a este taller."

                if not error and id_mecanico:
                    cursor.execute("""
                        SELECT id_mecanico
                        FROM mecanico
                        WHERE id_mecanico = %s
                          AND id_taller = %s
                          AND estado = 'activo'
                    """, (id_mecanico, id_taller))

                    if not cursor.fetchone():
                        error = "El mecánico seleccionado no es válido."

                if not error and kilometraje:
                    if not kilometraje.isdigit():
                        error = "El kilometraje debe ser un número entero."
                    elif int(kilometraje) < 0:
                        error = "El kilometraje no puede ser negativo."

                if not error:
                    cursor.execute("""
                        SELECT codigo_orden
                        FROM orden_trabajo
                        WHERE id_taller = %s
                        ORDER BY id_orden DESC
                        LIMIT 1
                    """, (id_taller,))

                    ultima = cursor.fetchone()
                    consecutivo = 1

                    if ultima and ultima["codigo_orden"]:
                        try:
                            consecutivo = int(
                                ultima["codigo_orden"].split("-")[-1]
                            ) + 1
                        except ValueError:
                            consecutivo = 1

                    codigo_orden = f"OT-{id_taller}-{consecutivo:05d}"

                    cursor.execute("""
                        INSERT INTO orden_trabajo (
                            id_taller, codigo_orden, id_vehiculo,
                            id_mecanico, estado, kilometraje,
                            observaciones, creado_por
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        id_taller,
                        codigo_orden,
                        id_vehiculo,
                        int(id_mecanico) if id_mecanico else None,
                        estado,
                        int(kilometraje) if kilometraje else None,
                        observaciones or None,
                        session.get("id_usuario")
                    ))

                    conexion.commit()
                    return redirect(url_for("ordenes", guardado="1"))

        cursor.execute("""
            SELECT v.id_vehiculo, v.placa, v.marca, v.modelo,
                   c.nombre AS cliente
            FROM vehiculo v
            INNER JOIN cliente c
                ON c.id_cliente = v.id_cliente
               AND c.id_taller = v.id_taller
            WHERE v.id_taller = %s
            ORDER BY v.placa
        """, (id_taller,))
        vehiculos = cursor.fetchall()

        cursor.execute("""
            SELECT id_mecanico, nombre, especialidad
            FROM mecanico
            WHERE id_taller = %s AND estado = 'activo'
            ORDER BY nombre
        """, (id_taller,))
        mecanicos = cursor.fetchall()

        cursor.execute("""
            SELECT o.id_orden, o.codigo_orden, o.fecha_ingreso,
                   o.fecha_salida, o.estado, o.kilometraje,
                   o.observaciones, v.placa, v.marca, v.modelo,
                   c.nombre AS cliente, m.nombre AS mecanico
            FROM orden_trabajo o
            INNER JOIN vehiculo v
                ON v.id_vehiculo = o.id_vehiculo
               AND v.id_taller = o.id_taller
            INNER JOIN cliente c
                ON c.id_cliente = v.id_cliente
               AND c.id_taller = v.id_taller
            LEFT JOIN mecanico m
                ON m.id_mecanico = o.id_mecanico
               AND m.id_taller = o.id_taller
            WHERE o.id_taller = %s
            ORDER BY o.id_orden DESC
        """, (id_taller,))
        ordenes_lista = cursor.fetchall()

        if request.args.get("guardado") == "1":
            mensaje = "Orden de trabajo registrada correctamente."

        return render_template(
            "ordenes.html",
            vehiculos=vehiculos,
            mecanicos=mecanicos,
            ordenes=ordenes_lista,
            mensaje=mensaje,
            error=error
        )

    except Exception:
        conexion.rollback()
        app.logger.exception("Error en el módulo de órdenes de trabajo")
        return "Ocurrió un error al procesar la orden. Revisa la terminal.", 500

    finally:
        cursor.close()
        conexion.close()

        
@app.route("/inventario", methods=["GET", "POST"])
def inventario():
    permiso = requiere_rol("administrador", "asesor")
    if permiso:
        return permiso

    id_taller = session.get("id_taller")

    if id_taller is None:
        return "Selecciona un taller para gestionar el inventario.", 403

    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)
    mensaje = ""
    error = ""

    try:
        if request.method == "POST":
            accion = request.form.get("accion", "")

            if accion == "registrar":
                codigo = request.form.get("codigo", "").strip()
                nombre = request.form.get("nombre", "").strip()
                descripcion = request.form.get("descripcion", "").strip()
                precio = request.form.get("precio", "0").strip()
                stock = request.form.get("stock", "0").strip()
                stock_minimo = request.form.get("stock_minimo", "0").strip()

                try:
                    precio_num = float(precio)
                    stock_num = int(stock)
                    minimo_num = int(stock_minimo)

                    if not codigo or not nombre:
                        error = "El código y el nombre son obligatorios."
                    elif precio_num < 0 or stock_num < 0 or minimo_num < 0:
                        error = "El precio y las existencias no pueden ser negativos."
                    else:
                        cursor.execute("""
                            SELECT id_repuesto
                            FROM repuesto
                            WHERE id_taller = %s AND codigo = %s
                        """, (id_taller, codigo))

                        if cursor.fetchone():
                            error = "Ya existe un repuesto con ese código."
                        else:
                            cursor.execute("""
                                INSERT INTO repuesto (
                                    id_taller, codigo, nombre, descripcion,
                                    precio, stock, stock_minimo
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """, (
                                id_taller, codigo, nombre,
                                descripcion or None, precio_num,
                                stock_num, minimo_num
                            ))

                            id_repuesto = cursor.lastrowid

                            if stock_num > 0:
                                cursor.execute("""
                                    INSERT INTO movimiento_inventario (
                                        id_taller, id_repuesto, id_usuario,
                                        tipo, cantidad, motivo
                                    )
                                    VALUES (%s, %s, %s, 'entrada', %s, %s)
                                """, (
                                    id_taller, id_repuesto,
                                    session.get("id_usuario"),
                                    stock_num, "Existencias iniciales"
                                ))

                            conexion.commit()
                            return redirect(
                                url_for("inventario", guardado="1")
                            )

                except ValueError:
                    error = "Verifica que precio y cantidades sean números válidos."

            elif accion == "movimiento":
                id_repuesto = request.form.get("id_repuesto", "").strip()
                tipo = request.form.get("tipo", "")
                cantidad = request.form.get("cantidad", "").strip()
                motivo = request.form.get("motivo", "").strip()

                if tipo not in ["entrada", "salida", "ajuste"]:
                    error = "Selecciona un tipo de movimiento válido."
                else:
                    try:
                        cantidad_num = int(cantidad)

                        if cantidad_num <= 0:
                            error = "La cantidad debe ser mayor que cero."
                        else:
                            cursor.execute("""
                                SELECT id_repuesto, stock
                                FROM repuesto
                                WHERE id_repuesto = %s
                                  AND id_taller = %s
                                  AND estado = 'activo'
                                FOR UPDATE
                            """, (id_repuesto, id_taller))

                            repuesto = cursor.fetchone()

                            if not repuesto:
                                error = "Selecciona un repuesto activo válido."
                            elif tipo == "salida" and cantidad_num > repuesto["stock"]:
                                error = "No hay suficientes existencias para esa salida."
                            else:
                                if tipo == "entrada":
                                    nuevo_stock = repuesto["stock"] + cantidad_num
                                elif tipo == "salida":
                                    nuevo_stock = repuesto["stock"] - cantidad_num
                                else:
                                    nuevo_stock = cantidad_num

                                cursor.execute("""
                                    UPDATE repuesto
                                    SET stock = %s
                                    WHERE id_repuesto = %s AND id_taller = %s
                                """, (nuevo_stock, id_repuesto, id_taller))

                                cursor.execute("""
                                    INSERT INTO movimiento_inventario (
                                        id_taller, id_repuesto, id_usuario,
                                        tipo, cantidad, motivo
                                    )
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                """, (
                                    id_taller, id_repuesto,
                                    session.get("id_usuario"),
                                    tipo, cantidad_num,
                                    motivo or "Movimiento manual"
                                ))

                                conexion.commit()
                                return redirect(
                                    url_for("inventario", guardado="1")
                                )

                    except ValueError:
                        error = "La cantidad debe ser un número entero válido."
            else:
                error = "Acción no válida."

        cursor.execute("""
            SELECT id_repuesto, codigo, nombre, descripcion,
                   precio, stock, stock_minimo, estado
            FROM repuesto
            WHERE id_taller = %s
            ORDER BY nombre
        """, (id_taller,))
        repuestos = cursor.fetchall()

        cursor.execute("""
            SELECT mi.tipo, mi.cantidad, mi.fecha, mi.motivo,
                   r.codigo, r.nombre, u.nombre AS usuario
            FROM movimiento_inventario mi
            INNER JOIN repuesto r
                ON r.id_repuesto = mi.id_repuesto
               AND r.id_taller = mi.id_taller
            LEFT JOIN usuario u
                ON u.id_usuario = mi.id_usuario
            WHERE mi.id_taller = %s
            ORDER BY mi.id_movimiento DESC
            LIMIT 50
        """, (id_taller,))
        movimientos = cursor.fetchall()

        if request.args.get("guardado") == "1":
            mensaje = "Operación de inventario registrada correctamente."

        return render_template(
            "inventario.html",
            repuestos=repuestos,
            movimientos=movimientos,
            mensaje=mensaje,
            error=error
        )

    except Exception:
        conexion.rollback()
        app.logger.exception("Error en el módulo de inventario")
        return "Ocurrió un error en el inventario. Revisa la terminal.", 500

    finally:
        cursor.close()
        conexion.close()

        

@app.route("/citas", methods=["GET", "POST"])
def citas():
    permiso = requiere_rol(
        "administrador", "asesor", "recepcionista", "mecanico"
    )
    if permiso:
        return permiso


    id_taller = session.get("id_taller")

    if id_taller is None:
        return "No tienes un taller asignado para gestionar citas.", 403

    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    try:
        mensaje = None

        if request.method == "POST":
            id_cliente = request.form.get("id_cliente")
            id_vehiculo = request.form.get("id_vehiculo")
            id_mecanico = request.form.get("id_mecanico") or None
            fecha = request.form.get("fecha")
            hora = request.form.get("hora")
            motivo = request.form.get("motivo")
            observaciones = request.form.get("observaciones")

            if not all([id_cliente, id_vehiculo, fecha, hora]):
                mensaje = "Completa los campos obligatorios."
            else:
                cursor.execute("""
                    SELECT id_cliente
                    FROM cliente
                    WHERE id_cliente = %s AND id_taller = %s
                """, (id_cliente, id_taller))
                cliente = cursor.fetchone()

                cursor.execute("""
                    SELECT id_vehiculo
                    FROM vehiculo
                    WHERE id_vehiculo = %s
                      AND id_taller = %s
                      AND id_cliente = %s
                """, (id_vehiculo, id_taller, id_cliente))
                vehiculo = cursor.fetchone()

                if not cliente:
                    mensaje = "El cliente seleccionado no pertenece a este taller."
                elif not vehiculo:
                    mensaje = "El vehículo no pertenece al cliente seleccionado."
                else:
                    if id_mecanico:
                        cursor.execute("""
                            SELECT id_mecanico
                            FROM mecanico
                            WHERE id_mecanico = %s
                              AND id_taller = %s
                              AND estado = 'activo'
                        """, (id_mecanico, id_taller))
                        mecanico = cursor.fetchone()

                        if not mecanico:
                            mensaje = "El mecánico seleccionado no está disponible."
                    
                    if mensaje is None:
                        cursor.execute("""
                            SELECT id_cita
                            FROM cita
                            WHERE id_taller = %s
                              AND fecha = %s
                              AND hora = %s
                              AND estado IN (
                                  'programada',
                                  'confirmada',
                                  'en_atencion'
                              )
                        """, (id_taller, fecha, hora))
                        cita_existente = cursor.fetchone()

                        if cita_existente:
                            mensaje = "Ya existe una cita para ese taller en esa fecha y hora."
                        else:
                            cursor.execute("""
                                INSERT INTO cita (
                                    id_taller,
                                    id_cliente,
                                    id_vehiculo,
                                    id_mecanico,
                                    fecha,
                                    hora,
                                    motivo,
                                    observaciones
                                )
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            """, (
                                id_taller,
                                id_cliente,
                                id_vehiculo,
                                id_mecanico,
                                fecha,
                                hora,
                                motivo or None,
                                observaciones or None
                            ))

                            conexion.commit()
                            mensaje = "Cita registrada correctamente."

        cursor.execute("""
            SELECT id_cliente, nombre, documento
            FROM cliente
            WHERE id_taller = %s
            ORDER BY nombre
        """, (id_taller,))
        clientes = cursor.fetchall()

        cursor.execute("""
            SELECT id_vehiculo, id_cliente, placa, marca, modelo
            FROM vehiculo
            WHERE id_taller = %s
            ORDER BY placa
        """, (id_taller,))
        vehiculos = cursor.fetchall()

        cursor.execute("""
            SELECT id_mecanico, nombre, especialidad
            FROM mecanico
            WHERE id_taller = %s AND estado = 'activo'
            ORDER BY nombre
        """, (id_taller,))
        mecanicos = cursor.fetchall()

        cursor.execute("""
            SELECT
                c.id_cita,
                c.fecha,
                c.hora,
                c.motivo,
                c.estado,
                c.observaciones,
                cl.nombre AS nombre_cliente,
                cl.documento,
                v.placa,
                v.marca,
                v.modelo,
                m.nombre AS nombre_mecanico
            FROM cita c
            INNER JOIN cliente cl
                ON c.id_cliente = cl.id_cliente
               AND c.id_taller = cl.id_taller
            INNER JOIN vehiculo v
                ON c.id_vehiculo = v.id_vehiculo
               AND c.id_taller = v.id_taller
            LEFT JOIN mecanico m
                ON c.id_mecanico = m.id_mecanico
               AND c.id_taller = m.id_taller
            WHERE c.id_taller = %s
            ORDER BY c.fecha DESC, c.hora DESC
        """, (id_taller,))
        citas_registradas = cursor.fetchall()

        return render_template(
            "citas.html",
            clientes=clientes,
            vehiculos=vehiculos,
            mecanicos=mecanicos,
            citas=citas_registradas,
            mensaje=mensaje
        )

    finally:
        cursor.close()
        conexion.close()

        
@app.route("/pagos", methods=["GET", "POST"])
def pagos():
    permiso = requiere_rol("administrador", "asesor")
    if permiso:
        return permiso

    id_taller = session.get("id_taller")

    if id_taller is None:
        return "No tienes un taller asignado para gestionar pagos.", 403

    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    try:
        mensaje = None

        if request.method == "POST":
            id_orden = request.form.get("id_orden")
            monto = request.form.get("monto")
            metodo_pago = request.form.get("metodo_pago")
            referencia = request.form.get("referencia", "").strip() or None

            if not all([id_orden, monto, metodo_pago]):
                mensaje = "Completa todos los campos obligatorios."
            else:
                try:
                    monto = float(monto)
                except ValueError:
                    monto = 0

                if monto <= 0:
                    mensaje = "El monto debe ser mayor que cero."
                elif metodo_pago not in (
                    "efectivo", "transferencia", "tarjeta", "otro"
                ):
                    mensaje = "Selecciona un método de pago válido."
                else:
                    cursor.execute("""
                        SELECT id_orden
                        FROM orden_trabajo
                        WHERE id_orden = %s AND id_taller = %s
                    """, (id_orden, id_taller))

                    orden = cursor.fetchone()

                    if not orden:
                        mensaje = "La orden seleccionada no pertenece a este taller."
                    else:
                        cursor.execute("""
                            INSERT INTO pago (
                                id_taller,
                                id_orden,
                                monto,
                                metodo_pago,
                                referencia,
                                registrado_por
                            )
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            id_taller,
                            id_orden,
                            monto,
                            metodo_pago,
                            referencia,
                            session.get("id_usuario")
                        ))

                        conexion.commit()
                        mensaje = "Pago registrado correctamente."

        cursor.execute("""
            SELECT
                id_orden,
                codigo_orden,
                estado
            FROM orden_trabajo
            WHERE id_taller = %s
            ORDER BY id_orden DESC
        """, (id_taller,))
        ordenes = cursor.fetchall()

        cursor.execute("""
            SELECT
                p.id_pago,
                p.fecha,
                p.monto,
                p.metodo_pago,
                p.estado,
                p.referencia,
                ot.codigo_orden
            FROM pago p
            INNER JOIN orden_trabajo ot
                ON p.id_orden = ot.id_orden
               AND p.id_taller = ot.id_taller
            WHERE p.id_taller = %s
            ORDER BY p.fecha DESC, p.id_pago DESC
        """, (id_taller,))
        pagos_registrados = cursor.fetchall()

        return render_template(
            "pagos.html",
            ordenes=ordenes,
            pagos=pagos_registrados,
            mensaje=mensaje
        )

    finally:
        cursor.close()
        conexion.close()


@app.route("/informes")
def informes():
    permiso = requiere_rol("administrador")
    if permiso:
        return permiso

    id_taller = session.get("id_taller")

    if id_taller is None:
        return "No tienes un taller asignado para consultar informes.", 403

    conexion = obtener_conexion()
    cursor = conexion.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT estado, COUNT(*) AS total
            FROM orden_trabajo
            WHERE id_taller = %s
            GROUP BY estado
            ORDER BY estado
        """, (id_taller,))
        ordenes_por_estado = cursor.fetchall()

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM orden_trabajo
            WHERE id_taller = %s
        """, (id_taller,))
        total_ordenes = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM pago
            WHERE id_taller = %s
        """, (id_taller,))
        total_pagos = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT COALESCE(SUM(monto), 0) AS total
            FROM pago
            WHERE id_taller = %s
              AND estado = 'aprobado'
        """, (id_taller,))
        total_recaudado = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM repuesto
            WHERE id_taller = %s AND estado = 'activo'
        """, (id_taller,))
        total_repuestos = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT codigo, nombre, stock, stock_minimo
            FROM repuesto
            WHERE id_taller = %s
              AND estado = 'activo'
              AND stock <= stock_minimo
            ORDER BY stock ASC, nombre
        """, (id_taller,))
        repuestos_bajos = cursor.fetchall()

        return render_template(
            "informes.html",
            ordenes_por_estado=ordenes_por_estado,
            total_ordenes=total_ordenes,
            total_pagos=total_pagos,
            total_recaudado=total_recaudado,
            total_repuestos=total_repuestos,
            repuestos_bajos=repuestos_bajos
        )

    finally:
        cursor.close()
        conexion.close()

     
@app.route("/usuarios")
def usuarios():
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "administrador":
        return "No tienes permiso para acceder a este módulo.", 403

    id_taller = session.get("id_taller")

    if id_taller is None:
        return "No tienes un taller asignado.", 403

    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id_usuario,
                nombre,
                correo,
                rol,
                estado,
                fecha_creacion
            FROM usuario
            WHERE id_taller = %s
            ORDER BY nombre
        """, (id_taller,))

        usuarios_lista = cursor.fetchall()

        cursor.execute("""
            SELECT
                id_invitacion,
                correo_destino,
                rol,
                fecha_creacion,
                fecha_expiracion,
                estado
            FROM invitacion
            WHERE id_taller = %s
            ORDER BY fecha_creacion DESC
        """, (id_taller,))

        invitaciones_lista = cursor.fetchall()

        return render_template(
            "usuarios.html",
            usuarios=usuarios_lista,
            invitaciones=invitaciones_lista
        )

    except Exception:
        app.logger.exception("Error en el módulo de usuarios.")
        return "No fue posible cargar los usuarios. Revisa la terminal.", 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None and conexion.is_connected():
            conexion.close()


@app.route("/crear-invitacion", methods=["POST"])
def crear_invitacion():
    if "id_usuario" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "administrador":
        return "No tienes permiso para crear invitaciones.", 403

    id_taller = session.get("id_taller")

    if id_taller is None:
        return "No tienes un taller asignado.", 403

    correo = request.form.get("correo_destino", "").strip().lower()
    rol = request.form.get("rol", "").strip()

    roles_permitidos = {
        "administrador",
        "asesor",
        "recepcionista",
        "mecanico"
    }

    if not correo or "@" not in correo or rol not in roles_permitidos:
        return redirect(url_for("usuarios"))

    conexion = None
    cursor = None

    try:
        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT id_usuario
            FROM usuario
            WHERE LOWER(correo) = %s
        """, (correo,))

        if cursor.fetchone():
            return "Ese correo ya tiene una cuenta registrada.", 400

        cursor.execute("""
            SELECT id_invitacion
            FROM invitacion
            WHERE id_taller = %s
              AND LOWER(correo_destino) = %s
              AND estado = 'pendiente'
              AND fecha_expiracion > NOW()
        """, (id_taller, correo))

        if cursor.fetchone():
            return "Ya existe una invitación pendiente para ese correo.", 400

        token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

        fecha_expiracion = datetime.now() + timedelta(days=7)

        cursor.execute("""
            INSERT INTO invitacion (
                id_taller,
                correo_destino,
                rol,
                token_hash,
                id_usuario_invitador,
                fecha_expiracion,
                estado
            )
            VALUES (%s, %s, %s, %s, %s, %s, 'pendiente')
        """, (
            id_taller,
            correo,
            rol,
            token_hash,
            session["id_usuario"],
            fecha_expiracion
        ))

        
        # Crear el enlace único para aceptar la invitación.
        enlace = url_for(
            "aceptar_invitacion",
            token=token,
            _external=True
        )

        # Preparar el correo de invitación.
        mensaje_correo = Message(
            subject="Invitación para unirte a TecnoTaller",
            recipients=[correo],
            body=f"""
Hola:

Has recibido una invitación para unirte a TecnoTaller.

Para crear tu cuenta, abre el siguiente enlace:

{enlace}

Este enlace es personal y tiene una vigencia de 7 días.

Si no esperabas esta invitación, puedes ignorar este mensaje.

Equipo TecnoTaller
"""
        )

        # Enviar el correo antes de confirmar el registro.
        mail.send(mensaje_correo)
        conexion.commit()

        app.logger.info(
            "Invitación creada y enviada al correo %s para el taller %s",
            correo,
            id_taller
        )

        return (
            "Invitación enviada correctamente a "
            + correo
            + "."
        )


    except Exception:
        if conexion is not None and conexion.is_connected():
            conexion.rollback()

        app.logger.exception("Error al crear la invitación.")
        return "No fue posible crear la invitación. Revisa la terminal.", 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexion is not None and conexion.is_connected():
            conexion.close()


@app.route("/cerrar-sesion")
def cerrar_sesion():
    session.clear()
    return redirect(url_for("login"))


@app.route("/aceptar-invitacion/<token>", methods=["GET", "POST"])
def aceptar_invitacion(token):
    conexion = None
    cursor = None

    try:
        # Convertir el token recibido en su hash para buscarlo en la BD.
        token_hash = hashlib.sha256(
            token.encode("utf-8")
        ).hexdigest()

        conexion = obtener_conexion()
        cursor = conexion.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                i.id_invitacion,
                i.id_taller,
                i.correo_destino,
                i.rol,
                i.fecha_expiracion,
                i.estado,
                t.nombre AS nombre_taller
            FROM invitacion i
            INNER JOIN taller t
                ON t.id_taller = i.id_taller
            WHERE i.token_hash = %s
            LIMIT 1
        """, (token_hash,))

        invitacion = cursor.fetchone()

        if not invitacion:
            return "La invitación no existe o el enlace no es válido.", 404

        if invitacion["estado"] != "pendiente":
            return "Esta invitación ya fue utilizada o no está disponible.", 400

        if invitacion["fecha_expiracion"] <= datetime.now():
            cursor.execute("""
                UPDATE invitacion
                SET estado = 'expirada'
                WHERE id_invitacion = %s
            """, (invitacion["id_invitacion"],))
            conexion.commit()

            return "La invitación ha expirado. Solicita una nueva.", 400

        if request.method == "GET":
            return render_template(
                "aceptar_invitacion.html",
                token=token,
                correo=invitacion["correo_destino"],
                rol=invitacion["rol"],
                nombre_taller=invitacion["nombre_taller"],
                error=None
            )

        nombre = request.form.get("nombre", "").strip()
        contrasena = request.form.get("contrasena", "")
        confirmar_contrasena = request.form.get(
            "confirmar_contrasena", ""
        )

        if not nombre or not contrasena or not confirmar_contrasena:
            return render_template(
                "aceptar_invitacion.html",
                token=token,
                correo=invitacion["correo_destino"],
                rol=invitacion["rol"],
                nombre_taller=invitacion["nombre_taller"],
                error="Completa todos los campos."
            )

        if len(nombre) > 100:
            return render_template(
                "aceptar_invitacion.html",
                token=token,
                correo=invitacion["correo_destino"],
                rol=invitacion["rol"],
                nombre_taller=invitacion["nombre_taller"],
                error="El nombre no puede superar los 100 caracteres."
            )

        if len(contrasena) < 8:
            return render_template(
                "aceptar_invitacion.html",
                token=token,
                correo=invitacion["correo_destino"],
                rol=invitacion["rol"],
                nombre_taller=invitacion["nombre_taller"],
                error="La contraseña debe tener al menos 8 caracteres."
            )

        if contrasena != confirmar_contrasena:
            return render_template(
                "aceptar_invitacion.html",
                token=token,
                correo=invitacion["correo_destino"],
                rol=invitacion["rol"],
                nombre_taller=invitacion["nombre_taller"],
                error="Las contraseñas no coinciden."
            )

        contrasena_hash = generate_password_hash(contrasena)

        # Confirmar que el correo no haya sido registrado entretanto.
        cursor.execute("""
            SELECT id_usuario
            FROM usuario
            WHERE correo = %s
            LIMIT 1
        """, (invitacion["correo_destino"],))

        if cursor.fetchone():
            return render_template(
                "aceptar_invitacion.html",
                token=token,
                correo=invitacion["correo_destino"],
                rol=invitacion["rol"],
                nombre_taller=invitacion["nombre_taller"],
                error="Este correo ya tiene una cuenta. Contacta al administrador."
            )

        cursor.execute("""
            INSERT INTO usuario (
                id_taller,
                nombre,
                correo,
                contrasena_hash,
                rol,
                estado
            )
            VALUES (%s, %s, %s, %s, %s, 'activo')
        """, (
            invitacion["id_taller"],
            nombre,
            invitacion["correo_destino"],
            contrasena_hash,
            invitacion["rol"]
        ))

        cursor.execute("""
            UPDATE invitacion
            SET estado = 'aceptada',
                fecha_aceptacion = NOW()
            WHERE id_invitacion = %s
              AND estado = 'pendiente'
        """, (invitacion["id_invitacion"],))

        if cursor.rowcount != 1:
            conexion.rollback()
            return "La invitación ya fue utilizada. Solicita una nueva.", 400

        conexion.commit()

        return redirect(url_for("login"))

    except Exception:
        if conexion:
            conexion.rollback()

        app.logger.exception(
            "Error al aceptar una invitación de TecnoTaller"
        )
        return "Ocurrió un error al procesar la invitación.", 500

    finally:
        if cursor:
            cursor.close()

        if conexion and conexion.is_connected():
            conexion.close()


if __name__ == "__main__":
    app.run(debug=False)
