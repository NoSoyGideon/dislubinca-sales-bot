# src/database/init_db.py

import sqlite3
import os

# CONSTANTE DE CONTROL PRINCIPAL
# True  = Ejecuta las verificaciones de columnas y repara la DB en caliente.
# False = Salto rápido directo a producción (Máxima velocidad).
EJECUTAR_MIGRACION_AL_ARRANCAR = True

def inicializar_base_de_datos():
    db_path = os.getenv(
        "DB_PATH",
        os.path.join(os.path.dirname(__file__), "usuarios.db")
    )
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conexion = sqlite3.connect(db_path)
    cursor = conexion.cursor()

    # Forzar el uso estricto de llaves foráneas en SQLite[cite: 2]
    cursor.execute("PRAGMA foreign_keys = ON;")

    # ==========================================
    #       1. CREACIÓN DE TABLAS MAESTRAS
    # ==========================================
    
    # 👥 TABLA A: CONFIGURACIÓN DE RUTAS Y USUARIOS
    # Ahora las rutas están pre-configuradas. Los vendedores "reclaman" la ruta al loguearse.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            ruta INTEGER PRIMARY KEY,                  -- La Ruta manda (Ej: 10, 15, 21, 30)
            telegram_id INTEGER UNIQUE DEFAULT NULL,   -- NULL si el vendedor no se ha registrado aún
            nombre_telegram TEXT NOT NULL,             -- "Ruta 21" por defecto, o su nombre real
            rol TEXT DEFAULT 'VENDEDOR',
            estado TEXT DEFAULT 'PENDIENTE',
            bajo_responsabilidad_supervisor BOOLEAN DEFAULT 1 -- 1 = TRUE, 0 = FALSE (Caso R-21)
        )
    ''')

    # 🎯 TABLA B: CUOTAS MENSUALES (Esquema EAV Escalable)
    # Soporta UDVD, Cobranza, Activaciones y cualquier cuota loca que inventen después.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cuotas_mensuales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            periodo TEXT NOT NULL,                     -- Formato: 'YYYY-MM' (Ej: '2026-02')
            ruta_id INTEGER,                           -- Vinculado a usuarios(ruta). NULL = Cuota Total Empresa
            tipo_cuota TEXT NOT NULL,                  -- 'UDVD', 'COBRANZA', 'ACTIVACIONES', etc.
            valor_cuota REAL NOT NULL,                 -- Monto asignado
            FOREIGN KEY (ruta_id) REFERENCES usuarios(ruta) ON DELETE CASCADE,
            UNIQUE(periodo, ruta_id, tipo_cuota)       -- Evita duplicar la misma cuota en el mes
        )
    ''')

    # 📊 TABLA C: OPERACIONES DIARIAS CORRECAMINOS (Unificada Mañana y Noche)
    # Almacena los 6 campos métricos diarios + el desglose contable y la tasa BCV.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operaciones_diarias (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,                       -- Formato: 'YYYY-MM-DD'
            ruta_id INTEGER NOT NULL,                  -- Vinculado a usuarios(ruta)
            
            -- Bloque Venta UDVD
            meta_udvd REAL DEFAULT 0.0,
            real_udvd REAL DEFAULT 0.0,
            

            
            
            -- Bloque Activaciones
            meta_activaciones INTEGER DEFAULT 0,
            real_activaciones INTEGER DEFAULT 0,
            
            -- Bloque Cobranza (CxC)
            meta_cxc REAL DEFAULT 0.0,
            real_cxc REAL DEFAULT 0.0,
            
            -- Bloque Financiero Nocturno (Desglose de Caja)
            efectivo_usd REAL DEFAULT 0.0,
            zelle_usd REAL DEFAULT 0.0,
            bs_cambiados_usd REAL DEFAULT 0.0,
            tasa_bcv REAL DEFAULT 0.0,                 -- Tasa del día oficial de la cobranza
            --
            -- Bloque Venta GRUPO_AMIGO
            meta_amigo REAL DEFAULT 0.0,
            real_amigo REAL DEFAULT 0.0,
            
            -- Bloque Venta GRUPO_CELTA
            meta_celta REAL DEFAULT 0.0,
            real_celta REAL DEFAULT 0.0,
            
            timestamp_registro DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (ruta_id) REFERENCES usuarios(ruta) ON DELETE CASCADE,
            UNIQUE(fecha, ruta_id)                     -- Un solo registro operativo por ruta al día
        )
    ''')

    # 🪵 TABLA D: LOGS PARA AUDITORÍA[cite: 1]
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs_sistema (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            nivel TEXT,
            mensaje TEXT
        )
    ''')

    # 🧹 TABLA E: CONTROL DE MANTENIMIENTOS MENSUALES
    # Impide repetir una purga si el bot se reinicia o el job se dispara dos veces.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mantenimientos_mensuales (
            periodo TEXT PRIMARY KEY,                  -- Formato: 'YYYY-MM'
            ejecutado_en DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    conexion.commit()

    # ==========================================
    #   2. SISTEMA DE MIGRACIONES EN CALIENTE
    # ==========================================
    if EJECUTAR_MIGRACION_AL_ARRANCAR:
        # Inspeccionamos estructuralmente la tabla unificada por si acaso muta en el futuro
        cursor.execute("PRAGMA table_info(operaciones_diarias);")
        columnas_actuales = [col[1] for col in cursor.fetchall()]

        # 🚀 FUTURAS EXPANSIONES (Si el negocio pide otra métrica diaria después, solo la agregas aquí)
        # Formato: "nombre_columna": "TIPO_DE_DATO DEFAULT DEFECTO"
        campos_futuros_operaciones = {
            # "meta_visitas": "INTEGER DEFAULT 0",
            # "real_visitas": "INTEGER DEFAULT 0",
        }

        cambios = False
        for col, tipo in campos_futuros_operaciones.items():
            if col not in columnas_actuales:
                cursor.execute(f"ALTER TABLE operaciones_diarias ADD COLUMN {col} {tipo};")
                print(f"⚙️ [MIGRACIÓN] Inyectando columna futura '{col}' en caliente.")
                cambios = True

        if cambios:
            conexion.commit()

    conexion.close()
    print("🚀 [EasyHammer Studio] Base de Datos HÍBRIDA & EVOLUTIVA inicializada con éxito.")

if __name__ == "__main__":
    inicializar_base_de_datos()