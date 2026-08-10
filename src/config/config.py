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
        self.dropbox_key = os.getenv("DROPBOX_API_KEY")
        self.dropbox_secret = os.getenv("DROPBOX_API_SECRET")
        self.dropbox_refresh_token = os.getenv("DROPBOX_REFRESH_TOKEN")
        
        
        if not self.gemini_key or not self.telegram_token or not self.dropbox_key or not self.dropbox_secret or not self.dropbox_refresh_token:
            self.logger.registrar_log("ERROR", "Faltan variables críticas en el archivo .env")
        else:
            self.logger.registrar_log("INFO", "Configuración de Gemini y Telegram cargada correctamente.")

    def obtener_api_key(self):
        return self.gemini_key

    def obtener_telegram_token(self):  # <--- NUEVO MÉTODO
        return self.telegram_token

    def obtener_dropbox_key(self):
        return self.dropbox_key

    def obtener_dropbox_secret(self):
        return self.dropbox_secret

    def obtener_dropbox_refresh_token(self):
        return self.dropbox_refresh_token