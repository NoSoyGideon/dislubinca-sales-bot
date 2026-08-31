# src/bot/report_flow.py

from datetime import datetime
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    filters
)

from bot.keyboards import BotKeyboards
from bot.auth_flow import reiniciar_menu_handler
from services.ia_parser import IAParser
from services.orquestador_datos import OrquestadorDatos
from services.excel_service import ExcelService
from services.dropbox_service import DropboxService
from database.connection import DBConnection
from database.logs_repo import LogsRepository
from database.reportes_repo import ReportesRepository
from database.usuarios_repo import UsuariosRepository

# Conectores e instancias
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

parser_ia = IAParser()

# Estados de conversación

ESTADO_TEXTO_REPORTE, ESTADO_ACUMULANDO_RAFAGA, ESTADO_CONFIRMACION_REPORTE = range(3)

MAX_MENSAJES_RAFAGA = 5  # Límite para evitar abusos o desbordes
# ========================================================
#            MANEJADORES DEL FLUJO DE REPORTES
# ========================================================

async def iniciar_reporte_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Punto de entrada: Presionar cualquier botón de reporte (Mañana, Noche, Cobranza)
    """
    telegram_id = update.effective_user.id
    
    usr = usuarios_repo.obtener_usuario_por_telegram(telegram_id)
    if not usr or usr.get("estado") != "AUTORIZADO":
        await update.message.reply_text(
            "❌ **Acceso denegado.** Tu cuenta aún no ha sido autorizada por el supervisor.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    texto_boton = update.message.text
    context.user_data["turno_reporte"] = texto_boton
    context.user_data["ruta_id"] = usr["ruta"]

    if texto_boton == BotKeyboards.TURNO_MANANA:
        modo_txt = "Plan Matutino"
    elif texto_boton == BotKeyboards.TURNO_NOCHE:
        modo_txt = "Cierre Nocturno"
    else:
        modo_txt = "Cobranza"

    html_solicitud = f"""
📝 <b>REPORTE — {modo_txt.upper()}</b>
📍 <b>Ruta asignada:</b> Ruta {usr['ruta']}

Por favor, describa la relación de su planificación de trabajo para el día de hoy (Metas UDVD, Visitas, CxC y Grupo Amigo/Celta).

