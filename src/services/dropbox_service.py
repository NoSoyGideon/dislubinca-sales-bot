# src/services/dropbox_service.py

import os
import shutil
import dropbox
from dropbox.exceptions import AuthError, ApiError
from dropbox.files import WriteMode
from config.config import Config

class DropboxService:
    
    RUTA_TMP = os.path.join(os.path.dirname(__file__), "../../tmp")
    
    def __init__(self, logs_repo):
        """
        Inicializa el cliente de Dropbox con tus credenciales infinitas.
        Recibe el repositorio de logs centralizado para evitar dependencias circulares.
        """
        self.config = Config()
        self.logger = logs_repo
        
        self.app_key = self.config.obtener_dropbox_key()
        self.app_secret = self.config.obtener_dropbox_secret()
        self.refresh_token = self.config.obtener_dropbox_refresh_token()
        
        self.dbx = None
        print("🔑 [DropboxService] Inicializando conexión con Dropbox...",os.path.dirname(__file__))
        self._conectar()

    def _conectar(self):
        """Establece la conexión usando el Refresh Token para garantizar acceso infinito"""
        try:
            self.dbx = dropbox.Dropbox(
                app_key=self.app_key,
                app_secret=self.app_secret,
                oauth2_refresh_token=self.refresh_token,
                timeout=30.0  # <--- Agrega esto. 30 segundos máximo.
            )
            # Prueba rápida de vida: Si no lanza error, estamos dentro
            self.dbx.users_get_current_account()
            print("📦 [Dropbox] Conexión establecida y verificada con éxito.")
        except AuthError as e:
            msg = f"Error de autenticación en Dropbox: {e}"
            print(f"❌ {msg}")
            self.logger.registrar_log("CRITICAL", msg) # Ajustado a tu firma limpia de logs_repo
            self.dbx = None
        except Exception as e:
            msg = f"No se pudo inicializar DropboxService: {e}"
            print(f"❌ {msg}")
            self.logger.registrar_log("CRITICAL", msg)
            self.dbx = None

    def subir_archivo(self, ruta_local: str, ruta_dropbox: str) -> bool:
            """Sube o reemplaza un archivo hacia la carpeta de Dropbox con auditoría intensiva."""
            print(f"🔍 [AUDITORÍA] Iniciando 'subir_archivo' -> Local: {ruta_local} | Destino: {ruta_dropbox}")
            
            print("🔍 [AUDITORÍA 1] Comprobando instancia de conexión a Dropbox (self.dbx)...")
            if not self.dbx:
                print("🔍 [AUDITORÍA 1.1] self.dbx no existe. Llamando a self._conectar()...")
                self._conectar()
                print("🔍 [AUDITORÍA 1.2] self._conectar() finalizó el intento.")
                if not self.dbx: 
                    print("❌ [AUDITORÍA] Error: La conexión falló y self.dbx sigue siendo None. Abortando.")
                    return False
            else:
                print("🔍 [AUDITORÍA 1] Instancia self.dbx OK.")

            print("🔍 [AUDITORÍA 2] Validando existencia física del archivo local...")
            if not os.path.exists(ruta_local):
                print(f"⚠️ [AUDITORÍA] Archivo local no encontrado en la ruta: {ruta_local}")
                return False
            print("🔍 [AUDITORÍA 2] Archivo local localizado correctamente.")

            print("🔍 [AUDITORÍA 3] Sanitizando la ruta destino en Dropbox...")
            if not ruta_dropbox.startswith("/"):
                ruta_dropbox = f"/{ruta_dropbox}"
            print(f"🔍 [AUDITORÍA 3] Ruta de Dropbox lista: {ruta_dropbox}")

            try:
                print(f"🔍 [AUDITORÍA 4] Abriendo archivo '{ruta_local}' en modo lectura binaria...")
                with open(ruta_local, "rb") as f:
                    print("🔍 [AUDITORÍA 4.1] Archivo abierto. Procediendo a leer con f.read()...")
                    contenido = f.read()
                    peso_kb = len(contenido) / 1024
                print(f"🔍 [AUDITORÍA 4.2] Lectura exitosa. Archivo en memoria ram. Peso: {peso_kb:.2f} KB.")

                # --- AQUÍ ES DONDE PROBABLEMENTE SE ESTÁ CONGELANDO ---
                print("⚠️ [AUDITORÍA 5] DISPARANDO API DE DROPBOX: self.dbx.files_upload()... [AQUÍ SE PUEDE COLGAR]")
                
                self.dbx.files_upload(
                    contenido, 
                    ruta_dropbox, 
                    mode=WriteMode.overwrite
                )
                
                print("✅ [AUDITORÍA 6] self.dbx.files_upload() EJECUTADO CORRECTAMENTE (No se congeló).")
                # -----------------------------------------------------

                print(f"📤 [Dropbox Cloud] Sincronizado con éxito en: {ruta_dropbox}")
                return True

            except ApiError as e:
                msg = f"Error de API en Dropbox al subir ({ruta_dropbox}): {e}"
                print(f"❌ [AUDITORÍA - EXCEPCIÓN DE API DROPBOX] {msg}")
                self.logger.registrar_log("ERROR", msg)
                return False
            except Exception as e:
                msg = f"Error inesperado al subir ({ruta_dropbox}): {e}"
                print(f"❌ [AUDITORÍA - EXCEPCIÓN GENERAL] {msg}")
                self.logger.registrar_log("ERROR", msg)
                return False
            finally:
                print("🔍 [AUDITORÍA FINAL] Saliendo del bloque de la función 'subir_archivo'.")
    def descargar_archivo(self, ruta_dropbox: str, ruta_local_destino: str) -> bool:
        """
        Descarga un archivo desde Dropbox al almacenamiento local.
        Maneja de forma controlada el escenario donde el archivo del mes aún no existe.
        """
        if not self.dbx:
            self._conectar()
            if not self.dbx: return False

        if not ruta_dropbox.startswith("/"):
            ruta_dropbox = f"/{ruta_dropbox}"

        try:
            self.dbx.files_download_to_file(ruta_local_destino, ruta_dropbox)
            print(f"📥 [Dropbox Cloud] Descargado con éxito: {ruta_dropbox}")
            return True
        except ApiError as e:
            # Si el archivo no existe en la nube (ej: inicio de mes), 
            # retornamos False limpiamente para usar la plantilla base.
            if e.error.is_path() and e.error.get_path().is_not_found():
                print(f"⚠️ [Dropbox Cloud] El archivo '{ruta_dropbox}' no existe en la nube. Se procesará localmente.")
                return False
                
            msg = f"Error de API al descargar de Dropbox ({ruta_dropbox}): {e}"
            print(f"❌ {msg}")
            self.logger.registrar_log("ERROR", msg)
            return False
        except Exception as e:
            msg = f"Error inesperado al descargar ({ruta_dropbox}): {e}"
            print(f"❌ {msg}")
            self.logger.registrar_log("ERROR", msg)
            return False

    def respaldar_bd_local(self, ruta_local_db: str, ruta_dropbox: str = "backups/usuarios.db") -> bool:
        """Copia la base SQLite local a Dropbox como respaldo de producción."""
        if not os.path.exists(ruta_local_db):
            print(f"⚠️ [Dropbox] No existe la base local para respaldar: {ruta_local_db}")
            return False

        if not self.dbx:
            self._conectar()
            if not self.dbx:
                return False

        try:
            with open(ruta_local_db, "rb") as archivo:
                contenido = archivo.read()

            if not ruta_dropbox.startswith("/"):
                ruta_dropbox = f"/{ruta_dropbox.lstrip('/')}"

            self.dbx.files_upload(contenido, ruta_dropbox, mode=WriteMode.overwrite)
            print(f"💾 [Dropbox] Respaldo realizado correctamente en {ruta_dropbox}")
            self.logger.registrar_log("INFO", f"Base de datos respaldada en Dropbox: {ruta_dropbox}")
            return True
        except Exception as e:
            msg = f"No se pudo respaldar la base de datos en Dropbox: {e}"
            print(f"❌ {msg}")
            self.logger.registrar_log("ERROR", msg)
            return False

    def restaurar_bd_desde_dropbox(self, ruta_local_db: str, ruta_dropbox: str = "backups/usuarios.db") -> bool:
        """Descarga el respaldo de Dropbox a la base local si existe."""
        if not self.dbx:
            self._conectar()
            if not self.dbx:
                return False

        if not ruta_dropbox.startswith("/"):
            ruta_dropbox = f"/{ruta_dropbox.lstrip('/')}"

        os.makedirs(os.path.dirname(os.path.abspath(ruta_local_db)), exist_ok=True)
        destino_temporal = f"{ruta_local_db}.tmp"

        try:
            self.dbx.files_download_to_file(destino_temporal, ruta_dropbox)
            if os.path.exists(ruta_local_db):
                respaldo_anterior = f"{ruta_local_db}.bak"
                if os.path.exists(respaldo_anterior):
                    os.remove(respaldo_anterior)
                shutil.copy2(ruta_local_db, respaldo_anterior)
            os.replace(destino_temporal, ruta_local_db)
            print(f"📥 [Dropbox] Base de datos restaurada localmente desde {ruta_dropbox}")
            self.logger.registrar_log("INFO", f"Base de datos restaurada desde Dropbox: {ruta_dropbox}")
            return True
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                print(f"⚠️ [Dropbox] No existe respaldo en la nube en {ruta_dropbox}; se usa la base local actual.")
                return False
            msg = f"Error al restaurar la base desde Dropbox: {e}"
            print(f"❌ {msg}")
            self.logger.registrar_log("ERROR", msg)
            return False
        except Exception as e:
            msg = f"Error inesperado al restaurar la base desde Dropbox: {e}"
            print(f"❌ {msg}")
            self.logger.registrar_log("ERROR", msg)
            if os.path.exists(destino_temporal):
                os.remove(destino_temporal)
            return False