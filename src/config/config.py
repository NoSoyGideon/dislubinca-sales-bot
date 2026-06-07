import os
# Corrección en el import: traemos 'load_dotenv'
from dotenv import load_dotenv
from database.connection import DBConnection
from database.logs_repo import LogsRepository

# Cargar las variables del archivo .env
load_dotenv()
class Config:
    def __init__(self):
        conector = DBConnection()
        self.logger = LogsRepository(conector)
        
        self.gemini_key = os.getenv("GEMINI_API_KEY")
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")  # <--- NUEVA LÍNEA
        
        if not self.gemini_key or not self.telegram_token:
            self.logger.registrar_log("ERROR", "Faltan variables críticas en el archivo .env")
        else:
            self.logger.registrar_log("INFO", "Configuración de Gemini y Telegram cargada correctamente.")

    def obtener_api_key(self):
        return self.gemini_key

    def obtener_telegram_token(self):  # <--- NUEVO MÉTODO
        return self.telegram_token