# admin_cli.py

import sys
import os
import time  # <--- Importamos la librería de tiempo de Python

# Asegurar que Python encuentre la carpeta 'src'
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from database.connection import DBConnection

class AdminCLI:
    def __init__(self):
        self.db = DBConnection()

    def mostrar_menu(self):
        print("\n⚙️  === PANEL DE CONTROL [EASYHAMMER STUDIO] ===")
        print("1. 👥 Consultar todos los usuarios")
        print("2. 🔑 Autorizar / Crear un Vendedor (Asignar Ruta)")
        print("3. 🚫 Dar de baja / Bloquear un usuario")
        print("4. 🪵 Consultar últimos logs de la DB")
        print("5. 🗑️  Borrar TODOS los logs de la DB")
        print("6. 💥 LIMPIEZA DE PRUEBAS: Borrar todos los datos de cobros")
        print("7. 👑 Cambiar Rango (Vendedor <--> Supervisor) [FÁCIL]") # <-- Nueva opción
        print("0. 🚪 Salir")
        print("================================================")

    def consultar_usuarios(self):
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT telegram_id, nombre_telegram, ruta, rol, estado FROM usuarios")
        usuarios = cursor.fetchall()
        conexion.close()

        if not usuarios:
            print("\nℹ️ No hay usuarios registrados en la base de datos.")
            time.sleep(2)  # Pausa de lectura
            return

        print("\n┌" + "─"*75 + "┐")
        print(f"│ {'ID Telegram':<15} │ {'Nombre':<20} │ {'Ruta':<6} │ {'Rol':<12} │ {'Estado':<10} │")
        print("├" + "─"*75 + "┤")
        for u in usuarios:
            ruta = str(u[2]) if u[2] is not None else "N/A"
            print(f"│ {u[0]:<15} │ {u[1]:<20} │ {ruta:<6} │ {u[3]:<12} │ {u[4]:<10} │")
        print("└" + "─"*75 + "┘")
        
        # Le damos un respiro al programador para que analice la tabla
        print("\n⏳ Volviendo al menú principal en 2 segundos...")
        time.sleep(2)

    def autorizar_o_crear_usuario(self):
        telegram_id = input("\n🔢 Ingresa el ID de Telegram del usuario: ").strip()
        nombre = input("👤 Ingresa el nombre/alias del usuario: ").strip()
        ruta = input("🗺️  Ingresa el número de ruta (o presiona Enter si es Supervisor): ").strip()
        
        rol = "VENDEDOR"
        estado = "AUTORIZADO"
        ruta_val = int(ruta) if ruta else None
        if not ruta_val:
            rol = "SUPERVISOR"

        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO usuarios (telegram_id, nombre_telegram, ruta, rol, estado)
                VALUES (?, ?, ?, ?, ?)
            ''', (telegram_id, nombre, ruta_val, rol, estado))
            conexion.commit()
            print(f"\n✅ Usuario {nombre} guardado y AUTORIZADO con éxito.")
        except Exception as e:
            print(f"\n❌ Error al guardar usuario: {e}")
        finally:
            conexion.close()
        
        time.sleep(2)  # Pausa antes del menú

    def gestionar_supervisor_facil(self):
        """Lista usuarios activos/pendientes para alternar su rol de supervisor fácilmente."""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        
        # Traemos solo los usuarios que no estén bloqueados
        cursor.execute("SELECT telegram_id, nombre_telegram, rol, ruta FROM usuarios WHERE estado != 'BLOQUEADO'")
        usuarios = cursor.fetchall()
        
        if not usuarios:
            print("\nℹ️ No hay usuarios activos en la base de datos para ascender/degradar.")
            conexion.close()
            time.sleep(2)
            return

        print("\n👑 --- SELECCIÓN RÁPIDA DE RANGOS ---")
        for i, u in enumerate(usuarios, 1):
            ruta_str = f"Ruta {u[3]}" if u[3] is not None else "Global"
            print(f"{i}. 👤 {u[1]} | Rol: [{u[2]}] | Alcance: {ruta_str} | ID: {u[0]}")
        print("=====================================")
        
        seleccion = input("👉 Elige el número del usuario que deseas cambiar (o Enter para cancelar): ").strip()
        
        if not seleccion:
            conexion.close()
            return
            
        try:
            idx = int(seleccion) - 1
            if idx < 0 or idx >= len(usuarios):
                print("\n⚠️ Número fuera de rango.")
                conexion.close()
                time.sleep(1.5)
                return
        except ValueError:
            print("\n⚠️ Entrada inválida. Debes poner un número.")
            conexion.close()
            time.sleep(1.5)
            return

        # Cargamos los datos del usuario elegido
        telegram_id_sel, nombre_sel, rol_actual, ruta_actual = usuarios[idx]
        
        # LOGICA DE SWITCHEOTOGGLE
        if rol_actual == "VENDEDOR":
            # ASCENSO: Pasa a ser Supervisor (Se le quita la ruta asignada porque es global)
            cursor.execute(
                "UPDATE usuarios SET rol = 'SUPERVISOR', ruta = NULL, estado = 'AUTORIZADO' WHERE telegram_id = ?", 
                (telegram_id_sel,)
            )
            print(f"\n🚀 ¡ASCENDIDO! *{nombre_sel}* ahora es SUPERVISOR (Acceso Global).")
        else:
            # DEGRADACIÓN: Vuelve a ser Vendedor, por ende OBLIGATORIAMENTE requiere una ruta
            print(f"\n📉 Quitando rango de supervisor a *{nombre_sel}*...")
            nueva_ruta = input("🗺️  Asigna el número de ruta para este vendedor (Ej: 10, 15, 17): ").strip()
            
            try:
                ruta_val = int(nueva_ruta)
            except ValueError:
                print("\n❌ Error: Un vendedor activo necesita un número de ruta válido. Operación cancelada.")
                conexion.close()
                time.sleep(2)
                return
                
            cursor.execute(
                "UPDATE usuarios SET rol = 'VENDEDOR', ruta = ? WHERE telegram_id = ?", 
                (ruta_val, telegram_id_sel)
            )
            print(f"\n💼 Cambiado con éxito. *{nombre_sel}* ahora es VENDEDOR de la Ruta {ruta_val}.")

        conexion.commit()
        conexion.close()
        time.sleep(2.5)

    def bloquear_usuario(self):
        telegram_id = input("\n🔢 Ingresa el ID de Telegram a bloquear: ").strip()
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("UPDATE usuarios SET estado = 'BLOQUEADO' WHERE telegram_id = ?", (telegram_id,))
        if cursor.rowcount > 0:
            print(f"\n🚫 Usuario {telegram_id} bloqueado de forma inmediata.")
        else:
            print("\n⚠️ No se encontró ningún usuario con ese ID.")
        conexion.commit()
        conexion.close()
        
        time.sleep(2)

    def consultar_logs(self):
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT timestamp, nivel, mensaje FROM logs_sistema ORDER BY id DESC LIMIT 20")
        logs = cursor.fetchall()
        conexion.close()

        if not logs:
            print("\nℹ️ La tabla de logs está vacía.")
            time.sleep(2)
            return

        print("\n📜 --- ÚLTIMOS 20 LOGS DEL SISTEMA ---")
        for log in logs:
            print(f"[{log[0]}] {log[1]}: {log[2]}")
        
        print("\n⏳ Volviendo al menú principal en 2 segundos...")
        time.sleep(2)

    def borrar_logs(self):
        confirmar = input("\n⚠️ ¿Estás seguro de vaciar todos los logs? (s/n): ").strip().lower()
        if confirmar == 's':
            conexion = self.db.obtener_conexion()
            cursor = conexion.cursor()
            cursor.execute("DELETE FROM logs_sistema")
            conexion.commit()
            conexion.close()
            print("\n🗑️ Historial de logs completamente limpio.")
            time.sleep(2)

    def limpiar_datos_prueba(self):
        print("\n🚨 ALERTA: Esto borrará todos los reportes diarios de los vendedores de forma irreversible.")
        confirmar = input("¿Estás COMPLETAMENTE seguro de resetear las tablas de cobros? (s/n): ").strip().lower()
        if confirmar == 's':
            conexion = self.db.obtener_conexion()
            cursor = conexion.cursor()
            try:
                cursor.execute("DELETE FROM registros_diarios")
                conexion.commit()
                print("\n💥 Datos de cobranzas eliminados. Base de datos lista para pruebas limpias.")
            except Exception as e:
                print(f"\n❌ Error al limpiar datos: {e}")
            finally:
                conexion.close()
            
            time.sleep(2)

    def ejecutar(self):
        while True:
            self.mostrar_menu()
            opcion = input("👉 Selecciona una opción: ").strip()
            
            if opcion == "1":
                self.consultar_usuarios()
            elif opcion == "2":
                self.autorizar_o_crear_usuario()
            elif opcion == "3":
                self.bloquear_usuario()
            elif opcion == "4":
                self.consultar_logs()
            elif opcion == "5":
                self.borrar_logs()
            elif opcion == "6":
                self.limpiar_datos_prueba()
            elif opcion == "7":
                self.gestionar_supervisor_facil() # <-- Enlazamos la función aquí
            elif opcion == "0":
                print("\n👋 Saliendo del Panel de Control. ¡A tirar código, mi king!")
                break
            else:
                print("\n⚠️ Opción inválida. Intenta de nuevo.")
                time.sleep(1.5)

if __name__ == "__main__":
    cli = AdminCLI()
    cli.ejecutar()