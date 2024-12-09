import numpy as np
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

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

# Criar a coluna 'azimuth_rx_to_tx' com o azimute calculado
df['azimuth_rx_to_tx'] = df.apply(
    lambda row: calcular_azimute(
        row['rx_lat'], row['rx_lon'], row['tx_lat'], row['tx_lon']
    ) if pd.notnull(row['rx_lat']) and pd.notnull(row['rx_lon']) and
         pd.notnull(row['tx_lat']) and pd.notnull(row['tx_lon']) else np.nan,
    axis=1
)

# Sidebar para filtros
st.sidebar.header("Filtros")
selected_band = st.sidebar.multiselect("Selecione Bandas", options=df['band'].unique())
if selected_band:
    df = df[df['band'].isin(selected_band)]

start_date = st.sidebar.date_input("Data inicial", df['time'].min().date())
end_date = st.sidebar.date_input("Data final", df['time'].max().date())
hour_start = st.sidebar.slider("Hora Inicial", 0, 23, 0)
hour_end = st.sidebar.slider("Hora Final", 0, 23, 23)
df = df[(df['hour'] >= hour_start) & (df['hour'] <= hour_end)]
if start_date and end_date:
    df = df[(df['time'].dt.date >= start_date) & (df['time'].dt.date <= end_date)]

# Agrupar por hora cheia e banda
df_grouped = df.groupby(['hora_cheia', 'band']).agg(
    num_spots=('id', 'count'),
    avg_snr=('snr', 'mean')
).reset_index()
df_grouped['hora_cheia'] = pd.Categorical(df_grouped['hora_cheia'],
                                          categories=[f"{str(h).zfill(2)}:00" for h in range(24)],
                                          ordered=True)
df_grouped = df_grouped.sort_values(by='hora_cheia')

# Função para colorir a tabela
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

# Tabela de Melhor Intervalo
st.subheader("Tabela de Melhor Intervalo de Hora por Banda")
best_intervals = df_grouped[df_grouped['num_spots'] > 5].sort_values(by='hora_cheia', ascending=True)
st.dataframe(best_intervals.style.apply(colorize_table, axis=1), use_container_width=True)
st.caption("Essa tabela mostra os melhores horários para comunicação com base no número de spots e na qualidade do sinal (SNR). Quanto mais verde, melhor o horário.")




# Gráfico de Barras: Quantidade de Spots
st.subheader("Quantidade de Spots por Hora Cheia e Banda")
spot_fig = px.bar(df_grouped, x='hora_cheia', y='num_spots', color='band', title="Quantidade de Spots por Hora Cheia e Banda")
st.plotly_chart(spot_fig)
st.caption("Este gráfico mostra o número de spots (sinais recebidos) ao longo do dia em diferentes bandas. Mais spots indicam maior atividade de comunicação.")

# Gráfico de Barras: Média de SNR
st.subheader("Média de SNR por Hora Cheia e Banda")
snr_fig = px.bar(df_grouped, x='hora_cheia', y='avg_snr', color='band', title="Média de SNR por Hora Cheia e Banda")
st.plotly_chart(snr_fig)
st.caption("Este gráfico mostra a média do nível de sinal (SNR) para cada hora do dia em cada banda. Valores maiores indicam melhor qualidade do sinal.")

# Gráfico Polar: Direção e SNR
st.subheader("Gráfico Polar de Direção (RX → TX) e SNR")
polar_fig = go.Figure()
polar_fig.add_trace(go.Scatterpolar(
    r=df['snr'], theta=df['azimuth_rx_to_tx'], mode='markers',
    marker=dict(size=8, color='blue', opacity=0.6),
    text=df.apply(lambda row: f"TX: {row['tx_sign']} | RX: {row['rx_sign']}<br>Azimuth: {row['azimuth_rx_to_tx']}<br>SNR: {row['snr']}<br>Power: {row['power_w']} W", axis=1),
    hoverinfo='text'
))
polar_fig.update_layout(
    polar=dict(angularaxis=dict(direction="clockwise", tickmode="linear", tick0=0, dtick=30),
               radialaxis=dict(visible=True, range=[df['snr'].min(), df['snr'].max()])),
    title="Gráfico Polar de Direção (RX → TX)"
)
st.plotly_chart(polar_fig)
st.caption("Este gráfico polar mostra a direção de propagação (azimute) dos sinais. Cada ponto representa um sinal recebido, e o tamanho do valor radial indica a qualidade do sinal (SNR).")

# Gráfico de Dispersão
st.subheader("SNR ao longo do Tempo")
scatter_fig = px.scatter(df, x='time', y='snr', color='band', title="SNR ao longo do Tempo")
st.plotly_chart(scatter_fig)
st.caption("Este gráfico mostra como a qualidade do sinal (SNR) varia ao longo do tempo. Padrões temporais podem indicar horários com melhor propagação.")

# Tabela Detalhada
st.subheader("Tabela de Dados Detalhados")
st.dataframe(df[['time', 'rx_sign', 'tx_sign', 'band', 'snr', 'distance', 'mode', 'power_w', 'azimuth_rx_to_tx']])
st.caption("Esta tabela exibe informações detalhadas de cada sinal recebido, incluindo horário, banda, nível de sinal (SNR), e direção de propagação (azimute).")
