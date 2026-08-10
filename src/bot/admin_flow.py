from datetime import datetime
import re

from telegram import ReplyKeyboardRemove, Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters
)

from bot.keyboards import SupervisorKeyboards, BotKeyboards
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

ESTADO_MONITOREO_VENDEDOR ,ESTADO_CARGA_MASIVA,ESTADO_SI_NO,ESTADO_REPORTE_RAFAGA,ESTADO_CONFIRMACION_REPORTE_SUP= range(20, 25)
# ========================================================
# 🏠 NAVEGACIÓN Y MENÚS PRINCIPALES
# ========================================================

async def iniciar_menu_personal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Despliega el submenú de Gestión de Personal para el Supervisor.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END

    mensaje_personal = (
        "👥 **MÓDULO DE GESTIÓN DE PERSONAL**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Bienvenido al panel de control de equipo de ventas. Desde aquí puedes "
        "administrar el acceso y verificar la actividad de tu fuerza de ventas.\n\n"
        "📌 **Opciones Disponibles:**\n"
        "• 📩 **Ver Solicitudes:** Revisa y aprueba solicitudes de nuevos vendedores.\n"
        "• 📊 **Estatus Vendedores:** Consulta quién ha enviado su reporte hoy.\n"
        "• 📋 **Lista Activos:** Directorio de rutas y personal autorizados.\n\n"
        "👇 *Selecciona una opción del menú inferior para continuar:*"
    )

    await update.message.reply_text(
        mensaje_personal,
        reply_markup=SupervisorKeyboards.obtener_sub_personal(),
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def iniciar_menu_principal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Regresa al menú principal del Supervisor.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos para acceder a este menú.")
        return ConversationHandler.END

    await update.message.reply_text(
        "👑 **Panel Principal de Control - Supervisor**\n\n"
        "Selecciona un submódulo para trabajar:",
        reply_markup=SupervisorKeyboards.obtener_menu_principal(),
        parse_mode="Markdown"
    )
    return ConversationHandler.END



async def iniciar_menu_coutas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Despliega el submenú de Gestión de Cuotas para el Supervisor.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END

    mensaje_cuotas = (
        "🎯 **MÓDULO DE GESTIÓN DE CUOTAS**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Desde este panel puedes administrar las cuotas de ventas y cobranza "
        "para cada ruta, ya sea de forma masiva o individual.\n\n"
        "📌 **Opciones Disponibles:**\n"
        "• 🚀 **Carga Masiva de Cuotas:** Actualiza todas las rutas desde un archivo Excel.\n"
        "• ✏️ **Editar Cuota por Ruta:** Ajusta la cuota de una ruta específica.\n"
        "• 🔄 **Sincronizar Excel automáticamente:** Configura la sincronización automática de cuotas.\n\n"
        "👇 *Selecciona una opción del menú inferior para continuar:*"
    )

    await update.message.reply_text(
        mensaje_cuotas,
        reply_markup=SupervisorKeyboards.obtener_sub_cuotas(),
        parse_mode="Markdown"
    )
    return ConversationHandler.END
# ========================================================
# ⚙️ FUNCIONALIDADES DEL SUBMENÚ PERSONAL
# ========================================================

async def ver_solicitudes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    📩 Acciones para 'Ver Solicitudes'
    Muestra la lista de usuarios en estado PENDIENTE con sus botones Inline de aprobación.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END

    pendientes = usuarios_repo.listar_vendedores_pendientes()

    if not pendientes:
        await update.message.reply_text(
            "✅ **SIN SOLICITUDES PENDIENTES**\n\n"
            "No hay nuevos vendedores esperando aprobación en este momento.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"📩 **SOLICITUDES DE ACCESO PENDIENTES ({len(pendientes)})**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode="Markdown"
    )

    # Imprimir un mensaje individual por cada solicitud pendiente con su InlineKeyboard
    for usr in pendientes:

        nombre = usr[1]
        
        
        nombre = nombre if nombre else "Sin Nombre"
        ruta_id = usr[0]
        ruta = ruta_id if ruta_id else "S/R"
        telegram_id = usr[2] if len(usr) > 2 else "Sin ID"


        texto_usr = (
            f"👤 **Vendedor:** {nombre}\n"
            f"🚚 **Ruta Solicitada:** Ruta {ruta}"
        )

        teclado_inline = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Aprobar", callback_data=f"aprobar_usr:{telegram_id}:{ruta}"),
                InlineKeyboardButton("❌ Rechazar", callback_data=f"rechazar_usr:{telegram_id}:{ruta}")
            ]
        ])

        await update.message.reply_text(
            texto_usr,
            reply_markup=teclado_inline,
            parse_mode="Markdown"
        )

    return ConversationHandler.END


