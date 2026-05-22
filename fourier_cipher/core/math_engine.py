# =============================================================================
# MATH ENGINE
# Todas as funções matemáticas calculadas do zero.
# Nenhuma importação de biblioteca matemática — apenas Python puro.
# =============================================================================


# -----------------------------------------------------------------------------
# PI — Fórmula de Machin: π = 16·arctan(1/5) - 4·arctan(1/239)
# Muito mais rápida que a série de Leibniz, que converge lentamente demais.
# -----------------------------------------------------------------------------
def _arctan_series(x: float, terms: int = 80) -> float:
    """Série de Taylor para arctan(x): Σ (-1)^n · x^(2n+1) / (2n+1)"""
    result = 0.0
    x_pow  = x
    x_sq   = x * x
    for n in range(terms):
        term    = x_pow / (2 * n + 1)
        result += term if n % 2 == 0 else -term
        x_pow  *= x_sq
    return result


PI     = 16.0 * _arctan_series(1/5) - 4.0 * _arctan_series(1/239)
TWO_PI = 2.0 * PI


# -----------------------------------------------------------------------------
# NORMALIZAÇÃO — Reduz θ para [-π, π] antes de aplicar as séries.
# Usa aritmética modular para robustez com valores extremos.
# -----------------------------------------------------------------------------
def _normalize(x: float) -> float:
    # Módulo seguro: reduz a [0, 2π) e depois ajusta para [-π, π]
    x = x - TWO_PI * int(x / TWO_PI)
    if x > PI:
        x -= TWO_PI
    elif x < -PI:
        x += TWO_PI
    # Segundo ajuste para valores que caem exatamente nos limites
    if x > PI:
        x -= TWO_PI
    elif x < -PI:
        x += TWO_PI
    return x


# -----------------------------------------------------------------------------
# SENO — Série de Taylor: sin(x) = x - x³/3! + x⁵/5! - ...
# Convergência adaptativa: para quando |termo| < ε (tipicamente 5-10 termos).
# -----------------------------------------------------------------------------
def sin_t(x: float, eps: float = 1e-15) -> float:
    x      = _normalize(x)
    result = 0.0
    x_pow  = x
    x_sq   = x * x
    fact   = 1.0
    for n in range(20):           # limite de segurança (nunca precisa de 20)
        if n > 0:
            fact  *= (2*n) * (2*n + 1)
            x_pow *= x_sq
        term = x_pow / fact
        if term < 0:
            term = -term
        if n > 2 and term < eps:  # convergiu
            break
        result += (x_pow / fact) if n % 2 == 0 else -(x_pow / fact)
    return result


# -----------------------------------------------------------------------------
# COSSENO — Série de Taylor: cos(x) = 1 - x²/2! + x⁴/4! - ...
# Convergência adaptativa idêntica à do seno.
# -----------------------------------------------------------------------------
def cos_t(x: float, eps: float = 1e-15) -> float:
    x      = _normalize(x)
    result = 1.0
    x_pow  = 1.0
    x_sq   = x * x
    fact   = 1.0
    for n in range(1, 20):
        fact  *= (2*n - 1) * (2*n)
        x_pow *= x_sq
        term = x_pow / fact
        if term < 0:
            term = -term
        if n > 2 and term < eps:
            break
        result += (x_pow / fact) if n % 2 == 0 else -(x_pow / fact)
    return result


# -----------------------------------------------------------------------------
# SENO E COSSENO SIMULTÂNEOS — Calcula ambos em uma única passada.
# Economiza ~50% quando ambos os valores são necessários (ex.: rotação).
# -----------------------------------------------------------------------------
def sincos_t(x: float, eps: float = 1e-15) -> tuple:
    """Retorna (sin(x), cos(x)) com uma única normalização e loop."""
    x    = _normalize(x)
    x_sq = x * x

    # --- Seno: sin(x) = x - x³/3! + x⁵/5! - x⁷/7! + ...
    #     Termo n (0-indexed): sinal = (-1)^n, potência = x^(2n+1), fator = (2n+1)!
    s_result = x          # termo n=0
    s_pow    = x
    s_fact   = 1.0

    # --- Cosseno: cos(x) = 1 - x²/2! + x⁴/4! - x⁶/6! + ...
    #     Termo n (0-indexed): sinal = (-1)^n, potência = x^(2n), fator = (2n)!
    c_result = 1.0        # termo n=0
    c_pow    = 1.0
    c_fact   = 1.0

    for n in range(1, 20):
        # Seno termo n: potência x^(2n+1), fatorial (2n+1)!
        s_fact *= (2*n) * (2*n + 1)
        s_pow  *= x_sq
        s_term  = s_pow / s_fact
        s_result += s_term if n % 2 == 0 else -s_term

        # Cosseno termo n: potência x^(2n), fatorial (2n)!
        c_fact *= (2*n - 1) * (2*n)
        c_pow  *= x_sq
        c_term  = c_pow / c_fact
        c_result += c_term if n % 2 == 0 else -c_term

        # Critério de parada: ambos convergiram
        s_abs = s_term if s_term >= 0 else -s_term
        c_abs = c_term if c_term >= 0 else -c_term
        if n > 2 and s_abs < eps and c_abs < eps:
            break

    return (s_result, c_result)


# -----------------------------------------------------------------------------
# RAIZ QUADRADA — Newton-Raphson: x_{n+1} = (x_n + S/x_n) / 2
# Converge quadraticamente — dobra os dígitos corretos a cada passo.
# 12 iterações é mais que suficiente para float64 (precisão de máquina).
# Chute inicial melhorado via escalonamento por potência de 2.
# -----------------------------------------------------------------------------
def sqrt_nr(s: float) -> float:
    if s < 0: raise ValueError("sqrt de negativo indefinido.")
    if s == 0: return 0.0
    # Chute inicial melhorado: escala para ficar perto da raiz real
    x = s
    while x * x > s * 4:
        x /= 2.0
    while x * x < s / 4:
        x *= 2.0
    for _ in range(12):
        x = (x + s / x) / 2.0
    return x


# -----------------------------------------------------------------------------
# ATAN2 — Necessário para extrair a fase de números complexos.
# Usa série de arctan com redução de quadrante para cobrir [-π, π].
# -----------------------------------------------------------------------------
def atan2_t(y: float, x: float) -> float:
    """atan2(y, x) calculado via série de Taylor com ajuste de quadrante."""
    if x == 0.0:
        if y > 0: return  PI / 2
        if y < 0: return -PI / 2
        return 0.0

    def _atan(t: float) -> float:
        # Redução: |t| > 1 → atan(t) = π/2 - atan(1/t)
        flip = False
        if t < -1.0 or t > 1.0:
            t    = 1.0 / t
            flip = True
        t_sq  = t * t
        t_pow = t
        res   = 0.0
        for n in range(60):
            term = t_pow / (2*n+1)
            # Convergência adaptativa
            if term < 0:
                term = -term
            if n > 5 and term < 1e-15:
                break
            res  += t_pow / (2*n+1) if n % 2 == 0 else -t_pow / (2*n+1)
            t_pow *= t_sq
        if flip:
            res = (PI/2 - res) if t >= 0 else (-PI/2 - res)
        return res

    angle = _atan(y / x)
    # Ajuste de quadrante
    if x < 0:
        angle += PI if y >= 0 else -PI
    return angle


# -----------------------------------------------------------------------------
# MÓDULO DE COMPLEXO — |z| = √(re² + im²)
# -----------------------------------------------------------------------------
def cabs(re: float, im: float) -> float:
    return sqrt_nr(re * re + im * im)