import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import altair as alt

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Gestión de Artículos - Claudia Zapater", layout="wide", page_icon="💶")

# --- FUNCIONES DE SCRAPING ---
def extraer_fecha_exacta(tag_time):
    try:
        config_str = tag_time.get('data-module-launcher-config')
        if config_str:
            config_dict = json.loads(config_str)
            full_date = config_dict.get('publishDate', '')
            if full_date: return str(full_date)[:10]
    except: pass
    texto = tag_time.get_text(strip=True)
    return texto.split("|")[0].strip() if "|" in texto else "2000-01-01"

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
                if not art.find('a', string=lambda t: t and "Claudia Zapater" in t): continue 
                titular = art.find(['h2', 'h3']).get_text(strip=True) if art.find(['h2', 'h3']) else ""
                fecha_str = extraer_fecha_exacta(art.find('time'))
                url_rel = art.find('a', href=True)['href']
                url_completa = url_rel if url_rel.startswith('http') else f"https://www.larazon.es{url_rel}"

                if titular and fecha_str >= "2025-01-01":
                    noticias.append({"Título": titular, "Fecha": fecha_str, "URL": url_completa})
                elif fecha_str < "2025-01-01" and fecha_str != "2000-01-01":
                    status_placeholder.success("✅ Datos actualizados.")
                    return pd.DataFrame(noticias)
            pagina += 1
            time.sleep(0.4)
        except: break
    return pd.DataFrame(noticias)

# --- SESSION STATE ---
if 'df_original' not in st.session_state:
    st.session_state.df_original = None

# --- INTERFAZ ---
st.title("💶 Monitor de Producción y Facturación")

with st.sidebar:
    st.header("Control")
    if st.button("🚀 Actualizar Datos"):
        df_raw = iniciar_scraping("https://www.larazon.es/autores/claudia-zapater")
        if not df_raw.empty:
            df_raw['Fecha_dt'] = pd.to_datetime(df_raw['Fecha'])
            df_raw['Mes-Filtro'] = df_raw['Fecha_dt'].dt.strftime('%m-%Y')
            df_raw['Mes-Grafico'] = df_raw['Fecha_dt'].dt.strftime('%b-%Y').str.upper()
            st.session_state.df_original = df_raw

    if st.session_state.df_original is not None:
        st.markdown("---")
        vista_grafico = st.radio("Ver gráfico por:", ["Nº de Noticias", "Euros (€)"])
        meses_disponibles = sorted(st.session_state.df_original['Mes-Filtro'].unique(), reverse=True)
        seleccion_meses = st.multiselect("Filtrar TABLA por mes:", options=meses_disponibles, default=meses_disponibles)

# --- RENDERIZADO ---
if st.session_state.df_original is not None:
    df_total = st.session_state.df_original
    
    # 1. MÉTRICAS (Siempre del total)
    m1, m2, m3 = st.columns(3)
    total_arts = len(df_total)
    m1.metric("Total Artículos 2025", total_arts)
    m2.metric("Precio unitario", "80 €")
    m3.metric("Total Facturado Anual", f"{total_arts * 80} €")

    # 2. GRÁFICA (Highlight)
    conteo_mensual = df_total.groupby(['Mes-Grafico', 'Mes-Filtro'], sort=False).size().reset_index(name='Cantidad')
    conteo_mensual['Euros'] = conteo_mensual['Cantidad'] * 80
    y_col = 'Cantidad' if vista_grafico == "Nº de Noticias" else 'Euros'
    
    # Lógica de color: Si el mes está en la selección, Rojo; si no, Gris.
    conteo_mensual['Color'] = conteo_mensual['Mes-Filtro'].apply(
        lambda x: '#E63946' if x in seleccion_meses else '#D3D3D3'
    )

    st.write(f"### 📈 Rendimiento Mensual (Resaltado: {', '.join(seleccion_meses)})")
    chart = alt.Chart(conteo_mensual).mark_bar().encode(
        x=alt.X('Mes-Grafico:N', title='Mes', sort=None),
        y=alt.Y(f'{y_col}:Q', title=y_col),
        color=alt.Color('Color:N', scale=None), # Usa los colores definidos en la columna 'Color'
        tooltip=['Mes-Grafico', y_col]
    ).properties(height=350)
    st.altair_chart(chart, use_container_width=True)

    # 3. TABLA (Filtrada)
    st.write(f"### 📋 Detalle de Artículos ({len(seleccion_meses)} meses seleccionados)")
    df_tabla = df_total[df_total['Mes-Filtro'].isin(seleccion_meses)].sort_values('Fecha_dt', ascending=False).copy()
    df_tabla['Fecha_Pub'] = df_tabla['Fecha_dt'].dt.strftime('%d-%m-%Y')
    df_tabla.insert(0, '№', range(1, len(df_tabla) + 1))
    
    st.dataframe(
        df_tabla[['№', 'Título', 'Fecha_Pub', 'Mes-Filtro', 'URL']],
        use_container_width=True,
        column_config={
            "URL": st.column_config.LinkColumn("Enlace"),
            "Mes-Filtro": "Mes (MM-AAAA)",
            "Fecha_Pub": "Publicado"
        },
        hide_index=True
    )
else:
    st.info("👋 Haz clic en 'Actualizar Datos' para cargar la información.")
