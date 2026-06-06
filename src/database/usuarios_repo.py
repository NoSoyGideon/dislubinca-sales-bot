class UsuariosRepository:
    def __init__(self, db_connection):
        """Recibe el conector central de la base de datos"""
        self.db = db_connection

    def obtener_usuario(self, telegram_id):
        """Busca un usuario por su ID de Telegram. Devuelve dict o None"""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        
        cursor.execute(
            "SELECT nombre_telegram, ruta, rol, estado FROM usuarios WHERE telegram_id = ?", 
            (telegram_id,)
        )
        resultado = cursor.fetchone()
        conexion.close()

        if resultado:
            return {
                "nombre": resultado[0],
                "ruta": resultado[1],
                "rol": resultado[2],
                "estado": resultado[3]
            }
        return None

    def registrar_vendedor_pendiente(self, telegram_id, nombre_telegram):
        """Registra a un vendedor nuevo en estado PENDIENTE"""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute(
                "INSERT INTO usuarios (telegram_id, nombre_telegram) VALUES (?, ?)",
                (telegram_id, nombre_telegram)
            )
            conexion.commit()
            return True
        except Exception:
            return False  # Si ya existe el ID por un intento previo
        finally:
            conexion.close()

    def autorizar_vendedor(self, telegram_id, numero_ruta):
        """Cambia el estado a AUTORIZADO y le asigna su ruta de cobranza"""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE usuarios SET estado = 'AUTORIZADO', ruta = ? WHERE telegram_id = ?",
            (numero_ruta, telegram_id)
        )
        conexion.commit()
        exito = cursor.rowcount > 0
        conexion.close()
        return exito

    def dar_de_baja_usuario(self, telegram_id):
        """Bloquea el acceso de un usuario al sistema"""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute(
            "UPDATE usuarios SET estado = 'BLOQUEADO' WHERE telegram_id = ?",
            (telegram_id,)
        )
        conexion.commit()
        exito = cursor.rowcount > 0
        conexion.close()
        return exito