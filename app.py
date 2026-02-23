import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time

# --- FUNCIONES DE APOYO ---
def limpiar_fecha_exacta(tag_time):
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
    return texto

def scraping_pro(url_autor):
    lista_noticias = []
    pagina = 1
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/115.0.0.0"}
    
    status_text = st.empty()
    
    while True:
        url_actual = f"{url_autor}/{pagina}" if pagina > 1 else url_autor
        status_text.text(f"🔎 Analizando página {pagina}...")
        
        try:
            res = requests.get(url_actual, headers=headers, timeout=10)
            if res.status_code != 200:
                break
                
            soup = BeautifulSoup(res.text, 'html.parser')
            articulos = soup.find_all('article')
            
            if not articulos:
                break
                
            for art in articulos:
                enlace_tag = art.find('a', href=True, title=True)
                tag_time = art.find('time')
                
                if enlace_tag:
                    titular = enlace_tag.get_text(strip=True)
                    url_rel = enlace_tag['href']
                    url_completa = url_rel if url_rel.startswith('http') else f"https://www.larazon.es{url_rel}"
                    fecha = limpiar_fecha_exacta(tag_time) if tag_time else "2000-01-01"
                    
                    # FILTRO: Solo datos desde 2025
                    if fecha >= "2025-01-01":
                        lista_noticias.append({
                            "Título": titular,
                            "Fecha": fecha,
                            "URL": url_completa
                        })
                    elif fecha < "2025-01-01" and fecha != "N/A":
                        # Si ya llegamos a noticias de 2024, dejamos de buscar
                        status_text.text("📅 Alcanzado límite de fecha (2024). Finalizando...")
                        return pd.DataFrame(lista_noticias)
            
            time.sleep(0.4)
            pagina += 1
        except:
            break

    return pd.DataFrame(lista_noticias)

# --- INTERFAZ STREAMLIT ---
st.set_page_config(page_title="Scraper La Razón", layout="wide")

st.title("📊 Análisis de Artículos: Claudia Zapater")
st.markdown("Esta app extrae noticias de *La Razón* y analiza la frecuencia de publicación desde **2025**.")

if st.button("🚀 Iniciar Extracción de Datos"):
    with st.spinner("Trabajando..."):
        df = scraping_pro("https://www.larazon.es/autores/claudia-zapater")
        
    if not df.empty:
        # Convertir fecha a objeto datetime para manejar meses
        df['Fecha'] = pd.to_datetime(df['Fecha'])
        
        # 1. GRÁFICO POR MES
        st.subheader("📈 Artículos publicados por mes (2025+)")
        # Crear columna de Mes-Año para agrupar
        df['Mes'] = df['Fecha'].dt.to_period('M').astype(str)
        conteo_mensual = df.groupby('Mes').size()
        
        st.bar_chart(conteo_mensual)

        # 2. TABLA DE RESULTADOS
        st.subheader("📋 Detalle de Noticias")
        # Formatear la fecha para que se vea bonita en la tabla
        df_display = df.copy()
        df_display['Fecha'] = df_display['Fecha'].dt.strftime('%Y-%m-%d')
        
        # Re-insertar número de entrada
        df_display = df_display.reset_index(drop=True)
        df_display.insert(0, 'Número de entrada', range(1, len(df_display) + 1))
        
        st.dataframe(
            df_display[['Número de entrada', 'Título', 'Fecha', 'URL']], 
            use_container_width=True,
            column_config={
                "URL": st.column_config.LinkColumn("Enlace al artículo")
            }
        )
        
        # Botón de descarga
        csv = df_display.to_csv(index=False).encode('utf-8')
        st.download_button("💾 Descargar CSV", csv, "noticias_zapater.csv", "text/csv")
        
    else:
        st.warning("No se encontraron noticias de 2025 en adelante.")
