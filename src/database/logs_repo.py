class LogsRepository:
    def __init__(self, db_connection):
        """Recibe el conector central de la base de datos"""
        self.db = db_connection

    def registrar_log(self, nivel, mensaje):
            """Inserta un evento de auditoría en la DB y lo escupe en la consola Linux"""
            nivel_formateado = nivel.upper()
            
            # --- MEJORA: El print en vivo para la consola ---
            # Dependiendo de la gravedad, le puedes poner un emoji para que salte a la vista
            emoji = "ℹ️" if nivel_formateado == "INFO" else "⚠️" if nivel_formateado == "WARNING" else "❌"
            print(f"{emoji} [{nivel_formateado}] {mensaje}")
            
            # --- El guardado de siempre en la DB ---
            conexion = self.db.obtener_conexion()
            cursor = conexion.cursor()
            try:
                cursor.execute(
                    "INSERT INTO logs_sistema (nivel, mensaje) VALUES (?, ?)",
                    (nivel_formateado, mensaje)
                )
                conexion.commit()
            except Exception as e:
                print(f"💥 [Fallo Crítico Logger] No se pudo guardar en DB: {e}")
            finally:
                conexion.close()

    def obtener_ultimos_logs(self, limite=50):
            """Devuelve los últimos N logs ordenados del más reciente al más viejo"""
            conexion = self.db.obtener_conexion()
            cursor = conexion.cursor()
            
            # Corrección: Eliminamos 'Whitenoise' y nos aseguramos de mantener la coma
            cursor.execute(
                "SELECT timestamp, nivel, mensaje FROM logs_sistema ORDER BY id DESC LIMIT ?",
                (limite,)
            )
            resultados = cursor.fetchall()
            conexion.close()
            
            return resultados