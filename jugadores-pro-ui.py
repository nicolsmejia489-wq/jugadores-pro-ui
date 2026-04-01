import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text
import requests

# --- CONFIGURACIÓN DE PÁGINA Y SEGURIDAD ---
st.set_page_config(page_title="Admin Jugadores PRO", page_icon="⚙️")

# Una barrera de seguridad simple para que solo tú entres por ahora
password_correcta = "AdminGolGana2026"  # Cambia esto por tu clave real
if "autenticado" not in st.session_state:
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🔒 Acceso Restringido")
    pwd_ingresada = st.text_input("Contraseña de Administrador:", type="password")
    if st.button("Ingresar"):
        if pwd_ingresada == password_correcta:
            st.session_state.autenticado = True
            st.rerun()
        else:
            st.error("Contraseña incorrecta.")
    st.stop() # Detiene la ejecución si no está logueado

# --- CONEXIÓN A NEON ---
# Asegúrate de poner tu DATABASE_URL en los secrets de este nuevo Streamlit
try:
    engine = create_engine(st.secrets["DATABASE_URL"])
except Exception as e:
    st.error("Falta configurar los secrets de la base de datos.")
    st.stop()

# --- INTERFAZ PRINCIPAL ---
st.title("⚙️ Panel de Control: Jugadores PRO")
st.markdown("Plataforma exclusiva para la gestión profunda de estadísticas.")
st.divider()

st.subheader("1. Torneos Disponibles para Sincronización")

# Buscamos los torneos finalizados directamente en tu BD
try:
    with engine.connect() as db:
        query = text("""
            SELECT id, nombre, fecha_fin 
            FROM torneos 
            WHERE estado = 'Finalizado'
            ORDER BY id DESC
        """)
        df_torneos = pd.read_sql(query, db)
except Exception as e:
    st.error(f"Error leyendo Neon: {e}")
    df_torneos = pd.DataFrame()

if df_torneos.empty:
    st.info("No hay torneos en estado 'Finalizado' listos para procesar.")
else:
    # Selector de torneo
    opciones = dict(zip(df_torneos['nombre'], df_torneos['id']))
    torneo_elegido = st.selectbox("Selecciona el torneo:", options=list(opciones.keys()))
    id_torneo = opciones[torneo_elegido]
    
    st.caption(f"ID del Torneo seleccionado: {id_torneo}")
    
    st.divider()
    st.subheader("2. Motor de Extracción EA Sports")
    st.info("Este botón enviará la orden a nuestra API en Railway para que busque los partidos del torneo seleccionado y extraiga las estadísticas de cada jugador.")
    
    # --- EL BOTÓN QUE LLAMA A TU FASTAPI ---
    if st.button("🚀 Iniciar Sincronización por Lotes", type="primary", use_container_width=True):
        
        # Aquí ponemos la URL de la API que tienes encendida en Railway
        # Asegúrate de no poner una barra (/) al final del dominio si la ruta ya la tiene
        url_api = f"https://jugadorespro-produccion.up.railway.app/sincronizar-torneo/{id_torneo}"
        
        with st.spinner("Enviando orden a la API... El servidor está procesando los partidos."):
            try:
                # Disparamos la petición POST a FastAPI
                respuesta = requests.post(url_api)
                
                if respuesta.status_code == 200:
                    st.success("✅ ¡La API terminó el proceso con éxito!")
                    datos = respuesta.json()
                    
                    # Mostramos el reporte que nos mandó FastAPI
                    with st.expander("Ver reporte detallado de la API"):
                        for linea in datos.get("detalle", []):
                            st.write(f"- {linea}")
                else:
                    st.error(f"⚠️ La API devolvió un error (Código {respuesta.status_code})")
                    st.write(respuesta.text)
                    
            except Exception as e:
                st.error(f"❌ No se pudo conectar con la API en Railway. Detalle: {e}")