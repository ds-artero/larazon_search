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
                fecha_str = extraer_fecha_exacta(tag_time)
                
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
        # Limpieza y formateo de datos
        df['Fecha_dt'] = pd.to_datetime(df['Fecha'])
        df = df.sort_values('Fecha_dt')
        
        # Columna para el gráfico (Texto: ENE-2025)
        df['Mes-Año-Grafico'] = df['Fecha_dt'].dt.strftime('%b-%Y').str.upper()
        
        # Agrupación y Cálculo
        conteo_mensual = df.groupby(['Mes-Año-Grafico'], sort=False).size().reset_index(name='Cantidad')
        conteo_mensual['Cantidad'] = conteo_mensual['Cantidad'].astype(int)
        conteo_mensual['Euros'] = (conteo_mensual['Cantidad'] * 80).astype(float)
        
        # Definición de variables para el gráfico
        if vista_grafico == "Nº de Noticias":
            y_col = 'Cantidad'
            titulo_y = "Cantidad de artículos"
            limite_y = float(conteo_mensual['Cantidad'].max() + 5)
        else:
            y_col = 'Euros'
            titulo_y = "Importe total (€)"
            limite_y = float(conteo_mensual['Euros'].max() + 400)

        # Gráfico Altair
        st.write(f"### 📈 {titulo_y} por Mes")
        chart = alt.Chart(conteo_mensual).mark_bar(color='#E63946').encode(
            x=alt.X('Mes-Año-Grafico:N', title='Mes', sort=None),
            y=alt.Y(f'{y_col}:Q', title=titulo_y, scale=alt.Scale(domain=[0, limite_y])),
            tooltip=['Mes-Año-Grafico', y_col]
        ).properties(height=400)
        
        st.altair_chart(chart, use_container_width=True)

        # Métricas
        m1, m2, m3 = st.columns(3)
        total_noticias = len(df)
        m1.metric("Total Artículos", total_noticias)
        m2.metric("Precio unitario", "80 €")
        m3.metric("Total Facturado", f"{total_noticias * 80} €")

        # --- SECCIÓN DE TABLA ACTUALIZADA ---
        st.write("### 📋 Histórico de Artículos")
        df_display = df.sort_values('Fecha_dt', ascending=False).copy()
        
        # Formateamos las columnas de fecha
        df_display['Fecha_Original'] = df_display['Fecha_dt'].dt.strftime('%d-%m-%Y')
        df_display['Mes'] = df_display['Fecha_dt'].dt.strftime('%m-%A').str.replace(r'^[A-Za-z]+', lambda x: x.group(0), regex=True) # Fallback simple
        # Corrección directa para el formato MM-AAAA
        df_display['Mes'] = df_display['Fecha_dt'].dt.strftime('%m-%Y') 
        
        # Insertar contador
        df_display.insert(0, '№', range(1, len(df_display) + 1))
        
        # Mostrar tabla con la nueva columna 'Mes'
        st.dataframe(
            df_display[['№', 'Título', 'Fecha_Original', 'Mes', 'URL']],
            use_container_width=True,
            column_config={
                "URL": st.column_config.LinkColumn("Enlace"),
                "Fecha_Original": "Fecha Pub.",
                "Mes": "Mes (MM-AAAA)"
            },
            hide_index=True
        )
    else:
        st.warning("No hay datos para mostrar de 2025.")

# Pie de página
st.markdown("---")
st.caption("Desarrollado para el seguimiento de facturación de Claudia Zapater.")
