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
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
    status_placeholder = st.empty()
    
    while True:
        url_actual = f"{url_autor}/{pagina}" if pagina > 1 else url_autor
        status_placeholder.info(f"🔍 Escaneando página {pagina}...")
        
        try:
            response = requests.get(url_actual, headers=headers, timeout=15)
            if response.status_code != 200:
                break
            soup = BeautifulSoup(response.text, 'html.parser')
            articulos = soup.find_all('article')
            if not articulos:
                break
                
            for art in articulos:
                # Filtro de Autor Exacto
                autor_tag = art.find('a', string=lambda t: t and "Claudia Zapater" in t)
                if not autor_tag:
                    continue 

                tag_titulo = art.find(['h2', 'h3'])
                tag_enlace = art.find('a', href=True)
                titular = tag_titulo.get_text(strip=True) if tag_titulo else ""
                tag_time = art.find('time')
                fecha_str = extraer_fecha_exacta(tag_time) if tag_time else "2000-01-01"
                
                url_rel = tag_enlace['href'] if tag_enlace else ""
                url_completa = url_rel if url_rel.startswith('http') else f"https://www.larazon.es{url_rel}"

                if titular and fecha_str >= "2025-01-01":
                    noticias.append({"Título": titular, "Fecha": fecha_str, "URL": url_completa})
                elif fecha_str < "2025-01-01" and fecha_str != "2000-01-01":
                    status_placeholder.success("✅ Extracción finalizada.")
                    return pd.DataFrame(noticias)
            
            pagina += 1
            time.sleep(0.4)
        except:
            break
    return pd.DataFrame(noticias)

# --- INTERFAZ ---
st.title("💶 Monitor de Producción y Facturación")
st.sidebar.header("Configuración")
vista_grafico = st.sidebar.radio("Ver gráfico por:", ["Nº de Noticias", "Euros (€)"])

if st.button("🚀 Actualizar Datos"):
    df = iniciar_scraping("https://www.larazon.es/autores/claudia-zapater")
    
    if not df.empty:
        df['Fecha_dt'] = pd.to_datetime(df['Fecha'])
        df = df.sort_values('Fecha_dt')
        df['Mes-Año'] = df['Fecha_dt'].dt.strftime('%b-%Y').str.upper()
        
        # Agrupación y Cálculo
        conteo_mensual = df.groupby(['Mes-Año'], sort=False).size().reset_index(name='Cantidad')
        conteo_mensual['Euros'] = conteo_mensual['Cantidad'] * 80
        
        # Lógica de escala dinámica
        if vista_grafico == "Nº de Noticias":
            y_col = 'Cantidad'
            titulo_y = "Cantidad de artículos"
            formato_tooltip = 'd'
            limite_y = int(conteo_mensual['Cantidad'].max()) + 5
        else:
            y_col = 'Euros'
            titulo_y = "Importe total (€)"
            formato_tooltip = '.2f'
            limite_y = int(conteo_mensual['Euros'].max()) + (5 * 80)

        # Gráfico Altair
        chart = alt.Chart(conteo_mensual).mark_bar(color='#E63946', cornerRadiusTop=5).encode(
            x=alt.X('Mes-Año:N', title='Mes', sort=None),
            y=alt.Y(f'{y_col}:Q', title=titulo_y, scale=alt.Scale(domain=[0, limite_y])),
            tooltip=[alt.Tooltip('Mes-Año'), alt.Tooltip(f'{y_col}', format=formato_tooltip)]
        ).properties(height=450)
        
        st.altair_chart(chart, use_container_width=True)

        # Métricas
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Artículos", len(df))
        m2.metric("Precio unitario", "80 €")
        m3.metric("Total Facturado", f"{len(df)*80} €")

        # Tabla
        st.write("### 📋 Histórico de Artículos")
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
        st.warning("No hay datos para mostrar.")
