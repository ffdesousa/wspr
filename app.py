import numpy as np
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import os
from dotenv import load_dotenv
import requests
import xml.etree.ElementTree as ET
import sqlite3
import pycountry
import datetime

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()
QRZ_USERNAME = os.getenv('QRZ_USERNAME')
QRZ_PASSWORD = os.getenv('QRZ_PASSWORD')

# Carregar o arquivo JSON
with open("spots.json", "r") as file:
    data = json.load(file)

# Nomes das colunas
columns = [
    "id", "time", "band", "rx_sign", "rx_lat", "rx_lon", "rx_loc",
    "tx_sign", "tx_lat", "tx_lon", "tx_loc", "distance", "azimuth",
    "rx_azimuth", "frequency", "power", "snr", "drift", "version", "code"
]

# Converter para DataFrame
df = pd.DataFrame(data, columns=columns)

# Ajustar tipos e interpretar campos
df['time'] = pd.to_datetime(df['time'])
df['hour'] = df['time'].dt.hour
df['hora_cheia'] = df['time'].dt.strftime('%H:00')  # Formato HH:00

# Mapear bandas
band_mapping = {
    -1: "LF", 0: "MF", 1: "160m", 3: "80m", 5: "60m", 7: "40m", 10: "30m",
    14: "20m", 18: "17m", 21: "15m", 24: "12m", 28: "10m", 50: "6m", 70: "4m",
    144: "2m", 432: "70cm", 1296: "23cm"
}
df['band'] = df['band'].map(band_mapping)

# Mapear potência
power_mapping = {
    0: 0.001, 3: 0.002, 7: 0.005, 10: 0.01, 13: 0.02, 17: 0.05, 20: 0.1,
    23: 0.2, 27: 0.5, 30: 1, 33: 2, 37: 5, 40: 10, 43: 20, 47: 50,
    50: 100, 53: 200, 57: 500, 60: 1000
}
df['power_w'] = df['power'].map(power_mapping)

# Mapear modos
mode_mapping = {
    1: "WSPR2/FST4W-120", 2: "FST4W-900", 4: "FST4W-300", 8: "FST4W-1800"
}
df['mode'] = df['code'].map(mode_mapping)

# Configurar o banco de dados SQLite
DB_PATH = 'd:/Documents/projetos/wspr/indicativos.db'

# Função para inicializar o banco de dados
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS indicativos (
        callsign TEXT PRIMARY KEY,
        country TEXT,
        continent TEXT
    )''')
    conn.commit()
    conn.close()

# Função para persistir indicativos únicos no banco de dados
def persistir_indicativos(indicativos_df):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for index, row in indicativos_df.iterrows():
        cursor.execute('''INSERT OR IGNORE INTO indicativos (callsign) VALUES (?)''', (row['tx_sign'],))
    conn.commit()
    conn.close()

# Função para recuperar indicativos que não têm país
def recuperar_indicativos_sem_info():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''SELECT callsign FROM indicativos WHERE country IS NULL''')
    indicativos = cursor.fetchall()
    conn.close()
    return [i[0] for i in indicativos]

# Inicializar o banco de dados
init_db()

# Criar um DataFrame separado com indicativos únicos
indicativos_unicos = df['tx_sign'].unique()
indicativos_df = pd.DataFrame(indicativos_unicos, columns=['tx_sign'])

# Persistir os indicativos únicos no banco de dados
persistir_indicativos(indicativos_df)

# Recuperar indicativos que não têm país
indicativos_sem_info = recuperar_indicativos_sem_info()

# Dicionário para armazenar os resultados das consultas
cache_indicativos = {}

# Variável global para armazenar a sessão
QRZ_SESSION_KEY = None

def get_qrz_session():
    global QRZ_SESSION_KEY
    if QRZ_SESSION_KEY:
        return QRZ_SESSION_KEY
        
    url = f"https://xmldata.qrz.com/xml/current/?username={QRZ_USERNAME}&password={QRZ_PASSWORD}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            namespace = {'qrz': 'http://xmldata.qrz.com'}
            session = root.find('.//qrz:Key', namespaces=namespace)
            if session is not None:
                QRZ_SESSION_KEY = session.text
                return QRZ_SESSION_KEY
    except Exception as e:
        st.error(f"Erro ao obter sessão QRZ: {str(e)}")
    return None

def consultar_indicativos():
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT callsign AS tx_sign, country, continent FROM indicativos"  # Ajustando o nome da coluna
    df_indicativos = pd.read_sql_query(query, conn)
    conn.close()
    return df_indicativos

