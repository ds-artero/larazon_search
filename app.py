import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import altair as alt

# ... (Las funciones extraer_fecha_exacta e iniciar_scraping se mantienen igual) ...

if st.button("🚀 Ejecutar Análisis"):
    df = iniciar_scraping("https://www.larazon.es/autores/claudia-zapater")
    
    if not df.empty:
        df['Fecha'] = pd.to_datetime(df['Fecha'])
        
        # Formatear el mes como 'DEC-2025'
        # Usamos dt.strftime('%b-%Y').str.upper() para el formato pedido
        df['Mes-Año'] = df['Fecha'].dt.strftime('%b-%Y').str.upper()
        
        # Agrupar y contar
        conteo_mensual = df.groupby(['Mes-Año'], sort=False).size().reset_index(name='Cantidad')
        
        # Calcular límites del eje Y
        max_articulos = conteo_mensual['Cantidad'].max()
        limite_superior = max_articulos + 5

        # --- GRÁFICO PERSONALIZADO CON ALTAIR ---
        st.write("### 📈 Frecuencia de publicación por mes")
        
        chart = alt.Chart(conteo_mensual).mark_bar(color='#ff4b4b').encode(
            x=alt.X('Mes-Año:N', title='Mes', sort=None), # sort=None para mantener orden cronológico si viene ordenado
            y=alt.Y('Cantidad:Q', 
                     title='Número de Artículos',
                     scale=alt.Scale(domain=[0, limite_superior])), # Escala 0 a Máx+5
            tooltip=['Mes-Año', 'Cantidad']
        ).properties(
            width=700,
            height=400
        )

        st.altair_chart(chart, use_container_width=True)

        # --- TABLA Y DESCARGA (Igual que antes) ---
        st.write("### 📋 Listado de Noticias")
        df_display = df.copy()
        df_display['Fecha'] = df_display['Fecha'].dt.strftime('%d-%m-%Y')
        df_display.insert(0, '№', range(1, len(df_display) + 1))
        
        st.dataframe(
            df_display[['№', 'Título', 'Fecha', 'URL']],
            use_container_width=True,
            column_config={"URL": st.column_config.LinkColumn("Enlace")},
            hide_index=True
        )