ℹ️ <i>Nota: El sistema registrará la información con la fecha actual de forma automática. Si desea reportar una fecha distinta, especifíquela explícitamente en el texto.</i>
""".strip()
    
    await update.message.reply_text(
        html_solicitud,
        reply_markup=BotKeyboards.obtener_teclado_salir(),
        parse_mode="HTML"
    )
    return ESTADO_TEXTO_REPORTE


async def procesar_texto_whatsapp_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Recibe el texto, le adjunta la pista contextual según el botón presionado y lo envía a Gemini.
    """
    texto_raw = update.message.text
    telegram_id = update.effective_user.id
    ruta_id = context.user_data.get("ruta_id")
    turno_reporte = context.user_data.get("turno_reporte")

    if not ruta_id:
        usr = usuarios_repo.obtener_usuario_por_telegram(telegram_id)
        if usr and usr.get("estado") == "AUTORIZADO":
            ruta_id = usr["ruta"]
            context.user_data["ruta_id"] = ruta_id
        else:
            await update.message.reply_text("❌ Perfil no encontrado. Usa `/start` para registrarte.")
            return ConversationHandler.END

    # 🎯 Inyección de contexto para eliminar ambigüedades en Gemini
    if turno_reporte == BotKeyboards.TURNO_MANANA:
        contexto_intencion = "[CONTEXTO DE BOTÓN: TIPO PLAN MATUTINO/MAÑANA]\n"
    elif turno_reporte == BotKeyboards.TURNO_NOCHE:
        contexto_intencion = "[CONTEXTO DE BOTÓN: TIPO CIERRE NOCTURNO COMPLETO]\n"
    elif turno_reporte == BotKeyboards.REPORTE_COBRANZA:
        contexto_intencion = "[CONTEXTO DE BOTÓN: TIPO SOLO COBRANZA Y CAJA]\n"
    else:
        contexto_intencion = ""

    texto_para_ia = f"{contexto_intencion}{texto_raw}"

    await update.message.reply_text("⏳ *DislubinBot esta procesando reporte ... El sistema le notificarán al finalizar.*", parse_mode="Markdown")

    resultado_ia = parser_ia.parsear_texto_libre(texto_para_ia)

    # 1. Validar si la respuesta de la IA fue exitosa
    if not resultado_ia or not resultado_ia.get("exito", False):
        error_detalle = resultado_ia.get("error", "Error desconocido") if resultado_ia else "Sin respuesta"

        # Manejo diferenciado según la causa del error
        if "API Key" in error_detalle or "genai.Client" in error_detalle:
            mensaje_usuario = (
                "🚨 <b>Servicio de IA no disponible.</b>\n\n"
                "El servicio no está configurado correctamente (API Key ausente o inválida). Notifique al administrador del sistema."
            )
        elif "JSON" in error_detalle:
            mensaje_usuario = (
                "⚠️ <b>No se pudo interpretar el reporte.</b>\n\n"
                "Asegúrese de enviar un texto con los montos, unidades o metas estructuradas.\n\n"
                "💡 <i>Envíe <code>/cancelar</code> para regresar al menú.</i>"
            )
        else:
            mensaje_usuario = (
                "🚦 <b>Sistema con alto volumen de solicitudes.</b>\n\n"
                "En este momento estamos experimentando un alto tráfico de reportes. Su mensaje no pudo ser procesado.\n\n"
                "💡 <i>Por favor, espere un par de minutos e intente nuevamente o envíe <code>/cancelar</code> para reiniciar.</i>"
            )

        await update.message.reply_text(
            mensaje_usuario,
            reply_markup=BotKeyboards.obtener_teclado_vendedor(),
            parse_mode="HTML"
        )
        return ConversationHandler.END

    context.user_data["payload_ia"] = resultado_ia
    tipo_intencion = str(resultado_ia.get("tipo_intencion", "")).upper()
    
    fecha_eval = resultado_ia.get("fecha_mencionada") or datetime.now().strftime("%Y-%m-%d")
    context.user_data["fecha_evaluar"] = fecha_eval

    # Clasificación del modo
    es_matutino = "PLAN_MATUTINO" in tipo_intencion
    es_solo_cobranza = turno_reporte == BotKeyboards.REPORTE_COBRANZA or "COBRANZA" in tipo_intencion
    
    context.user_data["es_matutino"] = es_matutino
    context.user_data["es_solo_cobranza"] = es_solo_cobranza

    # 📋 Previsualización según la modalidad
    if es_matutino:
        resumen_txt = (
            f"📋 **PREVISUALIZACIÓN - PLAN MATUTINO**\n"
            f"📍 **Ruta:** {ruta_id} | 📅 **Fecha:** {fecha_eval}\n\n"
            f"📦 **Meta UDVD:** {resultado_ia.get('meta_udvd', 0)} UDVD\n"
            f"💵 **Meta Cobranza:** ${float(resultado_ia.get('meta_cxc', 0.0)):,.2f}\n"
            f"🎯 **Meta Visitas:** {resultado_ia.get('meta_activaciones', 0)}\n"
            f"👥 **Meta Grupo Amigo:** {resultado_ia.get('meta_amigo', 0)}\n"
            f"🚗 **Meta Grupo Celta:** {resultado_ia.get('meta_celta', 0)}\n"
        )
    elif es_solo_cobranza:
        resumen_txt = (
            f"📋 **PREVISUALIZACIÓN - SOLO COBRANZA Y CAJA**\n"
            f"📍 **Ruta:** {ruta_id} | 📅 **Fecha:** {fecha_eval}\n\n"
            f"💵 **Cobranza Total:** ${float(resultado_ia.get('real_cxc', 0.0)):,.2f}\n\n"
            f"💰 **DESGLOSE DE CAJA:**\n"
            f"• Efectivo ($): ${float(resultado_ia.get('efectivo_usd', 0.0)):,.2f}\n"
            f"• Transferencia/Zelle ($): ${float(resultado_ia.get('zelle_usd', 0.0)):,.2f}\n"
            f"• Bolívares Cambiados ($): ${float(resultado_ia.get('bs_cambiados_usd', 0.0)):,.2f}\n"
            f"• Tasa BCV: {float(resultado_ia.get('tasa_bcv', 0.0))} Bs/$\n"
        )
    else:
        resumen_txt = (
            f"📋 **PREVISUALIZACIÓN - CIERRE NOCTURNO COMPLETO**\n"
            f"📍 **Ruta:** {ruta_id} | 📅 **Fecha:** {fecha_eval}\n\n"
            f"📦 **Venta Real UDVD:** {resultado_ia.get('real_udvd', 0)} UDVD\n"
            f"💵 **Cobranza Real:** ${float(resultado_ia.get('real_cxc', 0.0)):,.2f}\n"
            f"🎯 **Visitas Logradas:** {resultado_ia.get('real_activaciones', 0)}\n\n"
            f"👥 **Grupo Amigo:** {resultado_ia.get('real_amigo', 0)}\n"
            f"🚗 **Grupo Celta:** {resultado_ia.get('real_celta', 0)}\n"
            # f"💰 **DESGLOSE DE CAJA:**\n"
            # f"• Efectivo ($): ${float(resultado_ia.get('efectivo_usd', 0.0)):,.2f}\n"
            # f"• Transferencia/Zelle ($): ${float(resultado_ia.get('zelle_usd', 0.0)):,.2f}\n"
            # f"• Bolívares Cambiados ($): ${float(resultado_ia.get('bs_cambiados_usd', 0.0)):,.2f}\n"
            # f"• Tasa BCV: {float(resultado_ia.get('tasa_bcv', 0.0))} Bs/$\n"
        )

    resumen_txt += "\n¿Los datos extraídos son correctos?"

    await update.message.reply_text(
        resumen_txt,
        reply_markup=BotKeyboards.obtener_teclado_confirmacion(),
        parse_mode="Markdown"
    )
    return ESTADO_CONFIRMACION_REPORTE

