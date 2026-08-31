import os
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

(
    ESTADO_MONITOREO_VENDEDOR,
    ESTADO_CARGA_MASIVA,
    ESTADO_SI_NO,
    ESTADO_REPORTE_AUTOMATICO,
    ESTADO_REPORTE_MULTIPLE,
    ESTADO_CONFIRMACION_REPORTE_SUP,
    ESTADO_REPORTE_RUTA_SUP,
    ESTADO_SELECCIONAR_TIPO_REPORTE_SUP,
    ESTADO_PROCESAR_DATOS_REPORTE_SUP
) = range(20, 29)


CANTIDAD_VALORES_REQUERIDOS = 5


# ========================================================
# 🏠 NAVEGACIÓN Y MENÚS PRINCIPALES
# ========================================================




async def iniciar_menu_personal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Despliega el submenú de Gestión de Personal para el Supervisor.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
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
        await update.message.reply_text("❌ No tienes permisos para acceder a este menú.", reply_markup=BotKeyboards.obtener_teclado_salir())
        return ConversationHandler.END

    await update.message.reply_text(
        "👑 **Panel Principal de Control - Supervisor**\n\n"
        "Selecciona un submódulo para trabajar:",
        reply_markup=SupervisorKeyboards.obtener_menu_principal(),
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def salir_al_menu_supervisor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cierra el flujo activo del supervisor y vuelve al menú principal."""
    context.user_data.clear()
    await iniciar_menu_principal(update, context)
    return ConversationHandler.END


async def iniciar_menu_coutas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Despliega el submenú de Gestión de Cuotas para el Supervisor.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
        return ConversationHandler.END

    mensaje_cuotas = (
        "🎯 **MÓDULO DE GESTIÓN DE CUOTAS**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Desde este panel puedes administrar las cuotas de ventas y cobranza "
        "para cada ruta, ya sea de forma masiva o individual.\n\n"
        "📌 **Opciones Disponibles:**\n"
        "• 🚀 **Carga Masiva de Cuotas:** Actualiza todas las rutas desde un archivo Excel.\n"
        "• ✏️ **Editar Cuota por Ruta:** Ajusta la cuota de una ruta específica.\n"
        "• 🔄 **Sincronizar Excel automáticamente:** Configura la sincronización automática de cuotas.\n"
        "• 💾 **Hacer Backup de Base de Datos:** Guarda una copia actual de usuarios.db en Dropbox.\n\n"
        "👇 *Selecciona una opción del menú inferior para continuar:*"
    )

    await update.message.reply_text(
        mensaje_cuotas,
        reply_markup=SupervisorKeyboards.obtener_sub_cuotas(),
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def backup_db_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Crea un respaldo manual de la base local SQLite y la sube a Dropbox."""
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
        return ConversationHandler.END

    ruta_db = conector.db_path
    if not ruta_db or not os.path.exists(ruta_db):
        await update.message.reply_text(
            "⚠️ No hay una base de datos local disponible para respaldar.",
            reply_markup=SupervisorKeyboards.obtener_volver_menu(),
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    ok = dropbox_service.respaldar_bd_local(ruta_db)
    if ok:
        await update.message.reply_text(
            "✅ **Backup de base de datos completado**\n\n"
            "La copia de usuarios.db fue enviada a Dropbox correctamente.",
            reply_markup=SupervisorKeyboards.obtener_volver_menu(),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            "❌ **No pude hacer el backup**\n\n"
            "La base local existe, pero no se logró enviar la copia a Dropbox.",
            reply_markup=SupervisorKeyboards.obtener_volver_menu(),
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
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
        return ConversationHandler.END

    pendientes = usuarios_repo.listar_vendedores_pendientes()

    if not pendientes:
        await update.message.reply_text(
            "✅ **SIN SOLICITUDES PENDIENTES**\n\n"
            "No hay nuevos vendedores esperando aprobación en este momento.",
            reply_markup=SupervisorKeyboards.obtener_volver_menu(),
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"📩 **SOLICITUDES DE ACCESO PENDIENTES ({len(pendientes)})**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        reply_markup=SupervisorKeyboards.obtener_volver_menu(),
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
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
        return ConversationHandler.END

    hoy_str = datetime.now().strftime("%Y-%m-%d")
    
    # Traer estatus general de todas las rutas activas
    estatus_rutas = reportes_repo.obtener_estatus_cargas_hoy_todas_rutas(hoy_str)

    if not estatus_rutas:
        await update.message.reply_text(
            "⚠️ No hay vendedores o rutas activas registradas en el sistema.",
            reply_markup=SupervisorKeyboards.obtener_volver_menu(),
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

    await update.message.reply_text(txt, reply_markup=SupervisorKeyboards.obtener_volver_menu(), parse_mode="Markdown")
    return ConversationHandler.END


async def lista_activos_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    📋 Acciones para 'Lista Activos'
    Muestra el directorio completo de vendedores autorizados en Disulubinca.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
        return ConversationHandler.END

    activos = usuarios_repo.listar_vendedores_autorizados()

    if not activos:
        await update.message.reply_text(
            "📋 **DIRECTORIO DE PERSONAL**\n\n"
            "No hay vendedores autorizados activos en el sistema actualmente.",
            reply_markup=SupervisorKeyboards.obtener_volver_menu(),
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

    await update.message.reply_text(txt, reply_markup=SupervisorKeyboards.obtener_volver_menu(), parse_mode="Markdown")
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
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
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
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
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
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
        return ConversationHandler.END

    mes_str = datetime.now().strftime("%Y-%m")
    
    # Traer métricas del dashboard general (todas las rutas sumadas)
    d = reportes_repo.obtener_resumen_dashboard_global(mes_str)

    if not d:
        await update.message.reply_text("⚠️ No se encontraron registros para el mes en curso.", reply_markup=SupervisorKeyboards.obtener_volver_menu())
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

    await update.message.reply_text(txt, reply_markup=SupervisorKeyboards.obtener_volver_menu(), parse_mode="Markdown")
    return ConversationHandler.END


async def avance_mes_supervisor_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    📊 Acciones para 'Avance por Supervisor'
    Muestra el resumen ejecutivo consolidado del mes actual filtrado por supervisor.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
        return ConversationHandler.END

    mes_str = datetime.now().strftime("%Y-%m")
    
    # Traer métricas del dashboard filtradas por supervisor
    d = reportes_repo.obtener_resumen_dashboard_supervisor(mes_str)

    if not d:
        await update.message.reply_text("⚠️ No se encontraron registros para el mes en curso.", reply_markup=SupervisorKeyboards.obtener_volver_menu())
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
    
    txt += f"💰 **COBRANZA TOTAL ($):**\n"
    txt += f"• Meta Mes: {d.get('cuota_cxc', 0):,.0f} $\n"
    txt += f"• Logrado: {d.get('acumulado_cxc', 0):,.0f} $\n"
    txt += f"• Progreso: `{b_cxc} {p_cxc:.1f}%`\n"
    txt += f"• Falta: {d.get('falta_cxc', 0):,.0f} $\n\n"

    await update.message.reply_text(txt, reply_markup=SupervisorKeyboards.obtener_volver_menu(), parse_mode="Markdown")
    return ConversationHandler.END



async def seleccionar_avance_ruta_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    📊 Acciones para 'Avance por Ruta'
    Muestra el resumen ejecutivo consolidado del mes actual filtrado por ruta.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
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

async def seleccionar_reporte_ruta_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    📊 Acciones para 'Avance por Ruta'
    Muestra el resumen ejecutivo consolidado del mes actual filtrado por ruta.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
        return ConversationHandler.END

    # Obtener teclado dinámico con rutas activas
    teclado_rutas = BotKeyboards.obtener_teclado_rutas(conector)

    await update.message.reply_text(
        "🚚 **SELECCIONA UNA RUTA PARA CARGAR SU REPORTE**\n\n"
        "Elige la ruta que desea cargar:",
        reply_markup=teclado_rutas,
        parse_mode="Markdown"
    )
    return ESTADO_REPORTE_RUTA_SUP







async def avence_por_ruta_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    📊 Acciones para 'Avance por Ruta'
    Muestra el resumen ejecutivo consolidado del mes actual filtrado por ruta.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
        return ConversationHandler.END

    texto = update.message.text
    
    # Extraer el número de ruta
    coincidencia = re.search(r'\d+', texto)
    num_ruta = int(coincidencia.group()) if coincidencia else None

    if num_ruta is None:
        await update.message.reply_text(
            "⚠️ No se pudo identificar la ruta seleccionada. Por favor, inténtalo de nuevo.",
            reply_markup=SupervisorKeyboards.obtener_sub_monitoreo()
        )
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
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
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
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
        return ConversationHandler.END

    await update.message.reply_text(
        "🚀 **Registra o edita las cuotas**\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Por favor, escribe en un solo mensaje las difenretes cuotas de el mes que contiene las cuotas actualizadas para todas las rutas.\n\n",

        parse_mode="Markdown",
        reply_markup=BotKeyboards.obtener_teclado_salir()
    )
    return ESTADO_CARGA_MASIVA

async def procesar_carga_masiva_cuotas_handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Procesa la carga masiva de cuotas desde un mensaje de texto.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
        return ConversationHandler.END

    cuotas_texto = update.message.text
    resultado_ia = parser_ia.parsear_cuotas(cuotas_texto)

    # 1. Validar si la respuesta de la IA fue exitosa y trae cuotas
    if not resultado_ia or not resultado_ia.get("exito", False) or not resultado_ia.get("lote_cuotas"):
        error_detalle = resultado_ia.get("error", "No se detectaron cuotas válidas") if resultado_ia else "Sin respuesta del servidor"

        # Manejo diferido según la causa del error
        if "API Key" in error_detalle or "genai.Client" in error_detalle:
            mensaje_usuario = (
                "🚨 **Servicio de IA no disponible.**\n"
                "Hay un problema de configuración con el servicio Gemini. Contacta al soporte técnico."
            )
        elif "JSON" in error_detalle:
            mensaje_usuario = (
                "⚠️ **No pude interpretar las cuotas ingresadas.**\n\n"
                "Asegúrate de indicar las rutas y metas claramente (Ejemplo: `r10: 2000 udvd, 5000 cxc, 10 visitas`).\n\n"
                "💡 *Ingresa el texto nuevamente o envía `/cancelar` para salir.*"
            )
        else:
            mensaje_usuario = (
                "⚠️ **No se encontraron cuotas para procesar.**\n\n"
                "Verifica que las rutas y montos estén escritos correctamente e reintenta."
            )

        await update.message.reply_text(
            mensaje_usuario,
            parse_mode="Markdown",
            reply_markup=SupervisorKeyboards.obtener_teclado_reintento()
        )
        return ESTADO_CARGA_MASIVA
    mes_str = datetime.now().strftime("%Y-%m-%d")
    
    cuotas_dicc = resultado_ia.get("lote_cuotas", resultado_ia)
    resultado = orquestador.establecer_cuotas_mensuales(fecha_str=mes_str,lote_cuotas=cuotas_dicc,usuarios_repo=usuarios_repo)
    exito, mensaje = resultado
    if exito:
        await update.message.reply_text(
            f"✅ **Carga Masiva Exitosa**\n\n"
            f"Se han actualizado las cuotas.",
            reply_markup=SupervisorKeyboards.obtener_volver_menu(),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ **Error en la Carga Masiva**\n\n"
            f"{mensaje}",
            reply_markup=SupervisorKeyboards.obtener_volver_menu(),
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
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
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

async def iniciar_reporte_automatico_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Inicia el proceso de generación de un reporte en ráfaga para un supervisor.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
        return ConversationHandler.END

    html_solicitud_ia = """
    ⚡ <b>GENERACIÓN DE REPORTE CON IA</b>

    Ingrese el reporte con el mayor detalle posible para evitar errores de interpretación. El sistema procesará la información e impactará el registro de la jornada.

    ℹ️ <i>Nota: El sistema registrará los datos con la fecha actual por defecto. Si está reportando una fecha distinta o un ajuste, asegúrese de especificarla explícitamente en el texto enviado.<b>No se olvide de especifificar la ruta</b></i>
    """.strip()

    await update.message.reply_text(
        html_solicitud_ia,
        reply_markup=SupervisorKeyboards.obtener_teclado_reintento(),
        parse_mode="HTML"
    )
    return ESTADO_REPORTE_AUTOMATICO


def _guardar_reporte_desde_payload(payload: dict, fecha_eval: str, ruta_id: int | str) -> tuple[bool, str]:
    """Aplica el payload del reporte IA al sistema sin pedir confirmación adicional."""
    tipo_intencion = str(payload.get("tipo_intencion", "")).upper()
    es_matutino = "PLAN_MATUTINO" in tipo_intencion
    es_solo_cobranza = "COBRANZA" in tipo_intencion

    try:
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
            return exito, "Plan matutino"

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
        return exito, "Cierre nocturno" if not es_solo_cobranza else "Cobranza"
    except Exception as exc:
        return False, f"Error técnico: {exc}"


async def iniciar_reporte_multiple_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Activa un flujo de ingreso múltiple de reportes sin confirmaciones intermedias."""
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
        return ConversationHandler.END

    context.user_data["reporte_multiple_total"] = 0
    context.user_data["reporte_multiple_exitos"] = 0
    context.user_data["reporte_multiple_errores"] = 0
    context.user_data["reporte_multiple_detalles"] = []

    await update.message.reply_text(
        "📦 **MODO DE REPORTES MÚLTIPLES ACTIVADO**\n\n"
        "Envía los reportes uno tras otro. El bot los procesará secuencialmente sin pedir confirmación intermedia.\n\n"
        "🧭 Si quieres salir, usa el botón de volver al menú.\n"
        "⚠️ Se aplicará un límite técnico prudente por seguridad.",
        reply_markup=SupervisorKeyboards.obtener_volver_menu(),
        parse_mode="Markdown"
    )
    return ESTADO_REPORTE_MULTIPLE


async def procesar_reporte_multiple_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa un reporte del lote, mantiene el estado activo y si hay error sale al menú con información."""
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
        return ConversationHandler.END

    texto = update.message.text or ""
    if texto in (SupervisorKeyboards.VOLVER_MENU, BotKeyboards.SALIR_MENU, "⬅️ Volver al Menú Principal", "🏠 Volver al inicio"):
        total = context.user_data.get("reporte_multiple_total", 0)
        exitos = context.user_data.get("reporte_multiple_exitos", 0)
        errores = context.user_data.get("reporte_multiple_errores", 0)
        await update.message.reply_text(
            f"📦 **Lote terminado**\n\n"
            f"✅ Reportes exitosos: {exitos}\n"
            f"❌ Reportes fallidos: {errores}\n"
            f"📊 Total procesados: {total}",
            reply_markup=SupervisorKeyboards.obtener_volver_menu(),
            parse_mode="Markdown"
        )
        context.user_data.clear()
        return await iniciar_menu_principal(update, context)

    maximo_reportes = 20
    total_actual = context.user_data.get("reporte_multiple_total", 0)
    if total_actual >= maximo_reportes:
        await update.message.reply_text(
            "⚠️ **Se alcanzó el límite técnico del lote**\n\n"
            "Ya se procesó la máxima cantidad permitida. El flujo se cerró y puedes volver al menú principal.",
            reply_markup=SupervisorKeyboards.obtener_volver_menu(),
            parse_mode="Markdown"
        )
        context.user_data.clear()
        return await iniciar_menu_principal(update, context)

    numero_reporte = total_actual + 1
    await update.message.reply_text(
        f"⏳ Procesando reporte #{numero_reporte}...",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="Markdown"
    )

    resultado_ia = parser_ia.parsear_texto_libre(texto)
    if not resultado_ia or not resultado_ia.get("exito", False):
        detalle_error = resultado_ia.get("error", "No se recibió respuesta válida del analizador.") if resultado_ia else "Error desconocido"
        context.user_data["reporte_multiple_errores"] = context.user_data.get("reporte_multiple_errores", 0) + 1
        await update.message.reply_text(
            f"❌ **Error en reporte #{numero_reporte}**\n\n"
            f"{detalle_error}\n\n"
            "El lote se detuvo y se informó al administrador. Vuelve al menú para continuar.",
            reply_markup=SupervisorKeyboards.obtener_volver_menu(),
            parse_mode="Markdown"
        )
        context.user_data.clear()
        return await iniciar_menu_principal(update, context)

    ruta_id = resultado_ia.get("ruta")
    fecha_eval = resultado_ia.get("fecha_mencionada") or datetime.now().strftime("%Y-%m-%d")
    ok, detalle = _guardar_reporte_desde_payload(resultado_ia, fecha_eval, ruta_id)

    context.user_data["reporte_multiple_total"] = numero_reporte
    if ok:
        context.user_data["reporte_multiple_exitos"] = context.user_data.get("reporte_multiple_exitos", 0) + 1
        detalle_lote = context.user_data.get("reporte_multiple_detalles", [])
        detalle_lote.append({"ruta": ruta_id, "fecha": fecha_eval, "tipo": detalle})
        context.user_data["reporte_multiple_detalles"] = detalle_lote

        await update.message.reply_text(
            f"✅ **Reporte #{numero_reporte} guardado correctamente**\n\n"
            f"📍 Ruta: {ruta_id}\n"
            f"📅 Fecha: {fecha_eval}\n"
            f"🧾 Tipo: {detalle}\n\n"
            f"📦 Lote activo: {numero_reporte} reportes recibidos.",
            reply_markup=SupervisorKeyboards.obtener_volver_menu(),
            parse_mode="Markdown"
        )
        return ESTADO_REPORTE_MULTIPLE

    context.user_data["reporte_multiple_errores"] = context.user_data.get("reporte_multiple_errores", 0) + 1
    await update.message.reply_text(
        f"❌ **No se pudo guardar el reporte #{numero_reporte}**\n\n"
        f"📍 Ruta: {ruta_id}\n"
        f"🚨 Detalle: {detalle}\n\n"
        "El lote se detuvo para evitar procesar datos inconsistentes.",
        reply_markup=SupervisorKeyboards.obtener_volver_menu(),
        parse_mode="Markdown"
    )
    context.user_data.clear()
    return await iniciar_menu_principal(update, context)


async def procesar_reporte_automatico_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Procesa el reporte en automatico enviado por el supervisor.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
        return ConversationHandler.END

    reporte_texto = update.message.text
    
    await update.message.reply_text(
        "⏳ *DislubinBot esta procesando reporte ... Por favor espera.*",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove()
    )
    
    resultado_ia = parser_ia.parsear_texto_libre(reporte_texto)

    # 1. Validar si la llamada a la IA fue exitosa o devolvió error
    if not resultado_ia or not resultado_ia.get("exito", False):
        # Extraemos el mensaje de error técnico
        error_detalle = resultado_ia.get("error", "No se recibió respuesta válida del analizador.") if resultado_ia else "Error desconocido al procesar el texto."
        
        # Evaluamos qué tipo de falla ocurrió para dar mejor retroalimentación
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
            reply_markup=SupervisorKeyboards.obtener_teclado_reintento(),
            parse_mode="HTML"
        )
        return ESTADO_REPORTE_AUTOMATICO

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
            f"💰 **Meta Amigo:** ${float(resultado_ia.get('meta_amigo', 0.0)):,.2f}\n"
            f"🚗 **Meta Celta:** ${float(resultado_ia.get('meta_celta',0.0)):,.2f}\n"
            
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
            
            # f"💰 **DESGLOSE DE CAJA:**\n"
            # f"• Efectivo ($): ${float(resultado_ia.get('efectivo_usd', 0.0)):,.2f}\n"
            # f"• Transferencia/Zelle ($): ${float(resultado_ia.get('zelle_usd', 0.0)):,.2f}\n"
            # f"• Bolívares Cambiados ($): ${float(resultado_ia.get('bs_cambiados_usd', 0.0)):,.2f}\n"
            # f"• Tasa BCV: {float(resultado_ia.get('tasa_bcv', 0.0))} Bs/$\n"
            f"💰 **Meta Grupo Amigo:** ${float(resultado_ia.get('real_amigo', 0.0)):,.2f}\n"
            f"🚗 **Meta Celta:** ${float(resultado_ia.get('real_celta',0.0)):,.2f}\n"
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

    if decision in (BotKeyboards.CONFIRMAR, BotKeyboards.SI):
        await update.message.reply_text(
            "⏳ *Guardando en la base de datos local y sincronizando en Dropbox...*",
            parse_mode="Markdown",
            reply_markup=BotKeyboards.obtener_teclado_salir()
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
                reply_markup=SupervisorKeyboards.obtener_volver_repetir(),
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
    return ESTADO_CONFIRMACION_REPORTE_SUP


async def pedir_confirmacion_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Solicita confirmación al usuario antes de realizar una acción crítica.
    """
    telegram_id = update.effective_user.id
    if not usuarios_repo.es_administrador(telegram_id):
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
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
        await update.message.reply_text("❌ No tienes permisos de administrador.", reply_markup=BotKeyboards.obtener_teclado_salir())
        return ConversationHandler.END
    fecha_str = datetime.now().strftime("%Y-%m-%d")
    # Lógica para sincronizar el archivo Excel
    exito = orquestador.ejecutar_sincronizacion_nocturna_excel(fecha_str)

    if exito:
        await update.message.reply_text(
            "✅ **Sincronización Exitosa**\n\n"
            "El archivo Excel ha sido sincronizado correctamente.",
            reply_markup=SupervisorKeyboards.obtener_volver_menu(),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            f"❌ **Error en la Sincronización**\n\n",
            reply_markup=SupervisorKeyboards.obtener_volver_menu(),
            parse_mode="Markdown"
        )

    return ConversationHandler.END


def extraer_numeros_reporte(texto: str, cantidad_esperada: int = CANTIDAD_VALORES_REQUERIDOS) -> list[float] | None:
    """
    Parsea de forma segura una cadena de texto para extraer exactamente 'cantidad_esperada' de números.
    Maneja comas decimales, elimina símbolos de moneda y soporta múltiples delimitadores.
    """
    if not texto:
        return None

    # 1. Limpiar símbolos de moneda y texto ruidoso
    texto_limpio = re.sub(r'[\$]|USD|usd|Bs|bs|pts', '', texto).strip()

    # 2. Dividir prioritariamente por separadores explícitos (-, _, /, ;, pipe | o saltos de línea)
    # Si no existen delimitadores explícitos, se usa el espacio en blanco.
    if re.search(r'[-_/;|\n]', texto_limpio):
        partes = re.split(r'[-_/;|\n]+', texto_limpio)
    else:
        partes = texto_limpio.split()

    numeros = []
    for parte in partes:
        p = parte.strip()
        if not p:
            continue
        
        # Normalizar comas a puntos para decimales (ej: "150,50" -> "150.50")
        p = p.replace(',', '.')
        
        # Buscar patrón numérico válido (enteros o flotantes)
        coincidencia = re.search(r'^\d+(?:\.\d+)?$', p)
        if coincidencia:
            numeros.append(float(coincidencia.group()))

    # Verificar que la cantidad extraída sea exactamente la esperada
    if len(numeros) == cantidad_esperada:
        return numeros
    
    return None


async def seleccionar_tipo_reporte_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Paso 2: Guarda la ruta seleccionada y solicita el tipo de reporte.
    """
    texto_ruta = update.message.text

    if texto_ruta == SupervisorKeyboards.VOLVER_MENU:
        return await iniciar_menu_principal(update, context)

    # Extraer el ID entero de la ruta (ej: "Ruta 4" -> 4)
    coincidencia = re.search(r'\d+', texto_ruta)
    num_ruta = int(coincidencia.group()) if coincidencia else None

    if num_ruta is None:
        await update.message.reply_text(
            "⚠️ No se pudo identificar la ruta seleccionada. Inténtalo de nuevo.",
            reply_markup=BotKeyboards.obtener_teclado_salir()
        )
        return ESTADO_REPORTE_RUTA_SUP

    # Guardar la ruta en user_data
    context.user_data["ruta_id_manual"] = num_ruta

    await update.message.reply_text(
        f"🚚 **Ruta {num_ruta} seleccionada.**\n\n"
        "Elige el tipo de reporte que deseas ingresar:",
        reply_markup=SupervisorKeyboards.obtener_teclado_tipos_reporte(),
        parse_mode="Markdown"
    )
    return ESTADO_SELECCIONAR_TIPO_REPORTE_SUP


async def pedir_datos_reporte_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Paso 3: Guarda el tipo de reporte seleccionado y solicita los 3 números.
    """
    tipo_reporte = update.message.text

    if tipo_reporte == SupervisorKeyboards.VOLVER_MENU:
        return await iniciar_menu_principal(update, context)

    context.user_data["tipo_reporte_manual"] = tipo_reporte

    # Construir instrucciones personalizadas según el tipo de reporte
    if tipo_reporte == SupervisorKeyboards.TIPO_PLAN_DIA:
        instrucciones = (
            "📋 **PLAN DEL DÍA**\n\n"
            "Por favor, ingresa los **3 valores** planeados en el siguiente orden:\n"
            "1. UDVD planeadas\n"
            "2. CxC planeadas\n"
            "3. Visitas planeadas\n\n"
            "4. Unidades Grupo Amigo planeadas\n"
            "5. Unidades Celta planeadas\n"
            "💡 *Ejemplo:* `150 - 2500 - 12` o `150_2500_12`"
        )
    elif tipo_reporte == SupervisorKeyboards.TIPO_CIERRE_NOCHE:
        instrucciones = (
            "🌙 **CIERRE DE NOCHE**\n\n"
            "Por favor, ingresa los **3 valores** conseguidos en el siguiente orden:\n"
            "1. UDVD conseguidas\n"
            "2. CxC conseguidas\n"
            "3. Visitas conseguidas\n\n"
            "4. Unidades Grupo Amigo conseguidas\n"
            "5. Unidades Celta conseguidas\n"
            "💡 *Ejemplo:* `140 - 2300,50 - 10` o `140 / 2300.50 / 10`"
        )
    elif tipo_reporte == SupervisorKeyboards.TIPO_COBRANZA:
        instrucciones = (
            "💵 **REPORTE DE COBRANZA**\n\n"
            "Por favor, ingresa los **3 montos** recaudados en el siguiente orden:\n"
            "1. Efectivo ($)\n"
            "2. Zelle / Transferencia ($)\n"
            "3. Bolívares\n\n"
            "💡 *Ejemplo:* `$500 - $300.50 - 4500` o `500_300,50_4500`"
        )
    else:
        await update.message.reply_text(
            "⚠️ Tipo de reporte no válido. Por favor selecciona una opción del menú.",
            reply_markup=SupervisorKeyboards.obtener_teclado_tipos_reporte()
        )
        return ESTADO_SELECCIONAR_TIPO_REPORTE_SUP

    await update.message.reply_text(
        instrucciones,
        reply_markup=BotKeyboards.obtener_teclado_salir(),
        parse_mode="Markdown"
    )
    return ESTADO_PROCESAR_DATOS_REPORTE_SUP


async def procesar_datos_reporte_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Paso 4: Valida y procesa los datos ingresados por el usuario.
    """
    texto_ingresado = update.message.text
    exito_registro: bool = False
    # Si presiona reintentar desde el teclado de error
    if texto_ingresado == SupervisorKeyboards.REINTENTAR:
        # Re-invocar la solicitud del tipo de reporte actual
        return await pedir_datos_reporte_handler(update, context)

    if texto_ingresado == SupervisorKeyboards.VOLVER_MENU:
        return await iniciar_menu_principal(update, context)
    ruta_id = context.user_data.get("ruta_id_manual")
    tipo_reporte = context.user_data.get("tipo_reporte_manual")
    
    if tipo_reporte == SupervisorKeyboards.TIPO_COBRANZA:
        valores = extraer_numeros_reporte(texto_ingresado, cantidad_esperada=3)
        
        if valores is None:
            exito_registro = False
            await update.message.reply_text(
                f"❌ **Error en los datos ingresados.**\n\n"
                f"No pudimos identificar exactamente {CANTIDAD_VALORES_REQUERIDOS} números válidos.\n"
                "Asegúrate de separar los valores usando guiones (`-`), guiones bajos (`_`), comas o barras (`/`).",
                reply_markup=SupervisorKeyboards.obtener_teclado_reintento(),
                parse_mode="Markdown"
            )
            # Permanece en el mismo estado para capturar el botón de reintento o un nuevo texto
            return ESTADO_PROCESAR_DATOS_REPORTE_SUP

        val1,val2,val3 = valores
        if tipo_reporte == SupervisorKeyboards.TIPO_COBRANZA:
            exito_registro = orquestador.procesar_cierre_nocturno(ruta=ruta_id,real_udvd=0, real_cobranza=0, real_activaciones=0,efectivo=val1,zelle=val2,bs=val3,real_amigo=0,real_celta=0,tasa_bcv=0)
    else:

    # Intentar extraer los 3 números con la función segura
        valores = extraer_numeros_reporte(texto_ingresado, cantidad_esperada=CANTIDAD_VALORES_REQUERIDOS)

        # Booleano de estado de la operació
        if valores is None:
            exito_registro = False
            await update.message.reply_text(
                f"❌ **Error en los datos ingresados.**\n\n"
                f"No pudimos identificar exactamente {CANTIDAD_VALORES_REQUERIDOS} números válidos.\n"
                "Asegúrate de separar los valores usando guiones (`-`), guiones bajos (`_`), comas o barras (`/`).",
                reply_markup=SupervisorKeyboards.obtener_teclado_reintento(),
                parse_mode="Markdown"
            )
            # Permanece en el mismo estado para capturar el botón de reintento o un nuevo texto
            return ESTADO_PROCESAR_DATOS_REPORTE_SUP
        

        # --- ÉXITO EN EL PARSEO ---


        val1, val2, val3 ,val4,val5= valores

        if tipo_reporte == SupervisorKeyboards.TIPO_PLAN_DIA:
            exito_registro = orquestador.procesar_plan_matutino(ruta=ruta_id,meta_udvd=val1,meta_cobranza=val2,meta_activaciones=val3,meta_amigo=val4,meta_celta=val5)
        if tipo_reporte == SupervisorKeyboards.TIPO_CIERRE_NOCHE:
            exito_registro = orquestador.procesar_cierre_nocturno(ruta=ruta_id,real_udvd=val1, real_cobranza=val2, real_activaciones=val3,efectivo=0,zelle=0,bs=0,tasa_bcv=0,real_amigo=val4,real_celta=val5)

    if not exito_registro:
        await update.message.reply_text(
            f"❌ **Error en el procesamiento de los datos**\n\n"
            f"Ah ocurrido un error inesperado al procesar los datos.\n"
            "Vuelava a intentarlo o intente mas tarde, si vuelve a fallar comuniquese con el supervisor",
            reply_markup=SupervisorKeyboards.obtener_teclado_reintento(),
            parse_mode="Markdown"
        )
        # Permanece en el mismo estado para capturar el botón de reintento o un nuevo texto
        return ESTADO_PROCESAR_DATOS_REPORTE_SUP

    # Mensaje de confirmación al usuario
    await update.message.reply_text(
        f"✅ **DATOS PROCESADOS CORRECTAMENTE**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🚚 **Ruta:** {ruta_id}\n"
        f"📋 **Reporte:** {tipo_reporte}\n\n"
        f"*(Espacio listo para sincronización de datos)*",
        reply_markup=SupervisorKeyboards.obtener_volver_repetir(),
        parse_mode="Markdown"
    )

    # Limpiar datos temporales de la sesión
    context.user_data.pop("ruta_id_manual", None)
    context.user_data.pop("tipo_reporte_manual", None)

    return ESTADO_PROCESAR_DATOS_REPORTE_SUP



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
        MessageHandler(filters.Text([SupervisorKeyboards.BACKUP_DB, "💾 Hacer Backup de Base de Datos"]), backup_db_handler),

        
        MessageHandler(filters.Text([SupervisorKeyboards.INGESTION]), iniciar_menu_reportes),
        MessageHandler(filters.Text([SupervisorKeyboards.CARGA_INDIVIDUAL]), seleccionar_reporte_ruta_handler),
        MessageHandler(filters.Text([SupervisorKeyboards.CARGA_RAFAGA_SUP]), iniciar_reporte_automatico_handler),
        MessageHandler(filters.Text([SupervisorKeyboards.REPORTE_MULTIPLE]), iniciar_reporte_multiple_handler),
        # Reutiliza estatus_vendedores_handler
        # MessageHandler(filters.Text([SupervisorKeyboards.CUADRE_COBRANZA, "💰 Cuadre Cobranza"]), cuadre_cobranza_handler),

        # Volver al Menú Principal
        MessageHandler(filters.Text([SupervisorKeyboards.VOLVER_MENU, "🔙 Volver al Menú Principal", "⬅️ Volver"]), iniciar_menu_principal),
    ],
    states={
        ESTADO_MONITOREO_VENDEDOR: [
            MessageHandler(filters.Text([BotKeyboards.SALIR_MENU]), salir_al_menu_supervisor_handler),
            MessageHandler(filters.Text([SupervisorKeyboards.VOLVER_MENU, "🔙 Volver al Menú Principal"]), iniciar_menu_principal),
            MessageHandler(filters.TEXT & ~filters.COMMAND, avence_por_ruta_handle)
        ],
        ESTADO_CARGA_MASIVA: [
            MessageHandler(filters.Text([BotKeyboards.SALIR_MENU]), salir_al_menu_supervisor_handler),
            MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_carga_masiva_cuotas_handle)
        ],
        ESTADO_SI_NO: [
            MessageHandler(filters.Text([BotKeyboards.SALIR_MENU]), salir_al_menu_supervisor_handler),
            MessageHandler(filters.Regex("^(Sí|si|SI|sí)$"), sincronizar_excel),
            MessageHandler(filters.Text([BotKeyboards.SI]), sincronizar_excel),
            MessageHandler(filters.Regex("^(No|no|NO)$"), iniciar_menu_coutas),
            MessageHandler(filters.Text([BotKeyboards.NO]), iniciar_menu_coutas)
        # Manejo de respuesta inesperada  
        ],
        ESTADO_REPORTE_AUTOMATICO: [
            MessageHandler(filters.Text([BotKeyboards.SALIR_MENU]), salir_al_menu_supervisor_handler),
            MessageHandler(filters.Text([SupervisorKeyboards.REINTENTAR]), iniciar_reporte_automatico_handler),
            MessageHandler(filters.Text([SupervisorKeyboards.VOLVER_MENU]), iniciar_menu_principal),
            MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_reporte_automatico_handler),
        ],
        ESTADO_REPORTE_MULTIPLE: [
            MessageHandler(filters.Text([BotKeyboards.SALIR_MENU]), salir_al_menu_supervisor_handler),
            MessageHandler(filters.Text([SupervisorKeyboards.VOLVER_MENU, "🔙 Volver al Menú Principal", "⬅️ Volver"]), iniciar_menu_principal),
            MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_reporte_multiple_handler),
        ],
        ESTADO_CONFIRMACION_REPORTE_SUP: [
            MessageHandler(filters.Text([BotKeyboards.SALIR_MENU]), salir_al_menu_supervisor_handler),
            MessageHandler(filters.Text([BotKeyboards.CONFIRMAR, BotKeyboards.CANCELAR, BotKeyboards.NO, BotKeyboards.SI]), confirmacion_guardado_sup_handler),
            MessageHandler(filters.Text([SupervisorKeyboards.VOLVER_MENU, "🔙 Volver al Menú Principal"]), iniciar_menu_principal),
            MessageHandler(filters.Text([SupervisorKeyboards.CARGAR_OTRO_REPORTE]), iniciar_reporte_automatico_handler)
        ],
        ESTADO_REPORTE_RUTA_SUP: [
            MessageHandler(filters.Text([BotKeyboards.SALIR_MENU]), salir_al_menu_supervisor_handler),
            MessageHandler(filters.Text([SupervisorKeyboards.VOLVER_MENU, "🔙 Volver al Menú Principal"]), iniciar_menu_principal),
            MessageHandler(filters.TEXT & ~filters.COMMAND, seleccionar_tipo_reporte_handler)
        ],
        ESTADO_SELECCIONAR_TIPO_REPORTE_SUP: [
            MessageHandler(filters.Text([BotKeyboards.SALIR_MENU]), salir_al_menu_supervisor_handler),
            MessageHandler(filters.Text([SupervisorKeyboards.VOLVER_MENU, "🔙 Volver al Menú Principal"]), iniciar_menu_principal),
            MessageHandler(filters.TEXT & ~filters.COMMAND, pedir_datos_reporte_handler)
        ],
        ESTADO_PROCESAR_DATOS_REPORTE_SUP: [
            MessageHandler(filters.Text([BotKeyboards.SALIR_MENU]), salir_al_menu_supervisor_handler),
            MessageHandler(filters.Text([SupervisorKeyboards.VOLVER_MENU, "🔙 Volver al Menú Principal"]), iniciar_menu_principal),
            MessageHandler(filters.TEXT & ~filters.COMMAND, procesar_datos_reporte_handler),
            MessageHandler(filters.Text([SupervisorKeyboards.CARGAR_OTRO_REPORTE]), iniciar_reporte_automatico_handler),
     
        ]
    },
    fallbacks=[
        CommandHandler("menu", reiniciar_menu_handler),
        CommandHandler("inicio", reiniciar_menu_handler),
        CommandHandler("hola", reiniciar_menu_handler),
        MessageHandler(filters.Text([BotKeyboards.SALIR_MENU]), salir_al_menu_supervisor_handler),
        MessageHandler(filters.Text([SupervisorKeyboards.VOLVER_MENU, "🔙 Volver al Menú Principal"]), iniciar_menu_principal)
    ],
    per_message=False,
    allow_reentry=True,
    per_user=True,
    per_chat=True,
    
)