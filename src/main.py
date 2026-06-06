import sys
import os

# Asegurar que Python encuentre la carpeta 'src'
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

# Importamos las piezas reales que acabas de programar
from database.connection import DBConnection
from database.logs_repo import LogsRepository

if __name__ == "__main__":
    print("🚀 [EasyHammer Studio] Probando el subsistema de Logs...")
    
    # 1. Inicializamos el conector y el repositorio del Logger
    conector = DBConnection()
    logger = LogsRepository(conector)
    
    # 2. Simulamos el registro de un evento común y un error flagrante
    logger.registrar_log("INFO", "El Orquestador principal se ha encendido correctamente en Linux.")
    logger.registrar_log("ERROR", "La simulación detectó que el archivo Excel no se encontró (Prueba).")
    
    print("✅ Logs enviados a la base de datos.")
    print("\n🔍 Leyendo los últimos logs guardados en la DB:")
    
    # 3. Traemos los logs guardados para ver si se escribieron bien
    historial = logger.obtener_ultimos_logs(limite=5)
    for log in historial:
        # log[0] = timestamp, log[1] = nivel, log[2] = mensaje
        print(f"[{log[0]}] {log[1]}: {log[2]}")