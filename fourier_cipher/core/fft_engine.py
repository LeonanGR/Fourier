# =============================================================================
# FFT ENGINE — Algoritmo de Cooley-Tukey (Radix-2, DIT)
#
# X[k] = Σ x[n] · e^(-j·2π·k·n/N)
#
# A "borboleta":
#   X[k]     = E[k] + W^k · O[k]
#   X[k+N/2] = E[k] - W^k · O[k]
#   onde W^k = e^(-j·2π·k/N) = cos(...) - j·sin(...)
#
# Complexos representados como listas [re, im] — sem classe, sem numpy.
#
# =============================================================================

from core.math_engine import cos_t, sin_t, sincos_t, TWO_PI


# --- Aritmética complexa inline ---

def _cadd(a, b): return [a[0]+b[0], a[1]+b[1]]
def _csub(a, b): return [a[0]-b[0], a[1]-b[1]]
def _cmul(a, b):
    # (a+jb)(c+jd) = (ac-bd) + j(ad+bc)
    return [a[0]*b[0] - a[1]*b[1],
            a[0]*b[1] + a[1]*b[0]]


# -----------------------------------------------------------------------------
# ZERO-PADDING — Cooley-Tukey exige N = potência de 2
# -----------------------------------------------------------------------------
def _next_pow2(n: int) -> int:
    p = 1
    while p < n: p <<= 1
    return p


def _pad(signal: list) -> list:
    """Completa com zeros complexos até N ser potência de 2."""
    target = _next_pow2(len(signal))
    return signal + [[0.0, 0.0]] * (target - len(signal))


# -----------------------------------------------------------------------------
# PRÉ-CÁLCULO DE TWIDDLE FACTORS
# W_N^k = e^(-j·2π·k/N) = cos(-2πk/N) + j·sin(-2πk/N)
#
# Para cada tamanho de bloco, os twiddle factors se repetem ciclicamente.
# Pré-computar evita chamadas repetidas a sin_t/cos_t.
# Cache indexado por tamanho N — reutilizado entre FFTs do mesmo tamanho.
# -----------------------------------------------------------------------------
_twiddle_cache = {}


def _get_twiddles(n: int) -> list:
    """Retorna lista de twiddle factors [cos, sin] para FFT de tamanho n."""
    if n in _twiddle_cache:
        return _twiddle_cache[n]

    half = n // 2
    twiddles = [None] * half
    for k in range(half):
        angle = -TWO_PI * k / n
        s, c = sincos_t(angle)
        twiddles[k] = [c, s]

    _twiddle_cache[n] = twiddles
    return twiddles


# -----------------------------------------------------------------------------
# BIT-REVERSAL PERMUTATION
# Reordena o array in-place para a FFT iterativa.
# -----------------------------------------------------------------------------
def _bit_reverse(x: list, n: int, log2n: int) -> None:
    """Permutação bit-reversal in-place."""
    for i in range(n):
        rev = 0
        val = i
        for _ in range(log2n):
            rev = (rev << 1) | (val & 1)
            val >>= 1
        if rev > i:
            x[i], x[rev] = x[rev], x[i]


# -----------------------------------------------------------------------------
# FFT 1D — Iterativa com bit-reversal e twiddle factors pré-computados
#
# Substitui a versão recursiva original para eliminar:
#   - Criação de sub-listas (x[0::2], x[1::2]) em cada nível
#   - Overhead de chamadas de função recursivas
#   - Chamadas repetidas a sin_t/cos_t
# Mesma complexidade O(N log N), mas constante multiplicativa muito menor.
# -----------------------------------------------------------------------------
def fft(x: list) -> list:
    """
    FFT iterativa. Entrada: lista de [re, im].
    Retorna espectro X[k] como lista de [re, im].
    """
    n = len(x)
    if n == 1:
        return [[x[0][0], x[0][1]]]

    # Cópia de trabalho
    result = [[xi[0], xi[1]] for xi in x]

    # Calcula log2(n)
    log2n = 0
    temp = n
    while temp > 1:
        log2n += 1
        temp >>= 1

    # Bit-reversal permutation
    _bit_reverse(result, n, log2n)

    # Borboletas por estágio (tamanhos 2, 4, 8, ..., n)
    size = 2
    while size <= n:
        half = size // 2
        twiddles = _get_twiddles(size)

        for start in range(0, n, size):
            for k in range(half):
                w = twiddles[k]
                idx_e = start + k
                idx_o = start + k + half

                # t = W · result[idx_o]
                o_re = result[idx_o][0]
                o_im = result[idx_o][1]
                t_re = w[0] * o_re - w[1] * o_im
                t_im = w[0] * o_im + w[1] * o_re

                # Borboleta
                e_re = result[idx_e][0]
                e_im = result[idx_e][1]
                result[idx_e] = [e_re + t_re, e_im + t_im]
                result[idx_o] = [e_re - t_re, e_im - t_im]

        size <<= 1

    return result


# -----------------------------------------------------------------------------
# IFFT 1D — Via conjugação: ifft(X) = (1/N)·conj(fft(conj(X)))
# Reutiliza exatamente o mesmo kernel da FFT — sem código duplicado.
# -----------------------------------------------------------------------------
def ifft(X: list) -> list:
    n     = len(X)
    conj  = [[c[0], -c[1]] for c in X]        # conjuga entrada
    out   = fft(conj)                           # FFT direta
    return [[s[0]/n, -s[1]/n] for s in out]    # conjuga e normaliza


# -----------------------------------------------------------------------------
# FFT 2D — Separabilidade: FFT nas linhas, depois nas colunas
# F[u,v] é separável em duas FFT 1D ortogonais.
#
# NOTA: Espera-se que o input já tenha padding (potência de 2).
# Se as dimensões não forem potência de 2, aplica _pad() automaticamente.
# Para evitar padding duplo, use skip_pad=True quando já tiver feito
# padding externamente.
# -----------------------------------------------------------------------------
def fft2d(matrix: list, skip_pad: bool = False) -> list:
    if skip_pad:
        rows_fft = [fft(row) for row in matrix]
    else:
        rows_fft = [fft(_pad(row)) for row in matrix]

    # Passo 2: Transpõe → FFT em cada coluna → transpõe de volta
    cols = len(rows_fft[0])
    rows = len(rows_fft)
    transposed = [[rows_fft[r][c] for r in range(rows)] for c in range(cols)]

    if skip_pad:
        cols_fft = [fft(col) for col in transposed]
    else:
        cols_fft = [fft(_pad(col)) for col in transposed]

    return [[cols_fft[c][r] for c in range(cols)] for r in range(rows)]


def ifft2d(matrix: list) -> list:
    rows = len(matrix)
    cols = len(matrix[0])
    rows_ifft   = [ifft(row) for row in matrix]
    transposed  = [[rows_ifft[r][c] for r in range(rows)] for c in range(cols)]
    cols_ifft   = [ifft(col) for col in transposed]
    return [[cols_ifft[c][r] for c in range(cols)] for r in range(rows)]