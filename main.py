@app.post("/sincronizar-torneo/{id_torneo}")
async def sincronizar_torneo(id_torneo: int):
    detalle_log = []
    try:
        with engine.connect() as db:
            # 1. Buscamos partidos del torneo que NO tengan estadísticas aún
            # Agregamos JOINs para traer los nombres de los equipos
            query = text("""
                SELECT 
                    p.id, 
                    el.nombre as local_nombre, 
                    ev.nombre as visitante_nombre 
                FROM partidos p
                JOIN equipos_globales el ON p.local_id = el.id
                JOIN equipos_globales ev ON p.visitante_id = ev.id
                WHERE p.id_torneo = :id 
                  AND p.estado = 'Finalizado'
            """)
            
            partidos = db.execute(query, {"id": id_torneo}).fetchall()
            
            if not partidos:
                return {"status": "ok", "detalle": ["No hay partidos finalizados pendientes de procesar."]}

            for p in partidos:
                p_id = p.id
                nombres_vs = f"{p.local_nombre} vs {p.visitante_nombre}"
                
                # --- AQUÍ EMPIEZA TU LÓGICA DE EXTRACCIÓN DE EA ---
                # Simulamos la búsqueda en EA con el ID y los nombres
                encontrado_en_ea = buscar_en_ea_sports(p_id) # Tu función actual
                
                if not encontrado_en_ea:
                    # SALIDA DETALLADA QUE PEDISTE:
                    detalle_log.append(f"❌ Partido {p_id} ({nombres_vs}): No encontrado en EA Sports.")
                else:
                    detalle_log.append(f"✅ Partido {p_id} ({nombres_vs}): Sincronizado correctamente.")
            
            return {"status": "completado", "detalle": detalle_log}

    except Exception as e:
        return {"status": "error", "detalle": [f"Error crítico: {str(e)}"]}
