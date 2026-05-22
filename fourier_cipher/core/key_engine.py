# =============================================================================
# KEY ENGINE — Matriz de Frequência da Senha (FFT)
# =============================================================================

import random
from core.fft_engine import fft, fft2d

def get_key_matrix_1d(password: str, size: int) -> list:
    """
    Gera a matriz da senha 1D no domínio da frequência (harmônicos).
    Usa a senha como semente para gerar um sinal no domínio do tempo e
    então calcula sua FFT. Isso garante Simetria Hermitiana exata.
    """
    if not password:
        random.seed(None)
    else:
        random.seed(password)
        
    # Gera sinal aleatório no domínio do tempo (simulando amplitudes PCM 16-bit)
    # Lista de complexos [re, im] onde im = 0.0
    time_domain = [[float(random.randint(-32768, 32767)), 0.0] for _ in range(size)]
    
    # Retorna o espectro (harmônicos) da senha
    return fft(time_domain)


def get_key_matrix_2d(password: str, rows: int, cols: int) -> list:
    """
    Gera a matriz da senha 2D no domínio da frequência (harmônicos).
    Usa a senha como semente para gerar uma imagem aleatória e calcula sua FFT2D.
    """
    if not password:
        random.seed(None)
    else:
        random.seed(password)
        
    # Gera matriz de pixels aleatórios (simulando 8-bit [0, 255])
    time_domain = []
    for _ in range(rows):
        row = [[float(random.randint(0, 255)), 0.0] for _ in range(cols)]
        time_domain.append(row)
        
    # Retorna o espectro 2D da senha (skip_pad=True assume que a entrada já tem dimensões potência de 2)
    return fft2d(time_domain, skip_pad=True)