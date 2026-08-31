# src/bot/common_handlers.py

from telegram import Update
from telegram.ext import ContextTypes

from bot.keyboards import BotKeyboards


async def ayuda_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Menú principal de ayuda con opciones específicas.
    """
    texto_guia = (
        "🆘 **AYUDA RÁPIDA**\n\n"
        "Selecciona una de las opciones para ver cómo funciona cada sección del bot."
    )
    await update.message.reply_text(
        texto_guia,
        reply_markup=BotKeyboards.obtener_teclado_ayuda(),
        parse_mode="Markdown"
    )


async def ayuda_categoria_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Explica cada opción del menú de ayuda y muestra un botón para volver.
    """
    opcion = update.message.text

    if opcion == BotKeyboards.SALIR_MENU:
        from bot.auth_flow import reiniciar_menu_handler
        await reiniciar_menu_handler(update, context)
        return

    if opcion == BotKeyboards.AYUDA_REPORTE:
        texto = (
            "📘 **REPORTES**\n\n"
            "Aquí tienes tres formas de registrar información:\n\n"
            "☀️ **Reportar Plan del día**\n"
            "• Se usa al iniciar la jornada.\n"
            "• Sirve para registrar metas de UDVD, cobranza y visitas.\n\n"
            "🌙 **Reportar Cierre**\n"
            "• Se usa cuando ya terminó el día.\n"
            "• Guarda ventas reales, visitas logradas y el cierre de caja.\n\n"
            "💵 **Reportar Cobranza**\n"
            "• Se usa cuando solo quieres enviar la cobranza y el desglose de dinero.\n"
            "• Es ideal para registrar efectivo, transferencia/Zelle y bolívares.\n\n"
            "En todos los casos, el bot intenta interpretar el texto con IA y te muestra una previsualización antes de guardar."
        )
    elif opcion == BotKeyboards.AYUDA_RAFAGA:
        texto = (
            "⚡️ **REPORTE RÁFAGA**\n\n"
            "Esta opción está pensada para cuando prefieres enviar varios fragmentos de texto en vez de uno largo.\n\n"
            "✅ ¿Cómo funciona?\n"
            "• Escribes los mensajes uno por uno.\n"
            "• El bot los guarda en una sola secuencia.\n"
            "• Cuando termines, presionas **🏁 Finalizar Ráfaga**.\n"
            "• Luego el sistema unifica toda la información y te muestra una vista previa final.\n\n"
            "Es útil para reportes improvisados, cambios rápidos o cuando el texto llega por partes."
        )
    elif opcion == BotKeyboards.AYUDA_RENDIMIENTO:
        texto = (
            "📊 **RENDIMIENTO**\n\n"
            "Aquí puedes consultar tu avance personal durante el mes.\n\n"
            "✅ Te muestra información como:\n"
            "• Cuota asignada.\n"
            "• Porcentaje alcanzado.\n"
            "• Dinero cobrado.\n"
            "• Estado de tus reportes del día.\n\n"
            "Es la opción para revisar cómo va tu trabajo y qué tan cerca estás de cumplir tus metas."
        )
    else:
        texto = (
            "🧭 **Ayuda del bot**\n\n"
            "Usa las opciones del teclado para consultar cada sección del sistema."
        )

    await update.message.reply_text(
        texto,
        reply_markup=BotKeyboards.obtener_teclado_ayuda_volver(),
        parse_mode="Markdown"
    )