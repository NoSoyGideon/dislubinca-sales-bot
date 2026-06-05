import sqlite3
import os

def inicializar_base_de_datos():
    # Creamos la base de datos en la carpeta database
    db_path = os.path.join(os.path.dirname(__file__), 'usuarios.db')
    conexion = sqlite3.connect(db_path)
    cursor = conexion.cursor()

    # Creamos la tabla de usuarios/vendedores
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            telegram_id INTEGER PRIMARY KEY,
            nombre_telegram TEXT,
            ruta INTEGER,
            rol TEXT DEFAULT 'VENDEDOR',
            estado TEXT DEFAULT 'PENDIENTE'
        )
    ''')

    conexion.commit()
    conexion.close()
    print("¡Base de datos y tabla de usuarios creadas con éxito!")

if __name__ == "__main__":
    inicializar_base_de_datos()