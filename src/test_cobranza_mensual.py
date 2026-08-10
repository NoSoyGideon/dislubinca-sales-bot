import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from database.connection import DBConnection
from database.logs_repo import LogsRepository
from database.reportes_repo import ReportesRepository
from database.usuarios_repo import UsuariosRepository
from services.dropbox_service import DropboxService
from services.excel_service import ExcelService
from services.orquestador_datos import OrquestadorDatos

def probar_cobranza_mensual():
    print("\n💵 === PROBANDO REPORTE DIARIO DE COBRANZA AUTOMÁTICO ===")
    
    conector = DBConnection()
    logger = LogsRepository(conector)
    reportes_repo = ReportesRepository(conector)
    dropbox_service = DropboxService(logger)
    excel_service = ExcelService(dropbox_service)
    usurops_repo = UsuariosRepository(conector)
    orquestador = OrquestadorDatos(
        reportes_repo=reportes_repo,
        logs_repo=logger,
        dropbox_service=dropbox_service,
        excel_service=excel_service
    )

    # Probamos con una fecha de AGOSTO 2026 (04/08/2026 - Martes)
    fecha_test = "2026-08-04"
    
    cuotas = { 
            10:{"udvd":12000,"cobranza": 15000, "visitas": 130},
            15:{"udvd":10000,"cobranza": 12000, "visitas": 100},
            17:{"udvd":9000,"cobranza": 10000, "visitas": 101},
            21:{"udvd":2000,"cobranza": 4000, "visitas": 30},
            30:{"udvd":8000,"cobranza": 4200, "visitas": 82},
            32:{"udvd":6000,"cobranza": 2000, "visitas": 53},
            39:{"udvd":1000,"cobranza": 4200, "visitas": 23}
            }
    orquestador.establecer_cuotas_mensuales(fecha_test,cuotas,usurops_repo)

if __name__ == "__main__":
    probar_cobranza_mensual()