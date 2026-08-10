# src/services/orquestador_datos.py

import os
from datetime import datetime
from services.excel_service import ExcelService

class OrquestadorDatos:
    def __init__(self, reportes_repo, logs_repo, dropbox_service,excel_service):
        """
        El cerebro unificado de Gasperini.
        Orquesta y amarra SQLite (reportes_repo), el Logger (logs_repo)
        y el inyector físico de Excel en Dropbox (ExcelService).
        """
        self.repo = reportes_repo
        self.logs = logs_repo
        self.dropbox = dropbox_service
        # Inyectamos el servicio real de Excel pasándole el conector de Dropbox
        self.excel = excel_service

    def _es_fecha_actual(self, fecha_str: str) -> bool:
        """Determina si una fecha pertenece al mes y año en curso para decidir el flujo de lectura"""
        try:
            fecha_evaluar = datetime.strptime(fecha_str.strip(), "%Y-%m-%d")
            ahora = datetime.now()
            return fecha_evaluar.month == ahora.month and fecha_evaluar.year == ahora.year
        except Exception:
            return True  # Por seguridad ante fallos, prioriza SQLite

    # ========================================================
    # 📥 CONTROL DE FLUJO: ESCRITURA REAL EN CALIENTE
    # ========================================================

    def procesar_plan_matutino(self, ruta: int, meta_udvd: float, meta_cobranza: float, meta_activaciones: int, fecha_str: str = None) -> bool:
            fecha_op = fecha_str if fecha_str else datetime.now().strftime("%Y-%m-%d")
            self.logs.registrar_log("INFO", f"Iniciando Plan Matutino Doble para Ruta {ruta} el {fecha_op}")

            # 1. Guardar en SQLite local
            exito_db = self.repo.registrar_o_actualizar_plan_matutino(
                ruta=ruta,
                meta_udvd=meta_udvd,
                meta_cobranza=meta_cobranza,
                meta_activaciones=meta_activaciones,
                fecha_especifica=fecha_op
            )

            if not exito_db:
                return False

            # 2. Inyección física en ambas pestañas (Día Previo + Día Actual)
            payload_metas = {
                "meta_udvd": meta_udvd,
                "meta_activaciones": meta_activaciones,
                "meta_cxc": meta_cobranza
            }

            return self.excel.inyectar_plan_matutino_doble(
                ruta=ruta,
                fecha_target=fecha_op,
                metas=payload_metas
            )
    def procesar_cierre_nocturno(self, ruta: int, real_udvd: float, real_cobranza: float, real_activaciones: int, efectivo: float, zelle: float, bs: float, tasa_bcv: float, fecha_str: str = None) -> bool:
            fecha_op = fecha_str if fecha_str else datetime.now().strftime("%Y-%m-%d")
            self.logs.registrar_log("INFO", f"Iniciando Cierre Nocturno para Ruta {ruta} el {fecha_op}")

            # 1. Guardar Cierre Nocturno en SQLite
            exito_db = self.repo.registrar_o_actualizar_cierre_nocturno(
                ruta=ruta,
                real_udvd=real_udvd,
                real_cobranza=real_cobranza,
                real_activaciones=real_activaciones,
                efectivo=efectivo,
                zelle=zelle,
                bs=bs,
                tasa_bcv=tasa_bcv,
                fecha_especifica=fecha_op
            )

            if not exito_db:
                return False

            # 2. Inyección de Logros en Excel (Filas 12, 15, 18)
            payload_cierre = {
                "real_udvd": real_udvd,
                "real_activaciones": real_activaciones,
                "real_cobranza": real_cobranza
            }

            exito_excel = self.excel.inyectar_cierre_nocturno_excel(
                ruta=ruta,
                fecha=fecha_op,
                datos_cierre=payload_cierre
            )
            ok_cobranza = self.excel.inyectar_cobranza_diaria_excel(
            ruta=ruta,
            fecha_str=fecha_op,
            efectivo=efectivo,
            zelle=zelle,
            bs=bs
        )
            

            if not exito_excel:
                return False

            # 3. Invocar Función Auxiliar de Relevo de Cobranza (Fase B)
            # Extraemos de SQLite los montos cobrados confirmados para esa fecha
            monto_cobrado_bd = self.repo.obtener_total_cobrado_ruta_fecha(ruta, fecha_op) or real_cobranza

            if monto_cobrado_bd > 0:
                lote_cobros = {ruta: monto_cobrado_bd}
                self.excel.actualizar_cobranza_acumulada_excel(lote_cobros=lote_cobros, fecha_str=fecha_op)

            return True
    # ========================================================
    # 🔍 CONTROL DE FLUJO: LECTURA INTELIGENTE MULTI-SOLICITUD
    # ========================================================

    def consultar_dashboard_inteligente(self, periodo_str: str, ruta_id: int = None, fecha_str: str = None) -> dict:
        """
        [ADUANA DE DATA MASTER]
        Implementa la función Multi-solicitud. Si la consulta corresponde al mes en curso,
        dispara el Dashboard BI en caliente desde SQLite a velocidad relámpago.
        Si se pide un mes viejo depurado, baja el histórico estructurado de Dropbox.
        """
        fecha_evaluar = fecha_str if fecha_str else datetime.now().strftime("%Y-%m-%d")
        
        if self._es_fecha_actual(fecha_evaluar):
            self.logs.registrar_log("INFO", f"📊 Despachando Dashboard BI Multi-solicitud desde SQLite local para {periodo_str}")
            return self.repo.obtener_dashboard_bi(
                periodo_str=periodo_str,
                ruta_id=ruta_id,
                fecha_especifica=fecha_evaluar
            )
        
        # FLUJO DE VIAJE EN EL TIEMPO: Data vieja depurada de SQLite
        self.logs.registrar_log("INFO", f"🔍 Extrayendo analítica histórica para {periodo_str} desde Dropbox...")
        
        # Traemos la información directo desde las funciones del adaptador físico de Excel
        datos_matutinos = self.excel.extraer_operacion_diaria_vendedor(ruta_id, fecha_evaluar) if ruta_id else {}
        datos_caja = self.excel.extraer_caja_nocturna_dia(fecha_evaluar)
        
        return {
            "periodo": periodo_str,
            "fecha_consulta": fecha_evaluar,
            "origen": "Dropbox Histórico",
            "datos_historicos_ruta": datos_matutinos,
            "matriz_caja_dia": datos_caja
        }

    # ========================================================
    # 🧹 CONTROL DE FLUJO: HIGIENE Y MIGRACIÓN CÍCLICA
    # ========================================================

    def ejecutar_mantenimiento_mensual(self, mes_str: str) -> bool:
        """
        Saca todo el histórico consolidado del mes de la tabla unificada de SQLite,
        valida que esté a salvo y purga la base de datos local para mantener a Gasperini ligero.
        """
        self.logs.registrar_log("WARNING", f"🧹 Iniciando ciclo de depuración e higiene para el mes: {mes_str}")
        
        # 1. Extraer bloque de operaciones unificadas
        data_vaciado = self.repo.extraer_todo_para_depuracion(mes_str)
        if not data_vaciado:
            self.logs.registrar_log("INFO", "No se encontraron registros locales que requieran depuración.")
            return True

        # 2. Realizar inyecciones de respaldo en masa por seguridad (si aplica)
        # Nota: Como nuestro sistema ya escribe en caliente cada noche, este paso es meramente
        # de auditoría para verificar que el Excel y la DB local estuvieran cuadrados.
        
        # 3. Purgar físicamente las filas de operaciones_diarias de ese mes
        exito_purga = self.repo.eliminar_bloque_depurado(mes_str)
        
        if exito_purga:
            self.logs.registrar_log("INFO", f"💥 Purga exitosa del mes {mes_str}. Base de datos local optimizada.")
            return True
        else:
            self.logs.registrar_log("ERROR", f"❌ No se pudo completar la purga del mes {mes_str} en SQLite.")
            return False
        
    def establecer_cuotas_mensuales(self, fecha_str: str, lote_cuotas: dict, usuarios_repo) -> tuple[bool, str]:
        """
        [MÉTODO MAESTRO COMPLETO]
        Valida, setea y edita las cuotas (UDVD, Cobranza, Visitas) para múltiples rutas.
        Si una cuota es 0 o no se especificó, SE IGNORA para no sobrescribir valores existentes.
        """
        print(f"\n⚡ [Orquestador] Procesando lote de cuotas para la fecha: {fecha_str}")
        
        # 0. DESEMPAQUETAR SI VIENE DENTRO DE "lote_cuotas"
        if isinstance(lote_cuotas, dict) and "lote_cuotas" in lote_cuotas:
            lote_cuotas = lote_cuotas["lote_cuotas"]

        # 1. VALIDACIÓN DE ENTRADAS Y RUTAS
        rutas_validas_db = usuarios_repo.listar_rutas_configuradas()
        lote_sanitizado = {}

        for ruta_id, metas in lote_cuotas.items():
            # Validación A: ¿La ruta existe en el sistema?
            if int(ruta_id) not in rutas_validas_db:
                print(f"⚠️ [Orquestador] La Ruta {ruta_id} no existe en la BD. Descartada.")
                continue

            # Validación B: Extraer solo valores > 0
            try:
                udvd_val = float(metas.get("udvd", 0.0))
                cxc_val = float(metas.get("cobranza", 0.0))
                visitas_val = float(metas.get("visitas", 0.0))
            except (ValueError, TypeError):
                msg = f"❌ Error: Se enviaron valores no numéricos para la Ruta {ruta_id}."
                print(f"⚠️ [Orquestador] {msg}")
                return False, msg

            # Construimos el trío ignorando lo que sea 0
            metas_filtradas = {}
            if udvd_val > 0:
                metas_filtradas["udvd"] = udvd_val
            if cxc_val > 0:
                metas_filtradas["cobranza"] = cxc_val
            if visitas_val > 0:
                metas_filtradas["visitas"] = visitas_val

            # Solo agregamos la ruta si tiene al menos una cuota válida a actualizar
            if metas_filtradas:
                lote_sanitizado[int(ruta_id)] = metas_filtradas

        if not lote_sanitizado:
            return False, "No se proporcionaron cuotas válidas mayores a cero para actualizar."

        # 2. EVALUACIÓN DE REGLA DE TIEMPO (FECHA)
        hoy_dt = datetime.now()
        fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
        
        es_mes_pasado = (fecha_dt.year < hoy_dt.year) or (fecha_dt.year == hoy_dt.year and fecha_dt.month < hoy_dt.month)
        es_mes_actual = (hoy_dt.year == fecha_dt.year and hoy_dt.month == fecha_dt.month)

        periodo_str = fecha_str[:7]

        if es_mes_pasado:
            cuota_existente = self.repo.obtener_cuota_global_mes(periodo_str, 'UDVD')
            if cuota_existente == 0.0:
                msg = f"⚠️ Operación omitida: El periodo {periodo_str} es pasado y no tiene registro previo en BD."
                print(f"🛑 [Orquestador] {msg}")

        # 3. IMPACTO EN SQLITE (Si es mes actual)
        if es_mes_actual:
            print("🗄️ [Orquestador] Registrando cuotas especificadas en SQLite...")
            for ruta_id, metas in lote_sanitizado.items():
                if "udvd" in metas:
                    self.repo.asignar_cuota_mensual(periodo_str, ruta_id, 'UDVD', metas["udvd"])
                if "cobranza" in metas:
                    self.repo.asignar_cuota_mensual(periodo_str, ruta_id, 'COBRANZA', metas["cobranza"])
                if "visitas" in metas:
                    self.repo.asignar_cuota_mensual(periodo_str, ruta_id, 'VISITAS', metas["visitas"])

        # 4. INYECCIÓN EN EXCEL & SYNCHRO DROPBOX
        print("📊 [Orquestador] Sincronizando con Excel en Dropbox...")
        exito_excel = self.excel.actualizar_cuotas_control_excel(
            fecha_str=fecha_str, 
            lote_cuotas=lote_sanitizado
        )

        if exito_excel:
            return True, "Cuotas actualizadas exitosamente en Base de Datos y Excel."
        else:
            return False, "Error al sincronizar las cuotas con el archivo en Dropbox."
    def procesar_reporte_texto_ia(self, texto_mensaje: str, parser_ia, ruta_fallback: int = None, fecha_fallback: str = None) -> tuple[bool, str]:
            """
            [MOTOR DE IMPACTO VÍA IA]
            Parsea un mensaje libre de Telegram usando Gemini y ejecuta
            automáticamente el flujo correspondiente (Mañana, Noche o Ajuste).
            """
            if not fecha_fallback:
                fecha_fallback = datetime.now().strftime("%Y-%m-%d")

            self.logs.registrar_log("INFO", f"🤖 Procesando reporte vía IA para mensaje: '{texto_mensaje[:40]}...'")

            # 1. Parsear el texto usando Gemini Flash
            payload_json = parser_ia.parsear_texto_libre(texto_mensaje)

            if not payload_json:
                msg = "❌ No se pudo interpretar el reporte. Por favor, verifica el formato."
                self.logs.registrar_log("WARNING", f"IA Parser devolvió None para: {texto_mensaje}")
                return False, msg

            # 2. Aplicar Fallbacks de Ruta y Fecha
            ruta_final = payload_json.get("ruta") or ruta_fallback
            fecha_final = payload_json.get("fecha_mencionada") or fecha_fallback

            if not ruta_final:
                return False, "❌ No se identificó la ruta en el mensaje ni en el perfil del usuario."

            tipo_intencion = payload_json.get("tipo_intencion")
            datos = payload_json.get("datos", {})

            print(f"📊 [Orquestador IA] Parseo Exitoso:")
            print(f"  📍 Ruta: {ruta_final} | Fecha: {fecha_final} | Intención: {tipo_intencion}")
            print(f"  📦 Datos extraídos: {datos}")

            # 3. Ruteo según la intencion detectada
            if tipo_intencion == "REPORTE_FULL_MANANA":
                exito = self.procesar_plan_matutino(
                    ruta=int(ruta_final),
                    meta_udvd=float(datos.get("unidades") or 0.0),
                    meta_cobranza=float(datos.get("cxc") or 0.0),
                    meta_activaciones=int(datos.get("visitas") or 0),
                    fecha_str=fecha_final
                )
                
                if exito:
                    msg_retorno = (
                        f"✅ **Plan Matutino Registrado Vía IA**\n\n"
                        f"📍 **Ruta:** {ruta_final}\n"
                        f"📅 **Fecha:** {fecha_final}\n"
                        f"📦 **UDVD:** {datos.get('unidades') or 0}\n"
                        f"🎯 **Visitas:** {datos.get('visitas') or 0}\n"
                        f"💰 **CXC Prometida:** ${datos.get('cxc') or 0.0}"
                    )
                    return True, msg_retorno
                return False, "Error al inyectar el plan matutino en el sistema."

            elif tipo_intencion == "REPORTE_FULL_NOCHE":
                # Aquí llamaremos al flujo de cierre nocturno
                exito = self.procesar_cierre_nocturno(
                    ruta=int(ruta_final),
                    real_udvd=float(datos.get("unidades") or 0.0),
                    real_cobranza=float(datos.get("cobranza_usd") or 0.0),
                    real_activaciones=int(datos.get("visitas") or 0),
                    efectivo=float(datos.get("efectivo_usd") or 0.0),
                    zelle=float(datos.get("zelle_usd") or 0.0),
                    bs=float(datos.get("bs_monto") or 0.0),
                    tasa_bcv=0.0,
                    fecha_str=fecha_final
                )
                if exito:
                    return True, f"✅ Cierre nocturno registrado vía IA para la Ruta {ruta_final} ({fecha_final})."
                return False, "Error al procesar el cierre nocturno."

            return False, f"Intención '{tipo_intencion}' no soportada actualmente."
    
    def consultar_informe_detallado(self, rutas_lista: list[int], fecha_str: str = None) -> str:
        """Formatea la consulta 360° para una o varias rutas"""
        data = self.repo.obtener_informe_360_rutas(rutas_lista, fecha_str)
        if not data:
            return "❌ No se encontraron datos para las rutas seleccionadas."

        texto_respuesta = "📊 **INFORME DETALLADO DE OPERACIONES**\n"
        
        for r_id, info in data.items():
            f = info["fechas"]
            ayer, hoy, manana = info["ayer"], info["hoy"], info["manana"]

            texto_respuesta += f"\n───────────────\n"
            texto_respuesta += f"📍 **RUTA {r_id}**\n"
            
            # AYER
            u_a = ayer.get("real_udvd", 0)
            m_u_a = ayer.get("meta_udvd", 0)
            st_a = "✅ Complete" if u_a > 0 else "⚠️ Sin reporte"
            texto_respuesta += f"⏮️ **Ayer ({f['ayer']}):** UDVD {u_a}/{m_u_a} | Status: {st_a}\n"

            # HOY
            m_h = hoy.get("meta_udvd", 0)
            r_h = hoy.get("real_udvd", 0)
            ef = hoy.get("efectivo_usd", 0.0)
            ze = hoy.get("zelle_usd", 0.0)
            bs = hoy.get("bs_cambiados_usd", 0.0)
            tot_caja = ef + ze + bs

            texto_respuesta += f"▶️ **Hoy ({f['hoy']}):**\n"
            texto_respuesta += f"  • Plan UDVD: {m_h} | Real UDVD: {r_h}\n"
            texto_respuesta += f"  • Cobranza Caja: ${tot_caja:.2f} (Efectivo: ${ef:.2f}, Zelle: ${ze:.2f}, Bs: ${bs:.2f})\n"

            # MAÑANA
            m_m = manana.get("meta_udvd", 0)
            st_m = "🟢 Plan Creado" if m_m > 0 else "🔴 Falta Plan"
            texto_respuesta += f"⏭️ **Mañana ({f['manana']}):** Plan UDVD: {m_m} | Status: {st_m}\n"

        return texto_respuesta
    def consultar_cuotas_mes(self, periodo_str: str) -> str:
        """Formatea la consulta de cuotas mensuales agrupando por ruta"""
        # 1. Obtenemos el diccionario agrupado {ruta_id: {tipo: valor}}
        cuotas_dict = self.repo.obtener_cuota_mes(periodo_str)
        
        if not cuotas_dict:
            return f"ℹ️ No se encontraron cuotas registradas para el mes <b>{periodo_str}</b>."

        # Header del reporte
        txt = f"📊 <b>CUOTAS MENSUALES — {periodo_str}</b>\n\n"

        # 2. Iteramos por cada ruta y sus metas
        for ruta_id, metas in cuotas_dict.items():
            udvd = int(metas.get("UDVD", 0))
            cobranza = float(metas.get("COBRANZA", 0.0))
            visitas = int(metas.get("VISITAS", 0))

            # Dibujamos cada tarjeta de ruta
            txt += f"🚛 <b>Ruta R-{ruta_id}</b>\n"
            txt += f" ├ 📦 UDVD: <code>{udvd}</code>\n"
            txt += f" ├ 💵 Cobranza: <code>${cobranza:,.2f}</code>\n"
            txt += f" └ 👥 Visitas: <code>{visitas}</code>\n\n"

        return txt.strip()
    def consultar_semaforo_hoy(self, fecha_str: str = None, incluir_todas_rutas: bool = True) -> str:
        """Formatea el resumen del semáforo exprés ('¿Cómo van hoy?')"""
        resumen = self.repo.obtener_semaforo_reportes_dia(fecha_str, incluir_todas_rutas)
        
        if not resumen:
            return "ℹ️ No hay rutas registradas para auditar."

        f_eval = fecha_str or datetime.now().strftime("%Y-%m-%d")
        filtro_txt = "Todas las Rutas" if incluir_todas_rutas else "Rutas bajo Supervisión Directa"
        
        txt = f"🚦 **ESTADO DE REPORTES DEL DÍA ({f_eval})**\n"
        txt += f"📋 *Filtro: {filtro_txt}*\n\n"

        for r in resumen:
            mat = "✅ listo" if r["matutino"] == "listo" else "🔴 falta"
            noc = "✅ listo" if r["nocturno"] == "listo" else "🔴 falta"
            cob = "✅ listo" if r["cobranza"] == "listo" else "🔴 falta"

            txt += f"• **Ruta {r['ruta']}:** Matutino: {mat} | Nocturno: {noc} | Cobranza: {cob}\n"

        return txt
    def consultar_dashboard_ruta(self, ruta_id: int, periodo_str: str = None) -> str:
        """Formatea la vista individual de un vendedor para el Dashboard BI"""
        p = periodo_str or datetime.now().strftime("%Y-%m")
        d = self.repo.obtener_resumen_dashboard_ruta(ruta_id, p)

        if not d or (d["cuota_udvd"] == 0 and d["acumulado_udvd"] == 0):
            return f"⚠️ No se encontraron datos ni cuotas registradas para la **Ruta {ruta_id}** en {p}."

        st_u = "🟢" if d["porcentaje_udvd"] >= 80 else "🟡" if d["porcentaje_udvd"] >= 50 else "🔴"
        st_c = "🟢" if d["porcentaje_cxc"] >= 80 else "🟡" if d["porcentaje_cxc"] >= 50 else "🔴"

        txt = f"👤 **INFORME DE RENDIMIENTO MES ({p})**\n"
        txt += f"📍 **Ruta:** {d['ruta']}\n\n"
        
        txt += f"📦 **VENTAS (UDVD):** {st_u}\n"
        txt += f"• Cuota: {d['cuota_udvd']:.0f} UDVD\n"
        txt += f"• Logrado: {d['acumulado_udvd']:.0f} UDVD ({d['porcentaje_udvd']:.1f}%)\n"
        txt += f"• Falta: {d['falta_udvd']:.0f} UDVD\n"
        txt += f"⚡ *Ritmo Requerido:* {d['run_rate_diario']} UDVD / día hábil\n\n"

        txt += f"💰 **COBRANZA ($):** {st_c}\n"
        txt += f"• Cuota: ${d['cuota_cxc']:.2f}\n"
        txt += f"• Logrado: ${d['acumulado_cxc']:.2f} ({d['porcentaje_cxc']:.1f}%)\n"
        txt += f"• Falta: ${d['falta_cxc']:.2f}\n\n"

        txt += f"💵 **DESGLOSE CAJA ACUMULADA:**\n"
        txt += f"• Efectivo: ${d['efectivo']:.2f}\n"
        txt += f"• Zelle: ${d['zelle']:.2f}\n"
        txt += f"• Bs: ${d['bs']:.2f}\n\n"
        txt += f"📊 *Total Entregado:* ${d['total_caja']:.2f}\n"
        txt += f"🎯 *Visitas Efectivas:* {d['visitas_acumuladas']} clientes\n"

        return txt
    
    def _generar_barra_progreso(self, porcentaje: float) -> str:
        """Helper para generar la barra visual de 10 bloques"""
        # Aseguramos que el porcentaje esté entre 0 y 100 para la barra
        porc_seguro = max(0, min(100, porcentaje))
        bloques_llenos = int(porc_seguro / 10)
        bloques_vacios = 10 - bloques_llenos
        return f"[{'█' * bloques_llenos}{'░' * bloques_vacios}]"

    def consultar_mi_rendimiento_vendedor(self, ruta_id: int) -> str:
        """Vista unificada ultrarrápida para el vendedor en Telegram"""
        hoy_str = datetime.now().strftime("%Y-%m-%d")
        mes_str = datetime.now().strftime("%Y-%m")
        
        # 1. Traer estatus de cargas de hoy
        st_hoy = self.repo.obtener_estatus_hoy_ruta_individual(ruta_id, hoy_str)
        
        # 2. Traer métricas del mes
        d = self.repo.obtener_resumen_dashboard_ruta(ruta_id, mes_str)

        m_icon = "✅ LISTO" if st_hoy["matutino"] else "🔴 PENDIENTE"
        n_icon = "✅ LISTO" if st_hoy["nocturno"] else "🔴 PENDIENTE"
        c_icon = "✅ LISTO" if st_hoy["cobranza"] else "🔴 PENDIENTE"

        # 3. Generar barras visuales
        barra_udvd = self._generar_barra_progreso(d['porcentaje_udvd'])
        barra_cxc = self._generar_barra_progreso(d['porcentaje_cxc'])

        txt = f"📱 **MI RENDIMIENTO - RUTA {ruta_id}**\n\n"
        
        txt += f"📋 **ESTATUS DE HOY ({hoy_str}):**\n"
        txt += f"• Plan Matutino: {m_icon}\n"
        txt += f"• Cierre Nocturno: {n_icon}\n"
        txt += f"• Cobranza / Caja: {c_icon}\n\n"

        txt += f"📦 **MIS VENTAS (UDVD):**\n"
        txt += f"• Meta Mes: {d['cuota_udvd']:.0f} UDVD\n"
        txt += f"• Logrado: {d['acumulado_udvd']:.0f} UDVD\n"
        txt += f"• Progreso: `{barra_udvd} {d['porcentaje_udvd']:.1f}%`\n"
        txt += f"• Falta: {d['falta_udvd']:.0f} UDVD\n"
        txt += f"⚡ *Ritmo sugerido:* {d['run_rate_diario']} UDVD / día hábil\n\n"

        txt += f"💰 **MI COBRANZA ($):**\n"
        txt += f"• Meta Mes: ${d['cuota_cxc']:.2f}\n"
        txt += f"• Logrado: ${d['acumulado_cxc']:.2f}\n"
        txt += f"• Progreso: `{barra_cxc} {d['porcentaje_cxc']:.1f}%`\n"
        txt += f"• Falta: ${d['falta_cxc']:.2f}\n"

        return txt
    
    
    def procesar_reversion_reporte(self, ruta_id: int, fecha_str: str = None, modo: str = "COMPLETO") -> str:
        """Maneja la reversión/limpieza en SQLite y confirma el resultado"""
        f_eval = fecha_str or datetime.now().strftime("%Y-%m-%d")
        exito = self.repo.limpiar_reporte_dia(ruta_id=ruta_id, fecha_str=f_eval, modo=modo)

        if exito:
            if modo == "MATUTINO":
                return f"✅ **Plan Matutino eliminado** para la **Ruta {ruta_id}** ({f_eval})."
            elif modo == "NOCTURNO":
                return f"✅ **Cierre Nocturno y Caja eliminados** para la **Ruta {ruta_id}** ({f_eval})."
            else:
                return f"💥 **Operación reseteada por completo** para la **Ruta {ruta_id}** ({f_eval})."
        else:
            return f"❌ Ocurrió un error intentando revertir la operación de la **Ruta {ruta_id}**."
        
        
        # ========================================================
    #       🔄 JOB NOCTURNO: ALINEACIÓN EXCEL ➔ SQLITE
    # ========================================================

    def ejecutar_sincronizacion_nocturna_excel(self, fecha_base_str: str = None) -> bool:
        """
        [CRON JOB 01:00 AM - EL EXCEL MANDA]
        Escanea de forma totalmente pasiva el libro .xlsm de Dropbox.
        Actualiza cuotas en CONTROL y operaciones diarias en SQLite.
        """
        f_eval = fecha_base_str or datetime.now().strftime("%Y-%m-%d")
        periodo_str = f_eval[:7]

        self.logs.registrar_log("INFO", f"⏰ Iniciando Job Nocturno de Alineación para {f_eval}")

        # 1. Disparar escáner pasivo en Excel
        data_excel = self.excel.escanear_libro_mensual_completo(f_eval)

        if not data_excel or (not data_excel["cuotas_control"] and not data_excel["operaciones_diarias"]):
            print("ℹ️ [Orquestador] No se encontraron datos para sincronizar o el libro no existe.")
            return True

        conexion = self.repo.db.obtener_conexion()
        cursor = conexion.cursor()

        try:
            # 2. Sincronizar Cuotas de Pestaña CONTROL
            cuotas = data_excel.get("cuotas_control", {})
            for ruta_id, metas in cuotas.items():
                if "udvd" in metas:
                    self.repo.asignar_cuota_mensual(periodo_str, ruta_id, 'UDVD', metas["udvd"])
                if "cobranza" in metas:
                    self.repo.asignar_cuota_mensual(periodo_str, ruta_id, 'COBRANZA', metas["cobranza"])
                if "visitas" in metas:
                    self.repo.asignar_cuota_mensual(periodo_str, ruta_id, 'VISITAS', metas["visitas"])

            print(f"✅ [Orquestador] {len(cuotas)} cuotas de la pestaña CONTROL alineadas en SQLite.")

            # 3. Sincronizar Operaciones Diarias
            ops_diarias = data_excel.get("operaciones_diarias", {})
            registros_procesados = 0

            for fecha_op, rutas_map in ops_diarias.items():
                for ruta_id, vals in rutas_map.items():
                    cursor.execute("""
                        INSERT INTO operaciones_diarias (
                            fecha, ruta_id, meta_udvd, real_udvd,
                            meta_activaciones, real_activaciones, meta_cxc, real_cxc
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(fecha, ruta_id) DO UPDATE SET
                            meta_udvd = excluded.meta_udvd,
                            real_udvd = excluded.real_udvd,
                            meta_activaciones = excluded.meta_activaciones,
                            real_activaciones = excluded.real_activaciones,
                            meta_cxc = excluded.meta_cxc,
                            real_cxc = excluded.real_cxc
                    """, (
                        fecha_op, int(ruta_id),
                        vals["meta_udvd"], vals["real_udvd"],
                        vals["meta_activaciones"], vals["real_activaciones"],
                        vals["meta_cxc"], vals["real_cxc"]
                    ))
                    registros_procesados += 1

            conexion.commit()
            print(f"✅ [Orquestador] {registros_procesados} registros diarios alineados con éxito en SQLite.")
            self.logs.registrar_log("INFO", "Sincronización nocturna completada. SQLite alineado con Excel.")
            return True

        except Exception as e:
            print(f"❌ [Orquestador] Error alineando SQLite desde el Excel: {e}")
            self.logs.registrar_log("ERROR", f"Error en sincronización nocturna: {e}")
            return False
        finally:
            conexion.close()