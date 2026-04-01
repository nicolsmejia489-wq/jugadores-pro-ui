from fastapi import FastAPI, HTTPException
import requests
import urllib3
import time
from sqlalchemy import create_engine, text
import os

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = FastAPI(title="GolGana EA Worker")

# Configuramos la base de datos leyendo la variable de entorno
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    engine = create_engine(DATABASE_URL)

# --- AQUÍ PEGAMOS LAS FUNCIONES DE EXTRACCIÓN QUE YA HICIMOS ---
def limpiar_jugadores(jugadores_dict):
    # (El mismo código que ya validamos)
    datos_limpios = []
    for id_ea, j in jugadores_dict.items():
        datos_limpios.append({
            "nombre": j.get('playername', 'Desconocido'),
            "goles": j.get('goals', '0'),
            "asistencias": j.get('assists', '0'),
            "pases_c": j.get('passesmade', '0'),
            "pases_i": j.get('passattempts', '0'),
            "quites": j.get('tacklesmade', '0'),
            "nota": j.get('rating', '0.0')
        })
    return datos_limpios

def extraccion_ea(id_local, id_visitante):
    url = f"https://proclubs.ea.com/api/fc/clubs/matches?matchType=friendlyMatch&platform=common-gen5&clubIds={id_local}"
    headers = {'accept': 'application/json', 'user-agent': 'Mozilla/5.0'}
    
    response = requests.get(url, headers=headers, verify=False)
    if response.status_code == 200:
        historial = response.json()
        for partido in historial:
            ids_jugando = list(partido['clubs'].keys())
            if str(id_local) in ids_jugando and str(id_visitante) in ids_jugando:
                return {
                    "marcador_local": partido['clubs'][str(id_local)].get('goals', '0'),
                    "marcador_visitante": partido['clubs'][str(id_visitante)].get('goals', '0'),
                    "jugadores_local": limpiar_jugadores(partido['players'][str(id_local)]),
                    "jugadores_visitante": limpiar_jugadores(partido['players'][str(id_visitante)])
                }
    return None

# --- EL ENDPOINT QUE DISPARA EL TRABAJO ---
@app.post("/sincronizar-torneo/{id_torneo}")
def sincronizar_torneo(id_torneo: int):
    try:
        with engine.connect() as db:
            # 1. Ejecutamos tu consulta maestra
            query = text("""
                SELECT 
                    p.id AS id_partido, p.local_id, el.id_eafc_equipo AS ea_id_local,
                    p.visitante_id, ev.id_eafc_equipo AS ea_id_visitante
                FROM partidos p
                JOIN equipos_globales el ON p.local_id = el.id
                JOIN equipos_globales ev ON p.visitante_id = ev.id
                WHERE p.id_torneo = :id_torneo 
                  AND p.metodo_registro = 'IA' 
                  AND p.estado = 'Finalizado'
                  AND el.id_eafc_equipo IS NOT NULL 
                  AND ev.id_eafc_equipo IS NOT NULL;
            """)
            
            partidos = db.execute(query, {"id_torneo": id_torneo}).fetchall()
            
            if not partidos:
                return {"mensaje": "No hay partidos pendientes de sincronizar."}

            resultados_log = []

            # 2. Ciclo secuencial (Batch)
            for partido in partidos:
                id_partido = partido[0]
                ea_local = partido[2]
                ea_visita = partido[4]
                
                print(f"🔄 Procesando partido {id_partido}...")
                datos_ea = extraccion_ea(ea_local, ea_visita)
                
                if datos_ea:
                    # ---> AQUÍ VA TU LÓGICA DE GUARDADO (INSERT/UPDATE) <---
                    # Ejemplo:
                    # db.execute(text("UPDATE partidos SET goles_l=:gl, goles_v=:gv WHERE id=:id"), 
                    #            {"gl": datos_ea['marcador_local'], "gv": datos_ea['marcador_visitante'], "id": id_partido})
                    
                    # Iterar jugadores y guardar:
                    # for j in datos_ea['jugadores_local']:
                    #    db.execute(...)
                    
                    db.commit()
                    resultados_log.append(f"Partido {id_partido}: OK")
                else:
                    resultados_log.append(f"Partido {id_partido}: No encontrado en EA")
                
                # Pausa táctica de 2 segundos para no saturar a EA
                time.sleep(2)

            return {"mensaje": "Sincronización completada", "detalle": resultados_log}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))