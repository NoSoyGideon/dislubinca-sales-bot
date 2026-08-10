# src/bot/admin_handlers.py

from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler, CommandHandler

from bot.notifications import NotificationService
from database.connection import DBConnection
from database.usuarios_repo import UsuariosRepository
from database.logs_repo import LogsRepository

conector = DBConnection()
usuarios_repo = UsuariosRepository(conector)
logger = LogsRepository(conector)

async def callback_autorizacion_usuario_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Procesa las acciones Inline del supervisor:
    callback_data -> "aprobar_usr:<telegram_id>:<ruta>" o "rechazar_usr:<telegram_id>:<ruta>"
    """
    query = update.callback_query
    await query.answer()

    data_parts = query.data.split(":")
    accion = data_parts[0]
    target_telegram_id = data_parts[1]
    ruta_id = data_parts[2]

    sup_id = update.effective_user.id
    if not usuarios_repo.es_administrador(sup_id):
        await query.edit_message_text("❌ No tienes permisos para realizar esta acción.")
        return

    if accion == "aprobar_usr":
        exito = usuarios_repo.autorizar_vendedor(
            ruta_id=ruta_id,
        )
        if exito:
            await query.edit_message_text(
                f"✅ **USUARIO AUTORIZADO**\n\n"
                f"• ID: `{target_telegram_id}`\n"
                f"• Ruta: **R-{ruta_id}**\n"
                f"• Estado: **AUTORIZADO** 🟢\n"
                f"• Autorizado por: {update.effective_user.first_name}",
                parse_mode="Markdown"
            )
            # 🔔 PUSH AL VENDEDOR
            await NotificationService.notificar_resultado_autorizacion(
                bot=context.bot,
                vendedor_telegram_id=target_telegram_id,
                ruta=ruta_id,
                aprobado=True
            )
    elif accion == "rechazar_usr":
        exito = usuarios_repo.aprobar_o_rechazar_usuario(
            telegram_id=target_telegram_id,
            nuevo_estado="RECHAZADO"
        )
        if exito:
            await query.edit_message_text(
                f"❌ **SOLICITUD RECHAZADA**\n\n"
                f"• ID: `{target_telegram_id}`\n"
                f"• Ruta: **R-{ruta_id}**\n"
                f"• Estado: **RECHAZADO** 🔴",
                parse_mode="Markdown"
            )
            # 🔔 PUSH AL VENDEDOR
            await NotificationService.notificar_resultado_autorizacion(
                bot=context.bot,
                vendedor_telegram_id=target_telegram_id,
                ruta=ruta_id,
                aprobado=False
            )
async def resumen_ventas_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el total cobrado en el día (Solo Admin/Supervisor)"""
    telegram_id = update.effective_user.id
    
    # Muro de seguridad en la frontera
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ Comando no reconocido.")
        return

    # TODO: Aquí buscaremos los totales reales en la DB de cobranza en la siguiente fase
    await update.message.reply_text("📊 **Panel Ejecutivo**\n\nGenerando el resumen de cobranza del día de hoy en todo el estado Zulia... (Estructura lista)⏳")

async def listar_pendientes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra la lista de vendedores que esperan autorización (Solo Admin/Supervisor)"""
    telegram_id = update.effective_user.id
    
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ Comando no reconocido.")
        return

    # TODO: Aquí consultaremos los usuarios en estado 'PENDIENTE'
    await update.message.reply_text("👥 **Vendedores Pendientes**\n\nBuscando personal en lista de espera... (Estructura lista)⏳")

async def autorizar_vendedor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Autoriza un ID de Telegram y le asigna una ruta de cobranza (Solo Admin/Supervisor)"""
    telegram_id = update.effective_user.id
    
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ Comando no reconocido.")
        return

    # TODO: Aquí procesaremos los argumentos del comando (Ej: /autorizar 12345 10)
    await update.message.reply_text("✅ **Procesador de Autorizaciones**\n\nListo para recibir parámetros de ruta... (Estructura lista)⏳")