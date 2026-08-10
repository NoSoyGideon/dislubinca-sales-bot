# src/services/base_excel_service.py
from abc import ABC, abstractmethod

class BaseExcelService(ABC):
    
    @abstractmethod
    def extraer_operacion_diaria_vendedor(self, ruta: int, fecha: str) -> dict:
        """
        [SR] Viaja en el tiempo al archivo Excel mensual en Dropbox.
        Busca la pestaña correspondiente al día (ej: "MIERCOLES 04-02")
        y extrae los 6 campos métricos de esa ruta específica.
        Devuelve un diccionario con las metas y logros reales encontrados.
        """
        pass

    @abstractmethod
    def extraer_caja_nocturna_dia(self, fecha: str) -> dict:
        """
        [SR] Abre el archivo de 'REPORTE DIARIO DE COBRANZA' en Dropbox.
        Extrae la matriz completa de Efectivo, Zelle y Bs del día junto a la tasa BCV.
        """
        pass



    @abstractmethod
    def inyectar_cierre_nocturno_excel(self, ruta: int, fecha: str, datos_cierre: dict) -> bool:
        """
        Escribe en caliente en el Excel de Cobranza el desglose físico de caja
        (Efectivo, Zelle, Bs) y los logros reales de la ruta al terminar el día.
        """
        pass