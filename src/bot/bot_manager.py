# src/bot/bot_manager.py

import logging
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from bot.common_handlers import ayuda_handler
from bot.keyboards import BotKeyboards
from bot.vendedor_handlers import mi_rendimiento_handler
from config.config import Config
from database.connection import DBConnection
from database.logs_repo import LogsRepository

# 1. Importamos las Máquinas de Estado (Conversaciones)
from bot.auth_flow import auth_conversacion_handler
from bot.report_flow import reporte_conversacion_handler
from bot.admin_flow import admin_conversacion_handler

# 2. Importamos Handlers de Administración y Aprobaciones
from bot.admin_handlers import (
    callback_autorizacion_usuario_handler,
    resumen_ventas_handler,
    listar_pendientes_handler,
    autorizar_vendedor_handler
)
from database.reportes_repo import ReportesRepository
from database.usuarios_repo import UsuariosRepository
from services.dropbox_service import DropboxService
from services.excel_service import ExcelService
from services.orquestador_datos import OrquestadorDatos
import logging
from telegram.error import NetworkError, TimedOut


logger = logging.getLogger(__name__)
async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Captura errores globales y de red sin tumbar el bot ni spammear el log."""
    error = context.error
    
    # Si es un parpadeo de red común de Telegram, solo echamos un warning silenciador
    if isinstance(error, (NetworkError, TimedOut)):
        logging.warning(f"⚠️ Parpadeo de conexión con Telegram (NetworkError): {error}")
        return

    # Si es otro tipo de error no controlado, lo mandamos al log
    logging.error(f"❌ Excepción no controlada procesando evento: {error}", exc_info=error)
class DisulubincaBot:
    def __init__(self):
        self.config = Config()
        self.conector = DBConnection()
        self.logger_repo = LogsRepository(self.conector)
        self.token = self.config.obtener_telegram_token()
        self.reportes_repo = ReportesRepository(self.conector)
        self.usuarios_repo = UsuariosRepository(self.conector)
        self.dropbox_service = DropboxService(logger)
        self.excel_service = ExcelService(self.dropbox_service)
        self.orquestador = OrquestadorDatos(
            reportes_repo=self.reportes_repo,
            logs_repo=self.logger_repo,
            dropbox_service=self.dropbox_service,
            excel_service=self.excel_service
        )
        
        

    def iniciar_polling(self):
        """
        [MOTOR PRINCIPAL DE TELEGRAM]
        Configura la aplicación, registra todos los handlers centralizados
        y arranca el polling para escuchar eventos en caliente.
        """
        if not self.token:
            print("❌ ERROR CRÍTICO: No se encontró un TELEGRAM_TOKEN válido en la configuración.")
            self.logger_repo.registrar_log("ERROR", "No se puede arrancar el bot sin un TOKEN válido.")
            return

        print("🤖 Inicializando DisulubincaBot en Telegram...")

        # Construcción de la aplicación con timeouts resilientes
        application = (
            Application.builder()
            .token(self.token)
            .connect_timeout(30.0)
            .read_timeout(30.0)
            .build()
        )
        application.add_error_handler(global_error_handler)
        # 🚥 1. MÁQUINAS DE ESTADO (Prioridad Máxima en la cadena de captura)
        # auth_conversacion_handler captura el /start inicial para registros
        application.add_handler(auth_conversacion_handler)
        # reporte_conversacion_handler captura el flujo de envío de reportes
        application.add_handler(reporte_conversacion_handler)
        application.add_handler(admin_conversacion_handler)

        # 🚥 2. HANDLERS DE BOTONES INLINE (Aprobación/Rechazo de usuarios)
        application.add_handler(
            CallbackQueryHandler(
                callback_autorizacion_usuario_handler,
                pattern=r"^(aprobar_usr|rechazar_usr):"
            )
        )
        application.add_handler(MessageHandler(filters.Text(BotKeyboards.MI_RENDIMIENTO), mi_rendimiento_handler))
        application.add_handler(CommandHandler("miprogress", mi_rendimiento_handler))
        # 🚥 3. COMANDOS ADMINISTRATIVOS Y SUPERVISOR
        application.add_handler(CommandHandler("resumen", resumen_ventas_handler))
        application.add_handler(CommandHandler("pendientes", listar_pendientes_handler))
        application.add_handler(CommandHandler("autorizar", autorizar_vendedor_handler))
        application.add_handler(CommandHandler("ayuda", ayuda_handler))
        application.add_handler(CommandHandler("help", ayuda_handler))
        application.add_handler(MessageHandler(filters.Text(["❓ Ayuda / Soporte", "Ayuda", "ayuda"]), ayuda_handler))
        
        
        
        msg_inicio = "🤖 Bot de Telegram de Disulubinca encendido y escuchando eventos..."
        print(f"✅ {msg_inicio}")
        self.logger_repo.registrar_log("INFO", msg_inicio)

        # Arranca el bucle de polling
        application.run_polling(close_loop=False)


if __name__ == "__main__":
    bot = DisulubincaBot()
    bot.iniciar_polling()