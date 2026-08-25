import sqlite3
import os

def poblar_vendedores_produccion():
    # Respeta el mismo destino usado por el bot, incluido el Persistent Disk de Render.
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    db_path = os.getenv("DB_PATH", os.path.join(directorio_actual, "usuarios.db"))
        
    # Si aún no existe, lanzamos una alerta clara en lugar de crear un archivo vacío
    if not os.path.exists(db_path):
        print(f"❌ ERROR: No se encontró el archivo real 'usuarios.db' en ninguna ruta esperada.")
        print(f"Asegúrate de ejecutar el script desde la raíz de tu proyecto 'bot-inca'.")
        return
        
    print(f"🗄️ Conectando a la Base de Datos REAL en: {db_path}")
    
    conexion = sqlite3.connect(db_path)
    cursor = conexion.cursor()
    
    # Usaremos IDs únicos basados en la ruta para que no se dupliquen ni choquen bajo ninguna circunstancia
    vendedores = [
        (None, "Rumaldo Medina", 15, "VENDEDOR", "PENDIENTE",1),
        (None, "Alfredo Struch", 17, "VENDEDOR", "PENDIENTE",1),
        (None, "Dayanara Marriaga", 21, "VENDEDOR", "PENDIENTE",1),
        (None, "Laura Marín", 26, "VENDEDOR", "PENDIENTE",0),
        (None, "Rebeca Romero", 30, "VENDEDOR", "PENDIENTE",1),
        (None, "Mariedgar Martínez", 32, "VENDEDOR", "PENDIENTE",1),
        (None, "Carla Cardozo", 39, "VENDEDOR", "PENDIENTE",1),
        (6236041892, "Orlando Marcano", 13, "SUPERVISOR", "AUTORIZADO",1),
    ]
    
    # Limpiamos las pruebas viejas 'PENDIENTES' o duplicadas en la tabla para dejar la casa limpia
    try:
        cursor.execute("DELETE FROM usuarios WHERE rol = 'VENDEDOR';")
        
        query = """
            INSERT INTO usuarios (telegram_id, nombre_telegram, ruta, rol, estado,bajo_responsabilidad_supervisor)
            VALUES (?, ?, ?, ?, ?, ?);
        """
        
        cursor.executemany(query, vendedores)
        conexion.commit()
        print("🚀 [ÉXITO] ¡Vendedores guardados en la base de datos correcta!")
        
        # Verificación en caliente de la base de datos que acabamos de tocar
        cursor.execute("SELECT ruta, nombre_telegram, estado FROM usuarios WHERE rol = 'VENDEDOR' ORDER BY ruta;")
        print("\nFilas reales grabadas en el archivo:")
        for row in cursor.fetchall():
            print(f"  📍 Ruta {row[0]} ➔ {row[1]} [{row[2]}]")
            
    except sqlite3.Error as e:
        print(f"❌ Error de SQLite: {e}")
    finally:
        conexion.close()

if __name__ == "__main__":
    poblar_vendedores_produccion()