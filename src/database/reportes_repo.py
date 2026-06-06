from datetime import datetime

class ReportesRepository:
    def __init__(self, db_connection):
        """Recibe el conector central de la base de datos"""
        self.db = db_connection

    def _obtener_fecha_hoy(self):
        """Método interno para estandarizar la fecha actual"""
        return datetime.now().strftime("%Y-%m-%d")

    def verificar_reporte_existente(self, telegram_id, tipo_reporte):
        """Revisa si el vendedor ya reportó MAÑANA o NOCHE el día de hoy"""
        fecha_hoy = self._obtener_fecha_hoy()
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()

        cursor.execute(
            "SELECT id FROM registros_diarios WHERE telegram_id = ? AND fecha = ? AND tipo_reporte = ?",
            (telegram_id, fecha_hoy, tipo_reporte.upper())
        )
        resultado = cursor.fetchone()
        conexion.close()

        return resultado is not None

    def guardar_reporte_nuevo(self, telegram_id, ruta, tipo_reporte, datos_json):
        """Hace un INSERT limpio con el JSON de la IA y la fecha de hoy"""
        fecha_hoy = self._obtener_fecha_hoy()
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute(
                "INSERT INTO registros_diarios (telegram_id, ruta, fecha, tipo_reporte, datos_json) VALUES (?, ?, ?, ?, ?)",
                (telegram_id, ruta, fecha_hoy, tipo_reporte.upper(), datos_json)
            )
            conexion.commit()
            return True
        except Exception:
            return False
        finally:
            conexion.close()

    def actualizar_reporte_existente(self, telegram_id, tipo_reporte, datos_json):
        """Hace un UPDATE sobre el reporte de hoy si el vendedor decide reescribirlo"""
        fecha_hoy = self._obtener_fecha_hoy()
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute(
            "UPDATE registros_diarios SET datos_json = ? WHERE telegram_id = ? AND fecha = ? AND tipo_reporte = ?",
            (datos_json, telegram_id, fecha_hoy, tipo_reporte.upper())
        )
        conexion.commit()
        exito = cursor.rowcount > 0
        conexion.close()
        return exito