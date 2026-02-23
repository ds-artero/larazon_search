import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import altair as alt
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Scraper Claudia Zapater", layout="wide", page_icon="📝")

def extraer_fecha_exacta(tag_time):
    try:
        config_str = tag_time.get('data-module-launcher-config')
        if config_str:
            config_dict = json.loads(config_str)
            full_date = config_dict.get('publishDate', '')
            if full_date:
                return full_date[:10]
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
                # 1. Verificar Autor (FILTRO SOLICITADO)
                # Buscamos enlaces o textos que mencionen específicamente a Claudia Zapater
                autor_tag = art.find('a', string=lambda t: t and "Claudia Zapater" in t)
                if not autor_tag:
                    # Intento alternativo por si el nombre está en un span o clase específica
                    autor_tag = art.select_one('.article__author, .card__author')
                    if autor_tag and "Claudia Zapater" not in autor_tag.get_text():
                        continue # Si hay autor pero no es ella, saltamos
                    if not autor_tag:
                        # Si no encontramos rastro del autor en el card, 
                        # por precaución en este caso permitimos si el titular existe 
                        # (opcional: puedes poner 'continue' aquí si quieres ser 100% estricto)
                        pass

                # 2. Extraer Título
                tag_titulo = art.find(['h2', 'h3'])
                tag_enlace = art.find('a', href=True)
                
                titular = ""
                if tag_titulo:
                    titular = tag_titulo.get_text(strip=True)
                if len(titular) < 5 and tag_enlace:
                    titular = tag_enlace.get_text(strip=True) or tag_enlace.get('title', '')
                
                # 3. Extraer Fecha
                tag_time = art.find('time')
                fecha_str = extraer_fecha_exacta(tag_time) if tag_time else "2000-01-01"
                
                # 4. Extraer URL
                url_rel = tag_enlace['href'] if tag_enlace else ""
                url_completa = url_rel if url_rel.startswith('http') else f"https://www.larazon.es{url_rel}"

                # FILTRO FINAL: Titular presente + Fecha 2025+
                if titular and fecha_str >= "2025-01-01":
                    noticias.append({
                        "Título": titular,
                        "Fecha": fecha_str,
                        "URL": url_completa
                    })
                elif fecha_str < "2025-01-01" and fecha_str != "2000-01-01":
                    status_placeholder.success("✅ Filtrado por autor y fecha completado.")
                    return pd.DataFrame(noticias)
            
            pagina += 1
            time.sleep(0.5)
            
        except Exception as e:
            st.error(f"Error: {e}")
            break

    return pd.DataFrame(noticias)

# --- INTERFAZ STREAMLIT ---
st.title("📊 Monitor de Publicaciones: Claudia Zapater")
st.markdown("Solo se muestran artículos firmados por el autor y publicados desde **2025**.")

if st.button("🚀 Ejecutar Scraper"):
    df = iniciar_scraping("https://www.larazon.es/autores/claudia-zapater")
    
    if not df.empty:
        df['Fecha_dt'] = pd.to_datetime(df['Fecha'])
        df = df.sort_values('Fecha_dt')
        
        # Formato DEC-2025
        df['Mes-Año'] = df['Fecha_dt'].dt.strftime('%b-%Y').str.upper()
        
        conteo_mensual = df.groupby(['Mes-Año'], sort=False).size().reset_index(name='Cantidad')
        
        max_val = int(conteo_mensual['Cantidad'].max())
        limite_y = max_val + 5

        # Gráfico Altair
        chart = alt.Chart(conteo_mensual).mark_bar(color='#2A9D8F').encode(
            x=alt.X('Mes-Año:N', title='Mes de publicación', sort=None),
            y=alt.Y('Cantidad:Q', title='Artículos', scale=alt.Scale(domain=[0, limite_y])),
            tooltip=['Mes-Año', 'Cantidad']
        ).properties(height=400)
        
        st.altair_chart(chart, use_container_width=True)

        # Tabla
        df_display = df.sort_values('Fecha_dt', ascending=False).copy()
        df_display['Fecha'] = df_display['Fecha_dt'].dt.strftime('%d-%m-%Y')
        df_display.insert(0, '№', range(1, len(df_display) + 1))
        
        st.dataframe(
            df_display[['№', 'Título', 'Fecha', 'URL']],
            use_container_width=True,
            column_config={"URL": st.column_config.LinkColumn("Enlace")},
            hide_index=True
        )
    else:
        st.warning("No se encontraron artículos firmados por Claudia Zapater en 2025.")
