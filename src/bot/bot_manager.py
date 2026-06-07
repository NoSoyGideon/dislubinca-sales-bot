import sys
import os
from telegram import ReplyKeyboardMarkup, KeyboardButton, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from config.config import Config
from database.connection import DBConnection
from database.logs_repo import LogsRepository

class DisulubincaBot:
    def __init__(self):
        self.config = Config()
        self.conector = DBConnection()
        self.logger = LogsRepository(self.conector)
        self.token = self.config.obtener_telegram_token()

    async def verificar_usuario_autorizado(self, telegram_id):
        """Simula o consulta si el usuario existe en la DB de usuarios autorizados"""
        conexion = self.conector.obtener_conexion()
        cursor = conexion.cursor()
        try:
            # Buscamos en la tabla de usuarios que creamos al inicio del proyecto
            cursor.execute("SELECT nombre_telegram, rol FROM usuarios WHERE telegram_id = ?", (str(telegram_id),))
            usuario = cursor.fetchone()
            return usuario  # Devuelve (nombre, rol) o None si no existe
        except Exception as e:
            self.logger.registrar_log("ERROR", f"Error verificando seguridad de usuario: {e}")
            return None
        finally:
            conexion.close()

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manejador del comando /start con filtro de seguridad y botones chillis"""
        user = update.effective_user
        telegram_id = user.id
        nombre_tg = user.first_name
        
        self.logger.registrar_log("INFO", f"Usuario intentando iniciar bot: {nombre_tg} ({telegram_id})")

        # 🔒 CONTROL DE SEGURIDAD INTERNO
        usuario_db = await self.verificar_usuario_autorizado(telegram_id)
        
        if not usuario_db:
            self.logger.registrar_log("WARNING", f"Acceso denegado para {nombre_tg} ({telegram_id}). No registrado.")
            await update.message.reply_text(
                f"❌ **Acceso Denegado**\n\nHola {nombre_tg}, tu cuenta no está registrada en el sistema de Disulubinca.\n"
                f"Por favor, solicita al Supervisor de Ventas que registre tu ID: `{telegram_id}` para poder reportar.",
                parse_mode="Markdown"
            )
            return

        # Si pasa el filtro, extraemos su nombre real en la empresa
        nombre_real, rol = usuario_db
        self.logger.registrar_log("INFO", f"Acceso concedido a {nombre_real} (Rol: {rol})")

        # ☀️ 🌙 DEFINICIÓN DE LOS BOTONES
        botones = [
            [KeyboardButton("☀️ Reportar Mañana"), KeyboardButton("🌙 Reportar Noche")]
        ]
        teclado = ReplyKeyboardMarkup(botones, resize_keyboard=True, one_time_keyboard=True)

        await update.message.reply_text(
            f"🚀 **Bienvenido al Sistema de Ventas - Disulubinca**\n\n"
            f"Hola, *{nombre_real}* ({rol}).\n"
            f"Selecciona el turno del reporte de cobranza que vas a procesar hoy:",
            reply_markup=teclado,
            parse_mode="Markdown"
        )

    def iniciar_polling(self):
            """Arranca el bot con tolerancia a fallos de red y timeouts altos"""
            if not self.token:
                self.logger.registrar_log("ERROR", "No se puede arrancar el bot sin un TOKEN válido.")
                return

            # --- PARCHE DE RESISTENCIA MARACAIBO (Timeouts en 30s) ---
            application = (
                Application.builder()
                .token(self.token)
                .connect_timeout(30.0)  # Le damos 30 segundos para conectar
                .read_timeout(30.0)     # Le damos 30 segundos para leer datos
                .build()
            )

            # Enlazamos el comando /start
            application.add_handler(CommandHandler("start", self.start))

            self.logger.registrar_log("INFO", "🤖 Bot de Telegram de Disulubinca encendido y escuchando en Linux...")
            
            # Evitamos que un micro-corte de internet rompa el bucle del script
            application.run_polling(close_loop=False)