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
        # Preparación de datos base
        df['Fecha_dt'] = pd.to_datetime(df['Fecha'])
        df['Mes-Filtro'] = df['Fecha_dt'].dt.strftime('%m-%Y')
        df['Mes-Grafico'] = df['Fecha_dt'].dt.strftime('%b-%Y').str.upper()
        
        # --- NUEVO FILTRO EN SIDEBAR ---
        meses_disponibles = sorted(df['Mes-Filtro'].unique(), reverse=True)
        seleccion_meses = st.sidebar.multiselect(
            "Filtrar por Mes (MM-AAAA):",
            options=meses_disponibles,
            default=meses_disponibles
        )
        
        # Filtrar el DataFrame según la selección
        df_filtrado = df[df['Mes-Filtro'].isin(seleccion_meses)].copy()

        if not df_filtrado.empty:
            # Agrupación para gráfico
            conteo_mensual = df_filtrado.groupby(['Mes-Grafico'], sort=False).size().reset_index(name='Cantidad')
            conteo_mensual['Euros'] = (conteo_mensual['Cantidad'] * 80).astype(float)
            
            # Gráfico
            y_col = 'Cantidad' if vista_grafico == "Nº de Noticias" else 'Euros'
            titulo_y = "Artículos" if vista_grafico == "Nº de Noticias" else "Euros (€)"
            
            st.write(f"### 📈 {titulo_y} (Filtrado)")
            chart = alt.Chart(conteo_mensual).mark_bar(color='#E63946').encode(
                x=alt.X('Mes-Grafico:N', title='Mes', sort=None),
                y=alt.Y(f'{y_col}:Q', title=titulo_y),
                tooltip=['Mes-Grafico', y_col]
            ).properties(height=350)
            st.altair_chart(chart, use_container_width=True)

            # Métricas calculadas sobre el filtro
            m1, m2, m3 = st.columns(3)
            total_noticias = len(df_filtrado)
            m1.metric("Artículos Seleccionados", total_noticias)
            m2.metric("Precio unitario", "80 €")
            m3.metric("Total Facturado", f"{total_noticias * 80} €")

            # Tabla Histórica
            st.write("### 📋 Detalle de Artículos")
            df_display = df_filtrado.sort_values('Fecha_dt', ascending=False).copy()
            df_display['Fecha_Pub'] = df_display['Fecha_dt'].dt.strftime('%d-%m-%Y')
            df_display.insert(0, '№', range(1, len(df_display) + 1))
            
            st.dataframe(
                df_display[['№', 'Título', 'Fecha_Pub', 'Mes-Filtro', 'URL']],
                use_container_width=True,
                column_config={
                    "URL": st.column_config.LinkColumn("Enlace"),
                    "Mes-Filtro": "Mes (MM-AAAA)",
                    "Fecha_Pub": "Fecha"
                },
                hide_index=True
            )
        else:
            st.warning("No hay datos para los meses seleccionados.")
    else:
        st.warning("No se encontraron datos.")

st.markdown("---")
st.caption("Filtro de meses añadido. Formato de columna: MM-AAAA.")
