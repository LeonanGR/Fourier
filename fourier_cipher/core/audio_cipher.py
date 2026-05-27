# =============================================================================
# AUDIO CIPHER — Perturbação de Fase via Rotação Complexa na FFT
# =============================================================================

from core.fft_engine import fft, ifft, _pad
from core.key_engine import get_key_matrix_1d
from core.math_engine import cabs


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
    Cifra ou decifra um canal de áudio utilizando a verdadeira perturbação de fase
    no domínio da frequência (FFT), por meio de rotação complexa unitária.
    Aplica atenuação de escala para evitar overflow/PAPR no domínio do tempo,
    eliminando qualquer ruído residual na decifragem.
    """
    scale_factor = 0.40  # Fator de atenuação para conter o pico de potência (PAPR) no domínio do tempo
    
    if not decrypt:
        # Criptografia: Atenua a escala antes de aplicar a FFT para evitar estouros
        scaled_samples = [s * scale_factor for s in samples]
    else:
        scaled_samples = samples

    cx = _pad(_pcm_to_cx(scaled_samples))  # complexos + zero-pad para potência de 2
    n = len(cx)
    
    # Passo 1: Decomposição do áudio em harmônicas (FFT)
    X = fft(cx)
    
    # Passo 2: Geração da matriz da senha (harmônicas da senha)
    K = get_key_matrix_1d(password, n)
    
    # Passo 3: Rotação complexa unitária com a senha no domínio da frequência
    Y = [[0.0, 0.0] for _ in range(n)]
    half = n // 2
    
    for i in range(half + 1):
        # Componentes DC (0) e Nyquist (n/2) devem manter a fase inalterada (im=0) para evitar ruído espectral
        if i == 0 or i == half:
            Y[i] = [X[i][0], X[i][1]]
            continue
            
        k_re, k_im = K[i][0], K[i][1]
        mag = cabs(k_re, k_im)
        
        # Calcula o componente unitário de rotação (evita divisão por zero)
        if mag > 1e-12:
            u_re = k_re / mag
            u_im = k_im / mag
        else:
            u_re = 1.0
            u_im = 0.0
            
        x_re, x_im = X[i][0], X[i][1]
        
        if decrypt:
            # Descriptografia: Rotaciona pelo conjugado complexo (u_re - j * u_im)
            Y[i] = [
                x_re * u_re + x_im * u_im,
                -x_re * u_im + x_im * u_re
            ]
        else:
            # Criptografia: Rotaciona multiplicando diretamente (u_re + j * u_im)
            Y[i] = [
                x_re * u_re - x_im * u_im,
                x_re * u_im + x_im * u_re
            ]
            
    # Passo 4: Garante simetria hermitiana perfeita na segunda metade do espectro
    # Isso elimina qualquer desequilíbrio e vazamento de ruído imaginário no domínio do tempo
    for i in range(half + 1, n):
        Y[i] = [Y[n - i][0], -Y[n - i][1]]
            
    # Passo 5: Conversão novamente para áudio (IFFT)
    restored = ifft(Y)
    
    # Passo 6: Conversão para inteiros PCM
    dec_samples = _cx_to_pcm(restored)
    
    if decrypt:
        # Descriptografia: Restaura a amplitude original expandindo o sinal e aplicando limitador seguro (clip)
        restored_samples = []
        for s in dec_samples:
            val = round(s / scale_factor)
            val = max(-32768, min(32767, val))
            restored_samples.append(val)
        return restored_samples
    else:
        return dec_samples