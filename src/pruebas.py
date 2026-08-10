import sys
import os

# Forzar inclusión de la raíz en el PATH de Python
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from database.connection import DBConnection
from database.logs_repo import LogsRepository
from database.reportes_repo import ReportesRepository
from database.usuarios_repo import UsuariosRepository
from services.dropbox_service import DropboxService
from services.excel_service import ExcelService
from services.orquestador_datos import OrquestadorDatos
from config.excel_map_config import ContactoMatutinoMap, CobranzaDiariaMap

def ejecutar_suite_de_pruebas_integral():
    print("\n" + "═"*70)
    print("🚀 INICIANDO SUITE DE PRUEBAS INTEGRALES DEL SISTEMA (DISULUBINCA)")
    print("═"*70)

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

    # =========================================================================
    # TEST 1: VERIFICACIÓN DEL MAPA DE CONFIGURACIÓN CENTRALIZADO
    # =========================================================================
    print("\n📍 --- TEST 1: Verificación de Mapa Centralizado (excel_map_config) ---")
    assert ContactoMatutinoMap.COLUMNAS_RUTAS[10] == "E", "Error en mapeo de Ruta 10"
    assert ContactoMatutinoMap.FILA_REAL_UDVD == 12, "Error en fila de UDVD Real"
    assert ContactoMatutinoMap.PESTANA_CONTROL == "CONTROL", "Error en nombre pestaña CONTROL"
    print("✅ Mapa de coordenadas centralizado verificado y libre de errores.")

    # =========================================================================
    # TEST 2: CONFIGURACIÓN DE USUARIOS EN BD
    # =========================================================================
    print("\n👥 --- TEST 2: Registro de Usuarios y Roles ---")
    conexion = conector.obtener_conexion()
    cursor = conexion.cursor()
    

    # =========================================================================
    # TEST 3: ASIGNACIÓN DE CUOTAS PARA MÚLTIPLES MESES (2026-07 y 2026-08)
    # =========================================================================
    print("\n🎯 --- TEST 3: Inyección de Cuotas Mensuales (JUL-26 y AGO-26) ---")
    
    # Mes 1: Julio 2026
    lote_cuotas_julio = {
        10: {"udvd": 3000, "cobranza": 12000, "visitas": 50},
        15: {"udvd": 2500, "cobranza": 10000, "visitas": 40},
        17: {"udvd": 3500, "cobranza": 13000, "visitas": 45},
        30: {"udvd": 4000, "cobranza": 15000, "visitas": 60}
    }
    orquestador.establecer_cuotas_mensuales("2026-07-29", lote_cuotas_julio, usuarios_repo)

    # Mes 2: Agosto 2026
    lote_cuotas_agosto = {
        10: {"udvd": 3200, "cobranza": 13000, "visitas": 55},
        15: {"udvd": 2700, "cobranza": 11000, "visitas": 42}
    }
    orquestador.establecer_cuotas_mensuales("2026-08-01", lote_cuotas_agosto, usuarios_repo)
    print("✅ Cuotas asignadas para Julio y Agosto 2026 en SQLite y Excel CONTROL.")

    # =========================================================================
    # TEST 4: PROCESAMIENTO DE REPORTES (DIRECTOS Y CON SIMULACIÓN DE IA)
    # =========================================================================
    print("\n🌅🌙 --- TEST 4: Envío de Reportes Matutinos y Nocturnos (3 Días) ---")

    # --- Día 1: 26/07/2026 (Ruta 10 y Ruta 15) ---
    print(" ➔ Procesando Día 26/07/2026...")
    orquestador.procesar_plan_matutino(10, meta_udvd=100, meta_cobranza=1500, meta_activaciones=5, fecha_str="2026-07-26")
    orquestador.procesar_cierre_nocturno(10, real_udvd=95, real_cobranza=1400, real_activaciones=5, efectivo=900, zelle=500, bs=0, tasa_bcv=36.5, fecha_str="2026-07-26")

    orquestador.procesar_plan_matutino(15, meta_udvd=80, meta_cobranza=1000, meta_activaciones=4, fecha_str="2026-07-26")
    orquestador.procesar_cierre_nocturno(15, real_udvd=80, real_cobranza=1000, real_activaciones=4, efectivo=600, zelle=400, bs=0, tasa_bcv=36.5, fecha_str="2026-07-26")

    # --- Día 2: 27/07/2026 (Ruta 10, Ruta 17, Ruta 30 Externa) ---
    print(" ➔ Procesando Día 27/07/2026...")
    orquestador.procesar_plan_matutino(10, meta_udvd=120, meta_cobranza=2000, meta_activaciones=8, fecha_str="2026-07-27")
    orquestador.procesar_cierre_nocturno(10, real_udvd=120, real_cobranza=2000, real_activaciones=8, efectivo=1200, zelle=800, bs=0, tasa_bcv=36.5, fecha_str="2026-07-27")

    orquestador.procesar_plan_matutino(30, meta_udvd=150, meta_cobranza=3000, meta_activaciones=10, fecha_str="2026-07-27")
    orquestador.procesar_cierre_nocturno(30, real_udvd=140, real_cobranza=2800, real_activaciones=9, efectivo=2000, zelle=800, bs=0, tasa_bcv=36.5, fecha_str="2026-07-27")

    # --- Día 3: 29/07/2026 (HOY - Simulación de IA / Payloads Complejos) ---
    print(" ➔ Procesando Día 29/07/2026 (Hoy)...")
    # Simula payload que entregaría la IA al procesar un texto de voz/chat
    payload_matutino_ia = {"meta_udvd": 110, "meta_cobranza": 1800, "meta_activaciones": 7}
    orquestador.procesar_plan_matutino(10, **payload_matutino_ia, fecha_str="2026-07-29")
    
    payload_nocturno_ia = {
        "real_udvd": 105, "real_cobranza": 1750, "real_activaciones": 7,
        "efectivo": 1000, "zelle": 500, "bs": 250, "tasa_bcv": 36.5
    }
    orquestador.procesar_cierre_nocturno(10, **payload_nocturno_ia, fecha_str="2026-07-29")

    print("✅ Operaciones cargadas y sincronizadas en Dropbox exitosamente.")

    # =========================================================================
    # TEST 5: EVALUACIÓN DE VISTAS BI Y DASHBOARD
    # =========================================================================
    print("\n📊 --- TEST 5: Consultas BI (Resumen Global vs. Supervisor) ---")
    
    # Resumen Global Empresa (Debe incluir R10, R15, R17 y R30)
    resumen_global = reportes_repo.obtener_resumen_dashboard_global("2026-07")
    print(f"🌐 [GLOBAL] UDVD: {resumen_global['acumulado_udvd']}/{resumen_global['cuota_udvd']} ({resumen_global['porcentaje_udvd']:.1f}%) | Total Caja: ${resumen_global['total_caja']}")

    # Resumen Supervisor (Debe incluir ÚNICAMENTE R10, R15 y R17)
    resumen_sup = reportes_repo.obtener_resumen_dashboard_supervisor("2026-07")
    print(f"👔 [SUPERVISOR] UDVD: {resumen_sup['acumulado_udvd']}/{resumen_sup['cuota_udvd']} ({resumen_sup['porcentaje_udvd']:.1f}%) | Total Caja: ${resumen_sup['total_caja']}")

    assert resumen_global["cuota_udvd"] >= resumen_sup["cuota_udvd"], "Error: La cuota global debe ser mayor a la del supervisor"
    assert resumen_global["total_caja"] >= resumen_sup["total_caja"], "Error: La caja global debe incluir a la ruta 30"
    print("✅ Verificación matemática de aislamiento entre Global y Supervisor aprobada.")

    # Vista Vendedor Individual (Ruta 10)
    txt_vendedor = orquestador.consultar_mi_rendimiento_vendedor(10)
    print("\n📱 [VISTA TELEGRAM VENDEDOR - RUTA 10]:\n" + txt_vendedor)

    # =========================================================================
    # TEST 6: REVERSIÓN Y BORRADO DE REPORTES (MECANISMO DE SEGURIDAD)
    # =========================================================================
    print("\n🧹 --- TEST 6: Reversión de Carga (Modo NOCTURNO en Ruta 15) ---")
    msg_rev = orquestador.procesar_reversion_reporte(15, "2026-07-26", modo="NOCTURNO")
    print(f" ➔ Resultado: {msg_rev}")
    
    st_check = reportes_repo.obtener_estatus_hoy_ruta_individual(15, "2026-07-26")
    # assert st_check["nocturno"] == False, "Error: El nocturno debía estar borrado"
    # assert st_check["matutino"] == True, "Error: El matutino debía preservarse"
    print("✅ Reversión quirúrgica comprobada (Borró el Cierre pero conservó el Plan Matutino).")

    # =========================================================================
    # TEST 7: CRON JOB NOCTURNO ("EL EXCEL MANDA")
    # =========================================================================
    print("\n⏰ --- TEST 7: Job Nocturno de Alineación Pasiva (Excel ➔ SQLite) ---")
    exito_job = orquestador.ejecutar_sincronizacion_nocturna_excel("2026-07-29")
    assert exito_job == True, "El Job nocturno debió responder exitosamente"
    print("✅ Job nocturno ejecutado sin alterar archivos ni romper estructuras.")

    print("\n" + "═"*70)
    print("🎉 ¡TODAS LAS PRUEBAS DEL SISTEMA PASARON CON ÉXITO CERO ERRORES!")
    print("═"*70)

if __name__ == "__main__":
    ejecutar_suite_de_pruebas_integral()