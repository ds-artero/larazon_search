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
    
    # Filtramos desde el inicio de 2025 para tener histórico, 
    # pero la app priorizará 2026 para los cálculos
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
                tag_enlace = art.find('a', href=True)
                url_rel = tag_enlace['href'] if tag_enlace else ""
                url_completa = url_rel if url_rel.startswith('http') else f"https://www.larazon.es{url_rel}"

                # Recogemos datos desde 2025 para que el gráfico tenga contexto histórico
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
            df_raw['Año'] = df_raw['Fecha_dt'].dt.year
            df_raw['Mes-Filtro'] = df_raw['Fecha_dt'].dt.strftime('%m-%Y')
            df_raw['Mes-Grafico'] = df_raw['Fecha_dt'].dt.strftime('%b-%Y').str.upper()
            df_raw['Orden_Mes'] = df_raw['Fecha_dt'].dt.year * 100 + df_raw['Fecha_dt'].dt.month
            st.session_state.df_original = df_raw

    if st.session_state.df_original is not None:
        st.markdown("---")
        vista_grafico = st.radio("Ver gráfico por:", ["Nº de Noticias", "Euros (€)"])
        meses_disponibles = sorted(st.session_state.df_original['Mes-Filtro'].unique(), 
                                   key=lambda x: datetime.strptime(x, '%m-%Y'), reverse=True)
        seleccion_meses = st.multiselect("Filtrar TABLA por mes:", options=meses_disponibles, default=meses_disponibles)

# --- RENDERIZADO ---
if st.session_state.df_original is not None:
    # SEPARACIÓN POR AÑO PARA CÁLCULOS
    df_total = st.session_state.df_original
    df_2026 = df_total[df_total['Año'] == 2026].copy()
    
    # --- LÓGICA DE PROYECCIÓN 2026 ---
    fecha_inicio_2026 = datetime(2026, 1, 1)
    fecha_hoy = datetime.now()
    dias_transcurridos_2026 = (fecha_hoy - fecha_inicio_2026).days + 1
    
    total_arts_2026 = len(df_2026)
    ritmo_diario_2026 = total_arts_2026 / dias_transcurridos_2026
    promedio_mensual_2026 = ritmo_diario_2026 * 30.41
    proyeccion_anual_2026 = ritmo_diario_2026 * 365

    # 1. MÉTRICAS (SOLO 2026)
    st.write(f"### 📊 Resumen Rendimiento 2026 (Día {dias_transcurridos_2026} de 365)")
    m1, m2, m3 = st.columns(3)
    m1.metric("Artículos 2026", total_arts_2026)
    m2.metric("Ritmo Mensual Ajustado", f"{promedio_mensual_2026:.1f} art/mes")
    m3.metric("Proyección Final 2026", f"{int(proyeccion_anual_2026)} art.")

    c1, c2, c3 = st.columns(3)
    c1.metric("Facturado 2026", f"{total_arts_2026 * 80} €")
    c2.metric("Media Ingresos/Mes", f"{int(promedio_mensual_2026 * 80)} €")
    c3.metric("Expectativa Total 2026", f"{int(proyeccion_anual_2026 * 80)} €")

    # 2. GRÁFICA (CONTEXTO HISTÓRICO + HIGHLIGHT)
    conteo_mensual = df_total.groupby(['Mes-Grafico', 'Mes-Filtro', 'Orden_Mes'], sort=False).size().reset_index(name='Cantidad')
    conteo_mensual['Euros'] = conteo_mensual['Cantidad'] * 80
    y_col = 'Cantidad' if vista_grafico == "Nº de Noticias" else 'Euros'
    
    conteo_mensual['Color'] = conteo_mensual['Mes-Filtro'].apply(
        lambda x: '#E63946' if x in seleccion_meses else '#D3D3D3'
    )

    st.write(f"### 📈 Evolución Histórica (2025-2026)")
    
    chart = alt.Chart(conteo_mensual).mark_bar().encode(
        x=alt.X('Mes-Grafico:N', title='Mes', sort=alt.SortField(field='Orden_Mes', order='ascending')),
        y=alt.Y(f'{y_col}:Q', title=y_col),
        color=alt.Color('Color:N', scale=None),
        tooltip=['Mes-Grafico', y_col]
    ).properties(height=400)
    
    st.altair_chart(chart, use_container_width=True)

    # 3. TABLA (Filtrada)
    st.write(f"### 📋 Detalle de Artículos")
    df_tabla = df_total[df_total['Mes-Filtro'].isin(seleccion_meses)].sort_values('Fecha_dt', ascending=False).copy()
    df_tabla['Fecha_Pub'] = df_tabla['Fecha_dt'].dt.strftime('%d-%m-%Y')
    df_tabla.insert(0, '№', range(1, len(df_tabla) + 1))
    
    st.dataframe(
        df_tabla[['№', 'Título', 'Fecha_Pub', 'Mes-Filtro', 'URL']],
        use_container_width=True,
        column_config={
            "URL": st.column_config.LinkColumn("Enlace"),
            "Mes-Filtro": "Mes",
            "Fecha_Pub": "Publicado"
        },
        hide_index=True
    )
else:
    st.info("👋 Haz clic en 'Actualizar Datos' para ver el resumen de 2026.")