async def iniciar_reporte_rafaga_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Punto de entrada al presionar '⚡️ Reporte Ráfaga'
    """
    telegram_id = update.effective_user.id
    usr = usuarios_repo.obtener_usuario_por_telegram(telegram_id)
    
    if not usr or usr.get("estado") != "AUTORIZADO":
        await update.message.reply_text("❌ Acceso denegado. Tu cuenta no está autorizada.")
        return ConversationHandler.END

    # Inicializamos el búfer
    context.user_data["mensajes_rafaga"] = []
    context.user_data["ruta_id"] = usr["ruta"]
    context.user_data["modo_rafaga"] = True

    await update.message.reply_text(
        "⚡️ **MODO REPORTAR RÁFAGA ACTIVADO**\n\n"
        "Envía los mensajes que desees **uno por uno** .\n"
        "Cuando termines de enviar todo, presiona el botón **`🏁 Finalizar Ráfaga`** para procesarlo.",
        reply_markup=BotKeyboards.obtener_teclado_rafaga(),
        parse_mode="Markdown"
    )
    return ESTADO_ACUMULANDO_RAFAGA


async def acumular_mensaje_rafaga_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Acumula cada texto enviado durante el modo Ráfaga.
    """
    texto = update.message.text
    buf = context.user_data.get("mensajes_rafaga", [])
    
    buf.append(texto)
    context.user_data["mensajes_rafaga"] = buf
    total = len(buf)

    if total >= MAX_MENSAJES_RAFAGA:
        await update.message.reply_text(
            f"📥 **Mensaje #{total} recibido.** Se alcanzó el límite máximo de {MAX_MENSAJES_RAFAGA} mensajes.\n"
            "Procesando todo el reporte acumulado...",
            parse_mode="Markdown"
        )
        # Forzamos la consolidación automática
        return await procesar_rafaga_acumulada(update, context)

    await update.message.reply_text(
        f"📥 **Fragmento #{total} recibido y guardado.**\n"
        f"Envía el siguiente mensaje o presiona **`🏁 Finalizar Ráfaga`** cuando estés listo.",
        reply_markup=BotKeyboards.obtener_teclado_rafaga(),
        parse_mode="Markdown"
    )
    return ESTADO_ACUMULANDO_RAFAGA


