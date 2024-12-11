"""Módulo para processamento de dados WSPR."""

import pandas as pd
import numpy as np
from typing import Dict, Any
from config import BAND_MAPPING, POWER_MAPPING, MODE_MAPPING
from utils import obter_pais_continente_por_prefixo, calcular_azimute

def load_and_process_data(file_path: str) -> pd.DataFrame:
    """
    Carrega e processa os dados WSPR do arquivo JSON.
    
    Args:
        file_path: Caminho para o arquivo JSON
        
    Returns:
        pd.DataFrame: DataFrame processado
    """
    try:
        # Definir as colunas
        columns = [
            "id", "time", "band", "rx_sign", "rx_lat", "rx_lon", "rx_loc",
            "tx_sign", "tx_lat", "tx_lon", "tx_loc", "distance", "azimuth",
            "rx_azimuth", "frequency", "power", "snr", "drift", "version", "code"
        ]
        
        # Carregar dados especificando as colunas
        df = pd.read_json(file_path, orient='values')
        df.columns = columns
        
        # Processar timestamp
        df['time'] = pd.to_datetime(df['time'])
        df['hour'] = df['time'].dt.hour
        df['hora_cheia'] = df['time'].dt.strftime('%H:00')
        
        # Mapear bandas, potência e modos
        df['band'] = df['band'].map(BAND_MAPPING)
        df['power_w'] = df['power'].map(POWER_MAPPING)
        df['mode'] = df['code'].map(MODE_MAPPING)
        
        # Calcular azimutes de forma vetorizada
        valid_coords = pd.notnull(df[['rx_lat', 'rx_lon', 'tx_lat', 'tx_lon']]).all(axis=1)
        df['azimuth_rx_to_tx'] = np.nan
        if valid_coords.any():
            coords = df[valid_coords][['rx_lat', 'rx_lon', 'tx_lat', 'tx_lon']].values
            df.loc[valid_coords, 'azimuth_rx_to_tx'] = [
                calcular_azimute(lat1, lon1, lat2, lon2)
                for lat1, lon1, lat2, lon2 in coords
            ]
        
        # Obter país e continente
        df[['tx_country', 'tx_continent']] = df['tx_sign'].apply(
            lambda x: pd.Series(obter_pais_continente_por_prefixo(x))
        )
        
        return df
    
    except Exception as e:
        print(f"Erro ao processar dados: {str(e)}")
        raise
