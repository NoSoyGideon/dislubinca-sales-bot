# src/bot/bot_manager.py

import atexit
import logging
import signal
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
import os
from bot.common_handlers import ayuda_handler, ayuda_categoria_handler
from bot.keyboards import BotKeyboards
from bot.vendedor_handlers import mi_rendimiento_handler
from config.config import Config
from database.connection import DBConnection
from database.init_db import inicializar_base_de_datos
from database.dataset import poblar_vendedores_produccion
from database.logs_repo import LogsRepository

# 1. Importamos las Máquinas de Estado (Conversaciones)
from bot.auth_flow import auth_conversacion_handler, reiniciar_registro_handler, reiniciar_menu_handler
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
        self.dropbox_service = DropboxService(self.logger_repo)
        self._restaurar_base_desde_dropbox_si_existe()
        print("🗄️ Verificando e inicializando la base de datos...")
        inicializar_base_de_datos()
        poblar_vendedores_produccion()

        self.token = self.config.obtener_telegram_token()
        self.reportes_repo = ReportesRepository(self.conector)
        self.usuarios_repo = UsuariosRepository(self.conector)
        self.excel_service = ExcelService(self.dropbox_service)
        self.orquestador = OrquestadorDatos(
            reportes_repo=self.reportes_repo,
            logs_repo=self.logger_repo,
            dropbox_service=self.dropbox_service,
            excel_service=self.excel_service
        )
        self._registrar_guardado_de_cierre()

    def _restaurar_base_desde_dropbox_si_existe(self):
        """Intenta restaurar usuarios.db desde Dropbox antes de crear la base local."""
        ruta_db = self.conector.db_path
        ok = self.dropbox_service.restaurar_bd_desde_dropbox(ruta_db)
        if ok:
            print("✅ [Startup] Base de datos restaurada desde Dropbox.")
        else:
            print("ℹ️ [Startup] No se encontró respaldo en Dropbox o la restauración falló; se usará la base local/creación normal.")

    def _registrar_guardado_de_cierre(self):
        """Intenta guardar la base de datos al cerrar el proceso o recibir señales de interrupción."""
        atexit.register(self._guardar_db_en_dropbox)
        for senal in (signal.SIGINT, signal.SIGTERM):
            try:
                signal.signal(senal, self._handler_senal_cierre)
            except (AttributeError, ValueError):
                pass

    def _handler_senal_cierre(self, signum, frame):
        print(f"⚠️ [Shutdown] Señal de cierre recibida ({signum}). Intentando guardar respaldo final...")
        self._guardar_db_en_dropbox()
        raise SystemExit(0)

    def _guardar_db_en_dropbox(self):
        """Hace un backup final del SQLite a Dropbox sin bloquear la app."""
        try:
            if hasattr(self, "conector") and hasattr(self.conector, "db_path"):
                ruta_db = self.conector.db_path
                if os.path.exists(ruta_db):
                    ok = self.dropbox_service.respaldar_bd_local(ruta_db)
                    if ok:
                        print("💾 [Shutdown] Respaldo final de la base de datos enviado a Dropbox.")
                        return
                print("⚠️ [Shutdown] No hubo base local para respaldar al cerrar.")
        except Exception as exc:
            print(f"❌ [Shutdown] Error guardando base en Dropbox: {exc}")

    async def _mantenimiento_mensual_job(self, context):
        """Revisa y ejecuta el mantenimiento mensual en horario venezolano."""
        ahora = datetime.now(ZoneInfo("America/Caracas"))
        self._ejecutar_mantenimiento(ahora)

    def _ejecutar_mantenimiento(self, ahora):
        ejecutado = self.orquestador.ejecutar_mantenimiento_si_corresponde(ahora)
        if ejecutado:
            mes_anterior = (ahora.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
            print(f"🧹 Mantenimiento mensual ejecutado para {mes_anterior}.")

    async def _backup_db_job(self, context):
        """Backup diario automático de la base local hacia Dropbox a las 02:00."""
        try:
            if hasattr(self, "conector") and hasattr(self.conector, "db_path") and os.path.exists(self.conector.db_path):
                ok = self.dropbox_service.respaldar_bd_local(self.conector.db_path)
                if ok:
                    print("💾 [Scheduler] Backup nocturno de usuarios.db enviado a Dropbox.")
                    return
            print("⚠️ [Scheduler] No se pudo hacer el backup nocturno porque no hay base local disponible.")
        except Exception as exc:
            print(f"❌ [Scheduler] Error ejecutando backup nocturno: {exc}")

    def _programar_mantenimiento_mensual(self, application):
        """Programa el mantenimiento el día 10 a las 02:00 de Venezuela."""
        zona_venezuela = ZoneInfo("America/Caracas")
        application.job_queue.run_monthly(
            self._mantenimiento_mensual_job,
            when=time(hour=2, minute=0, tzinfo=zona_venezuela),
            day=10,
            name="mantenimiento_mensual"
        )
        application.job_queue.run_daily(
            self._backup_db_job,
            time(hour=2, minute=0, tzinfo=zona_venezuela),
            name="backup_db_diario"
        )

        ahora = datetime.now(zona_venezuela)
        if ahora.day == 10 and (ahora.hour, ahora.minute) >= (2, 0):
            self._ejecutar_mantenimiento(ahora)
        
        

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
        self._programar_mantenimiento_mensual(application)
        application.add_error_handler(global_error_handler)

        # 🛟 Comandos globales de recuperación: siempre deben estar disponibles
        # aunque el usuario esté en medio de cualquier flujo.
        application.add_handler(CommandHandler("cancelar", reiniciar_registro_handler))
        application.add_handler(CommandHandler("reiniciar", reiniciar_registro_handler))
        application.add_handler(CommandHandler("reset", reiniciar_registro_handler))
        application.add_handler(CommandHandler("menu", reiniciar_registro_handler))
        application.add_handler(CommandHandler("inicio", reiniciar_registro_handler))
        application.add_handler(CommandHandler("hola", reiniciar_registro_handler))
        application.add_handler(
            MessageHandler(
                filters.Regex(r"^(?:/menu|/inicio|/hola|/reiniciar|/reset|/cancelar|🏠 Volver al inicio|Volver al inicio)$"),
                reiniciar_menu_handler
            )
        )

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
        application.add_handler(MessageHandler(filters.Text(["❓ Ayuda / Soporte", "Ayuda", "ayuda", BotKeyboards.AYUDA]), ayuda_handler))
        application.add_handler(
            MessageHandler(
                filters.Text([
                    BotKeyboards.AYUDA_REPORTE,
                    BotKeyboards.AYUDA_RAFAGA,
                    BotKeyboards.AYUDA_RENDIMIENTO,
                    BotKeyboards.SALIR_MENU
                ]),
                ayuda_categoria_handler
            )
        )
        
        
        
        msg_inicio = "🤖 Bot de Telegram de Disulubinca encendido y escuchando eventos..."
        print(f"✅ {msg_inicio}")
        self.logger_repo.registrar_log("INFO", msg_inicio)

        # Arranca el bucle de polling
        application.run_polling(close_loop=False)


if __name__ == "__main__":
    bot = DisulubincaBot()
    bot.iniciar_polling()