async def finalizar_rafaga_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Se ejecuta cuando el vendedor presiona '🏁 Finalizar Ráfaga'.
    """
    buf = context.user_data.get("mensajes_rafaga", [])
    if not buf:
        await update.message.reply_text(
            "⚠️ No has enviado ningún mensaje todavía. Envía al menos uno o escribe `/cancelar`.",
            reply_markup=BotKeyboards.obtener_teclado_rafaga()
        )
        return ESTADO_ACUMULANDO_RAFAGA

    return await procesar_rafaga_acumulada(update, context)


async def procesar_rafaga_acumulada(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Unifica todos los fragmentos acumulados y se los entrega al parser de Gemini.
    """
    buf = context.user_data.get("mensajes_rafaga", [])
    texto_unificado = "\n\n".join(buf)

    # Inyectamos pista contextual de ráfaga
    contexto_intencion = "[CONTEXTO DE BOTÓN: TIPO REPORTE RÁFAGA/MULTI-MENSAJE COMPLETO]\n"
    texto_para_ia = f"{contexto_intencion}{texto_unificado}"

    await update.message.reply_text("⏳ *Procesando mensaje...*", parse_mode="Markdown")
    resultado_ia = parser_ia.parsear_texto_libre(texto_para_ia)

    # 1. Validar si la respuesta de la IA fue exitosa
    if not resultado_ia or not resultado_ia.get("exito", False):
        error_detalle = resultado_ia.get("error", "Error desconocido") if resultado_ia else "Sin respuesta"

        # Manejo diferenciado según la causa del error
        if "API Key" in error_detalle or "genai.Client" in error_detalle:
            mensaje_usuario = (
                "🚨 <b>Servicio de IA no disponible.</b>\n\n"
                "El servicio no está configurado correctamente (API Key ausente o inválida). Notifique al administrador del sistema."
            )
        elif "JSON" in error_detalle:
            mensaje_usuario = (
                "⚠️ <b>No se pudo interpretar el reporte.</b>\n\n"
                "Asegúrese de enviar un texto con los montos, unidades o metas estructuradas.\n\n"
                "💡 <i>Envíe <code>/cancelar</code> para regresar al menú.</i>"
            )
        else:
            mensaje_usuario = (
                "🚦 <b>Sistema con alto volumen de solicitudes.</b>\n\n"
                "En este momento estamos experimentando un alto tráfico de reportes. Su mensaje no pudo ser procesado.\n\n"
                "💡 <i>Por favor, espere un par de minutos e intente nuevamente o envíe <code>/cancelar</code> para reiniciar.</i>"
            )

        await update.message.reply_text(
            mensaje_usuario,
            reply_markup=BotKeyboards.obtener_teclado_vendedor(),
            parse_mode="HTML"
        )
        return ConversationHandler.END

    context.user_data["payload_ia"] = resultado_ia
    
    dia_destino = resultado_ia.get("dia_destino", "HOY")
    fecha_eval = reportes_repo._resolver_fecha_relativa(dia_destino)
    context.user_data["fecha_evaluar"] = fecha_eval
    ruta_id = context.user_data.get("ruta_id")

    # Alerta de cuadre de caja si aplica
    cobrado_total = float(resultado_ia.get("real_cxc", 0.0))
    efectivo = float(resultado_ia.get("efectivo_usd", 0.0))
    zelle = float(resultado_ia.get("zelle_usd", 0.0))
    bs = float(resultado_ia.get("bs_cambiados_usd", 0.0))
    suma_caja = efectivo + zelle + bs
    diferencia_caja = abs(cobrado_total - suma_caja)

    aviso_cuadre_txt = ""
    if cobrado_total > 0 and suma_caja > 0 and diferencia_caja > 0.01:
        aviso_cuadre_txt = f"\n\n⚠️ *Aviso de cuadre:* Hay ${diferencia_caja:,.2f} de diferencia entre la cobranza total y la suma de caja."

    # Previsualización unificada
    resumen_txt = (
        f"📋 **PREVISUALIZACIÓN - REPORTE RÁFAGA UNIFICADO**\n"
        f"📍 **Ruta:** {ruta_id} | 📅 **Fecha:** {fecha_eval}\n\n"
        f"📦 **Ventas (UDVD):** {resultado_ia.get('real_udvd', 0)} UDVD\n"
        f"💵 **Cobranza Total:** ${cobrado_total:,.2f}\n"
        f"🎯 **Visitas Logradas:** {resultado_ia.get('real_activaciones', 0)}\n\n"
        f"💰 **DESGLOSE DE CAJA:**\n"
        f"• Efectivo ($): ${efectivo:,.2f}\n"
        f"• Transferencia/Zelle ($): ${zelle:,.2f}\n"
        f"• Bolívares Cambiados ($): ${bs:,.2f}\n"
        f"• Tasa BCV: {float(resultado_ia.get('tasa_bcv', 0.0))} Bs/${aviso_cuadre_txt}\n\n"
        f"¿Deseas confirmar y guardar estos datos?"
    )

    await update.message.reply_text(
        resumen_txt,
        reply_markup=BotKeyboards.obtener_teclado_confirmacion(),
        parse_mode="Markdown"
    )
    return ESTADO_CONFIRMACION_REPORTE

