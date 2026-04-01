from fastapi import FastAPI
from sqlalchemy import create_engine, text
import os

app = FastAPI()

# --- 1. CONEXIÓN A BASE DE DATOS (ESTILO RAILWAY) ---
def get_engine():
    # Railway usa variables de entorno, no st.secrets
    url = os.getenv("DATABASE_URL")
    if not url:
        return None
    
    # Parche por si la URL de Neon viene con postgres://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    
    return create_engine(url)

engine = get_engine()

# --- 2. ENDPOINT DE SINCRONIZACIÓN ---
@app.post("/sincronizar-torneo/{id_torneo}")
async def sincronizar_torneo(id_torneo: int):
    detalle_log = []
    
    if engine is None:
        return {"status": "error", "detalle": ["Error: DATABASE_URL no configurada en Railway."]}

    try:
        with engine.connect() as db:
            # Buscamos partidos con JOIN para tener los nombres
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
                ORDER BY p.id ASC
            """)
            
            partidos = db.execute(query, {"id": id_torneo}).fetchall()
            
            if not partidos:
                return {"status": "ok", "detalle": ["No se encontraron partidos finalizados para este torneo."]}

            for p in partidos:
                nombres_vs = f"{p.local_nombre} vs {p.visitante_nombre}"
                
                # --- LÓGICA DE EXTRACCIÓN (Tu función mágica de EA) ---
                # Aquí iría tu función que raspa EA Sports. 
                # Por ahora simulamos el resultado:
                exito = False # Cambia esto por tu lógica real de scraping
                
                if exito:
                    detalle_log.append(f"✅ Partido {p.id} ({nombres_vs}): Sincronizado.")
                else:
                    detalle_log.append(f"❌ Partido {p.id} ({nombres_vs}): No encontrado en EA.")
            
            return {"status": "completado", "detalle": detalle_log}

    except Exception as e:
        return {"status": "error", "detalle": [f"Error crítico en el worker: {str(e)}"]}

@app.get("/")
def home():
    return {"mensaje": "Worker de Jugadores PRO activo"}
