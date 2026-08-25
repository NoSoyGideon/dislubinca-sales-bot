# src/config/excel_map_config.py

class ContactoMatutinoMap:
    """
    📍 Mapa de Coordenadas del Libro 'CONTACTO MATUTINO'
    Cualquier cambio de celdas o filas en la plantilla de Excel 
    se modifica ÚNICAMENTE en esta clase.
    """
    # Nombres de Pestañas Protegidas del Mantenimiento
    PESTANA_CONTROL = "CONTROL"
    PESTANA_PLANTILLA = "Plantilla"
    
    # Celda donde se inyecta la fecha en la hoja del día
    CELDA_FECHA_G4 = "G4"
    CELDA_DIAS_TRANSCURRIDOS = "D4"

    # Mapeo de Columnas por Ruta (Pestaña Diaria)
    COLUMNAS_RUTAS = {
        10: "E",
        15: "F",
        17: "G",
        21: "K",
        26: "L",
        30: "H",
        32: "I",
        39: "J"
    }

    # Filas de Plan Matutino (Objetivos del Día Actual)
    FILA_META_UDVD = 16
    FILA_META_VISITAS = 19
    FILA_META_CXC = 22
    FILA_META_AMIGO = 25
    FILA_META_CELTA = 28

    # Filas de Cierre Nocturno (Logros Reales)
    FILA_REAL_UDVD = 17
    FILA_REAL_VISITAS = 20
    FILA_REAL_CXC = 23
    FILA_REAL_AMIGO = 26
    FILA_REAL_CELTA = 29

    # Filas del Promesa / Objetivo del Día Previo (Hoja Anterior)
    FILA_PREVIO_UDVD = 33
    FILA_PREVIO_VISITAS = 34
    FILA_PREVIO_CXC = 35

    # 💵 Matriz de Relevo de Cobranza Semanal
    COLUMNA_BUSQUEDA_RUTA = "P"
    FILA_INICIO_RUTAS = 9
    FILA_FIN_RUTAS = 20

    COLUMNAS_DIAS_COBRANZA = {
        
        0: "S",  # Lunes
        1: "T",  # Martes
        2: "U",  # Miércoles
        3: "V",   # Jueves
        4: "R"   # Viernes
    }

    # 📊 Pestaña CONTROL (Cuotas Mensuales)
    FILA_INICIO_CONTROL = 13
    FILA_FIN_CONTROL = 20
    COLUMNA_CONTROL_RUTA = "O"
    COLUMNA_CONTROL_UDVD = "R"
    COLUMNA_CONTROL_CXC = "S"
    COLUMNA_CONTROL_VISITAS = "T"


# src/config/excel_map_config.py

# src/config/excel_map_config.py

class CobranzaDiariaMap:
    """
    📍 Mapa de Coordenadas del Libro 'REPORTE DIARIO DE COBRANZA'
    Cualquier cambio de celdas o filas en la plantilla de Excel
    se modifica ÚNICAMENTE en esta clase.
    """
    PLANTILLA_BASE_NOMBRE = "REPORTE_DIARIO_DE_COBRANZA_BASE.xlsx"
    MAIN_FOLDER = "/REPORTE DIARIO DE COBRANZA/"
    PESTANA_PLANTILLA_BASE = "Semana I"

    # Columnas asociadas a cada Ruta
    COLUMNAS_RUTAS = {
        10: "D",
        15: "E",
        17: "F",
        30: "G",
        32: "H",
        39: "I",
        21: "J"
    }

    # Desplazamiento geométrico de celdas por día (0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes)
    CONFIG_DIAS = {
        0: {"encabezado": "C3", "efectivo": 7, "zelle": 8, "bs": 9},
        1: {"encabezado": "C15", "efectivo": 19, "zelle": 20, "bs": 21},
        2: {"encabezado": "C27", "efectivo": 31, "zelle": 32, "bs": 33},
        3: {"encabezado": "C38", "efectivo": 42, "zelle": 43, "bs": 44},
        4: {"encabezado": "C49", "efectivo": 53, "zelle": 54, "bs": 55},
    }

    NOMBRES_DIAS_TEXTO = {
        0: "LUNES",
        1: "MARTES",
        2: "MIERCOLES",
        3: "JUEVES",
        4: "VIERNES"
    }