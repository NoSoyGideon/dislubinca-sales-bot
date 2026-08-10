# src/database/usuarios_repo.py

import sqlite3

class UsuariosRepository:
    def __init__(self, db_connection):
        """Recibe el conector central de la base de datos (DBConnection)"""
        self.db = db_connection

    def obtener_usuario_por_telegram(self, telegram_id):
        """Busca un usuario por su ID de Telegram (para el bot). Devuelve dict o None"""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute(
                "SELECT ruta, nombre_telegram, rol, estado, bajo_responsabilidad_supervisor FROM usuarios WHERE telegram_id = ?", 
                (telegram_id,)
            )
            resultado = cursor.fetchone()
            if resultado:
                return {
                    "ruta": resultado[0],
                    "nombre": resultado[1],
                    "rol": resultado[2],
                    "estado": resultado[3],
                    "bajo_responsabilidad": bool(resultado[4])
                }
            return None
        except Exception as e:
            print(f"❌ [UsuariosRepo] Error al obtener usuario por Telegram: {e}")
            return None
        finally:
            conexion.close()

    def obtener_usuario_por_ruta(self, ruta: int):
        """Busca una ruta directamente (Ideal para el caso de la Ruta 21 sin registrar)"""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute(
                "SELECT telegram_id, nombre_telegram, rol, estado, bajo_responsabilidad_supervisor FROM usuarios WHERE ruta = ?", 
                (ruta,)
            )
            resultado = cursor.fetchone()
            if resultado:
                return {
                    "telegram_id": resultado[0],
                    "nombre": resultado[1],
                    "rol": resultado[2],
                    "estado": resultado[3],
                    "bajo_responsabilidad": bool(resultado[4])
                }
            return None
        except Exception as e:
            print(f"❌ [UsuariosRepo] Error al obtener usuario por Ruta: {e}")
            return None
        finally:
            conexion.close()
            
    def registrar_o_reclamar_ruta(self, telegram_id, nombre_telegram, ruta: int):
        """
        Si la ruta ya fue pre-creada por el sistema, el vendedor vincula su telegram_id.
        Si no existe, la crea en estado PENDIENTE.
        """
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            # Verificar si la ruta ya existe de forma pre-hecha
            cursor.execute("SELECT telegram_id FROM usuarios WHERE ruta = ?", (ruta,))
            existe = cursor.fetchone()
            
            if existe:
                # Si existe pero no tiene dueño, el vendedor la reclama
                cursor.execute(
                    "UPDATE usuarios SET telegram_id = ?, nombre_telegram = ?, estado = 'PENDIENTE' WHERE ruta = ? AND telegram_id IS NULL",
                    (telegram_id, nombre_telegram, ruta)
                )
            else:
                # Si la ruta no existía en el mapa de control, se inserta completa
                cursor.execute(
                    "INSERT INTO usuarios (ruta, telegram_id, nombre_telegram, rol, estado) VALUES (?, ?, ?, 'VENDEDOR', 'PENDIENTE')",
                    (ruta, telegram_id, nombre_telegram)
                )
            conexion.commit()
            return True
        except Exception as e:
            print(f"❌ [UsuariosRepo] Error al registrar/reclamar ruta: {e}")
            return False
        finally:
            conexion.close()

    def autorizar_vendedor(self, ruta_id):
        """Cambia el estado a AUTORIZADO para permitirle operar"""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute(
                "UPDATE usuarios SET estado = 'AUTORIZADO' WHERE ruta = ?",
                (ruta_id,)
            )
            conexion.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ [UsuariosRepo] Error al autorizar vendedor: {e}")
            return False
        finally:
            conexion.close()

    def dar_de_baja_usuario(self, ruta_id):
        """Bloquea por completo el acceso de una ruta al sistema"""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute(
                "UPDATE usuarios SET estado = 'BLOQUEADO', telegram_id = NULL WHERE ruta = ?",
                (ruta_id,)
            )
            conexion.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"❌ [UsuariosRepo] Error al dar de baja: {e}")
            return False
        finally:
            conexion.close()

    def es_administrador(self, telegram_id) -> bool:
        """Verifica si el rol de Telegram pertenece a la directiva (Admin/Supervisor)"""
        usuario = self.obtener_usuario_por_telegram(telegram_id)
        if usuario:
            return usuario["rol"].lower().strip() in ["admin", "supervisor", "supervisor de ventas"]
        return False

    def esta_autorizado(self, telegram_id) -> bool:
        """Llave maestra de control de acceso para el middleware del bot"""
        usuario = self.obtener_usuario_por_telegram(telegram_id)
        if usuario:
            return usuario["estado"].upper().strip() == "AUTORIZADO"
        return False

    def obtener_estado_registro(self, telegram_id) -> str:
        usuario = self.obtener_usuario_por_telegram(telegram_id)
        if usuario:
            return usuario["estado"].upper().strip()
        return "NO_REGISTRADO"

    def listar_vendedores_pendientes(self):
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute(
                "SELECT ruta, nombre_telegram, telegram_id FROM usuarios WHERE estado = 'PENDIENTE' AND telegram_id IS NOT NULL ORDER BY ruta ASC"
            )
            return cursor.fetchall()
        except Exception:
            return []
        finally:
            conexion.close()
            
    def listar_vendedores_autorizados(self):
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute(
                "SELECT ruta, nombre_telegram, telegram_id FROM usuarios WHERE estado = 'AUTORIZADO' AND rol = 'VENDEDOR' ORDER BY ruta ASC"
            )
            return cursor.fetchall()
        except Exception:
            return []
        finally:
            conexion.close()       
            
    def listar_rutas_configuradas(self):
        """
        Extrae todas las rutas numéricas únicas dadas de alta en el sistema,
        ordenadas de menor a mayor para armar los teclados del bot.
        """
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute("SELECT DISTINCT ruta FROM usuarios WHERE rol = 'VENDEDOR' ORDER BY ruta ASC")
            return [fila[0] for fila in cursor.fetchall()]
        except Exception as e:
            print(f"❌ [UsuariosRepo] Error al listar rutas configuradas: {e}")
            return []
        finally:
            conexion.close()