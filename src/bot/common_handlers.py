# src/bot/common_handlers.py

from telegram import Update
from telegram.ext import ContextTypes

async def ayuda_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Guía interactiva sobre las funciones y botones del bot para el vendedor.
    """
    texto_guia = (
        "🤖 **MANUAL DE USO DEL BOT - DISULUBINCA**\n\n"
        "A continuación te explicamos la función de cada botón de tu menú:\n\n"
        "---"
        "☀️ **`☀️ Reportar Plan del dia`**\n"
        "• **Uso:** Al iniciar tu jornada laboral.\n"
        "• **Función:** Envía tu plan del día (metas de ventas, cobranza y clientes a visitar).\n\n"
        "🌙 **`🌙 Reportar Cierre`**\n"
        "• **Uso:** Al finalizar la jornada de ventas.\n"
        "• **Función:** Registra tus ventas reales del día, clientes visitados y el desglose de caja/cobranza.\n\n"
        "💵 **`💵 Reportar Cobranza`**\n"
        "• **Uso:** Cuando solo realizaste cobranza en la calle o quieres adelantar el cierre de caja.\n"
        "• **Función:** Registra únicamente los cobros y el desglose en Efectivo, Zelle y Bolívares.\n\n"
        "⚡️ **`⚡️ Reporte Ráfaga`**\n"
        "• **Uso:** Para cuando no quieres armar un solo texto largo en WhatsApp.\n"
        "• **Función:** Te permite copiar y reenviar los mensajes **uno por uno**. Al terminar de reenviar todo, presionas **`🏁 Finalizar Ráfaga`** y el bot unifica y calcula la sumatoria automáticamente.\n\n"
        "📊 **`📊 Mi Rendimiento`**\n"
        "• **Uso:** En cualquier momento del mes.\n"
        "• **Función:** Consulta tu avance mensual de cuota, porcentaje logrado, dinero cobrado y el estatus de tus reportes de hoy.\n\n"
        "---"
        "💡 *Consejo:* Si el reporte corresponde al día anterior, recuerda que la IA detecta la palabra **AYER** en el texto."
    )

    await update.message.reply_text(texto_guia, parse_mode="Markdown")