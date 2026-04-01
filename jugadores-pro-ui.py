import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import requests

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Admin Jugadores PRO (Dev Mode)", page_icon="🚀")

# --- 2. CONEXIÓN A NEON (DIAGNÓSTICO ROBUSTO) ---
@st.cache_resource
def inicializar_conexion():
    try:
        # Verificamos que la URL esté en los Secrets
        if "DATABASE_URL" not in st.secrets:
            st.error("❌ Error: No se encontró 'DATABASE_URL' en los Secrets de Streamlit.")
            return None
        
        url = st.secrets["DATABASE_URL"]
        
        # Parche de compatibilidad para SQLAlchemy 2.0+
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
            
        engine = create_engine(url)
        
        # Test de vida: ¿Neon responde?
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return engine
    except Exception as e:
        st.error(f"⚠️ Fallo crítico de conexión: {e}")
        return None

# Intentamos conectar de entrada
engine = inicializar_conexion()

# --- 3. INTERFAZ DE USUARIO ---
st.title("🚀 Jugadores PRO: Extracción Directa")
st.markdown("Fase de pruebas: Acceso directo al motor de sincronización.")

if engine is None:
    st.warning("Revisa la pestaña de Secrets en Streamlit Cloud. La base de datos no responde.")
    st.stop()

st.divider()

# --- 4. SELECCIÓN DE TORNEO ---
st.subheader("1. Seleccionar Torneo para Sincronizar")

try:
    with engine.connect() as db:
        query = text("""
            SELECT id, nombre 
            FROM torneos 
            WHERE fase = 'FINALIZADO'
            ORDER BY id DESC
        """)
        df_torneos = pd.read_sql(query, db)
except Exception as e:
    st.error(f"Error al leer torneos de Neon: {e}")
    df_torneos = pd.DataFrame()

if df_torneos.empty:
    st.info("No hay torneos finalizados en Neon.")
else:
    # Diccionario para el selector
    opciones = dict(zip(df_torneos['nombre'], df_torneos['id']))
    torneo_nombre = st.selectbox("Torneo:", options=list(opciones.keys()))
    id_torneo = opciones[torneo_nombre]
    
    st.write(f"Sincronizando ID: `{id_torneo}`")
    
    st.divider()
    
    # --- 5. EL DISPARADOR ---
    st.subheader("2. Ejecutar Lote")
    
    if st.button("🔥 DISPARAR SINCRONIZACIÓN", type="primary", use_container_width=True):
        
        # URL de tu API en Railway
        url_api = f"https://jugadorespro-produccion.up.railway.app/sincronizar-torneo/{id_torneo}"
        
        with st.spinner("⏳ La API de Railway está trabajando... No cierres esta pestaña."):
            try:
                # Petición a la FastAPI (con timeout largo)
                respuesta = requests.post(url_api, timeout=300)
                
                if respuesta.status_code == 200:
                    st.success("✅ ¡Misión cumplida! Datos inyectados en Neon.")
                    res_json = respuesta.json()
                    
                    with st.expander("Ver bitácora de la extracción"):
                        for log in res_json.get("detalle", []):
                            st.write(f"• {log}")
                else:
                    st.error(f"❌ La API falló (Status {respuesta.status_code})")
                    st.code(respuesta.text)
                    
            except Exception as e:
                st.error(f"❌ Error de red/timeout: {e}")