async def confirmacion_guardado_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Impacta en SQLite, Contacto Matutino y Reporte Diario de Cobranza.
    """
    decision = update.message.text
    ruta_id = context.user_data.get("ruta_id")
    payload = context.user_data.get("payload_ia", {})
    fecha_eval = context.user_data.get("fecha_evaluar") or datetime.now().strftime("%Y-%m-%d")
    es_matutino = context.user_data.get("es_matutino", False)

    if decision == BotKeyboards.CONFIRMAR or decision == BotKeyboards.SI:
        await update.message.reply_text(
            "⏳ *Carga procesándose en segundo plano. El sistema le notificarán al finalizar.*",
            parse_mode="Markdown"
        )

        exito = False
        if es_matutino:
            exito = orquestador.procesar_plan_matutino(
                ruta=ruta_id,
                meta_udvd=float(payload.get("meta_udvd", 0)),
                meta_cobranza=float(payload.get("meta_cxc", 0.0)),
                meta_activaciones=int(payload.get("meta_activaciones", 0)),
                meta_amigo=float(payload.get("meta_amigo", 0.0)),
                meta_celta=float(payload.get("meta_celta", 0.0)),
                fecha_str=fecha_eval
            )
        else:
            # Sirve tanto para Cierre Completo como para Solo Cobranza
            exito = orquestador.procesar_cierre_nocturno(
                ruta=ruta_id,
                real_udvd=float(payload.get("real_udvd", 0)),
                real_cobranza=float(payload.get("real_cxc", 0.0)),
                real_activaciones=int(payload.get("real_activaciones", 0)),
                efectivo=float(payload.get("efectivo_usd", 0.0)),
                zelle=float(payload.get("zelle_usd", 0.0)),
                bs=float(payload.get("bs_cambiados_usd", 0.0)),
                tasa_bcv=float(payload.get("tasa_bcv", 0.0)),
                real_amigo=float(payload.get("real_amigo", 0.0)),
                real_celta=float(payload.get("real_celta", 0.0)),
                fecha_str=fecha_eval
            )

        if exito:
            await update.message.reply_text(
                f"✅ **¡REPORTE REGISTRADO EXITOSAMENTE!**\n\n"
                f"📍 Ruta {ruta_id} | 📅 {fecha_eval}\n"
                f"Datos actualizados en SQLite y respaldados en la nube.",
                reply_markup=BotKeyboards.obtener_teclado_vendedor(),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❌ **Error al intentar sincronizar con Dropbox.** Por favor reintenta.",
                reply_markup=BotKeyboards.obtener_teclado_vendedor(),
                parse_mode="Markdown"
            )

    else:
        await update.message.reply_text(
            "❌ **Operación Cancelada.** Se han descartado los datos.",
            reply_markup=BotKeyboards.obtener_teclado_vendedor(),
            parse_mode="Markdown"
        )

    context.user_data.clear()
    return ConversationHandler.END


async def salir_al_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finaliza el flujo actual y devuelve al menú principal del usuario."""
    context.user_data.clear()
    if "_conversation_state" in context.user_data:
        del context.user_data["_conversation_state"]
    await reiniciar_menu_handler(update, context)
    return ConversationHandler.END


