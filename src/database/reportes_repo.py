# src/database/reportes_repo.py

from datetime import datetime, timedelta
import sqlite3


class ReportesRepository:
    def __init__(self, db_connection):
        """Recibe el conector central de la base de datos (DBConnection)"""
        self.db = db_connection

    def _normalizar_fecha(self, fecha_str=None):
        """Método interno para estandarizar fechas (YYYY-MM-DD)"""
        if fecha_str:
            return fecha_str.strip()
        return datetime.now().strftime("%Y-%m-%d")

    def _resolver_fecha_relativa(self, dia_destino_str):
        """Convierte 'AYER', 'HOY', 'MANANA' en un string de fecha 'YYYY-MM-DD'"""
        hoy = datetime.now()
        dia = str(dia_destino_str or "HOY").upper().strip()

        if dia == "AYER":
            return (hoy - timedelta(days=1)).strftime("%Y-%m-%d")
        elif dia in ["MANANA", "MAÑANA"]:
            return (hoy + timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            return hoy.strftime("%Y-%m-%d")

    # ========================================================
    #       🌅 MÓDULO 1: CONTROL DE OPERACIONES DIARIAS
    # ========================================================

    def registrar_o_actualizar_plan_matutino(self, ruta, meta_udvd=0, meta_cobranza=0.0, meta_activaciones=0, meta_amigo=0.0, meta_celta=0.0, fecha_especifica=None):
        """Registra o ingresa las metas del día para una ruta"""
        fecha_op = self._normalizar_fecha(fecha_especifica)
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute("""
                INSERT INTO operaciones_diarias (fecha, ruta_id, meta_udvd, meta_cxc, meta_activaciones, meta_amigo, meta_celta)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fecha, ruta_id) DO UPDATE SET
                    meta_udvd = CASE WHEN excluded.meta_udvd IS NOT NULL AND excluded.meta_udvd > 0 THEN excluded.meta_udvd ELSE operaciones_diarias.meta_udvd END,
                    meta_cxc = CASE WHEN excluded.meta_cxc IS NOT NULL AND excluded.meta_cxc > 0 THEN excluded.meta_cxc ELSE operaciones_diarias.meta_cxc END,
                    meta_activaciones = CASE WHEN excluded.meta_activaciones IS NOT NULL AND excluded.meta_activaciones > 0 THEN excluded.meta_activaciones ELSE operaciones_diarias.meta_activaciones END,
                    meta_amigo = CASE WHEN excluded.meta_amigo IS NOT NULL AND excluded.meta_amigo > 0 THEN excluded.meta_amigo ELSE operaciones_diarias.meta_amigo END,
                    meta_celta = CASE WHEN excluded.meta_celta IS NOT NULL AND excluded.meta_celta > 0 THEN excluded.meta_celta ELSE operaciones_diarias.meta_celta END
            """, (fecha_op, ruta, float(meta_udvd or 0), float(meta_cobranza or 0.0), int(meta_activaciones or 0), float(meta_amigo or 0.0), float(meta_celta or 0.0)))
            conexion.commit()
            return True
        except Exception as e:
            print(f"❌ [ReportesRepo] Error al registrar plan matutino: {e}")
            return False
        finally:
            conexion.close()

    def registrar_o_actualizar_cierre_nocturno(self, ruta, real_udvd=0, real_cobranza=0.0, real_activaciones=0, efectivo=0.0, zelle=0.0, bs=0.0, tasa_bcv=0.0, real_amigo=0.0, real_celta=0.0, fecha_especifica=None):
        """Registra o actualiza los logros reales y desglose físico de caja en la noche"""
        fecha_op = self._normalizar_fecha(fecha_especifica)
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute("""
                INSERT INTO operaciones_diarias (
                    fecha, ruta_id, real_udvd, real_cxc, real_activaciones, 
                    efectivo_usd, zelle_usd, bs_cambiados_usd, tasa_bcv,
                    real_amigo, real_celta
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(fecha, ruta_id) DO UPDATE SET
                    real_udvd = CASE WHEN excluded.real_udvd IS NOT NULL AND excluded.real_udvd > 0 THEN excluded.real_udvd ELSE operaciones_diarias.real_udvd END,
                    real_cxc = CASE WHEN excluded.real_cxc IS NOT NULL AND excluded.real_cxc > 0 THEN excluded.real_cxc ELSE operaciones_diarias.real_cxc END,
                    real_activaciones = CASE WHEN excluded.real_activaciones IS NOT NULL AND excluded.real_activaciones > 0 THEN excluded.real_activaciones ELSE operaciones_diarias.real_activaciones END,
                    efectivo_usd = CASE WHEN excluded.efectivo_usd > 0 THEN excluded.efectivo_usd ELSE operaciones_diarias.efectivo_usd END,
                    zelle_usd = CASE WHEN excluded.zelle_usd > 0 THEN excluded.zelle_usd ELSE operaciones_diarias.zelle_usd END,
                    bs_cambiados_usd = CASE WHEN excluded.bs_cambiados_usd > 0 THEN excluded.bs_cambiados_usd ELSE operaciones_diarias.bs_cambiados_usd END,
                    real_amigo = CASE WHEN excluded.real_amigo IS NOT NULL AND excluded.real_amigo > 0 THEN excluded.real_amigo ELSE operaciones_diarias.real_amigo END,
                    real_celta = CASE WHEN excluded.real_celta IS NOT NULL AND excluded.real_celta > 0 THEN excluded.real_celta ELSE operaciones_diarias.real_celta END,
                    tasa_bcv = CASE WHEN excluded.tasa_bcv > 0 THEN excluded.tasa_bcv ELSE operaciones_diarias.tasa_bcv END
            """, (fecha_op, ruta, float(real_udvd or 0), float(real_cobranza or 0.0), int(real_activaciones or 0), 
                  float(efectivo or 0.0), float(zelle or 0.0), float(bs or 0.0), float(tasa_bcv or 0.0), float(real_amigo or 0.0), float(real_celta or 0.0)))
            conexion.commit()
            return True
        except Exception as e:
            print(f"❌ [ReportesRepo] Error al registrar cierre nocturno: {e}")
            return False
        finally:
            conexion.close()

    # ========================================================
    #      THIS FUNCTION DOESN'T MAKE ANY SENSES
    # ========================================================


    def registrar_cobros_detalle(self, fecha_str, ruta_id, lista_cobros):
        """Registra cada cobro por cliente de forma individual"""
        if not lista_cobros:
            return True

        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            for c in lista_cobros:
                cliente = c.get("cliente", "Cliente Desconocido")
                monto = float(c.get("monto", 0.0))
                moneda = c.get("moneda", "USD").upper()
                
                cursor.execute("""
                    INSERT INTO cobranzas_detalle (fecha, ruta_id, cliente, monto, moneda)
                    VALUES (?, ?, ?, ?, ?)
                """, (fecha_str, ruta_id, cliente, monto, moneda))
            
            conexion.commit()
            return True
        except Exception as e:
            print(f"❌ [ReportesRepo] Error al registrar cobranzas detalle: {e}")
            return False
        finally:
            conexion.close()

    # ========================================================
    #       🎯 MÓDULO 2: GESTIÓN DE CUOTAS MENSUALES
    # ========================================================

    def asignar_cuota_mensual(self, periodo_str, ruta_id, tipo_cuota, valor):
        """Asigna una cuota a una ruta o a la empresa global (si ruta_id es None)"""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute("""
                INSERT INTO cuotas_mensuales (periodo, ruta_id, tipo_cuota, valor_cuota)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(periodo, ruta_id, tipo_cuota) DO UPDATE SET
                    valor_cuota = excluded.valor_cuota
            """, (periodo_str.strip(), ruta_id, tipo_cuota.upper().strip(), float(valor)))
            conexion.commit()
            return True
        except Exception as e:
            print(f"❌ [ReportesRepo] Error al asignar cuota mensual: {e}")
            return False
        finally:
            conexion.close()

    def _obtener_total_udvd_periodo(self, periodo_str, ruta_id=None, campo='meta'):
        """Suma consolidada UDVD + Grupo Amigo + Celta para el periodo solicitado."""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()

        campo_udvd = 'meta_udvd' if campo == 'meta' else 'real_udvd'
        campo_amigo = 'meta_amigo' if campo == 'meta' else 'real_amigo'
        campo_celta = 'meta_celta' if campo == 'meta' else 'real_celta'

        if ruta_id is None:
            cursor.execute(f"""
                SELECT COALESCE(SUM({campo_udvd}), 0.0)
                     + COALESCE(SUM({campo_amigo}), 0.0)
                     + COALESCE(SUM({campo_celta}), 0.0)
                FROM operaciones_diarias
                WHERE fecha LIKE ?
            """, (f"{periodo_str}%",))
        else:
            cursor.execute(f"""
                SELECT COALESCE(SUM({campo_udvd}), 0.0)
                     + COALESCE(SUM({campo_amigo}), 0.0)
                     + COALESCE(SUM({campo_celta}), 0.0)
                FROM operaciones_diarias
                WHERE fecha LIKE ? AND ruta_id = ?
            """, (f"{periodo_str}%", int(ruta_id)))

        resultado = cursor.fetchone()[0]
        conexion.close()
        return float(resultado) if resultado else 0.0

    def obtener_cuota_global_mes(self, periodo_str, tipo_cuota='UDVD'):
        """Consulta de cuota mensual total de la empresa; para UDVD incluye Amigo + Celta."""
        if tipo_cuota.upper() == 'UDVD':
            return self._obtener_total_udvd_periodo(periodo_str, ruta_id=None, campo='meta')

        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT SUM(valor_cuota) FROM cuotas_mensuales
            WHERE periodo = ? AND tipo_cuota = ? AND ruta_id IS NOT NULL
        """, (periodo_str, tipo_cuota.upper()))
        row_sum = cursor.fetchone()
        conexion.close()

        return float(row_sum[0]) if row_sum and row_sum[0] else 0.0

    def obtener_cuota_individual(self, periodo_str, ruta_id, tipo_cuota='UDVD'):
        """Consulta de cuota individual; para UDVD incluye Amigo + Celta."""
        if tipo_cuota.upper() == 'UDVD':
            return self._obtener_total_udvd_periodo(periodo_str, ruta_id=ruta_id, campo='meta')

        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT valor_cuota FROM cuotas_mensuales 
            WHERE periodo = ? AND ruta_id = ? AND tipo_cuota = ?
        """, (periodo_str, ruta_id, tipo_cuota.upper()))
        resultado = cursor.fetchone()
        conexion.close()
        return resultado[0] if resultado else 0.0
    
    def obtener_cuota_mes(self,periodo_str):
        """Obtiene todas las cuotas del mes en un diccionario {ruta_id: {tipo_cuota: valor}}"""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT ruta_id, tipo_cuota, valor_cuota FROM cuotas_mensuales
            WHERE periodo = ? ORDER BY ruta_id ASC, tipo_cuota ASC
        """, (periodo_str,))
        
        cuotas_mes = {}
        for ruta_id, tipo_cuota, valor in cursor.fetchall():
            if ruta_id not in cuotas_mes:
                cuotas_mes[ruta_id] = {}
            cuotas_mes[ruta_id][tipo_cuota.upper()] = valor
        
        conexion.close()
        return cuotas_mes

    def obtener_cuota_supervisor(self, periodo_str, tipo_cuota='UDVD'):
            """
            [FIX DISTINCT] Suma las cuotas del mes para las rutas bajo responsabilidad del supervisor,
            evitando duplicaciones si hay múltiples registros de usuarios por ruta.
            Para UDVD incluye grupo Amigo y Celta en el mismo KPI.
            """
            if tipo_cuota.upper() == 'UDVD':
                conexion = self.db.obtener_conexion()
                cursor = conexion.cursor()
                cursor.execute("""
                    SELECT COALESCE(SUM(meta_udvd), 0.0)
                         + COALESCE(SUM(meta_amigo), 0.0)
                         + COALESCE(SUM(meta_celta), 0.0)
                    FROM operaciones_diarias
                    WHERE fecha LIKE ?
                      AND ruta_id IN (
                          SELECT DISTINCT ruta
                          FROM usuarios
                          WHERE bajo_responsabilidad_supervisor = 1 AND ruta IS NOT NULL
                      )
                """, (f"{periodo_str}%",))
                resultado = cursor.fetchone()[0]
                conexion.close()
                return float(resultado) if resultado else 0.0

            conexion = self.db.obtener_conexion()
            cursor = conexion.cursor()
            cursor.execute("""
                SELECT SUM(valor_cuota) 
                FROM cuotas_mensuales
                WHERE periodo = ? 
                AND tipo_cuota = ? 
                AND ruta_id IN (
                    SELECT DISTINCT ruta 
                    FROM usuarios 
                    WHERE bajo_responsabilidad_supervisor = 1 AND ruta IS NOT NULL
                )
            """, (periodo_str, tipo_cuota.upper()))
            
            resultado = cursor.fetchone()[0]
            conexion.close()
            return float(resultado) if resultado else 0.0
    # ========================================================
    #       📊 MÓDULO 3: PROGRESOS, HISTÓRICOS Y AUDITORÍAS
    # ========================================================

    def obtener_progreso_global_mes(self, periodo_str, tipo_cuota='UDVD'):
        """Progreso mensual: Cuota total, cuánto lleva acumulado y cuánto falta."""
        cuota_total = self.obtener_cuota_global_mes(periodo_str, tipo_cuota)

        if tipo_cuota.upper() == 'UDVD':
            acumulado = self._obtener_total_udvd_periodo(periodo_str, ruta_id=None, campo='real')
        else:
            conexion = self.db.obtener_conexion()
            cursor = conexion.cursor()
            campo_real = "real_cxc" if tipo_cuota.upper() == "COBRANZA" else "real_activaciones"
            cursor.execute(f"SELECT SUM({campo_real}) FROM operaciones_diarias WHERE fecha LIKE ?", (f"{periodo_str}%",))
            acumulado = cursor.fetchone()[0]
            conexion.close()
            acumulado = acumulado if acumulado else 0.0

        falta = max(0.0, cuota_total - acumulado)
        porcentaje = (acumulado / cuota_total * 100) if cuota_total > 0 else 0.0

        return {"cuota_total": cuota_total, "acumulado": acumulado, "falta": falta, "porcentaje": porcentaje}

    def obtener_progreso_individual(self, periodo_str, ruta_id, tipo_cuota='UDVD'):
        """Progreso individual por vendedor: Cuota, acumulado y cuánto le falta."""
        cuota_vendedor = self.obtener_cuota_individual(periodo_str, ruta_id, tipo_cuota)

        if tipo_cuota.upper() == 'UDVD':
            acumulado = self._obtener_total_udvd_periodo(periodo_str, ruta_id=ruta_id, campo='real')
        else:
            conexion = self.db.obtener_conexion()
            cursor = conexion.cursor()
            campo_real = "real_cxc" if tipo_cuota.upper() == "COBRANZA" else "real_activaciones"
            cursor.execute(f"SELECT SUM({campo_real}) FROM operaciones_diarias WHERE fecha LIKE ? AND ruta_id = ?", (f"{periodo_str}%", ruta_id))
            acumulado = cursor.fetchone()[0]
            conexion.close()
            acumulado = acumulado if acumulado else 0.0

        falta = max(0.0, cuota_vendedor - acumulado)
        porcentaje = (acumulado / cuota_vendedor * 100) if cuota_vendedor > 0 else 0.0

        return {"cuota_individual": cuota_vendedor, "acumulado": acumulado, "falta": falta, "porcentaje": porcentaje}

    def obtener_total_metas_dia(self, fecha_str):
        """Consulta histórica de la sumatoria de objetivos/metas de un día específico"""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT SUM(meta_udvd), SUM(meta_cxc), SUM(meta_activaciones), SUM(meta_amigo), SUM(meta_celta) FROM operaciones_diarias WHERE fecha = ?", (fecha_str,))
        r = cursor.fetchone()
        conexion.close()
        return {"total_meta_udvd": r[0] or 0.0, "total_meta_cxc": r[1] or 0.0, "total_meta_act": r[2] or 0, "total_meta_amigo": r[3] or 0.0, "total_meta_celta": r[4] or 0.0}

    def obtener_total_cobrado_dia(self, fecha_str):
        """Consulta histórica de cobros del día: Sumatoria de lo cobrado real en una fecha"""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT SUM(real_cxc), SUM(efectivo_usd + zelle_usd + bs_cambiados_usd) 
            FROM operaciones_diarias WHERE fecha = ?
        """, (fecha_str,))
        r = cursor.fetchone()
        conexion.close()
        return {"total_cxc_real": r[0] or 0.0, "total_caja_nocturna": r[1] or 0.0}

    def obtener_total_cobrado_mes_divisas(self, periodo_str):
        """Total mensual cobrado estrictamente en divisas (Efectivo + Zelle)"""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT SUM(efectivo_usd + zelle_usd) FROM operaciones_diarias WHERE fecha LIKE ?", (f"{periodo_str}%",))
        resultado = cursor.fetchone()[0]
        conexion.close()
        return resultado if resultado else 0.0

    def obtener_total_cobrado_mes_general(self, periodo_str):
        """Total mensual cobrado general (Efectivo + Zelle + Bs Cambiados)"""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("SELECT SUM(efectivo_usd + zelle_usd + bs_cambiados_usd) FROM operaciones_diarias WHERE fecha LIKE ?", (f"{periodo_str}%",))
        resultado = cursor.fetchone()[0]
        conexion.close()
        return resultado if resultado else 0.0

    def obtener_desglose_semanal(self, fecha_inicio, fecha_fin):
        """Desglose diario detallado de cobros por vendedor/ruta en un rango (Semana)"""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        cursor.execute("""
            SELECT fecha, ruta_id, (efectivo_usd + zelle_usd + bs_cambiados_usd) as total_dia
            FROM operaciones_diarias 
            WHERE fecha BETWEEN ? AND ?
            ORDER BY ruta_id ASC, fecha ASC
        """, (fecha_inicio, fecha_fin))
        filas = cursor.fetchall()
        conexion.close()
        
        desglose = {}
        for f, r, t in filas:
            if r not in desglose:
                desglose[r] = {}
            desglose[r][f] = t or 0.0
        return desglose

    def calcular_meta_diaria_restante(self, periodo_str, ruta_id, dias_laborables_totales=24):
        """Calcula cuántas unidades debe vender al día considerando los días hábiles restantes"""
        progreso = self.obtener_progreso_individual(periodo_str, ruta_id, 'UDVD')
        falta = progreso["falta"]
        
        hoy = datetime.now()
        año, mes = map(int, periodo_str.split("-"))
        
        if hoy.year > año or (hoy.year == año and hoy.month > mes):
            return 0.0
            
        dias_transcurridos = hoy.day
        dias_restantes = max(1, dias_laborables_totales - int((dias_transcurridos / 30) * dias_laborables_totales))
        
        return round(falta / dias_restantes, 2)

    def obtener_reportes_faltantes_hoy(self):
        """Lista de control para auditar quién no ha reportado hoy (Mañana o Noche)"""
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT ruta, nombre_telegram FROM usuarios 
            WHERE estado = 'AUTORIZADO' AND bajo_responsabilidad_supervisor = 1
            AND ruta NOT IN (SELECT ruta_id FROM operaciones_diarias WHERE fecha = ? AND meta_udvd > 0)
        """, (fecha_hoy,))
        faltan_manana = [{"ruta": r[0], "nombre": r[1]} for r in cursor.fetchall()]

        cursor.execute("""
            SELECT ruta, nombre_telegram FROM usuarios 
            WHERE estado = 'AUTORIZADO' AND bajo_responsabilidad_supervisor = 1
            AND ruta NOT IN (SELECT ruta_id FROM operaciones_diarias WHERE fecha = ? AND real_udvd > 0)
        """, (fecha_hoy,))
        faltan_noche = [{"ruta": r[0], "nombre": r[1]} for r in cursor.fetchall()]

        conexion.close()
        return {"faltan_manana": faltan_manana, "faltan_noche": faltan_noche}

    # ========================================================
    #   🤖 MÓDULO 4: LA FUNCIÓN MULTI-SOLICITUD (DASHBOARD BI)
    # ========================================================

    def obtener_dashboard_bi(self, periodo_str, ruta_id=None, fecha_especifica=None):
        """Permite pedir múltiples métricas complejas en una sola llamada limpia."""
        fecha_evaluar = self._normalizar_fecha(fecha_especifica)
        
        dashboard = {
            "periodo": periodo_str,
            "fecha_consulta": fecha_evaluar,
            "empresa_global": {
                "cuota_udvd": self.obtener_progreso_global_mes(periodo_str, 'UDVD'),
                "cuota_cobranza": self.obtener_progreso_global_mes(periodo_str, 'COBRANZA'),
                "total_mes_divisas": self.obtener_total_cobrado_mes_divisas(periodo_str),
                "total_mes_general": self.obtener_total_cobrado_mes_general(periodo_str)
            },
            "historico_dia": {
                "metas_prometidas": self.obtener_total_metas_dia(fecha_evaluar),
                "cobros_logrados": self.obtener_total_cobrado_dia(fecha_evaluar)
            }
        }
        
        if ruta_id:
            dashboard["individual_ruta"] = {
                "ruta": ruta_id,
                "progreso_udvd": self.obtener_progreso_individual(periodo_str, ruta_id, 'UDVD'),
                "progreso_cobranza": self.obtener_progreso_individual(periodo_str, ruta_id, 'COBRANZA'),
                "meta_diaria_sugerida": self.calcular_meta_diaria_restante(periodo_str, ruta_id)
            }
            
        return dashboard

    # ========================================================
    #       🛠️ MÓDULO 5: PROCESADOR CENTRAL DEL IA PARSER
    # ========================================================

    # =======================================================
    #   fHUA, Never did i use this xd
    
    def procesar_payload_ia(self, payload_json, ruta_fallback=None):
        """
        [MOTOR DE IMPACTO AUTOMÁTICO]
        Recibe el diccionario procesado por IAParser y aplica los cambios en SQLite.
        Soporta:
        - REPORTE_FULL_MANANA
        - REPORTE_FULL_NOCHE
        - AJUSTE_INDIVIDUAL (Operaciones SET, ADD, DELETE sobre campos específicos)
        """
        if not payload_json:
            return False, "Payload vacío o inválido."

        ruta_id = payload_json.get("ruta") or ruta_fallback
        if not ruta_id:
            return False, "No se identificó el número de ruta."

        tipo_intencion = payload_json.get("tipo_intencion")
        dia_destino = payload_json.get("dia_destino", "HOY")
        fecha_target = self._resolver_fecha_relativa(dia_destino)

        datos = payload_json.get("datos", {})
        ajuste = payload_json.get("ajuste_especifico", {})

        # --- CASO A: REPORTE MATUTINO COMPLETO ---
        if tipo_intencion == "REPORTE_FULL_MANANA":
            exito = self.registrar_o_actualizar_plan_matutino(
                ruta=ruta_id,
                meta_udvd=datos.get("unidades", 0),
                meta_cobranza=datos.get("cxc", 0.0),
                meta_activaciones=datos.get("visitas", 0),
                fecha_especifica=fecha_target
            )
            return exito, f"Plan matutino del {fecha_target} guardado para Ruta {ruta_id}."

        # --- CASO B: REPORTE NOCTURNO COMPLETO ---
        elif tipo_intencion == "REPORTE_FULL_NOCHE":
            cobros_detalle = datos.get("cobros_detalle", [])
            total_usd = datos.get("cobranza_usd") or 0.0
            total_bs = datos.get("cobranza_bs") or 0.0

            # Si viene detalle de cobros pero no el total general, lo calculamos
            if not total_usd and cobros_detalle:
                total_usd = sum(c["monto"] for c in cobros_detalle if c.get("moneda") == "USD")

            exito_cierre = self.registrar_o_actualizar_cierre_nocturno(
                ruta=ruta_id,
                real_udvd=datos.get("unidades", 0),
                real_cobranza=total_usd,
                real_activaciones=datos.get("visitas", 0),
                efectivo=total_usd,
                zelle=0.0,
                bs=total_bs,
                tasa_bcv=0.0,
                fecha_especifica=fecha_target
            )

            if cobros_detalle:
                self.registrar_cobros_detalle(fecha_target, ruta_id, cobros_detalle)

            return exito_cierre, f"Cierre nocturno del {fecha_target} guardado para Ruta {ruta_id}."

        # --- CASO C: AJUSTE INDIVIDUAL PUNTUAL ---
        elif tipo_intencion == "AJUSTE_INDIVIDUAL":
            campo = ajuste.get("campo_a_modificar")
            valor_nuevo = ajuste.get("valor_nuevo")
            operacion = ajuste.get("operacion", "SET")

            # Mapeo de campos a columnas de la base de datos
            mapa_campos = {
                "unidades": "meta_udvd",
                "visitas": "meta_activaciones",
                "cxc": "meta_cxc",
                "cobranza_usd": "real_cxc",
                "cobranza_bs": "bs_cambiados_usd"
            }

            # Si el ajuste incluye agregar cobros de un cliente
            if campo == "cliente" or datos.get("cobros_detalle"):
                cobros_detalle = datos.get("cobros_detalle", [])
                if cobros_detalle:
                    self.registrar_cobros_detalle(fecha_target, ruta_id, cobros_detalle)
                    # Sumamos al acumulado real de cobranza
                    monto_extra = sum(c["monto"] for c in cobros_detalle if c.get("moneda") == "USD")
                    if monto_extra > 0:
                        self._aplicar_operacion_campo(fecha_target, ruta_id, "real_cxc", monto_extra, "ADD")
                return True, f"Ajuste de cobranza por cliente aplicado para Ruta {ruta_id} ({fecha_target})."

            columna_target = mapa_campos.get(campo)
            if not columna_target:
                # Si no especificó un campo en ajuste_especifico, buscamos datos directos
                if datos.get("unidades"):
                    self._aplicar_operacion_campo(fecha_target, ruta_id, "meta_udvd", datos["unidades"], "SET")
                if datos.get("cobranza_usd"):
                    self._aplicar_operacion_campo(fecha_target, ruta_id, "real_cxc", datos["cobranza_usd"], "SET")
                return True, f"Ajuste individual general procesado para Ruta {ruta_id}."

            exito = self._aplicar_operacion_campo(fecha_target, ruta_id, columna_target, valor_nuevo, operacion)
            return exito, f"Campo '{campo}' actualizado ({operacion} {valor_nuevo}) para Ruta {ruta_id}."

        return False, "Tipo de intención no reconocido."

    def _aplicar_operacion_campo(self, fecha_str, ruta_id, columna_db, valor, operacion="SET"):
        """Aplica operaciones matematicas (SET, ADD, DELETE) a un campo puntual"""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            # Asegurar que existe el registro diario para la ruta y fecha
            cursor.execute("""
                INSERT OR IGNORE INTO operaciones_diarias (fecha, ruta_id)
                VALUES (?, ?)
            """, (fecha_str, ruta_id))

            val_num = float(valor or 0.0)

            if operacion == "ADD":
                cursor.execute(f"""
                    UPDATE operaciones_diarias 
                    SET {columna_db} = COALESCE({columna_db}, 0) + ?
                    WHERE fecha = ? AND ruta_id = ?
                """, (val_num, fecha_str, ruta_id))
            elif operacion == "DELETE":
                cursor.execute(f"""
                    UPDATE operaciones_diarias 
                    SET {columna_db} = 0
                    WHERE fecha = ? AND ruta_id = ?
                """, (fecha_str, ruta_id))
            else:  # SET por defecto
                cursor.execute(f"""
                    UPDATE operaciones_diarias 
                    SET {columna_db} = ?
                    WHERE fecha = ? AND ruta_id = ?
                """, (val_num, fecha_str, ruta_id))

            conexion.commit()
            return True
        except Exception as e:
            print(f"❌ [ReportesRepo] Error en _aplicar_operacion_campo: {e}")
            return False
        finally:
            conexion.close()

    # ========================================================
    #       🧹 MÓDULO 6: HIGIENE Y DEPURACIÓN CÍCLICA
    # ========================================================

    def extraer_todo_para_depuracion(self, mes_str):
        """Extrae el mes completo de la tabla unificada para empaquetarlo en los Excels"""
        conexion = self.db.obtener_conexion()
        conexion.row_factory = sqlite3.Row
        cursor = conexion.cursor()
        cursor.execute("SELECT * FROM operaciones_diarias WHERE fecha LIKE ? ORDER BY fecha ASC, ruta_id ASC", (f"{mes_str}%",))
        resultados = [dict(row) for row in cursor.fetchall()]
        conexion.close()
        return resultados

    def eliminar_bloque_depurado(self, mes_str):
        """Limpia los registros de operaciones para mantener SQLite ultraligero"""
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute("DELETE FROM operaciones_diarias WHERE fecha LIKE ?", (f"{mes_str}%",))
            conexion.commit()
            return True
        except Exception:
            return False
        finally:
            conexion.close()
    def obtener_total_cobrado_ruta_fecha(self, ruta_id, fecha_str):
        """
        Consulta histórica de cobro real confirmado para una ruta y fecha específica.
        Retorna la cobranza real (real_cxc) o la suma de la caja nocturna (USD + Zelle + Bs).
        """
        fecha_op = self._normalizar_fecha(fecha_str)
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        try:
            cursor.execute("""
                SELECT COALESCE(real_cxc, 0.0), 
                       COALESCE(efectivo_usd + zelle_usd + bs_cambiados_usd, 0.0)
                FROM operaciones_diarias 
                WHERE fecha = ? AND ruta_id = ?
            """, (fecha_op, int(ruta_id)))
            
            resultado = cursor.fetchone()
            if not resultado:
                return 0.0
            
            real_cxc, total_caja = resultado[0], resultado[1]
            
            # Prioriza real_cxc si existe; si no, retorna el total desglosado de caja
            return float(real_cxc) if real_cxc > 0 else float(total_caja)
            
        except Exception as e:
            print(f"❌ [ReportesRepo] Error consultando cobro de Ruta {ruta_id} en {fecha_op}: {e}")
            return 0.0
        finally:
            conexion.close()
            
            
            
    def obtener_informe_360_rutas(self, rutas_lista: list[int], fecha_base: str = None) -> dict:
            """
            [CONSULTA DETALLADA 360°]
            Trae el histórico de Ayer, Hoy y Mañana para una o varias rutas.
            Retorna un diccionario con la información desglosada por ruta.
            """
            fecha_hoy = self._normalizar_fecha(fecha_base)
            dt_hoy = datetime.strptime(fecha_hoy, "%Y-%m-%d")
            
            # Calcular Ayer (omitiendo fin de semana si aplica) y Mañana
            dias_atras = 3 if dt_hoy.weekday() == 0 else 1
            dias_adelante = 3 if dt_hoy.weekday() == 4 else 1  # Si es viernes, mañana operativo es Lunes
            
            fecha_ayer = (dt_hoy - timedelta(days=dias_atras)).strftime("%Y-%m-%d")
            fecha_manana = (dt_hoy + timedelta(days=dias_adelante)).strftime("%Y-%m-%d")

            conexion = self.db.obtener_conexion()
            conexion.row_factory = sqlite3.Row
            cursor = conexion.cursor()

            informes = {}

            for r_id in rutas_lista:
                # Consultar los 3 días de golpe para la ruta
                cursor.execute("""
                    SELECT fecha, meta_udvd, real_udvd, meta_activaciones, real_activaciones, 
                        meta_cxc, real_cxc, efectivo_usd, zelle_usd, bs_cambiados_usd,
                        meta_amigo, real_amigo, meta_celta, real_celta
                    FROM operaciones_diarias 
                    WHERE ruta_id = ? AND fecha IN (?, ?, ?)
                """, (r_id, fecha_ayer, fecha_hoy, fecha_manana))
                
                filas = {row["fecha"]: dict(row) for row in cursor.fetchall()}

                informes[r_id] = {
                    "ayer": filas.get(fecha_ayer, {}),
                    "hoy": filas.get(fecha_hoy, {}),
                    "manana": filas.get(fecha_manana, {}),
                    "fechas": {"ayer": fecha_ayer, "hoy": fecha_hoy, "manana": fecha_manana}
                }

            conexion.close()
            return informes
        
    def obtener_semaforo_reportes_dia(self, fecha_base: str = None, incluir_todas_rutas: bool = True) -> list[dict]:
        """
        [AUDITORÍA EXPRÉS DEL DÍA]
        Devuelve el estado de cumplimiento (Listo / Falta) para cada ruta autorizada.
        Filtro: si incluir_todas_rutas=False, evalúa solo bajo_responsabilidad_supervisor = 1.
        """
        fecha_evaluar = self._normalizar_fecha(fecha_base)
        conexion = self.db.obtener_conexion()
        conexion.row_factory = sqlite3.Row
        cursor = conexion.cursor()

        # 1. Traer lista de rutas autorizadas aplicando el filtro de supervisor
        query_rutas = "SELECT ruta, nombre_telegram FROM usuarios WHERE estado = 'AUTORIZADO'"
        if not incluir_todas_rutas:
            query_rutas += " AND bajo_responsabilidad_supervisor = 1"
        query_rutas += " ORDER BY ruta ASC"

        cursor.execute(query_rutas)
        rutas_db = cursor.fetchall()

        # 2. Consultar registros de la fecha
        cursor.execute("""
            SELECT ruta_id, meta_udvd, real_udvd, 
                   (efectivo_usd + zelle_usd + bs_cambiados_usd) as caja_total,
                   real_cxc, meta_amigo, real_amigo, meta_celta, real_celta
            FROM operaciones_diarias 
            WHERE fecha = ?
        """, (fecha_evaluar,))
        
        ops_map = {row["ruta_id"]: dict(row) for row in cursor.fetchall()}
        conexion.close()

        resumen = []
        for r in rutas_db:
            r_id = r["ruta"]
            op = ops_map.get(r_id, {})

            # Evaluación de los 3 reportes
            tiene_matutino = bool(op.get("meta_udvd") and op["meta_udvd"] > 0)
            tiene_nocturno = bool(op.get("real_udvd") and op["real_udvd"] > 0)
            
            # Cobranza está 'Listo' si registró caja física o cobranza real
            caja = op.get("caja_total") or 0.0
            cxc = op.get("real_cxc") or 0.0
            tiene_cobranza = bool(caja > 0 or cxc > 0)

            resumen.append({
                "ruta": r_id,
                "nombre": r["nombre_telegram"] or f"Ruta {r_id}",
                "matutino": "listo" if tiene_matutino else "falta",
                "nocturno": "listo" if tiene_nocturno else "falta",
                "cobranza": "listo" if tiene_cobranza else "falta"
            })

        return resumen
    
    # ========================================================
    #       📊 MÓDULO ADICIONAL: DASHBOARD BI METHODOLOGY
    # ========================================================

    def obtener_resumen_dashboard_global(self, periodo_str: str) -> dict:
        """
        Calcula los totales consolidados de la empresa completa para el mes (YYYY-MM).
        Reaprovecha los métodos atómicos de la clase.
        """
        progreso_udvd = self.obtener_progreso_global_mes(periodo_str, 'UDVD')
        progreso_cxc = self.obtener_progreso_global_mes(periodo_str, 'COBRANZA')
        
        divisas = self.obtener_total_cobrado_mes_divisas(periodo_str)
        total_caja = self.obtener_total_cobrado_mes_general(periodo_str)

        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()
        
        # Desglose físico completo de la caja acumulada del mes
        cursor.execute("""
            SELECT SUM(efectivo_usd), SUM(zelle_usd), SUM(bs_cambiados_usd)
            FROM operaciones_diarias
            WHERE fecha LIKE ?
        """, (f"{periodo_str}%",))
        row = cursor.fetchone()
        conexion.close()

        return {
            "periodo": periodo_str,
            "cuota_udvd": progreso_udvd["cuota_total"],
            "acumulado_udvd": progreso_udvd["acumulado"],
            "porcentaje_udvd": progreso_udvd["porcentaje"],
            "falta_udvd": progreso_udvd["falta"],
            "cuota_cxc": progreso_cxc["cuota_total"],
            "acumulado_cxc": progreso_cxc["acumulado"],
            "porcentaje_cxc": progreso_cxc["porcentaje"],
            "falta_cxc": progreso_cxc["falta"],
            "efectivo": row[0] or 0.0,
            "zelle": row[1] or 0.0,
            "bs": row[2] or 0.0,
            "divisas": divisas,
            "total_caja": total_caja
        }

    def obtener_resumen_dashboard_supervisor(self, periodo_str: str) -> dict:
        """
        Calcula totales acumulados del mes SOLO para rutas con bajo_responsabilidad_supervisor = 1.
        """
        cuota_udvd_sup = self.obtener_cuota_supervisor(periodo_str, 'UDVD')
        cuota_cxc_sup = self.obtener_cuota_supervisor(periodo_str, 'COBRANZA')

        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()

        # Sumatoria de logros reales en el mes filtrados por la condición del supervisor.
        # Para UDVD el indicador consolidado debe incluir Grupo Amigo + Celta.
        cursor.execute("""
            SELECT 
                SUM(o.real_udvd + o.real_amigo + o.real_celta),
                SUM(o.real_cxc), 
                SUM(o.efectivo_usd), 
                SUM(o.zelle_usd), 
                SUM(o.bs_cambiados_usd)
            FROM operaciones_diarias o
            INNER JOIN usuarios u ON o.ruta_id = u.ruta
            WHERE o.fecha LIKE ? AND u.bajo_responsabilidad_supervisor = 1
        """, (f"{periodo_str}%",))

        row = cursor.fetchone()
        conexion.close()

        real_udvd = row[0] or 0.0
        real_cxc = row[1] or 0.0
        efectivo = row[2] or 0.0
        zelle = row[3] or 0.0
        bs = row[4] or 0.0

        pct_udvd = (real_udvd / cuota_udvd_sup * 100) if cuota_udvd_sup > 0 else 0.0
        pct_cxc = (real_cxc / cuota_cxc_sup * 100) if cuota_cxc_sup > 0 else 0.0

        return {
            "periodo": periodo_str,
            "cuota_udvd": cuota_udvd_sup,
            "acumulado_udvd": real_udvd,
            "porcentaje_udvd": pct_udvd,
            "falta_udvd": max(0.0, cuota_udvd_sup - real_udvd),
            "cuota_cxc": cuota_cxc_sup,
            "acumulado_cxc": real_cxc,
            "porcentaje_cxc": pct_cxc,
            "falta_cxc": max(0.0, cuota_cxc_sup - real_cxc),
            "efectivo": efectivo,
            "zelle": zelle,
            "bs": bs,
            "total_caja": efectivo + zelle + bs
        }
    def obtener_resumen_dashboard_ruta(self, ruta_id: int, periodo_str: str) -> dict:
        """
        Calcula el rendimiento acumulado del mes (YYYY-MM) para una sola ruta/vendedor.
        """
        cuota_udvd = self.obtener_cuota_individual(periodo_str, ruta_id, 'UDVD')
        cuota_cxc = self.obtener_cuota_individual(periodo_str, ruta_id, 'COBRANZA')
        
        progreso_udvd = self.obtener_progreso_individual(periodo_str, ruta_id, 'UDVD')
        progreso_cxc = self.obtener_progreso_individual(periodo_str, ruta_id, 'COBRANZA')
        
        run_rate_sugerido = self.calcular_meta_diaria_restante(periodo_str, ruta_id)

        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()

        # Consultar desglose acumulado de caja del mes para esa ruta
        cursor.execute("""
            SELECT 
                SUM(efectivo_usd), 
                SUM(zelle_usd), 
                SUM(bs_cambiados_usd),
                SUM(real_activaciones)
            FROM operaciones_diarias
            WHERE fecha LIKE ? AND ruta_id = ?
        """, (f"{periodo_str}%", int(ruta_id)))

        row = cursor.fetchone()
        conexion.close()

        efectivo = row[0] or 0.0
        zelle = row[1] or 0.0
        bs = row[2] or 0.0
        visitas_totales = row[3] or 0

        return {
            "periodo": periodo_str,
            "ruta": ruta_id,
            "cuota_udvd": cuota_udvd,
            "acumulado_udvd": progreso_udvd["acumulado"],
            "porcentaje_udvd": progreso_udvd["porcentaje"],
            "falta_udvd": progreso_udvd["falta"],
            "run_rate_diario": run_rate_sugerido,
            "cuota_cxc": cuota_cxc,
            "acumulado_cxc": progreso_cxc["acumulado"],
            "porcentaje_cxc": progreso_cxc["porcentaje"],
            "falta_cxc": progreso_cxc["falta"],
            "visitas_acumuladas": visitas_totales,
            "efectivo": efectivo,
            "zelle": zelle,
            "bs": bs,
            "total_caja": efectivo + zelle + bs
        }
        
        
    def obtener_estatus_hoy_todas_rutas(self, fecha_str: str = None) -> dict:
        """
        [USO EXCLUSIVO SUPERVISOR]
        Consulta rápido si las rutas ya enviaron su plan matutino, cierre nocturno y cobranza hoy.
        Retorna un diccionario con el estatus de cada ruta.
        """
        fecha_evaluar = self._normalizar_fecha(fecha_str)
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()

        try:
            cursor.execute("""
                SELECT ruta_id, meta_udvd, meta_cxc, real_udvd, real_cxc,
                    efectivo_usd, zelle_usd, bs_cambiados_usd
                FROM operaciones_diarias
                WHERE fecha = ?
            """, (fecha_evaluar,))
            filas = cursor.fetchall()

            estatus_rutas = {}
            for row in filas:
                ruta_id, meta_udvd, meta_cxc, real_udvd, real_cxc, efec, zelle, bs = row

                plan_listo = (meta_udvd > 0 or meta_cxc > 0)
                cierre_listo = (real_udvd > 0 or real_cxc > 0)
                suma_desglose_caja = float(efec or 0) + float(zelle or 0) + float(bs or 0)
                caja_listo = (suma_desglose_caja > 0)

                estatus_rutas[ruta_id] = {
                    "matutino": plan_listo,
                    "nocturno": cierre_listo,
                    "cobranza": caja_listo
                }

            return estatus_rutas

        except Exception as e:
            print(f"❌ [ReportesRepo] Error obteniendo estatus de todas las rutas: {e}")
            return {}
        finally:
            conexion.close()
    
    def obtener_estatus_hoy_ruta_individual(self, ruta_id: int, fecha_str: str = None) -> dict:
        """
        [USO EXCLUSIVO VENDEDOR]
        Consulta rápido si la ruta ya envió su plan matutino, cierre nocturno y cobranza hoy.
        """
        fecha_evaluar = self._normalizar_fecha(fecha_str)
        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()

        try:
            cursor.execute("""
                SELECT meta_udvd, meta_cxc, real_udvd, real_cxc,
                    efectivo_usd, zelle_usd, bs_cambiados_usd
                FROM operaciones_diarias
                WHERE fecha = ? AND ruta_id = ?
            """, (fecha_evaluar, int(ruta_id)))
            row = cursor.fetchone()

            if not row:
                return {
                    "matutino": False,
                    "nocturno": False,
                    "cobranza": False
                }

            meta_udvd, meta_cxc, real_udvd, real_cxc, efec, zelle, bs = row

            # 1. Plan Matutino cargado si hay metas mayores a cero
            plan_listo = (meta_udvd > 0 or meta_cxc > 0)
            
            # 2. Cierre Nocturno cargado si hay reporte de ventas o cobranza real
            cierre_listo = (real_udvd > 0 or real_cxc > 0)
            
            # 🎯 REGLA DE CAJA: Importa si especificó CÓMO se reparte el dinero
            suma_desglose_caja = float(efec or 0) + float(zelle or 0) + float(bs or 0)
            caja_listo = (suma_desglose_caja > 0)

            return {
                "matutino": plan_listo,
                "nocturno": cierre_listo,
                "cobranza": caja_listo
            }

        except Exception as e:
            print(f"❌ [ReportesRepo] Error obteniendo estatus del día: {e}")
            return {"matutino": False, "nocturno": False, "cobranza": False}
        finally:
            conexion.close()
        
        
    def limpiar_reporte_dia(self, ruta_id: int, fecha_str: str = None, modo: str = "COMPLETO") -> bool:
        """
        [MECANISMO DE SEGURIDAD Y REVERSIÓN]
        Limpia parcial o totalmente la operación de una ruta en una fecha.
        
        Modos soportados:
        - 'MATUTINO': Resetea metas a 0 (meta_udvd, meta_cxc, meta_activaciones)
        - 'NOCTURNO': Resetea logros reales y caja a 0 (real_udvd, real_cxc, real_activaciones, efectivo, zelle, bs)
                      y borra los cobros detallados por cliente en cobranzas_detalle.
        - 'COMPLETO' (Default): Resetea absolutamente toda la fila a 0 y borra detalles de cobranza.
        """
        fecha_evaluar = self._normalizar_fecha(fecha_str)
        modo_clean = modo.upper().strip()

        conexion = self.db.obtener_conexion()
        cursor = conexion.cursor()

        try:
            if modo_clean == "MATUTINO":
                cursor.execute("""
                    UPDATE operaciones_diarias
                    SET meta_udvd = 0, meta_cxc = 0.0, meta_activaciones = 0
                    WHERE fecha = ? AND ruta_id = ?
                """, (fecha_evaluar, int(ruta_id)))
                print(f"🧹 [ReportesRepo] Plan Matutino reseteado a 0 para Ruta {ruta_id} el {fecha_evaluar}.")

            elif modo_clean == "NOCTURNO":
                cursor.execute("""
                    UPDATE operaciones_diarias
                    SET real_udvd = 0, real_cxc = 0.0, real_activaciones = 0,
                        efectivo_usd = 0.0, zelle_usd = 0.0, bs_cambiados_usd = 0.0, tasa_bcv = 0.0
                    WHERE fecha = ? AND ruta_id = ?
                """, (fecha_evaluar, int(ruta_id)))
                
                # Limpiar también el detalle de cobros por clientes si existía
                cursor.execute("""
                    DELETE FROM cobranzas_detalle
                    WHERE fecha = ? AND ruta_id = ?
                """, (fecha_evaluar, int(ruta_id)))
                print(f"🧹 [ReportesRepo] Cierre Nocturno, Caja y Detalle borrados para Ruta {ruta_id} el {fecha_evaluar}.")

            elif modo_clean == "COMPLETO":
                cursor.execute("""
                    UPDATE operaciones_diarias
                    SET meta_udvd = 0, meta_cxc = 0.0, meta_activaciones = 0,
                        real_udvd = 0, real_cxc = 0.0, real_activaciones = 0,
                        efectivo_usd = 0.0, zelle_usd = 0.0, bs_cambiados_usd = 0.0, tasa_bcv = 0.0
                    WHERE fecha = ? AND ruta_id = ?
                """, (fecha_evaluar, int(ruta_id)))

                cursor.execute("""
                    DELETE FROM cobranzas_detalle
                    WHERE fecha = ? AND ruta_id = ?
                """, (fecha_evaluar, int(ruta_id)))
                print(f"💥 [ReportesRepo] Reset COMPLETO ejecutado para Ruta {ruta_id} el {fecha_evaluar}.")

            else:
                print(f"⚠️ [ReportesRepo] Modo de reversión desconocido: {modo}")
                return False

            conexion.commit()
            return True

        except Exception as e:
            print(f"❌ [ReportesRepo] Error en reversión de reporte: {e}")
            return False
        finally:
            conexion.close()