async def estatus_vendedores_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    📊 Acciones para 'Estatus Vendedores'
    Muestra la sabana diaria de cumplimiento de cargas de hoy por cada ruta activa.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END

    hoy_str = datetime.now().strftime("%Y-%m-%d")
    
    # Traer estatus general de todas las rutas activas
    estatus_rutas = reportes_repo.obtener_estatus_cargas_hoy_todas_rutas(hoy_str)

    if not estatus_rutas:
        await update.message.reply_text(
            "⚠️ No hay vendedores o rutas activas registradas en el sistema.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    txt = f"📊 **ESTATUS DE CARGAS DE HOY ({hoy_str})**\n"
    txt += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    completados = 0
    total_rutas = len(estatus_rutas)

    for item in estatus_rutas:
        r_id = item["ruta_id"]
        nombre = item.get("nombre_vendedor", "Sin Asignar")
        m_ok = "✅" if item.get("matutino") else "🔴"
        n_ok = "✅" if item.get("nocturno") else "🔴"
        c_ok = "✅" if item.get("cobranza") else "🔴"

        if item.get("matutino") and item.get("nocturno"):
            completados += 1

        txt += f"🚚 **Ruta {r_id}** ({nombre})\n"
        txt += f"   • Plan Matutino: {m_ok}\n"
        txt += f"   • Cierre Nocturno: {n_ok}\n"
        txt += f"   • Cobranza/Caja: {c_ok}\n\n"

    txt += f"📈 **Resumen del día:** {completados}/{total_rutas} rutas completadas al 100%."

    await update.message.reply_text(txt, parse_mode="Markdown")
    return ConversationHandler.END


async def lista_activos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    📋 Acciones para 'Lista Activos'
    Muestra el directorio completo de vendedores autorizados en Disulubinca.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END

    activos = usuarios_repo.listar_vendedores_autorizados()

    if not activos:
        await update.message.reply_text(
            "📋 **DIRECTORIO DE PERSONAL**\n\n"
            "No hay vendedores autorizados activos en el sistema actualmente.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    txt = f"📋 **DIRECTORIO DE PERSONAL AUTORIZADO ({len(activos)})**\n"
    txt += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    for ruta, nombre, uid in activos:
        # Manejo seguro si ruta llega como None o vacía desde la BD
        ruta_str = f"Ruta {ruta}" if ruta is not None else "S/R"
        
        txt += f"🚚 **{ruta_str}** | {nombre} (`{uid}`)\n"

    txt += "\n💡 *Para desautorizar o cambiar la ruta a un vendedor, utiliza el panel individual.*"

    await update.message.reply_text(txt, parse_mode="Markdown")
    return ConversationHandler.END

# ========================================================
# 📊 NAVEGACIÓN Y FUNCIONALIDADES DE MONITOREO Y PROGRESO
# ========================================================

async def iniciar_menu_monitoreo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Despliega el submenú de Monitoreo y Avance de Ventas/Cobranzas.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END

    mensaje_monitoreo = (
        "📊 **MÓDULO DE MONITOREO Y RENDIMIENTO**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Consulta en tiempo real el comportamiento comercial y financiero de Disulubinca:\n\n"
        "📌 **Opciones Disponibles:**\n"
        "• 📈 **Avance Mes:** Acumulado mensual de ventas (UDVD) y cobranza vs Metas.\n"
        "• 📋 **Estatus Hoy:** Cumplimiento de reportes diarios por ruta.\n"
        "• 💰 **Cuadre Cobranza:** Desglose total de caja de hoy (Efectivo, Zelle y Bs).\n\n"
        "👇 *Selecciona una opción del menú para consultar:*"
    )

    await update.message.reply_text(
        mensaje_monitoreo,
        reply_markup=SupervisorKeyboards.obtener_sub_monitoreo(),
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def iniciar_menu_reportes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Despliega el submenú de Reportes y Cuotas para el Supervisor.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END

    mensaje_reportes = (
        "📊 **MÓDULO DE REPORTES Y CUOTAS**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Desde este panel puedes consultar y administrar las cuotas de ventas y cobranza "
        "para cada ruta, ya sea de forma masiva o individual.\n\n"
        "📌 **Opciones Disponibles:**\n"
        "• ✏️ **Registrar o Editar Cuotas:** Actualiza las cuotas de ventas y cobranza.\n"
        "• 📊 **Ver Cuotas de Vendedores:** Consulta las cuotas asignadas a cada ruta.\n\n"
        "👇 *Selecciona una opción del menú para continuar:*"
    )

    await update.message.reply_text(
        mensaje_reportes,
        reply_markup=SupervisorKeyboards.obtener_sub_ingestion(),
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def avance_mes_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    📈 Acciones para 'Avance Mes'
    Muestra el resumen ejecutivo consolidado del mes actual.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END

    mes_str = datetime.now().strftime("%Y-%m")
    
    # Traer métricas del dashboard general (todas las rutas sumadas)
    d = reportes_repo.obtener_resumen_dashboard_global(mes_str)

    if not d:
        await update.message.reply_text("⚠️ No se encontraron registros para el mes en curso.")
        return ConversationHandler.END

    # Generación de barras visuales
    p_udvd = d.get('porcentaje_udvd', 0.0)
    p_cxc = d.get('porcentaje_cxc', 0.0)
    
    b_udvd = f"[{'█' * int(max(0, min(100, p_udvd)) / 10)}{'░' * (10 - int(max(0, min(100, p_udvd)) / 10))}]"
    b_cxc = f"[{'█' * int(max(0, min(100, p_cxc)) / 10)}{'░' * (10 - int(max(0, min(100, p_cxc)) / 10))}]"

    txt = f"📈 **RESUMEN CONSOLIDADO DE VENTAS ({mes_str})**\n"
    txt += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    txt += f"📦 **VENTAS TOTALES (UDVD):**\n"
    txt += f"• Meta Mes: {d.get('cuota_udvd', 0):,.0f} UDVD\n"
    txt += f"• Logrado: {d.get('acumulado_udvd', 0):,.0f} UDVD\n"
    txt += f"• Progreso: `{b_udvd} {p_udvd:.1f}%`\n"
    txt += f"• Falta: {d.get('falta_udvd', 0):,.0f} UDVD\n\n"

    txt += f"💰 **COBRANZA TOTAL ($):**\n"
    txt += f"• Meta Mes: ${d.get('cuota_cxc', 0.0):,.2f}\n"
    txt += f"• Logrado: ${d.get('acumulado_cxc', 0.0):,.2f}\n"
    txt += f"• Progreso: `{b_cxc} {p_cxc:.1f}%`\n"
    txt += f"• Falta: ${d.get('falta_cxc', 0.0):,.2f}\n"

    await update.message.reply_text(txt, parse_mode="Markdown")
    return ConversationHandler.END


async def avance_mes_supervisor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    📊 Acciones para 'Avance por Supervisor'
    Muestra el resumen ejecutivo consolidado del mes actual filtrado por supervisor.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END

    mes_str = datetime.now().strftime("%Y-%m")
    
    # Traer métricas del dashboard filtradas por supervisor
    d = reportes_repo.obtener_resumen_dashboard_supervisor(mes_str)

    if not d:
        await update.message.reply_text("⚠️ No se encontraron registros para el mes en curso.")
        return ConversationHandler.END

    # Generación de barras visuales
    p_udvd = d.get('porcentaje_udvd', 0.0)
    p_cxc = d.get('porcentaje_cxc', 0.0)
    
    b_udvd = f"[{'█' * int(max(0, min(100, p_udvd)) / 10)}{'░' * (10 - int(max(0, min(100, p_udvd)) / 10))}]"
    b_cxc = f"[{'█' * int(max(0, min(100, p_cxc)) / 10)}{'░' * (10 - int(max(0, min(100, p_cxc)) / 10))}]"

    txt = f"📊 **RESUMEN POR SUPERVISOR ({mes_str})**\n"
    txt += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    txt += f"📦 **VENTAS TOTALES (UDVD):**\n"
    txt += f"• Meta Mes: {d.get('cuota_udvd', 0):,.0f} UDVD\n"
    txt += f"• Logrado: {d.get('acumulado_udvd', 0):,.0f} UDVD\n"
    txt += f"• Progreso: `{b_udvd} {p_udvd:.1f}%`\n"
    txt += f"• Falta: {d.get('falta_udvd', 0):,.0f} UDVD\n\n"

    await update.message.reply_text(txt, parse_mode="Markdown")
    return ConversationHandler.END



async def seleccionar_avance_ruta_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    📊 Acciones para 'Avance por Ruta'
    Muestra el resumen ejecutivo consolidado del mes actual filtrado por ruta.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END

    # Obtener teclado dinámico con rutas activas
    teclado_rutas = BotKeyboards.obtener_teclado_rutas(conector)

    await update.message.reply_text(
        "🚚 **SELECCIONA UNA RUTA PARA VER SU AVANCE**\n\n"
        "Elige la ruta que deseas consultar:",
        reply_markup=teclado_rutas,
        parse_mode="Markdown"
    )
    return ESTADO_MONITOREO_VENDEDOR

async def avence_por_ruta_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    📊 Acciones para 'Avance por Ruta'
    Muestra el resumen ejecutivo consolidado del mes actual filtrado por ruta.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END

    texto = update.message.text
    
    # Extraer el número de ruta
    coincidencia = re.search(r'\d+', texto)
    num_ruta = int(coincidencia.group()) if coincidencia else None

    if num_ruta is None:
        await update.message.reply_text("⚠️ No se pudo identificar la ruta seleccionada. Por favor, inténtalo de nuevo.")
        return ESTADO_MONITOREO_VENDEDOR

    mes_str = datetime.now().strftime("%Y-%m")
    
    # Traer métricas del dashboard filtradas por ruta
    txt = orquestador.consultar_dashboard_ruta(num_ruta,mes_str)

    # if not d:
    #     await update.message.reply_text(f"⚠️ No se encontraron registros para la Ruta {num_ruta} en el mes en curso.")
    #     return ESTADO_MONITOREO_VENDEDOR

    # # Generación de barras visuales
    # p_udvd = d.get('porcentaje_udvd', 0.0)
    # p_cxc = d.get('porcentaje_cxc', 0.0)
    
    # b_udvd = f"[{'█' * int(max(0, min(100, p_udvd)) / 10)}{'░' * (10 - int(max(0, min(100, p_udvd)) / 10))}]"
    # b_cxc = f"[{'█' * int(max(0, min(100, p_cxc)) / 10)}{'░' * (10 - int(max(0, min(100, p_cxc)) / 10))}]"

    # txt = f"📊 **RESUMEN POR RUTA {num_ruta} ({mes_str})**\n"
    # txt += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"

    # txt += f"📦 **VENTAS TOTALES (UDVD):**\n"
    # txt += f"• Meta Mes: {d.get('cuota_udvd', 0):,.0f} UDVD\n"
    # txt += f"• Logrado: {d.get('acumulado_udvd', 0):,.0f} UDVD\n"
    # txt += f"• Progreso: `{b_udvd} {p_udvd:.1f}%`\n"
    # txt += f"• Falta: {d.get('falta_udvd', 0):,.0f} UDVD\n\n"
    
    # txt += f"💰 **COBRANZA TOTAL ($):**\n"
    # txt += f"• Meta Mes: ${d.get('cuota_cxc', 0.0):,.2f}\n"
    # txt += f"• Logrado: ${d.get('acumulado_cxc', 0.0):,.2f}\n"
    # txt += f"• Progreso: `{b_cxc} {p_cxc:.1f}%`\n"
    # txt += f"• Falta: ${d.get('falta_cxc', 0.0):,.2f}\n\n"

    # txt += f"📊 **RESUMEN GENERAL**\n"
    # txt += f"• Ruta: {num_ruta}\n"
    # txt += f"• Mes: {mes_str}\n\n"

  

    await update.message.reply_text(txt, reply_markup=SupervisorKeyboards.obtener_volver_menu(),parse_mode="Markdown")
    return ConversationHandler.END
async def obtener_estatus_hoy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    📋 Acciones para 'Estatus Hoy'
    Muestra el estatus de reportes diarios de hoy por cada ruta activa.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END

    hoy_str = datetime.now().strftime("%Y-%m-%d")
    
    # Traer estatus general de todas las rutas activas
    txt = orquestador.consultar_semaforo_hoy(hoy_str)

 

    await update.message.reply_text(txt, reply_markup=SupervisorKeyboards.obtener_volver_menu(),parse_mode="Markdown")
    return ConversationHandler.END

async def pedir_carga_masiva_cuotas_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🚀 Acciones para 'Carga Masiva de Cuotas'
    Permite al supervisor subir un archivo Excel con las cuotas de todas las rutas.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END

    await update.message.reply_text(
        "🚀 **Registra o edita las cuotas**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Por favor, escribe en un solo mensaje las difenretes cuotas de el mes que contiene las cuotas actualizadas para todas las rutas.\n\n",

        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return ESTADO_CARGA_MASIVA

async def procesar_carga_masiva_cuotas_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Procesa la carga masiva de cuotas desde un mensaje de texto.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END

    cuotas_texto = update.message.text
    resultado_ia = parser_ia.parsear_cuotas(cuotas_texto)
    mes_str = datetime.now().strftime("%Y-%m-%d")
    print(f"Resultado del parser IA: {resultado_ia}")  # Debugging line
    # Validar y procesar el texto recibido
    
    if resultado_ia is None or "error" in resultado_ia:
        await update.message.reply_text(
            "⚠️ **Parece que Hubo un error en la interpretación de las cuotas.**\n\n"
            "Por favor, espare unos segundo y prueba mas tarde.",
            parse_mode="Markdown"
        )
        return ESTADO_CARGA_MASIVA
    cuotas_dicc = resultado_ia.get("lote_cuotas", resultado_ia)
    resultado = orquestador.establecer_cuotas_mensuales(fecha_str=mes_str,lote_cuotas=cuotas_dicc,usuarios_repo=usuarios_repo)
    exito, mensaje = resultado
    if exito:
        await update.message.reply_text(
            f"✅ **Carga Masiva Exitosa**\n\n"
            f"Se han actualizado las cuotas.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ **Error en la Carga Masiva**\n\n"
            f"{mensaje}",
            parse_mode="Markdown"
        )

    return ConversationHandler.END


async def cuotas_todos_vendedores_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    ✏️ Acciones para 'Editar Cuota por Ruta'
    Permite al supervisor editar la cuota de un vendedor específico.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END
    
    mes_str = datetime.now().strftime("%Y-%m")
    txt = orquestador.consultar_cuotas_mes(mes_str)
    await update.message.reply_text(txt, reply_markup=SupervisorKeyboards.obtener_volver_menu(),parse_mode="HTML")

    return ConversationHandler.END


# async def cuadre_cobranza_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     """
#     💰 Acciones para 'Cuadre Cobranza'
#     Muestra la sumatoria exacta recaudada el día de hoy por método de pago.
#     """
#     telegram_id = update.effective_user.id
#     if not usuarios_repo.es_administrador(telegram_id):
#         await update.message.reply_text("❌ No tienes permisos de administrador.")
#         return ConversationHandler.END

#     hoy_str = datetime.now().strftime("%Y-%m-%d")
    
#     # Traer el consolidado de caja de hoy
#     caja = reportes_repo.obtener_cuadre_caja_diario(hoy_str)

#     efectivo = caja.get("efectivo_usd", 0.0)
#     zelle = caja.get("zelle_usd", 0.0)
#     bs = caja.get("bs_cambiados_usd", 0.0)
#     total = efectivo + zelle + bs

#     txt = f"💰 **CUADRE DIARIO DE COBRANZA ({hoy_str})**\n"
#     txt += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
#     txt += f"💵 **Efectivo ($):** ${efectivo:,.2f}\n"
#     txt += f"📲 **Zelle / Transf ($):** ${zelle:,.2f}\n"
#     txt += f"🇻🇪 **Bolívares (USD):** ${bs:,.2f}\n"
#     txt += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
#     txt += f"💎 **TOTAL RECAUDADO HOY:** `${total:,.2f}`\n\n"
#     txt += f"📊 *Rutas reportadas:* {caja.get('rutas_reportadas', 0)} rutas."

#     await update.message.reply_text(txt, parse_mode="Markdown")
#     return ConversationHandler.END
# ========================================================
# 🤖 HANDLER Y REGISTRO DE EVENTOS
# ========================================================

async def iniciar_reporte_rafaga_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Inicia el proceso de generación de un reporte en ráfaga para un supervisor.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END

    await update.message.reply_text(
        "⚡ **GENERACIÓN DE REPORTE EN RÁFAGA**\n\n"
        "Ingrese el reporte con lujo de detalles para evitar errores de interpretación. El sistema procesará la información y generará un reporte completo."
        "• Si está reportando una fecha distinta o ajuste, asegúrese de **especificar la fecha** explícitamente en el texto enviado.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    return ESTADO_REPORTE_RAFAGA



async def procesar_reporte_rafaga_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Procesa el reporte en ráfaga enviado por el supervisor.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END

    reporte_texto = update.message.text
    
    await update.message.reply_text("⏳ *DislubinBot esta procesando reporte ... Por favor espera.*", parse_mode="Markdown")
    
    resultado_ia = parser_ia.parsear_texto_libre(reporte_texto)
    


    # Validar y procesar el texto recibido
    if not resultado_ia or "error" in resultado_ia:
        await update.message.reply_text(
            "⚠️ **No pude interpretar los datos del reporte.**\n\n"
            "Asegúrate de copiar el reporte completo o envía `/cancelar` para reintentar.",
            reply_markup=SupervisorKeyboards.obtener_volver_menu(),
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    context.user_data["payload_ia_sup"] = resultado_ia
    tipo_intencion = str(resultado_ia.get("tipo_intencion", "")).upper()
    
    fecha_eval = resultado_ia.get("fecha_mencionada") or datetime.now().strftime("%Y-%m-%d")
    context.user_data["fecha_evaluar_sup"] = fecha_eval


    es_matutino = "PLAN_MATUTINO" in tipo_intencion
    es_solo_cobranza = "COBRANZA" in tipo_intencion
    ruta_id_ia = resultado_ia.get('ruta')
    
    context.user_data["es_matutino_sup"] = es_matutino
    context.user_data["es_solo_cobranza_sup"] = es_solo_cobranza
    context.user_data["ruta_id_sup"]=ruta_id_ia
    # 📋 Previsualización según la modalidad
    if es_matutino:
        resumen_txt = (
            f"📋 **PREVISUALIZACIÓN - PLAN MATUTINO**\n"
            f"📍 **Ruta:** {ruta_id_ia} | 📅 **Fecha:** {fecha_eval}\n\n"
            f"📦 **Meta UDVD:** {resultado_ia.get('meta_udvd', 0)} UDVD\n"
            f"💵 **Meta Cobranza:** ${float(resultado_ia.get('meta_cxc', 0.0)):,.2f}\n"
            f"🎯 **Meta Visitas:** {resultado_ia.get('meta_activaciones', 0)}\n"
        )
    elif es_solo_cobranza:
        resumen_txt = (
            f"📋 **PREVISUALIZACIÓN - SOLO COBRANZA Y CAJA**\n"
            f"📍 **Ruta:** {ruta_id_ia} | 📅 **Fecha:** {fecha_eval}\n\n"
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
            f"📍 **Ruta:** {ruta_id_ia} | 📅 **Fecha:** {fecha_eval}\n\n"
            f"📦 **Venta Real UDVD:** {resultado_ia.get('real_udvd', 0)} UDVD\n"
            f"💵 **Cobranza Real:** ${float(resultado_ia.get('real_cxc', 0.0)):,.2f}\n"
            f"🎯 **Visitas Logradas:** {resultado_ia.get('real_activaciones', 0)}\n\n"
            f"💰 **DESGLOSE DE CAJA:**\n"
            f"• Efectivo ($): ${float(resultado_ia.get('efectivo_usd', 0.0)):,.2f}\n"
            f"• Transferencia/Zelle ($): ${float(resultado_ia.get('zelle_usd', 0.0)):,.2f}\n"
            f"• Bolívares Cambiados ($): ${float(resultado_ia.get('bs_cambiados_usd', 0.0)):,.2f}\n"
            f"• Tasa BCV: {float(resultado_ia.get('tasa_bcv', 0.0))} Bs/$\n"
        )

    resumen_txt += "\n¿Los datos extraídos son correctos?"

    await update.message.reply_text(
        resumen_txt,
        reply_markup=BotKeyboards.obtener_teclado_confirmacion(),
        parse_mode="Markdown"
    )
    return ESTADO_CONFIRMACION_REPORTE_SUP


async def confirmacion_guardado_sup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Impacta en SQLite, Contacto Matutino y Reporte Diario de Cobranza.
    """
    decision = update.message.text
    ruta_id = context.user_data.get("ruta_id_sup")
    payload = context.user_data.get("payload_ia_sup", {})
    fecha_eval = context.user_data.get("fecha_evaluar_sup") or datetime.now().strftime("%Y-%m-%d")
    es_matutino = context.user_data.get("es_matutino_sup", False)

    if decision == BotKeyboards.CONFIRMAR or BotKeyboards.SI:
        await update.message.reply_text(
            "⏳ *Guardando en la base de datos local y sincronizando en Dropbox...*",
            parse_mode="Markdown"
        )

        exito = False
        if es_matutino:
            exito = orquestador.procesar_plan_matutino(
                ruta=ruta_id,
                meta_udvd=float(payload.get("meta_udvd", 0)),
                meta_cobranza=float(payload.get("meta_cxc", 0.0)),
                meta_activaciones=int(payload.get("meta_activaciones", 0)),
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
                fecha_str=fecha_eval
            )

        if exito:
            await update.message.reply_text(
                f"✅ **¡REPORTE REGISTRADO EXITOSAMENTE!**\n\n"
                f"📍 Ruta {ruta_id} | 📅 {fecha_eval}\n"
                f"Datos actualizados en SQLite y respaldados en la nube.",
                reply_markup=SupervisorKeyboards.obtener_volver_menu(),
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                "❌ **Error al intentar sincronizar con Dropbox.** Por favor reintenta.",
                reply_markup=SupervisorKeyboards.obtener_volver_menu(),
                parse_mode="Markdown"
            )

    else:
        await update.message.reply_text(
            "❌ **Operación Cancelada.** Se han descartado los datos.",
            reply_markup=SupervisorKeyboards.obtener_volver_menu(),
            parse_mode="Markdown"
        )

    context.user_data.clear()
    return ConversationHandler.END


async def pedir_confirmacion_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Solicita confirmación al usuario antes de realizar una acción crítica.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END

    await update.message.reply_text(
        "⚠️ **CONFIRMACIÓN REQUERIDA**\n\n"
        "¿Estás seguro de que deseas continuar con esta acción?\n\n"
        "Responde con 'Sí' para confirmar o 'No' para cancelar.",
        parse_mode="Markdown",
        reply_markup=BotKeyboards.obtener_teclado_confirmacion()
    )
    return ESTADO_SI_NO

async def sincronizar_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Acción para sincronizar el archivo Excel automáticamente.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.")
        return ConversationHandler.END
    fecha_str = datetime.now().strftime("%Y-%m-%d")
    # Lógica para sincronizar el archivo Excel
    exito = orquestador.ejecutar_sincronizacion_nocturna_excel(fecha_str)

    if exito:
        await update.message.reply_text(
            "✅ **Sincronización Exitosa**\n\n"
            "El archivo Excel ha sido sincronizado correctamente.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ **Error en la Sincronización**\n\n",
            parse_mode="Markdown"
        )

    return ConversationHandler.END


admin_conversacion_handler = ConversationHandler(
    entry_points=[
        # Submenú Personal
        MessageHandler(filters.Text([SupervisorKeyboards.PERSONAL, "👥 Personal"]), iniciar_menu_personal),
        MessageHandler(filters.Text([SupervisorKeyboards.VER_SOLICITUDES, "📩 Ver Solicitudes"]), ver_solicitudes_handler),
        MessageHandler(filters.Text([SupervisorKeyboards.ESTATUS_VENDEDORES, "📊 Estatus Vendedores"]), estatus_vendedores_handler),
        MessageHandler(filters.Text([SupervisorKeyboards.LISTA_ACTIVOS, "📋 Lista Activos"]), lista_activos_handler),
        
        # Submenú Monitoreo
        MessageHandler(filters.Text([SupervisorKeyboards.MONITOREO, "📊 Monitoreo"]), iniciar_menu_monitoreo),
        MessageHandler(filters.Text([SupervisorKeyboards.AVANCE_MES, "📈 Avance Mes"]), avance_mes_handler),
        MessageHandler(filters.Text([SupervisorKeyboards.AVANCE_MES_SUPERVISOR, "📊 Avance por Supervisor"]), avance_mes_supervisor_handler),
        MessageHandler(filters.Text([SupervisorKeyboards.ESTATUS_HOY, "📋 Estatus Hoy"]), obtener_estatus_hoy),
        MessageHandler(filters.Text([SupervisorKeyboards.AVANCE_POR_RUTA, "📊 Estatus Monitoreo"]), seleccionar_avance_ruta_handler),
        
        
        # submenú Cuotas
        MessageHandler(filters.Text([SupervisorKeyboards.CUOTAS, "🎯 Cuotas"]), iniciar_menu_coutas),
        MessageHandler(filters.Text([SupervisorKeyboards.CUOTA_MASIVA, "✏️ Registrar o Editar cuotas"]), pedir_carga_masiva_cuotas_handler),
        MessageHandler(filters.Text([SupervisorKeyboards.CUOTA_TODOS_VENDEDORES, "📊 Ver cuotas de vendedores"]), cuotas_todos_vendedores_handler),
        MessageHandler(filters.Text([SupervisorKeyboards.SINCRONIZACION, "🔄 Sincronizar Excel automáticamente"]), pedir_confirmacion_handler),

        
        MessageHandler(filters.Text([SupervisorKeyboards.INGESTION]), iniciar_menu_reportes),
        MessageHandler(filters.Text([SupervisorKeyboards.CARGA_INDIVIDUAL]), avance_mes_handler),
        MessageHandler(filters.Text([SupervisorKeyboards.CARGA_RAFAGA_SUP]), iniciar_reporte_rafaga_handler),
        # Reutiliza estatus_vendedores_handler
        # MessageHandler(filters.Text([SupervisorKeyboards.CUADRE_COBRANZA, "💰 Cuadre Cobranza"]), cuadre_cobranza_handler),

        # Volver al Menú Principal
        MessageHandler(filters.Text([SupervisorKeyboards.VOLVER_MENU, "🔙 Volver al Menú Principal", "⬅️ Volver"]), iniciar_menu_principal),
    ],
    states={
        ESTADO_MONITOREO_VENDEDOR: [
            MessageHandler(filters.Text([SupervisorKeyboards.VOLVER_MENU, "🔙 Volver al Menú Principal"]), iniciar_menu_principal),
            MessageHandler(filters.TEXT & ~filters.COMMAND, avence_por_ruta_handle)
        ],
        ESTADO_CARGA_MASIVA: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_carga_masiva_cuotas_handle)
        ],
        ESTADO_SI_NO: [
            MessageHandler(filters.Regex("^(Sí|si|SI|sí)$"), sincronizar_excel),
            MessageHandler(filters.Text([BotKeyboards.SI]), sincronizar_excel),
            MessageHandler(filters.Regex("^(No|no|NO)$"), iniciar_menu_coutas),
            MessageHandler(filters.Text([BotKeyboards.NO]), iniciar_menu_coutas)
        # Manejo de respuesta inesperada  
        ],
        ESTADO_REPORTE_RAFAGA: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_reporte_rafaga_handler)
        ],
        ESTADO_CONFIRMACION_REPORTE_SUP: [
            MessageHandler(filters.Text([BotKeyboards.CONFIRMAR, BotKeyboards.CANCELAR, BotKeyboards.NO, BotKeyboards.SI]), confirmacion_guardado_sup_handler)
        ]
    },
    fallbacks=[
        MessageHandler(filters.Text([SupervisorKeyboards.VOLVER_MENU, "🔙 Volver al Menú Principal"]), iniciar_menu_principal)
    ]
)