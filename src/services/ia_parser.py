import json
import google.generativeai as genai
from config.config import Config
from database.connection import DBConnection
from database.logs_repo import LogsRepository

class IAParser:
    def __init__(self):
        # 1. Cargamos configuración y Logger
        self.config = Config()
        conector = DBConnection()
        self.logger = LogsRepository(conector)
        
        # 2. Configurar la API de Google con tu llave secreta
        api_key = self.config.obtener_api_key()
        if api_key:
            genai.configure(api_key=api_key)
        
        # 3. Guardamos el string del Prompt como instrucción del sistema
        self.system_instruction = """
        Eres un extractor de datos de cobranza ultra preciso para EasyHammer Studio. Tu única tarea es recibir un reporte de texto libre enviado por un vendedor y transformarlo en un objeto JSON estructurado.

        REGLAS CRÍTICAS DE NEGOCIO:
        1. Extrae el número de la ruta. Busca patrones como "Ruta 15", "R15", "Ruta: 15" o similares. El valor de "ruta" debe ser estrictamente un número entero.
        2. Identifica cada cobro. Para cada cliente, extrae su nombre, el monto numérico cobrado y el símbolo de la moneda utilizada (Bs, $, etc.).
        3. Si un cliente no tiene monto o la información es completamente ilegible, ignora ese cliente en específico.

        REGLAS DE FORMATO TÉCNICO:
        - Tu respuesta debe ser ÚNICAMENTE el objeto JSON puro.
        - NO incluyas introducciones, NO incluyas saludos, NO incluyas explicaciones.
        - NO uses bloques de código Markdown (prohibido usar ```json o ```). Solo escribe el JSON plano comenzando con { y terminando con }.

        FORMATO JSON ESPERADO:
        {
          "ruta": 15,
          "cobros": [
            {"cliente": "Nombre Cliente 1", "monto": 150.0, "moneda": "$"},
            {"cliente": "Nombre Cliente 2", "monto": 3500.0, "moneda": "Bs"}
          ]
        }
        """

    def parsear_texto_libre(self, texto_vendedor):
        """Envía el texto a Gemini Flash y devuelve un diccionario de Python"""
        self.logger.registrar_log("INFO", "Iniciando peticion a Gemini Flash para parsear reporte...")
        
        try:
            # Inicializamos el modelo ligero ideal para tareas de texto estructurado
            model = genai.GenerativeModel(
                model_name="gemini-3.5-flash",  # <--- Le agregamos el -latest
                system_instruction=self.system_instruction
            )
            
            # Realizamos la llamada pasando el texto del vendedor
            respuesta = model.generate_content(texto_vendedor)
            texto_respuesta = respuesta.text.strip()
            
            # Convertimos el string que escupió la IA en un diccionario real de Python
            datos_json = json.loads(texto_respuesta)
            
            self.logger.registrar_log("INFO", f"Parseo exitoso. Detectada Ruta {datos_json.get('ruta')}.")
            return datos_json
            
        except json.JSONDecodeError as json_err:
            self.logger.registrar_log("ERROR", f"Gemini no devolvió un JSON limpio: {json_err}. Respuesta cruda: {texto_respuesta}")
            return None
        except Exception as e:
            self.logger.registrar_log("ERROR", f"Fallo crítico en la comunicación con Gemini: {e}")
            return None