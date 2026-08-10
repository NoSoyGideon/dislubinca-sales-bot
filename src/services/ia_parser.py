import json
from google import genai
from google.genai import types

from config.config import Config
from database.connection import DBConnection
from database.logs_repo import LogsRepository


class IAParser:
    def __init__(self):
        # 1. Cargamos configuración y Logger
        self.config = Config()
        conector = DBConnection()
        self.logger = LogsRepository(conector)

        # 2. Inicializar el cliente oficial del nuevo SDK
        api_key = self.config.obtener_api_key()
        self.client = genai.Client(api_key=api_key) if api_key else None

        # 3. Prompt con esquema PLANO para reportes individuales (Vendedores)
        self.system_instruction = """
Eres un asistente ultra preciso de extracción de datos para la empresa Disulubinca. Tu tarea es recibir reportes de texto libre en formatos de plantilla o conversación enviados por vendedores y transformarlos ESTRICTAMENTE en un objeto JSON estructurado.

### REGLAS CRÍTICAS DE EXTRACCIÓN DE DATOS:

1. **UNIDADES / UDVD:**
   - Si es Plan Matutino, asígnalo a `meta_udvd`.
   - Si es Cierre Nocturno, asígnalo a `real_udvd`.
   - Extrae el número de unidades PRINCIPALMENTE del campo "Lubricantes" (Ej: "Lubricantes = 120" -> 120).
   - IGNORA acumulados semanales (Ej: "19012UDVD").

2. **VISITAS / ACTIVACIONES:**
   - Si es Plan Matutino, asígnalo a `meta_activaciones`.
   - Si es Cierre Nocturno, asígnalo a `real_activaciones`.

3. **COBRANZAS / CXC:**
   - Si es Plan Matutino, la meta va en `meta_cxc`.
   - Si es Cierre Nocturno, el total va en `real_cxc`.

4. **DESGLOSE DE CAJA (Solo Cierre Nocturno):**
   - Extrae `efectivo_usd`, `zelle_usd`, `bs_cambiados_usd` y `tasa_bcv` si están presentes.

5. **FECHA Y RUTA:**
   - `fecha_mencionada`: Formato "YYYY-MM-DD" o null.
   - `ruta`: Número de la ruta (int) o null.

---

### TIPOS DE INTENCIÓN (`tipo_intencion`):
- `PLAN_MATUTINO`: Si incluye plan/metas, "PLAN del dia", o proyecciones matutinas.
- `REPORTE_FULL_NOCHE`: Si incluye "Cierre del dia", "Cobranza", o logros reales de la noche.
- `AJUSTE_INDIVIDUAL`: Si pide sumar, restar o modificar un dato puntual.

### DÍA DE DESTINO (`dia_destino`):
- `AYER`: Si menciona "ayer".
- `HOY`: Si menciona "hoy", fecha de hoy o por defecto.
- `MANANA`: Si menciona "mañana" o anticipo.

---

### FORMATO JSON STRICTO DE RESPUESTA:
{
  "ruta": null,
  "fecha_mencionada": null,
  "tipo_intencion": "PLAN_MATUTINO",
  "dia_destino": "HOY",
  "meta_udvd": 0,
  "meta_cxc": 0.0,
  "meta_activaciones": 0,
  "real_udvd": 0,
  "real_cxc": 0.0,
  "real_activaciones": 0,
  "efectivo_usd": 0.0,
  "zelle_usd": 0.0,
  "bs_cambiados_usd": 0.0,
  "tasa_bcv": 0.0
}
""" 

        # 4. Prompt para Carga Masiva de Cuotas / Metas Mensuales (Supervisor)
        self.system_instruction_supervisor = """
Eres un asistente experto en extracción masiva de datos para la empresa Disulubinca.
Tu objetivo es analizar textos libres que contengan las cuotas/metas asignadas a múltiples rutas y estructurarlos en un formato JSON específico.

### REGLAS DE EXTRACCIÓN:
1. **IDENTIFICACIÓN DE RUTAS:**
   - Detecta cualquier mención de ruta (ejemplos: "r10", "R-10", "ruta 10", "Ruta15"). Extrae únicamente el NÚMERO de la ruta como un Entero (int) o String numérico.
   
2. **MÉTRICAS POR RUTA:**
    - No es obligatorio que el mensaje contenga las tres métricas. Si solo indican una o dos, extrae las presentes y asigna 0 a las faltantes.
   - `udvd`: Unidades a vender (cajas, bidones, lubricantes, UDVD). Si no se especifica, usa 0.
   - `cobranza`: Monto a cobrar / meta de cobranza / CXC ($ / USD). Si no se especifica, usa 0.0.
   - `visitas`: Cantidad de clientes a visitar, activaciones o clientes nuevos. Si no se especifica, usa 0.

3. **ESTRUCTURA DE SALIDA:**
   Debes responder ÚNICA Y EXCLUSIVAMENTE con un objeto JSON en la raíz con la clave `lote_cuotas`.
   Dentro de `lote_cuotas`, cada clave debe ser el ID de la ruta (numérico) y su valor un diccionario con las tres métricas.

### FORMATO JSON ESTRICTO DE RESPUESTA:
{
  "lote_cuotas": {
    "10": {
      "udvd": 23213,
      "cobranza": 21312.0,
      "visitas": 32
    },
    "15": {
      "udvd": 11213,
      "cobranza": 4412.0,
      "visitas": 12
    }
  }
}
"""

    def _normalizar_respuesta(self, datos_raw: dict) -> dict:
        """
        Garantiza que el diccionario tenga todos los campos esperados por report_flow.py,
        evitando KeyError y nulos impredecibles.
        """
        esquema_defecto = {
            "ruta": None,
            "fecha_mencionada": None,
            "tipo_intencion": "PLAN_MATUTINO",
            "dia_destino": "HOY",
            "meta_udvd": 0,
            "meta_cxc": 0.0,
            "meta_activaciones": 0,
            "real_udvd": 0,
            "real_cxc": 0.0,
            "real_activaciones": 0,
            "efectivo_usd": 0.0,
            "zelle_usd": 0.0,
            "bs_cambiados_usd": 0.0,
            "tasa_bcv": 0.0
        }

        if not isinstance(datos_raw, dict):
            return esquema_defecto

        resultado = {}
        for clave, valor_defecto in esquema_defecto.items():
            valor = datos_raw.get(clave)
            if valor is None:
                resultado[clave] = valor_defecto
            else:
                try:
                    if isinstance(valor_defecto, float):
                        resultado[clave] = float(valor)
                    elif isinstance(valor_defecto, int) and not isinstance(valor_defecto, bool):
                        resultado[clave] = int(valor)
                    else:
                        resultado[clave] = valor
                except (ValueError, TypeError):
                    resultado[clave] = valor_defecto

        return resultado
    
    def _normalizar_respuesta_cuotas(self, datos_raw: dict) -> dict:
        """
        Normaliza la respuesta masiva de cuotas enviada por el supervisor.
        Retorna la estructura sanitizada: {"lote_cuotas": { int_ruta: {"udvd": int, "cobranza": float, "visitas": int} }}
        """
        if not isinstance(datos_raw, dict):
            return {"lote_cuotas": {}}

        lote_raw = datos_raw.get("lote_cuotas", {})
        if not isinstance(lote_raw, dict):
            return {"lote_cuotas": {}}

        lote_limpio = {}
        for ruta_key, valores in lote_raw.items():
            try:
                # Sanitizar la clave de la ruta a un ID numérico limpio
                ruta_id = int(str(ruta_key).lower().replace("r", "").replace("-", "").strip())
            except ValueError:
                continue  # Omitir claves no convertibles

            if isinstance(valores, dict):
                try:
                    udvd = int(valores.get("udvd", 0) or 0)
                except (ValueError, TypeError):
                    udvd = 0

                try:
                    cobranza = float(valores.get("cobranza", 0.0) or 0.0)
                except (ValueError, TypeError):
                    cobranza = 0.0

                try:
                    visitas = int(valores.get("visitas", 0) or 0)
                except (ValueError, TypeError):
                    visitas = 0

                lote_limpio[ruta_id] = {
                    "udvd": udvd,
                    "cobranza": cobranza,
                    "visitas": visitas
                }

        return {"lote_cuotas": lote_limpio}

    def parsear_texto_libre(self, texto_vendedor: str) -> dict:
        """Envía el texto a Gemini Flash y devuelve un diccionario normalizado para reporte diario"""
        if not self.client:
            self.logger.registrar_log("ERROR", "No se pudo inicializar genai.Client. Falta la API Key.")
            return None

        self.logger.registrar_log("INFO", "Iniciando petición a Gemini Flash para parsear reporte...")

        texto_respuesta = ""
        try:
            config = types.GenerateContentConfig(
                system_instruction=self.system_instruction,
                temperature=0.1,
                response_mime_type="application/json"
            )

            respuesta = self.client.models.generate_content(
                model="gemini-3.6-flash",
                contents=texto_vendedor,
                config=config
            )

            texto_respuesta = respuesta.text.strip()
            datos_json = json.loads(texto_respuesta)

            return self._normalizar_respuesta(datos_json)

        except json.JSONDecodeError as json_err:
            self.logger.registrar_log("ERROR", f"Gemini no devolvió un JSON limpio: {json_err}. Respuesta cruda: {texto_respuesta}")
            return None
        except Exception as e:
            self.logger.registrar_log("ERROR", f"Fallo crítico en la comunicación con Gemini: {e}")
            return None
        
    def parsear_cuotas(self, texto_supervisor: str) -> dict:
        """Envía el texto del supervisor a Gemini Flash y devuelve un diccionario normalizado de cuotas por lote"""
        if not self.client:
            self.logger.registrar_log("ERROR", "No se pudo inicializar genai.Client. Falta la API Key.")
            return None

        self.logger.registrar_log("INFO", "Iniciando petición a Gemini Flash para parsear cuotas masivas...")

        texto_respuesta = ""
        try:
            config = types.GenerateContentConfig(
                system_instruction=self.system_instruction_supervisor, # 👈 Usa la instrucción de supervisor
                temperature=0.1,
                response_mime_type="application/json"
            )

            respuesta = self.client.models.generate_content(
                model="gemini-3.6-flash",
                contents=texto_supervisor,
                config=config
            )

            texto_respuesta = respuesta.text.strip()
            datos_json = json.loads(texto_respuesta)

            # Normalizar con la capa defensiva de cuotas
            datos_normalizados = self._normalizar_respuesta_cuotas(datos_json)

            self.logger.registrar_log(
                "INFO",
                f"Parseo masivo de cuotas exitoso. Total de rutas procesadas: {len(datos_normalizados.get('lote_cuotas', {}))}."
            )
            return datos_normalizados

        except json.JSONDecodeError as json_err:
            self.logger.registrar_log("ERROR", f"Gemini no devolvió un JSON limpio en cuotas: {json_err}. Respuesta cruda: {texto_respuesta}")
            return None
        except Exception as e:
            self.logger.registrar_log("ERROR", f"Fallo crítico en la comunicación con Gemini al parsear cuotas: {e}")
            return None