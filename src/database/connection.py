# src/database/connection.py
import sqlite3
import os

class DBConnection:
    def __init__(self):
        self.db_path = os.path.join(os.path.dirname(__file__), 'usuarios.db')

    def obtener_conexion(self):
        conexion = sqlite3.connect(self.db_path)
        conexion.execute("PRAGMA foreign_keys = ON;")
        print("🔗 [DBConnection] Conexión a la base de datos establecida con éxito.")
        return conexion