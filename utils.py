"""Funções utilitárias para processamento de dados WSPR."""

import numpy as np
from typing import Tuple, Optional
from config import PREFIX_MAPPING

def calcular_azimute(lat1: float, lon1: float, lat2: float, lon2: float) -> Optional[float]:
    """
    Calcula o azimute entre dois pontos usando suas coordenadas.
    
    Args:
        lat1: Latitude do ponto 1 em graus
        lon1: Longitude do ponto 1 em graus
        lat2: Latitude do ponto 2 em graus
        lon2: Longitude do ponto 2 em graus
    
    Returns:
        float: Azimute em graus ou None se houver erro
    """
    try:
        lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
        delta_lon = lon2 - lon1
        x = np.sin(delta_lon) * np.cos(lat2)
        y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(delta_lon)
        azimute = np.arctan2(x, y)
        return np.degrees(azimute) % 360
    except Exception as e:
        print(f"Erro ao calcular azimute: {str(e)}")
        return None

def obter_pais_continente_por_prefixo(indicativo: str) -> Tuple[str, str]:
    """
    Obtém o país e continente baseado no prefixo do indicativo.
    
    Args:
        indicativo: Indicativo de rádio amador
    
    Returns:
        Tuple[str, str]: (país, continente)
    """
    try:
        prefixo = indicativo[:2]  # Pegando os dois primeiros caracteres como prefixo
        return PREFIX_MAPPING.get(prefixo, ('Desconhecido', 'Desconhecido'))
    except Exception as e:
        print(f"Erro ao obter país e continente: {str(e)}")
        return ('Desconhecido', 'Desconhecido')
