# =============================================================================
# IMAGE CIPHER — Perturbação de Fase via Rotação Complexa na FFT 2D
# =============================================================================

from core.fft_engine import fft2d, ifft2d, _next_pow2
from core.key_engine import get_key_matrix_2d
from core.math_engine import cabs


def _pad2d(matrix: list) -> tuple:
    """Zero-padding 2D para dimensões potência de 2. Retorna (padded, orig_r, orig_c, pad_r, pad_c)."""
    r, c    = len(matrix), len(matrix[0])
    tr, tc  = _next_pow2(r), _next_pow2(c)
    padded  = [[matrix[i][j] if i < r and j < c else 0.0
                for j in range(tc)] for i in range(tr)]
    return padded, r, c, tr, tc


def cipher_channel(channel: list, password: str, decrypt: bool = False, salt: str = "fc_img_v1", orig_size: tuple = None) -> list:
    """
    Cifra ou decifra um canal de imagem utilizando a verdadeira perturbação de fase
    no domínio da frequência (FFT2D), por meio de rotação complexa unitária.
    Aplica centralização de sinal e atenuação de escala 2D para evitar estouros (overflow/underflow)
    dos limites dos pixels [0, 255], assegurando qualidade visual perfeita na descriptografia.
    """
    scale_factor = 0.45  # Fator de atenuação para evitar estouros na perturbação de fase
    
    if not decrypt:
        # Criptografia: Desloca o range [0, 255] para [-128, 127], atenua por scale_factor e normaliza por 128.0
        processed = [[((p - 128.0) * scale_factor) / 128.0 for p in row] for row in channel]
    else:
        # Descriptografia: O input já vem centralizado em [0, 255] (salvo no arquivo)
        processed = [[(p - 128.0) / 128.0 for p in row] for row in channel]

    # Prepara matriz complexa (Im=0)
    cx_ch = [[[p, 0.0] for p in row] for row in processed]
    padded, orig_r, orig_c, tr, tc = _pad2d(cx_ch)
    
    # Passo 1: Decomposição da imagem em harmônicas (FFT2D)
    X = fft2d(padded, skip_pad=True)
    
    # Passo 2: Geração da matriz da senha 2D
    K = get_key_matrix_2d(password, tr, tc)
    
    # Passo 3: Rotação complexa unitária com a senha no domínio da frequência
    Y = []
    for r in range(tr):
        row = []
        for c in range(tc):
            k_re, k_im = K[r][c][0], K[r][c][1]
            mag = cabs(k_re, k_im)
            
            # Calcula o componente unitário de rotação (evita divisão por zero)
            if mag > 1e-12:
                u_re = k_re / mag
                u_im = k_im / mag
            else:
                u_re = 1.0
                u_im = 0.0
                
            x_re, x_im = X[r][c][0], X[r][c][1]
            
            if decrypt:
                # Descriptografia: Rotaciona pelo conjugado complexo (u_re - j * u_im)
                row.append([
                    x_re * u_re + x_im * u_im,
                    -x_re * u_im + x_im * u_re
                ])
            else:
                # Criptografia: Rotaciona multiplicando diretamente (u_re + j * u_im)
                row.append([
                    x_re * u_re - x_im * u_im,
                    x_re * u_im + x_im * u_re
                ])
        Y.append(row)
        
    # Passo 4: Conversão novamente para imagem (IFFT2D)
    restored = ifft2d(Y)
    
    if decrypt and orig_size is not None:
        crop_r, crop_c = orig_size
        cropped = [row[:crop_c] for row in restored[:crop_r]]
    else:
        cropped = restored

    # Passo 5: Conversão de volta para pixels inteiros [0, 255]
    result = []
    for row in cropped:
        pix_row = []
        for c in row:
            real_val = c[0]
            if decrypt:
                # 1. Escala o real de volta multiplicando por 128.0
                # 2. Reverte a atenuação dividindo por scale_factor
                # 3. Restaura o deslocamento original de +128.0
                val = round((real_val * 128.0) / scale_factor + 128.0)
            else:
                # 1. Escala o real de volta multiplicando por 128.0
                # 2. Restaura o deslocamento original de +128.0
                val = round(real_val * 128.0 + 128.0)
                
            # Garante limites estritos [0, 255]
            val = max(0, min(255, val))
            pix_row.append(val)
        result.append(pix_row)
        
    return result


def get_padded_size(h: int, w: int) -> tuple:
    """Retorna o tamanho padded (potência de 2) para uma imagem de tamanho hxw."""
    return _next_pow2(h), _next_pow2(w)