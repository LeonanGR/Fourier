# =============================================================================
# IMAGE CIPHER — Soma de Matrizes na FFT 2D
# =============================================================================

from core.fft_engine import fft2d, ifft2d, _next_pow2
from core.key_engine import get_key_matrix_2d

def _pad2d(matrix: list) -> tuple:
    """Zero-padding 2D para dimensões potência de 2. Retorna (padded, orig_r, orig_c, pad_r, pad_c)."""
    r, c    = len(matrix), len(matrix[0])
    tr, tc  = _next_pow2(r), _next_pow2(c)
    padded  = [[matrix[i][j] if i < r and j < c else [0.0, 0.0]
                for j in range(tc)] for i in range(tr)]
    return padded, r, c, tr, tc

def _channel_to_cx(ch: list) -> list:
    """Canal de pixels [0,255] -> complexos normalizados [0,1] com Im=0."""
    return [[[p/255.0, 0.0] for p in row] for row in ch]

def _cx_to_channel(mx: list) -> list:
    """Complexos -> pixels inteiros [0,255] (aplicando aritmética modular 256)."""
    result = []
    for row in mx:
        pix_row = []
        for c in row:
            v = round(c[0] * 255.0)
            # Módulo 256 garante perfeitamente a reversibilidade sem perda
            v = v % 256
            pix_row.append(v)
        result.append(pix_row)
    return result

def cipher_channel(channel: list, password: str, decrypt: bool = False, salt: str = "fc_img_v1", orig_size: tuple = None) -> list:
    """
    Cifra ou decifra um canal de imagem utilizando a adição de matriz com a senha
    no domínio da frequência (FFT2D).
    """
    cx_ch = _channel_to_cx(channel)
    padded, orig_r, orig_c, tr, tc = _pad2d(cx_ch)
    
    # Passo 1: Decomposição da imagem em harmônicas (FFT2D)
    X = fft2d(padded, skip_pad=True)
    
    # Passo 2: Geração da matriz da senha 2D
    K = get_key_matrix_2d(password, tr, tc)
    
    # Passo 3: Soma matricial com a senha no domínio da frequência
    Y = []
    for r in range(tr):
        row = []
        for c in range(tc):
            if decrypt:
                row.append([X[r][c][0] - K[r][c][0], X[r][c][1] - K[r][c][1]])
            else:
                row.append([X[r][c][0] + K[r][c][0], X[r][c][1] + K[r][c][1]])
        Y.append(row)
        
    # Passo 4: Conversão novamente para imagem (IFFT2D)
    restored = ifft2d(Y)
    
    if decrypt and orig_size is not None:
        crop_r, crop_c = orig_size
        cropped = [row[:crop_c] for row in restored[:crop_r]]
    elif decrypt:
        cropped = restored
    else:
        cropped = restored

    # Passo 5: Conversão para RGB (retorna os valores com módulo 256)
    return _cx_to_channel(cropped)

def get_padded_size(h: int, w: int) -> tuple:
    """Retorna o tamanho padded (potência de 2) para uma imagem de tamanho hxw."""
    return _next_pow2(h), _next_pow2(w)