# Função para consultar a API do QRZ.com com cache
def obter_informacoes_indicativo(indicativo):
    if indicativo in cache_indicativos:
        info = cache_indicativos[indicativo]
        if 'country' in info:
            return info['country']  # Retorna se já tiver o país

    # Se não existir ou não tiver país, consulta a API
    session_key = get_qrz_session()
    if not session_key:
        return 'Desconhecido'
        
    url = f"https://xmldata.qrz.com/xml/current/?s={session_key};callsign={indicativo}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            # Verificar se há erro na resposta
            error = root.find('.//Error')
            if error is not None:
                st.warning(f"Erro na consulta do indicativo {indicativo}: {error.text}")
                return 'Desconhecido'
                
            # Extraindo informações relevantes com verificações
            namespace = {'qrz': 'http://xmldata.qrz.com'}
            callsign = root.find('.//qrz:call', namespaces=namespace).text if root.find('.//qrz:call', namespaces=namespace) is not None else 'Desconhecido'
            country = root.find('.//qrz:country', namespaces=namespace).text if root.find('.//qrz:country', namespaces=namespace) is not None else 'Desconhecido'
            
            # Armazenando as informações no cache e no banco de dados
            cache_indicativos[indicativo] = {
                'callsign': callsign,
                'country': country,
            }
            atualizar_indicativos_no_banco(indicativo, country)  # Atualiza ou insere no banco de dados
            return country
    except Exception as e:
        st.error(f"Erro ao consultar indicativo {indicativo}: {str(e)}")
    return 'Desconhecido'

# Dicionário de continentes
continente_map = {
    'Africa': ['DZ', 'AO', 'BJ', 'BW', 'BF', 'BI', 'CM', 'CV', 'CF', 'TD', 'KM', 'DJ', 'EG', 'GQ', 'ER', 'SZ', 'ET', 'GA', 'GM', 'GH', 'GN', 'GW', 'KE', 'LS', 'LR', 'LY', 'MG', 'MW', 'ML', 'MR', 'MU', 'MA', 'MZ', 'NA', 'NE', 'NG', 'RW', 'ST', 'SN', 'SC', 'SL', 'SO', 'ZA', 'SS', 'SD', 'TZ', 'TG', 'TN', 'UG', 'EH', 'ZM', 'ZW'],
    'Asia': ['AF', 'AM', 'AZ', 'BH', 'BD', 'BT', 'BN', 'KH', 'CN', 'CY', 'GE', 'IN', 'ID', 'IR', 'IQ', 'IL', 'JP', 'JO', 'KZ', 'KP', 'KR', 'KW', 'KG', 'LA', 'LB', 'MY', 'MV', 'MN', 'MM', 'NP', 'OM', 'PK', 'PH', 'QA', 'SA', 'SG', 'LK', 'SY', 'TJ', 'TH', 'TL', 'TM', 'AE', 'UZ', 'VN', 'YE'],
    'Europe': ['AL', 'AD', 'AT', 'BY', 'BE', 'BA', 'BG', 'HR', 'CY', 'CZ', 'DK', 'EE', 'FI', 'FR', 'DE', 'GR', 'HU', 'IS', 'IE', 'IT', 'LV', 'LT', 'LU', 'MT', 'MD', 'MC', 'ME', 'NL', 'NO', 'PL', 'PT', 'RO', 'RU', 'SK', 'SI', 'ES', 'SE', 'CH', 'UA', 'GB', 'VA'],
    'North America': ['CA', 'US', 'MX', 'GT', 'BZ', 'HT', 'CU', 'JM', 'DO', 'SV', 'HN', 'NI', 'CR', 'PA'],
    'Oceania': ['AU', 'NZ', 'FJ', 'PG', 'WS', 'SB', 'VU', 'TO', 'CK', 'NU'],
    'South America': ['AR', 'BO', 'BR', 'CL', 'CO', 'EC', 'GY', 'PY', 'PE', 'SR', 'UY', 'VE'],
}

# Função para obter o continente a partir do país
def obter_continente(pais):
    # Tratamento especial para "Azores"
    if pais.lower() == "azores":
        return "Europe"
    
    # Tratamentos especiais para regiões e territórios
    region_map = {
        "cayman islands": "North America",
        "england": "Europe",
        "scotland": "Europe",
        "wales": "Europe",
        "jersey": "Europe",
        "canary islands": "Europe",  # Adicionando tratamento para as Ilhas Canárias
    }

    # Verifica se o país está no mapeamento de regiões
    if pais.lower() in region_map:
        return region_map[pais.lower()]
    
    try:
        country_alpha2 = pycountry.countries.lookup(pais).alpha_2
        for continente, paises in continente_map.items():
            if country_alpha2 in paises:
                return continente
        return "Desconhecido"
    except Exception as e:
        st.warning(f"Erro ao obter continente para {pais}: {str(e)}")
        return "Desconhecido"

