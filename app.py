import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import altair as alt
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión de Artículos - Claudia Zapater", layout="wide", page_icon="💶")

# --- LÓGICA DE DATOS (SCRAPING) ---
def extraer_fecha_exacta(tag_time):
    try:
        config_str = tag_time.get('data-module-launcher-config')
        if config_str:
            config_dict = json.loads(config_str)
            full_date = config_dict.get('publishDate', '')
            if full_date:
                return str(full_date)[:10]
    except:
        pass
    texto = tag_time.get_text(strip=True)
    if "|" in texto:
        return texto.split("|")[0].strip()
    return "2000-01-01"

def iniciar_scraping(url_autor):
    noticias = []
    pagina = 1
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
    status_placeholder = st.empty()
    
    while True:
        url_actual = f"{url_autor}/{pagina}" if pagina > 1 else url_autor
        status_placeholder.info(f"🔍 Escaneando página {pagina}...")
        
        try:
            response = requests.get(url_actual, headers=headers, timeout=15)
            if response.status_code != 200: break
            soup = BeautifulSoup(response.text, 'html.parser')
            articulos = soup.find_all('article')
            if not articulos: break
                
            for art in articulos:
                autor_tag = art.find('a', string=lambda t: t and "Claudia Zapater" in t)
                if not autor_tag: continue 

                tag_titulo = art.find(['h2', 'h3'])
                tag_enlace = art.find('a', href=True)
                titular = tag_titulo.get_text(strip=True) if tag_titulo else ""
                tag_time = art.find('time')
                fecha_str = extraer_fecha_exacta(tag_time)
                
                url_rel = tag_enlace['href'] if tag_enlace else ""
                url_completa = url_rel if url_rel.startswith('http') else f"https://www.larazon.es{url_rel}"

                if titular and fecha_str >= "2025-01-01":
                    noticias.append({"Título": titular, "Fecha": fecha_str, "URL": url_completa})
                elif fecha_str < "2025-01-01" and fecha_str != "2000-01-01":
                    status_placeholder.success("✅ Datos actualizados correctamente.")
                    return pd.DataFrame(noticias)
            
            pagina += 1
            time.sleep(0.4)
        except: break
    return pd.DataFrame(noticias)

# --- INICIALIZACIÓN DE SESSION STATE ---
if 'df_original' not in st.session_state:
    st.session_state.df_original = None

# --- INTERFAZ ---
st.title("💶 Monitor de Producción y Facturación")

with st.sidebar:
    st.header("Control de Datos")
    if st.button("🚀 Cargar/Actualizar Datos"):
        df_recuperado = iniciar_scraping("https://www.larazon.es/autores/claudia-zapater")
        if not df_recuperado.empty:
            # Procesamiento inicial
            df_recuperado['Fecha_dt'] = pd.to_datetime(df_recuperado['Fecha'])
            df_recuperado['Mes-Filtro'] = df_recuperado['Fecha_dt'].dt.strftime('%m-%Y')
            df_recuperado['Mes-Grafico'] = df_recuperado['Fecha_dt'].dt.strftime('%b-%Y').str.upper()
            st.session_state.df_original = df_recuperado
        else:
            st.error("No se encontraron artículos nuevos.")

    if st.session_state.df_original is not None:
        st.markdown("---")
        st.header("Filtros de Vista")
        vista_grafico = st.radio("Ver gráfico por:", ["Nº de Noticias", "Euros (€)"])
        
        meses_disponibles = sorted(st.session_state.df_original['Mes-Filtro'].unique(), reverse=True)
        seleccion_meses = st.multiselect(
            "Seleccionar Meses:",
            options=meses_disponibles,
            default=meses_disponibles
        )

# --- MOSTRAR RESULTADOS SI HAY DATOS ---
if st.session_state.df_original is not None:
    # Filtrado dinámico (se ejecuta al mover el filtro sin borrar la memoria)
    df_filtrado = st.session_state.df_original[st.session_state.df_original['Mes-Filtro'].isin(seleccion_meses)].copy()

    if not df_filtrado.empty:
        # Métricas
        m1, m2, m3 = st.columns(3)
        total_noticias = len(df_filtrado)
        m1.metric("Artículos", total_noticias)
        m2.metric("Precio unitario", "80 €")
        m3.metric("Total Facturado", f"{total_noticias * 80} €")

        # Gráfico
        conteo_mensual = df_filtrado.groupby(['Mes-Grafico'], sort=False).size().reset_index(name='Cantidad')
        conteo_mensual['Euros'] = (conteo_mensual['Cantidad'] * 80).astype(float)
        
        y_col = 'Cantidad' if vista_grafico == "Nº de Noticias" else 'Euros'
        st.write(f"### 📈 Visualización por {vista_grafico}")
        
        chart = alt.Chart(conteo_mensual).mark_bar(color='#E63946').encode(
            x=alt.X('Mes-Grafico:N', title='Mes', sort=None),
            y=alt.Y(f'{y_col}:Q', title=y_col),
            tooltip=['Mes-Grafico', y_col]
        ).properties(height=350)
        st.altair_chart(chart, use_container_width=True)

        # Tabla
        st.write("### 📋 Histórico de Artículos")
        df_display = df_filtrado.sort_values('Fecha_dt', ascending=False).copy()
        df_display['Fecha_Exacta'] = df_display['Fecha_dt'].dt.strftime('%d-%m-%Y')
        df_display.insert(0, '№', range(1, len(df_display) + 1))
        
        st.dataframe(
            df_display[['№', 'Título', 'Fecha_Exacta', 'Mes-Filtro', 'URL']],
            use_container_width=True,
            column_config={
                "URL": st.column_config.LinkColumn("Enlace"),
                "Mes-Filtro": "Mes (MM-AAAA)",
                "Fecha_Exacta": "Publicado"
            },
            hide_index=True
        )
    else:
        st.warning("Selecciona al menos un mes en el filtro de la izquierda.")
else:
    st.info("👋 Haz clic en el botón 'Actualizar Datos' de la izquierda para comenzar.")
