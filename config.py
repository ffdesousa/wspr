"""Arquivo de configuração contendo mapeamentos e constantes."""

# Mapeamento de prefixos para país e continente
PREFIX_MAPPING = {
    "PY": ("Brasil", "América do Sul"),
    "K": ("Estados Unidos", "América do Norte"),
    # ... (todo o mapeamento existente)
}

# Mapeamento de bandas
BAND_MAPPING = {
    -1: "LF", 0: "MF", 1: "160m", 3: "80m", 5: "60m", 7: "40m", 10: "30m",
    14: "20m", 18: "17m", 21: "15m", 24: "12m", 28: "10m", 50: "6m", 70: "4m",
    144: "2m", 432: "70cm", 1296: "23cm"
}

# Mapeamento de potência
POWER_MAPPING = {
    0: 0.001, 3: 0.002, 7: 0.005, 10: 0.01, 13: 0.02, 17: 0.05, 20: 0.1,
    23: 0.2, 27: 0.5, 30: 1, 33: 2, 37: 5, 40: 10, 43: 20, 47: 50,
    50: 100, 53: 200, 57: 500, 60: 1000
}

# Mapeamento de modos
MODE_MAPPING = {
    1: "WSPR2/FST4W-120", 2: "FST4W-900", 4: "FST4W-300", 8: "FST4W-1800"
}