def atualizar_indicativos_no_banco(indicativo, country):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''UPDATE indicativos SET country = ?, continent = ? WHERE callsign = ?''', 
                   (country, obter_continente(country), indicativo))
    conn.commit()
    conn.close()

# Consultar a API apenas para os indicativos que não têm país
with st.spinner('Carregando dados...'):  # Mensagem de carregamento
    for indicativo in indicativos_sem_info:
        # Verificando o retorno da função antes de atualizar o DataFrame
        country = obter_informacoes_indicativo(indicativo)  # Chamada para obter informações
        
indicativos_info = consultar_indicativos()

# Relacionar esse DataFrame com o DataFrame original
# (Supondo que o DataFrame original tenha uma coluna 'tx_sign')
df = df.merge(indicativos_info, on='tx_sign', how='left')

# Filtrar os dados para remover entradas com continente desconhecido
filtered_df = df[df['continent'] != 'Desconhecido']

# Obter horário atual em UTC
utc_now = datetime.datetime.utcnow().strftime('%H:%M:%S')
# Obter horário de Mato Grosso do Sul (UTC-3)
ms_time = (datetime.datetime.utcnow() - datetime.timedelta(hours=3)).strftime('%H:%M:%S')

# Criar colunas para exibir os horários
col1, col2 = st.columns(2)
with col1:
    st.metric(label="Horário Atual (UTC)", value=utc_now)
with col2:
    st.metric(label="Horário de Mato Grosso do Sul", value=ms_time)

# Sidebar para filtros
st.sidebar.header("Filtros")

# Filtro de banda com 10m selecionado por padrão
selected_band = st.sidebar.multiselect("Selecione Bandas", options=filtered_df['band'].unique(), default=['10m'])

# Filtro de data para a última semana
end_date = filtered_df['time'].max().date()
start_date = end_date - pd.Timedelta(days=7)
start_date = st.sidebar.date_input("Data inicial", start_date)
end_date = st.sidebar.date_input("Data final", end_date)

hour_start = st.sidebar.slider("Hora Inicial", 0, 23, 0)
hour_end = st.sidebar.slider("Hora Final", 0, 23, 23)

# Aplicar filtros ao DataFrame
if selected_band:
    filtered_df = filtered_df[filtered_df['band'].isin(selected_band)]
if start_date and end_date:
    filtered_df = filtered_df[(filtered_df['time'].dt.date >= start_date) & (filtered_df['time'].dt.date <= end_date)]
filtered_df = filtered_df[(filtered_df['hour'] >= hour_start) & (filtered_df['hour'] <= hour_end)]

# Agrupar por hora cheia e banda
filtered_df_grouped = filtered_df.groupby(['hora_cheia', 'band']).agg(
    num_spots=('id', 'count'),
    avg_snr=('snr', 'mean')
).reset_index()

# Agrupar por hora cheia e continente
hora_continente_grouped = filtered_df.groupby(['hora_cheia', 'continent']).agg(
    num_spots=('id', 'count'),
    avg_snr=('snr', 'mean')
).reset_index()

# Ordenar a coluna 'hora_cheia' como categoria
hora_continente_grouped['hora_cheia'] = pd.Categorical(hora_continente_grouped['hora_cheia'],
    categories=[f"{str(h).zfill(2)}:00" for h in range(24)],
    ordered=False
)

# Ordenar a coluna 'hora_cheia' como categoria
filtered_df_grouped['hora_cheia'] = pd.Categorical(filtered_df_grouped['hora_cheia'],
                                          categories=[f"{str(h).zfill(2)}:00" for h in range(24)],
                                          ordered=True)


# Função para calcular o azimute entre RX e TX
def calcular_azimute(lat1, lon1, lat2, lon2):
    try:
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        delta_lon = lon2 - lon1
        x = np.sin(delta_lon) * np.cos(lat2)
        y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(delta_lon)
        azimute = np.arctan2(x, y)
        return np.degrees(azimute) % 360
    except Exception as e:
        return np.nan


def colorize_table(row):
    num_spots = row['num_spots']
    avg_snr = row['avg_snr']
    color_value = (0.5 * num_spots) + (0.5 * avg_snr)
    if color_value > 50:
        return ['background-color: green; color: white'] * len(row)
    elif color_value > 20:
        return ['background-color: yellow; color: black'] * len(row)
    else:
        return ['background-color: red; color: white'] * len(row)


# Criar a coluna 'azimuth_rx_to_tx' com o azimute calculado
filtered_df['azimuth_rx_to_tx'] = filtered_df.apply(
    lambda row: calcular_azimute(
        row['rx_lat'], row['rx_lon'], row['tx_lat'], row['tx_lon']
    ) if pd.notnull(row['rx_lat']) and pd.notnull(row['rx_lon']) and
         pd.notnull(row['tx_lat']) and pd.notnull(row['tx_lon']) else np.nan,
    axis=1
)


# Visualização de quantidade de spots por hora cheia e banda
#st.subheader("Quantidade de Spots por Hora Cheia e Banda")
#spot_fig = px.bar(filtered_df_grouped, x='hora_cheia', y='num_spots', color='band', title="Quantidade de Spots por Hora Cheia e Banda")
#st.plotly_chart(spot_fig)

# Visualização de hora cheia por continente
st.subheader("Distribuição de Spots por Hora Cheia e Continente")



spot_fig_continente = px.bar(hora_continente_grouped, x='hora_cheia', y='num_spots', color='continent', title="Quantidade de Spots por Hora Cheia e Continente")
st.plotly_chart(spot_fig_continente)


# Tabela de Melhor Intervalo
st.subheader("Tabela de Melhor Intervalo de Hora por Banda")
best_intervals = filtered_df_grouped[filtered_df_grouped['num_spots'] > 5].sort_values(by='hora_cheia', ascending=True)
st.dataframe(best_intervals.style.apply(colorize_table, axis=1), use_container_width=True)
st.caption("Essa tabela mostra os melhores horários para comunicação com base no número de spots e na qualidade do sinal (SNR). Quanto mais verde, melhor o horário.")



# Gráfico de Barras: Média de SNR
st.subheader("Média de SNR por Hora Cheia e Banda")
snr_fig = px.bar(filtered_df_grouped, x='hora_cheia', y='avg_snr', color='band', title="Média de SNR por Hora Cheia e Banda")
st.plotly_chart(snr_fig)
st.caption("Este gráfico mostra a média do nível de sinal (SNR) para cada hora do dia em cada banda. Valores maiores indicam melhor qualidade do sinal.")

# Gráfico Polar: Direção e SNR
st.subheader("Gráfico Polar de Direção (RX → TX) e SNR")
polar_fig = go.Figure()
polar_fig.add_trace(go.Scatterpolar(
    r=filtered_df['snr'], theta=filtered_df['azimuth_rx_to_tx'], mode='markers',
    marker=dict(size=8, color='blue', opacity=0.6),
    text=filtered_df.apply(lambda row: f"TX: {row['tx_sign']} | RX: {row['rx_sign']}<br>Azimuth: {row['azimuth_rx_to_tx']}<br>SNR: {row['snr']}<br>Power: {row['power_w']} W", axis=1),
    hoverinfo='text'
))
polar_fig.update_layout(
    polar=dict(angularaxis=dict(direction="clockwise", tickmode="linear", tick0=0, dtick=30),
               radialaxis=dict(visible=True, range=[filtered_df['snr'].min(), filtered_df['snr'].max()])),
    title="Gráfico Polar de Direção (RX → TX)"
)
st.plotly_chart(polar_fig)
st.caption("Este gráfico polar mostra a direção de propagação (azimute) dos sinais. Cada ponto representa um sinal recebido, e o tamanho do valor radial indica a qualidade do sinal (SNR).")

# Gráfico de Dispersão
st.subheader("SNR ao longo do Tempo")

scatter_fig = px.scatter(
    filtered_df,
    x='time',
    y='snr',
    color='continent',
    title="SNR ao longo do Tempo",
    hover_data={
        'country': True,
        'continent': True,
        'snr': True,
        'hora_cheia': True,
        'tx_sign': True,

    }
)
st.plotly_chart(scatter_fig)
st.caption("Este gráfico mostra como a qualidade do sinal (SNR) varia ao longo do tempo. Padrões temporais podem indicar horários com melhor propagação.")

# Tabela Detalhada
st.subheader("Tabela de Dados Detalhados")
st.dataframe(filtered_df[['time', 'rx_sign', 'tx_sign', 'band', 'snr', 'distance', 'mode', 'power_w', 'azimuth_rx_to_tx', 'country', 'continent']])
st.caption("Esta tabela exibe informações detalhadas de cada sinal recebido, incluindo horário, banda, nível de sinal (SNR), e direção de propagação (azimute).")
