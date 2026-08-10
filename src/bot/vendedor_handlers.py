# src/bot/vendedor_handlers.py

from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards import BotKeyboards
from services.orquestador_datos import OrquestadorDatos
from services.excel_service import ExcelService
from services.dropbox_service import DropboxService
from database.connection import DBConnection
from database.logs_repo import LogsRepository
from database.reportes_repo import ReportesRepository
from database.usuarios_repo import UsuariosRepository

conector = DBConnection()
logger = LogsRepository(conector)
reportes_repo = ReportesRepository(conector)
usuarios_repo = UsuariosRepository(conector)
dropbox_service = DropboxService(logger)
excel_service = ExcelService(dropbox_service)

orquestador = OrquestadorDatos(
    reportes_repo=reportes_repo,
    logs_repo=logger,
    dropbox_service=dropbox_service,
    excel_service=excel_service
)

async def mi_rendimiento_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Responde al botón '📊 Mi Rendimiento' enviando el resumen del avance mensual y Run Rate.
    """
    telegram_id = update.effective_user.id
    usr = usuarios_repo.obtener_usuario_por_telegram(telegram_id)

    if not usr or usr.get("estado") != "AUTORIZADO":
        await update.message.reply_text("❌ No estás autorizado para consultar métricas de venta.")
        return

    ruta_id = usr["ruta"]
    await update.message.reply_text("📊 *Calculando tu rendimiento mensual y ritmo de venta...*", parse_mode="Markdown")

    try:
        reporte_txt = orquestador.consultar_mi_rendimiento_vendedor(ruta_id)

        await update.message.reply_text(reporte_txt, parse_mode="Markdown")
    except Exception as e:
        logger.registrar_log("ERROR", f"Error al generar mi_rendimiento para Ruta {ruta_id}: {e}")
        await update.message.reply_text("⚠️ No fue posible calcular tu rendimiento en este momento. Intenta más tarde.")