async def cancelar_flujo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "🚫 Flujo cancelado.",
        reply_markup=BotKeyboards.obtener_teclado_vendedor()
    )
    return ConversationHandler.END


# Máquina de estados exportable
# Dentro de report_flow.py:

reporte_conversacion_handler = ConversationHandler(
    entry_points=[
        MessageHandler(
            filters.Text([
                BotKeyboards.TURNO_MANANA,
                BotKeyboards.TURNO_NOCHE,
                BotKeyboards.REPORTE_COBRANZA
            ]),
            iniciar_reporte_handler
        ),
        MessageHandler(
            filters.Text([BotKeyboards.REPORTE_RAFAGA]),
            iniciar_reporte_rafaga_handler
        )
    ],
    states={
        ESTADO_TEXTO_REPORTE: [
            MessageHandler(filters.Text([BotKeyboards.SALIR_MENU]), salir_al_menu_handler),
            MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_texto_whatsapp_handler)
        ],
        ESTADO_ACUMULANDO_RAFAGA: [
            MessageHandler(filters.Text([BotKeyboards.SALIR_MENU]), salir_al_menu_handler),
            MessageHandler(filters.Text([BotKeyboards.FINALIZAR_RAFAGA]), finalizar_rafaga_handler),
            MessageHandler(filters.TEXT & ~filters.COMMAND, acumular_mensaje_rafaga_handler)
        ],
        ESTADO_CONFIRMACION_REPORTE: [
            MessageHandler(filters.Text([BotKeyboards.SALIR_MENU]), salir_al_menu_handler),
            MessageHandler(filters.Text([BotKeyboards.CONFIRMAR, BotKeyboards.SI, BotKeyboards.NO, BotKeyboards.CANCELAR]), confirmacion_guardado_handler)
        ]
    },
    fallbacks=[
        CommandHandler("cancelar", cancelar_flujo_handler),
        CommandHandler("menu", reiniciar_menu_handler),
        CommandHandler("inicio", reiniciar_menu_handler),
        CommandHandler("hola", reiniciar_menu_handler),
        MessageHandler(filters.Text([BotKeyboards.SALIR_MENU]), salir_al_menu_handler)
    ],per_message=False,  # Mantiene la conversación ligada al usuario/chat de forma estricta
    per_user=True,
    per_chat=True,
    allow_reentry=True  # 👈 PERMITE REENTRAR AL FLUJO AUNQUE NO HAYA TERMINADO OFICIALMENTE EL ANTERIO
)