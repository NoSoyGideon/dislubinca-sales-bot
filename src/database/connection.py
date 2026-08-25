# src/database/connection.py
import sqlite3
import os

class DBConnection:
    def __init__(self):
        self.db_path = os.getenv(
            "DB_PATH",
            os.path.join(os.path.dirname(__file__), "usuarios.db")
        )
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)

    def obtener_conexion(self):
        conexion = sqlite3.connect(self.db_path)
        conexion.execute("PRAGMA foreign_keys = ON;")
        print("🔗 [DBConnection] Conexión a la base de datos establecida con éxito.")
        return conexion