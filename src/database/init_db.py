import sqlite3
import os

def inicializar_base_de_datos():
    # Ruta absoluta de la base de datos dentro de src/database/
    db_path = os.path.join(os.path.dirname(__file__), 'usuarios.db')
    conexion = sqlite3.connect(db_path)
    cursor = conexion.cursor()

    # Enforzar el uso de llaves foráneas en SQLite
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Crear tabla de usuarios
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            telegram_id INTEGER PRIMARY KEY,
            nombre_telegram TEXT NOT NULL,
            ruta INTEGER,
            rol TEXT DEFAULT 'VENDEDOR',
            estado TEXT DEFAULT 'PENDIENTE'
        )
    ''')

    # 2. Crear tabla de registros diarios (con llave foránea vinculada al usuario)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registros_diarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER,
            ruta INTEGER,
            fecha TEXT,
            tipo_reporte TEXT,
            datos_json TEXT,
            FOREIGN KEY (telegram_id) REFERENCES usuarios(telegram_id) ON DELETE CASCADE
        )
    ''')

    # 3. Crear tabla de logs para auditoría rápida en consola
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs_sistema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            nivel TEXT,
            mensaje TEXT
        )
    ''')

    conexion.commit()
    conexion.close()
    print("🚀 [EasyHammer Studio] Base de datos estructurada e inicializada con éxito.")

if __name__ == "__main__":
    inicializar_base_de_datos()