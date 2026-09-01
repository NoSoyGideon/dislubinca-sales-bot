# src/bot/keyboards.py

from telegram import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from database.usuarios_repo import UsuariosRepository

class BotKeyboards:
    # Constantes para mensajes estandarizados
    TURNO_MANANA = "☀️ Reportar Plan del dia"
    TURNO_NOCHE = "🌙 Reportar Cierre"
    REPORTE_COBRANZA = "💵 Reportar Cobranza"
    REPORTE_RAFAGA = "⚡️ Reporte Ráfaga"
    MI_RENDIMIENTO = "📊 Mi Rendimiento"
    AYUDA = "❓ Ayuda / Instrucciones"
    AYUDA_REPORTE = "📘 Ayuda - Reportes"
    AYUDA_RAFAGA = "⚡️ Ayuda - Reporte Ráfaga"
    AYUDA_RENDIMIENTO = "📊 Ayuda - Rendimiento"
    
    FINALIZAR_RAFAGA = "🏁 Finalizar Ráfaga"
    
    CONFIRMAR = "✅ Confirmar y Guardar"
    CANCELAR = "❌ Cancelar / Corregir"

    # PLAN_DIA_UDVD = "📋 Plan del Día - UDVD"
    # PLAN_DIA_CXC = "📋 Plan del Día - Cuentas x cobrar"
    # PLAN_DIA_VISITAS = "📋 Plan del Día - Visitas"
    
    # CIERRE_NOCHE_UDVD = "📋 Cierre de Noche - UDVD"
    # CIERRE_NOCHE_CXC = "📋 Cierre de Noche - Cuentas x cobrar"
    # CIERRE_NOCHE_VISITAS = "📋 Cierre de Noche - Visitas"
    
    # COBRANZA_DOLARES = "💵 Cobranza en Dólares"
    # COBRA
    
    SI = "✅ Sí"
    NO = "❌ No"
    SALIR_MENU = "🏠 Volver al inicio"
    
    @classmethod
    def obtener_teclado_vendedor(cls) -> ReplyKeyboardMarkup:
        """Teclado principal del vendedor"""
        botones = [
            [KeyboardButton(cls.TURNO_MANANA), KeyboardButton(cls.TURNO_NOCHE)],
            [KeyboardButton(cls.REPORTE_COBRANZA), KeyboardButton(cls.REPORTE_RAFAGA)],
            [KeyboardButton(cls.AYUDA), KeyboardButton(cls.MI_RENDIMIENTO)]
        ]
        return ReplyKeyboardMarkup(botones, resize_keyboard=True)

    @classmethod
    def obtener_teclado_confirmacion(cls) -> ReplyKeyboardMarkup:
        """Teclado temporal para validar la extracción de la IA"""
        botones = [
            [KeyboardButton(cls.CONFIRMAR)],
            [KeyboardButton(cls.CANCELAR)]
        ]
        return ReplyKeyboardMarkup(botones, resize_keyboard=True, one_time_keyboard=True)
    @classmethod
    def obtener_teclado_rafaga(cls) -> ReplyKeyboardMarkup:
        """Teclado activo MIENTRAS el vendedor envía fragmentos de texto"""
        botones = [
            [KeyboardButton(cls.FINALIZAR_RAFAGA)],
            [KeyboardButton(cls.CANCELAR)],
            [KeyboardButton(cls.SALIR_MENU)]
        ]
        return ReplyKeyboardMarkup(botones, resize_keyboard=True)
    @classmethod
    def obtener_teclado_rutas(cls, db_connection) -> ReplyKeyboardMarkup:
        """Obtiene dinámicamente las rutas registradas en SQLite"""
        usuarios_repo = UsuariosRepository(db_connection)
        rutas = usuarios_repo.listar_rutas_configuradas()
        
        botones = []
        fila_actual = []
        
        for ruta in rutas:
            fila_actual.append(KeyboardButton(f"Ruta {ruta}"))
            if len(fila_actual) == 3:
                botones.append(fila_actual)
                fila_actual = []
                
        if fila_actual:
            botones.append(fila_actual)
            
        return ReplyKeyboardMarkup(botones, resize_keyboard=True, one_time_keyboard=True)
    
    
    @classmethod
    def obtener_teclado_confirmacion(cls) -> ReplyKeyboardMarkup:
        """Teclado temporal para validar la extracción de la IA"""
        botones = [
            [KeyboardButton(cls.SI)],
            [KeyboardButton(cls.NO)],
            [KeyboardButton(cls.SALIR_MENU)]
        ]
        return ReplyKeyboardMarkup(botones, resize_keyboard=True, one_time_keyboard=True)

    @classmethod
    def obtener_teclado_ayuda(cls) -> ReplyKeyboardMarkup:
        """Menú de ayuda con las categorías clave del bot."""
        botones = [
            [KeyboardButton(cls.AYUDA_REPORTE), KeyboardButton(cls.AYUDA_RAFAGA)],
            [KeyboardButton(cls.AYUDA_RENDIMIENTO), KeyboardButton(cls.SALIR_MENU)]
        ]
        return ReplyKeyboardMarkup(botones, resize_keyboard=True, one_time_keyboard=True)

    @classmethod
    def obtener_teclado_ayuda_volver(cls) -> ReplyKeyboardMarkup:
        """Teclado simple para volver al menú principal desde ayuda."""
        return ReplyKeyboardMarkup(
            [[KeyboardButton(cls.SALIR_MENU)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

    @classmethod
    def obtener_teclado_salir(cls) -> ReplyKeyboardMarkup:
        """Teclado visible para abandonar cualquier flujo activo."""
        return ReplyKeyboardMarkup(
            [[KeyboardButton(cls.SALIR_MENU)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )

class SupervisorKeyboards:
    # --- MENÚ PRINCIPAL SUPERVISOR (NIVEL 1) ---
    MONITOREO = "📊 Monitoreo y Progreso"
    CUOTAS = "🎯 Gestión de Cuotas y configuración"
    PERSONAL = "👥 Administración de Personal"
    INGESTION = "⚡️ Cargar Reportes (Manual)"
    
    # --- BOTÓN DE RETORNO ---
    VOLVER_MENU = "⬅️ Volver al Menú Principal"
    REINTENTAR = "🔄 Volver a Intentar"
    # --- SUBMENÚ MONITOREO (NIVEL 2) ---
    AVANCE_MES = "📈 Avance General del Mes"
    AVANCE_MES_SUPERVISOR = "📊 Avance por Supervisor"
    AVANCE_POR_RUTA = "📊 Avance por Ruta"
    ESTATUS_HOY = "📋 Estatus de Hoy"
    CUADRE_COBRANZA = "💵 Cuadre de Caja del Día"

    # --- SUBMENÚ CUOTAS (NIVEL 2) ---
    CUOTA_MASIVA = "✏️ Registrar o Editar cuotas"
    CUOTA_TODOS_VENDEDORES = "📊 Ver cuotas de vendedores"
    SINCRONIZACION = "🔄 Sincronizar Excel automaticamente"
    BACKUP_DB = "💾 Hacer Backup de Base de Datos"
    

    # --- SUBMENÚ PERSONAL (NIVEL 2) ---
    VER_SOLICITUDES = "📩 Solicitudes Pendientes"
    ESTATUS_VENDEDORES = "🔒 Habilitar/Deshabilitar Vendedor"
    LISTA_ACTIVOS = "📋 Vendedores Activos"

    # --- SUBMENÚ INGESTIÓN MANUAL (NIVEL 2) ---
    CARGA_INDIVIDUAL = "📝 Reporte Manual Individual"
    CARGA_RAFAGA_SUP = "⚡️ Reporte Manual Automatico"
    REPORTE_MULTIPLE = "📦 Reportes Múltiples"
    CARGAR_OTRO_REPORTE = "📋 Cargar otro reporte"
# Constantes para Tipos de Reportes
    TIPO_PLAN_DIA = "📋 Plan del Día"
    TIPO_CIERRE_NOCHE = "🌙 Cierre de Noche"
    TIPO_COBRANZA = "💵 Reporte de Cobranza"



    @classmethod
    def obtener_teclado_tipos_reporte(cls) -> ReplyKeyboardMarkup:
        """Teclado para seleccionar el tipo de reporte manual"""
        botones = [
            [KeyboardButton(cls.TIPO_PLAN_DIA), KeyboardButton(cls.TIPO_CIERRE_NOCHE)],
            [KeyboardButton(cls.TIPO_COBRANZA)],
            [KeyboardButton(cls.VOLVER_MENU)]
        ]
        return ReplyKeyboardMarkup(botones, resize_keyboard=True, one_time_keyboard=True)

    @classmethod
    def obtener_teclado_reintento(cls) -> ReplyKeyboardMarkup:
        """Teclado que se muestra en caso de un error en el formato de datos"""
        botones = [
            [KeyboardButton(cls.REINTENTAR)],
            [KeyboardButton(cls.VOLVER_MENU)]
        ]
        return ReplyKeyboardMarkup(botones, resize_keyboard=True, one_time_keyboard=True)
    @classmethod
    def obtener_menu_principal(cls) -> ReplyKeyboardMarkup:
        botones = [
            [KeyboardButton(cls.MONITOREO), KeyboardButton(cls.CUOTAS)],
            [KeyboardButton(cls.PERSONAL), KeyboardButton(cls.INGESTION)]
        ]
        return ReplyKeyboardMarkup(botones, resize_keyboard=True)

    @classmethod
    def obtener_sub_monitoreo(cls) -> ReplyKeyboardMarkup:
        botones = [
            [KeyboardButton(cls.AVANCE_MES), KeyboardButton(cls.AVANCE_MES_SUPERVISOR)],
            [KeyboardButton(cls.AVANCE_POR_RUTA)],
            [KeyboardButton(cls.ESTATUS_HOY)],
            # [KeyboardButton(cls.CUADRE_COBRANZA)],
            [KeyboardButton(cls.VOLVER_MENU)]
        ]
        return ReplyKeyboardMarkup(botones, resize_keyboard=True)

    @classmethod
    def obtener_sub_cuotas(cls) -> ReplyKeyboardMarkup:
        botones = [
            [KeyboardButton(cls.CUOTA_MASIVA), KeyboardButton(cls.CUOTA_TODOS_VENDEDORES)],
            [KeyboardButton(cls.SINCRONIZACION), KeyboardButton(cls.BACKUP_DB)],
            [KeyboardButton(cls.VOLVER_MENU)]
        ]
        return ReplyKeyboardMarkup(botones, resize_keyboard=True)

    @classmethod
    def obtener_sub_personal(cls) -> ReplyKeyboardMarkup:
        botones = [
            [KeyboardButton(cls.VER_SOLICITUDES)],
            # KeyboardButton(cls.ESTATUS_VENDEDORES),
            [KeyboardButton(cls.LISTA_ACTIVOS)],
            [KeyboardButton(cls.VOLVER_MENU)]
        ]
        return ReplyKeyboardMarkup(botones, resize_keyboard=True)

    @classmethod
    def obtener_sub_ingestion(cls) -> ReplyKeyboardMarkup:
        botones = [
            [KeyboardButton(cls.CARGA_INDIVIDUAL), KeyboardButton(cls.CARGA_RAFAGA_SUP)],
            [KeyboardButton(cls.REPORTE_MULTIPLE)],
            [KeyboardButton(cls.VOLVER_MENU)]
        ]
        return ReplyKeyboardMarkup(botones, resize_keyboard=True)
    
    @classmethod
    def obtener_volver_menu(cls) -> ReplyKeyboardMarkup:
        """Teclado simple para volver al menú principal"""
        botones = [[KeyboardButton(cls.VOLVER_MENU)]]
        return ReplyKeyboardMarkup(botones, resize_keyboard=True)
    
    @classmethod
    def obtener_volver_repetir(cls) -> ReplyKeyboardMarkup:
        
        botones =[[KeyboardButton(cls.VOLVER_MENU)],[KeyboardButton(cls.CARGAR_OTRO_REPORTE)]]
        return ReplyKeyboardMarkup(botones, resize_keyboard=True)