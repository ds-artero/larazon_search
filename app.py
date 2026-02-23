import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import altair as alt
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Scraper La Razón - 2025", layout="wide", page_icon="📰")

# --- 1. FUNCIONES DE EXTRACCIÓN (MOTOR DEL SCRAPER) ---

def extraer_fecha_exacta(tag_time):
    """Extrae la fecha real del atributo JSON o del texto."""
    try:
        config_str = tag_time.get('data-module-launcher-config')
        if config_str:
            config_dict = json.loads(config_str)
            full_date = config_dict.get('publishDate', '')
            if full_date:
                return full_date[:10]  # Retorna YYYY-MM-DD
    except:
        pass
    
    texto = tag_time.get_text(strip=True)
    if "|" in texto:
        return texto.split("|")[0].strip()
    return "2000-01-01"

def iniciar_scraping(url_autor):
    noticias = []
    pagina = 1
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    status_placeholder = st.empty()
    
    while True:
        url_actual = f"{url_autor}/{pagina}" if pagina > 1 else url_autor
        status_placeholder.info(f"🔍 Analizando página {pagina}...")
        
        try:
            response = requests.get(url_actual, headers=headers, timeout=15)
            if response.status_code != 200:
                break
                
            soup = BeautifulSoup(response.text, 'html.parser')
            articulos = soup.find_all('article')
            
            if not articulos:
                break
                
            for art in articulos:
                # Extraer Título (Lógica de triple verificación)
                tag_titulo = art.find(['h2', 'h3'])
                tag_enlace = art.find('a', href=True)
                
                titular = ""
                if tag_titulo:
                    titular = tag_titulo.get_text(strip=True)
                if len(titular) < 5 and tag_enlace:
                    titular = tag_enlace.get_text(strip=True) or tag_enlace.get('title', '')
                
                # Extraer Fecha
                tag_time = art.find('time')
                fecha_str = extraer_fecha_exacta(tag_time) if tag_time else "2000-01-01"
                
                # Extraer URL
                url_rel = tag_enlace['href'] if tag_enlace else ""
                url_completa = url_rel if url_rel.startswith('http') else f"https://www.larazon.es{url_rel}"

                # FILTRO 2025
                if titular and fecha_str >= "2025-01-01":
                    noticias.append({
                        "Título": titular,
                        "Fecha": fecha_str,
                        "URL": url_completa
                    })
                elif fecha_str < "2025-01-01" and fecha_str != "2000-01-01":
                    status_placeholder.success("✅ Datos de 2025 completados.")
                    return pd.DataFrame(noticias)
            
            pagina += 1
            time.sleep(0.5)
            
        except Exception as e:
            st.error(f"Error: {e}")
            break

    return pd.DataFrame(noticias)

# --- 2. INTERFAZ DE USUARIO (STREAMLIT) ---

st.title("📊 Análisis de Publicaciones - La Razón")
st.markdown("Extrayendo artículos de **Claudia Zapater** desde el 1 de enero de 2025.")

if st.button("🚀 Iniciar Extracción"):
    df = iniciar_scraping("https://www.larazon.es/autores/claudia-zapater")
    
    if not df.empty:
        # Convertir a datetime
        df['Fecha_dt'] = pd.to_datetime(df['Fecha'])
        
        # Formatear mes como DEC-2025 (ordenado cronológicamente para el gráfico)
        df = df.sort_values('Fecha_dt')
        df['Mes-Año'] = df['Fecha_dt'].dt.strftime('%b-%Y').str.upper()
        
        # Agrupar para el gráfico
        conteo_mensual = df.groupby(['Mes-Año'], sort=False).size().reset_index(name='Cantidad')
        
        # Lógica de escala Y (mín 0, máx + 5)
        max_val = int(conteo_mensual['Cantidad'].max())
        limite_y = max_val + 5

        # --- GRÁFICO ALTAIR ---
        st.write("### 📈 Artículos por Mes")
        chart = alt.Chart(conteo_mensual).mark_bar(color='#E63946').encode(
            x=alt.X('Mes-Año:N', title='Mes', sort=None),
            y=alt.Y('Cantidad:Q', title='Nº de Artículos', scale=alt.Scale(domain=[0, limite_y])),
            tooltip=['Mes-Año', 'Cantidad']
        ).properties(height=400)
        
        st.altair_chart(chart, use_container_width=True)

        # --- TABLA DE DATOS ---
        st.write("### 📋 Detalle de Noticias")
        df_display = df.sort_values('Fecha_dt', ascending=False).copy()
        df_display['Fecha'] = df_display['Fecha_dt'].dt.strftime('%d-%m-%Y')
        df_display.insert(0, '№', range(1, len(df_display) + 1))
        
        st.dataframe(
            df_display[['№', 'Título', 'Fecha', 'URL']],
            use_container_width=True,
            column_config={"URL": st.column_config.LinkColumn("Ver noticia")},
            hide_index=True
        )
        
        # Descarga CSV
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Descargar Datos (CSV)", csv, "noticias_2025.csv", "text/csv")
        
    else:
        st.warning("No se encontraron noticias de 2025.")
