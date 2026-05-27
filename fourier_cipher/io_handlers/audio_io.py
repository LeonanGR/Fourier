# =============================================================================
# AUDIO I/O — Leitura e Escrita de arquivos WAV usando soundfile e numpy
# =============================================================================

import soundfile as sf
import numpy as np


# -----------------------------------------------------------------------------
# LEITURA DE WAV
# -----------------------------------------------------------------------------

def read_wav(filepath: str) -> dict:
    """
    Lê um arquivo WAV e retorna um dicionário compatível com o cifrador:
      - 'sample_rate': int
      - 'num_channels': int
      - 'bit_depth': int
      - 'channels': lista de canais, onde cada canal é uma lista de inteiros PCM.
      - 'num_samples': int
    """
    # Lê os dados do arquivo de áudio diretamente como inteiros de 16 bits
    data, sample_rate = sf.read(filepath, dtype='int16')
    
    # Se for mono, a dimensão é 1D. Se for estéreo/multicanal, a dimensão é 2D.
    if data.ndim == 1:
        channels = [data.tolist()]
        num_channels = 1
    else:
        # Transpõe para separar os canais e converte para listas normais do Python
        channels = data.T.tolist()
        num_channels = data.shape[1]

    # Recupera metadados adicionais do arquivo
    info = sf.info(filepath)
    # Tenta extrair a profundidade de bits do subtipo (ex: 'PCM_16' -> 16)
    if 'PCM_' in info.subtype:
        try:
            bit_depth = int(info.subtype.replace('PCM_', ''))
        except ValueError:
            bit_depth = 16
    else:
        bit_depth = 16

    return {
        'sample_rate' : sample_rate,
        'num_channels': num_channels,
        'bit_depth'   : bit_depth,
        'channels'    : channels,
        'num_samples' : len(channels[0]),
    }


# -----------------------------------------------------------------------------
# ESCRITA DE WAV
# -----------------------------------------------------------------------------

def write_wav(filepath: str, channels: list, sample_rate: int,
              bit_depth: int = 16) -> None:
    """
    Escreve canais de áudio PCM em um arquivo WAV usando soundfile.
    channels: lista de canais, cada canal é uma lista de inteiros PCM.
    """
    # Transpõe os canais para que fiquem no formato intercalado (amostras, canais) esperado pelo soundfile
    data = np.array(channels).T

    # Mapeia profundidade de bits para o formato correto
    subtype = 'PCM_16'
    if bit_depth == 8:
        subtype = 'PCM_U8'
    elif bit_depth == 24:
        subtype = 'PCM_24'
    elif bit_depth == 32:
        subtype = 'PCM_32'

    sf.write(filepath, data, sample_rate, subtype=subtype)