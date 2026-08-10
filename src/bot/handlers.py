from telegram import ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import ContextTypes
from database.connection import DBConnection
from database.logs_repo import LogsRepository
from database.usuarios_repo import UsuariosRepository
from bot.keyboards import BotKeyboards
from bot.auth_flow import iniciar_registro_flow, ESTADO_REGISTRO_RUTA
import copy # <-- Necesitamos este módulo nativo de Python para clonar

# Inicializadores globales de datos para los manejadores
conector = DBConnection()
logger = LogsRepository(conector)
usuariosRepository = UsuariosRepository(conector)

async def verificar_usuario_autorizado(telegram_id):
    try:
        return usuariosRepository.verificar_usuarios(telegram_id)
    except Exception as e:
        logger.registrar_log("ERROR", f"Error verificando seguridad de usuario: {e}")
        return None

# src/bot/handlers.py

