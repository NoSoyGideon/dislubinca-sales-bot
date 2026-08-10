# src/bot/auth_flow.py

import re
from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler

from bot.keyboards import BotKeyboards,SupervisorKeyboards
from bot.notifications import NotificationService
from database.connection import DBConnection
from database.usuarios_repo import UsuariosRepository
from database.logs_repo import LogsRepository

# Inicializadores locales
conector = DBConnection()
usuarios_repo = UsuariosRepository(conector)
logger = LogsRepository(conector)

# Estados del Registro
ESTADO_REGISTRO_RUTA, ESTADO_REGISTRO_NOMBRE = range(10, 12)
RUTAS_VALIDAS = [10, 15, 13, 17, 21, 26, 30, 32, 39]

# ==========================================
#       FUNCIONES AUXILIARES DE LIMPIEZA
# ==========================================

def validar_nombre_real(texto: str) -> bool:
    """Verifica si el nombre es válido y no contiene saludos tontos o chismes."""
    palabras_prohibidas = ["hola", "buenos", "dias", "tardes", "noches", "saludos", "epale", "que fue"]
    texto_clean = texto.lower().strip()
    if len(texto_clean) < 3:
        return False
    return not any(palabra in texto_clean for palabra in palabras_prohibidas)

def formatear_nombre_vendedor(texto: str) -> str:
    """Aplica trim y convierte cada palabra a mayúscula inicial (Title Case)."""
    return " ".join(palabra.capitalize() for palabra in texto.strip().split())

# ==========================================
#         HANDLERS DE LA CONVERSACIÓN
# ==========================================

async def iniciar_registro_flow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Punto de entrada (/start) para usuarios no registrados o en proceso."""
    telegram_id = update.effective_user.id
    
    # 1. Verificar si ya existe en BD
    usr = usuarios_repo.obtener_usuario_por_telegram(telegram_id)
    
    if usr:
        
        if usr.get("rol") == "SUPERVISOR":
            await update.message.reply_text(
                f"👑 ¡Bienvenido de nuevo, Supervisor **{usr['nombre']}**!\n\n"
                f"Tienes el panel de control ejecutivo activo.",
                reply_markup=SupervisorKeyboards.obtener_menu_principal(),
                parse_mode="Markdown"
            )
            return ConversationHandler.END
        
        
        estado = usr.get("estado", "").upper()
        
        if estado == "AUTORIZADO":
            
            # Si ya está autorizado, mostrar su menú de vendedor
            await update.message.reply_text(
                f"👋 ¡Hola de nuevo, **{usr['nombre']}**! (Ruta {usr['ruta']})\n\n"
                f"Selecciona una opción del menú para comenzar.",
                reply_markup=BotKeyboards.obtener_teclado_vendedor(),
                parse_mode="Markdown"
            )
            return ConversationHandler.END
            
        elif estado == "PENDIENTE":
            await update.message.reply_text(
                f"⏳ Tu solicitud para la **Ruta {usr['ruta']}** está **PENDIENTE DE APROBACIÓN**.\n\n"
                f"El supervisor se encuentra revisando tu acceso. Te notificaremos por aquí cuando sea autorizada.",
                parse_mode="Markdown"
            )
            return ConversationHandler.END

    # 2. Si no existe, arrancar el flujo de registro
    teclado_rutas = BotKeyboards.obtener_teclado_rutas(conector)
    
    await update.message.reply_text(
        "🛢️ **¡BIENVENIDO AL BOT DE DISULUBINCA!**\n\n"
        "Para configurar tu perfil de vendedor, por favor **selecciona tu número de Ruta**:",
        reply_markup=teclado_rutas,
        parse_mode="Markdown"
    )
    return ESTADO_REGISTRO_RUTA

async def registro_ruta_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Captura y valida la ruta seleccionada."""
    texto = update.message.text
    
    # Extraer el número de ruta
    coincidencia = re.search(r'\d+', texto)
    num_ruta = int(coincidencia.group()) if coincidencia else None

    if not num_ruta or num_ruta not in RUTAS_VALIDAS:
        await update.message.reply_text(
            "⚠️ **Ruta no válida.** Por favor selecciona una de las rutas disponibles en los botones inferiores:",
            reply_markup=BotKeyboards.obtener_teclado_rutas(conector),
            parse_mode="Markdown"
        )
        return ESTADO_REGISTRO_RUTA

    context.user_data["registro_ruta"] = num_ruta
    
    await update.message.reply_text(
        f"✅ Ruta **R-{num_ruta}** seleccionada.\n\n"
        f"Ahora escribe tu **Nombre y Apellido Real** (ejemplo: *Juan Perez*):",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )
    return ESTADO_REGISTRO_NOMBRE

async def registro_nombre_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Captura, valida y sanitiza el nombre real del vendedor."""
    texto_raw = update.message.text
    telegram_id = update.effective_user.id

    if not validar_nombre_real(texto_raw):
        await update.message.reply_text(
            "⚠️ Por favor ingresa un **nombre y apellido válido**.",
            parse_mode="Markdown"
        )
        return ESTADO_REGISTRO_NOMBRE

    nombre_vendedor = formatear_nombre_vendedor(texto_raw)
    ruta_numero = context.user_data.get("registro_ruta")

    # Guardar solicitud en BD
    exito = usuarios_repo.registrar_o_reclamar_ruta(
        telegram_id=telegram_id,
        nombre_telegram=nombre_vendedor,
        ruta=ruta_numero
    )

    if exito:
        await update.message.reply_text(
            f"✅ **Solicitud enviada con éxito.**\n\n"
            f"👤 **Vendedor:** {nombre_vendedor}\n"
            f"📍 **Ruta:** {ruta_numero}\n\n"
            f"Espere a que el Supervisor apruebe su cuenta para comenzar a reportar.",
            parse_mode="Markdown"
        )
        
        # # 🔔 DISPARAR ALERTA PUSH A LOS SUPERVISORES
        # supervisores = usuarios_repo.obtener_telegram_ids_supervisores()
        # if supervisores:
        #     datos_usr = {
        #         "telegram_id": telegram_id,
        #         "nombre": nombre_vendedor,
        #         "ruta": ruta_numero
        #     }
        #     await NotificationService.notificar_nuevo_registro_a_supervisores(
        #         bot=context.bot,
        #         supervisores_telegram_ids=supervisores,
        #         usuario_data=datos_usr
        #     )
    else:
        await update.message.reply_text(
            "⚠️ Ocurrió un error o ya tienes una solicitud en proceso. Intenta de nuevo más tarde."
        )

    context.user_data.clear()
    return ConversationHandler.END

# Máquina de estados exportable
auth_conversacion_handler = ConversationHandler(
    entry_points=[CommandHandler("start", iniciar_registro_flow)],
    states={
        ESTADO_REGISTRO_RUTA: [MessageHandler(filters.TEXT & ~filters.COMMAND, registro_ruta_handler)],
        ESTADO_REGISTRO_NOMBRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, registro_nombre_handler)]
    },
    fallbacks=[]
)