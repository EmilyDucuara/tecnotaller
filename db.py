
import os
import mysql.connector

def obtener_conexion():
    return mysql.connector.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        port=int(os.environ.get("DB_PORT", "3306")),
        user=os.environ.get("DB_USER", "root"),
        password=os.environ.get("DB_PASSWORD", ""),
        database=os.environ.get("DB_NAME", "tecnotaller_v2"),
        ssl_ca=os.environ.get("DB_SSL_CA") or None,
        ssl_verify_cert=bool(os.environ.get("DB_SSL_CA")),
        connection_timeout=10
    )
