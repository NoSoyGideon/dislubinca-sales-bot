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
    FILA_META_UDVD = 11
    FILA_META_VISITAS = 14
    FILA_META_CXC = 17

    # Filas de Cierre Nocturno (Logros Reales)
    FILA_REAL_UDVD = 12
    FILA_REAL_VISITAS = 15
    FILA_REAL_CXC = 18

    # Filas del Promesa / Objetivo del Día Previo (Hoja Anterior)
    FILA_PREVIO_UDVD = 24
    FILA_PREVIO_VISITAS = 25
    FILA_PREVIO_CXC = 26

    # 💵 Matriz de Relevo de Cobranza Semanal
    COLUMNA_BUSQUEDA_RUTA = "P"
    FILA_INICIO_RUTAS = 9
    FILA_FIN_RUTAS = 20

    COLUMNAS_DIAS_COBRANZA = {
        0: "R",  # Lunes
        1: "S",  # Martes
        2: "T",  # Miércoles
        3: "U"   # Jueves
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
    PLANTILLA_BASE_NOMBRE = "REPORTE_DIARIO_DE_COBRANZA_BASE.xlsm"
    MAIN_FOLDER = "/REPORTE DIARIO DE COBRANZA/"
    PESTANA_PLANTILLA_BASE = "Semana I"

    # Columnas asociadas a cada Ruta
    COLUMNAS_RUTAS = {
        10: "D",
        15: "E",
        17: "F",
        21: "G",
        30: "H",
        32: "I",
        39: "J"
    }

    # Desplazamiento geométrico de celdas por día (0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes)
    CONFIG_DIAS = {
        0: {"encabezado": "C3", "efectivo": 6, "zelle": 7, "bs": 8},
        1: {"encabezado": "C15", "efectivo": 18, "zelle": 19, "bs": 20},
        2: {"encabezado": "C27", "efectivo": 30, "zelle": 31, "bs": 32},
        3: {"encabezado": "C38", "efectivo": 41, "zelle": 42, "bs": 43},
        4: {"encabezado": "C49", "efectivo": 52, "zelle": 53, "bs": 54},
    }

    NOMBRES_DIAS_TEXTO = {
        0: "LUNES",
        1: "MARTES",
        2: "MIERCOLES",
        3: "JUEVES",
        4: "VIERNES"
    }