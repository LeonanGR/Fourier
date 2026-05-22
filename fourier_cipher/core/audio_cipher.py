# =============================================================================
# AUDIO CIPHER — Soma de Matrizes na FFT
# =============================================================================

from core.fft_engine import fft, ifft, _pad
from core.key_engine import get_key_matrix_1d

def _pcm_to_cx(samples: list) -> list:
    """Amostras inteiras PCM-16 -> complexos normalizados [-1, 1] com Im=0."""
    return [[s / 32768.0, 0.0] for s in samples]

def _cx_to_pcm(signal: list) -> list:
    """Complexos -> inteiros PCM-16 (aplicando aritmética modular 65536)."""
    out = []
    for c in signal:
        v = round(c[0] * 32768.0)
        # Módulo 65536 garante que o sinal não sofra clipping e seja perfeitamente reversível
        v = (v + 32768) % 65536 - 32768
        out.append(v)
    return out

def cipher_audio(samples: list, password: str, decrypt: bool = False) -> list:
    """
    Cifra ou decifra um canal de áudio utilizando a adição de matriz com a senha
    no domínio da frequência (FFT).
    """
    cx = _pad(_pcm_to_cx(samples))  # complexos + zero-pad para potência de 2
    n = len(cx)
    
    # Passo 1: Decomposição do áudio em harmônicas (FFT)
    X = fft(cx)
    
    # Passo 2: Geração da matriz da senha (harmônicas da senha)
    K = get_key_matrix_1d(password, n)
    
    # Passo 3: Soma matricial com a senha no domínio da frequência
    Y = [[0.0, 0.0] for _ in range(n)]
    for i in range(n):
        if decrypt:
            Y[i] = [X[i][0] - K[i][0], X[i][1] - K[i][1]]
        else:
            Y[i] = [X[i][0] + K[i][0], X[i][1] + K[i][1]]
            
    # Passo 4: Conversão novamente para áudio (IFFT)
    restored = ifft(Y)
    
    # Passo 5: Conversão para PCM (retorna o tamanho completo com padding, 
    # o módulo garante reversibilidade)
    return _cx_to_pcm(restored)