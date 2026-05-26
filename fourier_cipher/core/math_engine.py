# =============================================================================
# MATH ENGINE
# =============================================================================


# -----------------------------------------------------------------------------
# PI — Fórmula de Machin: π = 16·arctan(1/5) - 4·arctan(1/239)
# -----------------------------------------------------------------------------
def _arctan_series(x: float, terms: int = 80) -> float: # Define a função, recebendo o valor x e o número de iterações terms (padrão 80).
    """Série de Taylor para arctan(x): Σ (-1)^n · x^(2n+1) / (2n+1)"""
    result = 0.0 # Inicializa a variável que acumulará o somatório da série.
    x_pow  = x   # Define a primeira potência de x (equivalente a x¹).
    x_sq   = x * x # Pré-calcula x² para ser usado como multiplicador nas iterações, evitando cálculos redundantes.
    for n in range(terms): # Inicia o loop para iterar sobre os termos definidos.
        term    = x_pow / (2 * n + 1) # Calcula o valor absoluto do termo atual (a potência dividida pelo respectivo número ímpar da série).
        result += term if n % 2 == 0 else -term # Alterna o sinal (série alternada). Se n for par, soma; se ímpar, subtrai.
        x_pow  *= x_sq # Prepara a potência para a próxima iteração multiplicando-a por x², transformando x¹ → x³ → x⁵ . . .
    return result # Retorna o valor aproximado do arco-tangente.


PI     = 16.0 * _arctan_series(1/5) - 4.0 * _arctan_series(1/239) # Aplica a fórmula de Machin π = 16 arctan(1/5) - 4 arctan(1/239), chamando a função anterior duas vezes.
TWO_PI = 2.0 * PI # Armazena 2π, usado amplamente para cálculos trigonométricos que cobrem um círculo completo.


# -----------------------------------------------------------------------------
# NORMALIZAÇÃO — Reduz θ para [-π, π] antes de aplicar as séries.
# Usa aritmética modular para robustez com valores extremos.
# -----------------------------------------------------------------------------
def _normalize(x: float) -> float: # Assinatura da função.
    # Módulo seguro: reduz a [0, 2π) e depois ajusta para [-π, π]
    x = x - TWO_PI * int(x / TWO_PI) # Aplica a lógica de módulo de forma segura para floats. Remove voltas completas do círculo (2π) do ângulo original.
    if x > PI: # Se o ângulo residual for maior que π (ex: 1.5π), ele subtrai 2π para mapeá-lo ao lado negativo (ex: -0.5π).
        x -= TWO_PI
    elif x < -PI: # Lógica inversa, caso o ângulo caia abaixo de -π.
        x += TWO_PI
    # O segundo bloco de if/elif idêntico: Trata erros minúsculos de precisão do ponto flutuante que possam deixar o valor exatamente na borda do limite após a primeira correção.
    if x > PI:
        x -= TWO_PI
    elif x < -PI:
        x += TWO_PI
    return x # Retorna o ângulo normalizado e pronto para as funções trigonométricas.


# -----------------------------------------------------------------------------
# SENO — Série de Taylor: sin(x) = x - x³/3! + x⁵/5! - ...
# Convergência adaptativa: para quando |termo| < ε (tipicamente 5-10 termos).
# -----------------------------------------------------------------------------
def sin_t(x: float, eps: float = 1e-15) -> float: # Define a função e a tolerância de erro (eps).
    x      = _normalize(x) # Normaliza o ângulo para [-π, π].
    result = 0.0; x_pow = x; x_sq = x * x; fact = 1.0 # Inicializa as variáveis. fact armazenará o fatorial iterativamente.
    for n in range(20): # Limite máximo de segurança. Na prática, o loop quebra (break) muito antes de 20 devido à convergência.
        if n > 0:
            fact  *= (2*n) * (2*n + 1) # Se não for a primeira volta, multiplica o fatorial anterior por seus próximos dois termos para obter o novo fatorial (ex: de 3! para 5!).
            x_pow *= x_sq # Atualiza a potência do numerador.
        term = x_pow / fact # Calcula o termo atual da série sem o sinal.
        if term < 0:
            term = -term # Retira o valor absoluto do termo temporariamente para testar a convergência sem quebrar.
        if n > 2 and term < eps: # Se passou de 2 iterações e o termo atual for menor que a margem de erro, encerra o cálculo pois a precisão máxima já foi atingida.
            break
        result += (x_pow / fact) if n % 2 == 0 else -(x_pow / fact) # Alterna os sinais dependendo se a iteração é par ou ímpar, somando ou subtraindo do resultado principal.
    return result


# -----------------------------------------------------------------------------
# COSSENO — Série de Taylor: cos(x) = 1 - x²/2! + x⁴/4! - ...
# Convergência adaptativa idêntica à do seno.
# -----------------------------------------------------------------------------
def cos_t(x: float, eps: float = 1e-15) -> float:
    # A estrutura inicial é idêntica à do seno, com a principal diferença em: result = 1.0 e x_pow = 1.0. O primeiro termo do cosseno (para x⁰) é 1.
    x      = _normalize(x)
    result = 1.0
    x_pow  = 1.0
    x_sq   = x * x
    fact   = 1.0
    for n in range(1, 20): # O loop começa em 1, pois o termo 0 já está embutido no resultado inicial.
        fact  *= (2*n - 1) * (2*n) # Gera o fatorial par iterativamente.
        x_pow *= x_sq
        term = x_pow / fact
        if term < 0:
            term = -term
        # As verificações de parada (break) e alternância de sinal são estruturalmente idênticas ao sin_t, variando apenas matematicamente para se alinhar aos números pares.
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
    x    = _normalize(x) # Normaliza o ângulo e cria a variável quadrática base que serve tanto para seno quanto para cosseno.
    x_sq = x * x

    # --- Seno: sin(x) = x - x³/3! + x⁵/5! - x⁷/7! + ...
    #     Termo n (0-indexed): sinal = (-1)^n, potência = x^(2n+1), fator = (2n+1)!
    s_result, s_pow, s_fact = x, x, 1.0 # Variáveis que rastreiam o estado do seno.

    # --- Cosseno: cos(x) = 1 - x²/2! + x⁴/4! - x⁶/6! + ...
    #     Termo n (0-indexed): sinal = (-1)^n, potência = x^(2n), fator = (2n)!
    c_result, c_pow, c_fact = 1.0, 1.0, 1.0 # Variáveis que rastreiam o estado do cosseno.

    for n in range(1, 20): # Único loop lidando com ambos simultaneamente.
        # Seno termo n: potência x^(2n+1), fatorial (2n+1)!
        s_fact *= (2*n) * (2*n + 1) # Atualizam os respectivos fatoriais (ímpares para seno, pares para cosseno).
        s_pow  *= x_sq # Atualizam as respectivas potências.
        s_term  = s_pow / s_fact

        # Cosseno termo n: potência x^(2n), fatorial (2n)!
        c_fact *= (2*n - 1) * (2*n)
        c_pow  *= x_sq
        c_term  = c_pow / c_fact

        # O bloco aplica os incrementos a s_result e c_result com a mesma alternância de sinais.
        s_result += s_term if n % 2 == 0 else -s_term
        c_result += c_term if n % 2 == 0 else -c_term

        # Critério de parada: ambos convergiram
        s_abs = s_term if s_term >= 0 else -s_term
        c_abs = c_term if c_term >= 0 else -c_term
        if n > 2 and s_abs < eps and c_abs < eps: # O loop só para quando o erro residual tanto do seno quanto do cosseno atinge a precisão desejada de hardware.
            break

    return (s_result, c_result) # Retorna ambos em uma tupla estruturada.


# -----------------------------------------------------------------------------
# RAIZ QUADRADA — Newton-Raphson: x_{n+1} = (x_n + S/x_n) / 2
# Converge quadraticamente — dobra os dígitos corretos a cada passo.
# 12 iterações é mais que suficiente para float64 (precisão de máquina).
# Chute inicial melhorado via escalonamento por potência de 2.
# -----------------------------------------------------------------------------
def sqrt_nr(s: float) -> float:
    if s < 0: raise ValueError("sqrt de negativo indefinido.") # Tratamentos essenciais de exceção para números imaginários (não abordados aqui) e zero.
    if s == 0: return 0.0
    x = s # Estabelece a variável S que foi passada como o primeiro "chute" x.
    while x * x > s * 4: # Enquanto o chute ao quadrado for estupidamente maior que o alvo, divide o chute pela metade (escalonamento grosseiro para evitar desperdício iterativo).
        x /= 2.0
    while x * x < s / 4: # Se o chute for pequeno demais, dobra seu tamanho.
        x *= 2.0
    for _ in range(12): # Como foi feito o escalonamento anterior, no máximo 12 iterações garantem a precisão total de um float64.
        x = (x + s / x) / 2.0 # É o coração da função. Aplica a fórmula da média de Newton: xn+1 = 1/2(xn + S/xn).
    return x # Retorna a raiz consolidada.


# -----------------------------------------------------------------------------
# ATAN2 — Necessário para extrair a fase de números complexos.
# Usa série de arctan com redução de quadrante para cobrir [-π, π].
# -----------------------------------------------------------------------------
def atan2_t(y: float, x: float) -> float:
    """atan2(y, x) calculated via série de Taylor com ajuste de quadrante."""
    if x == 0.0: # Trata as singularidades verticais, retornando π/2 ou -π/2 caso o vetor esteja exatamente sobre o eixo Y, e 0 para a origem.
        if y > 0: return  PI / 2
        if y < 0: return -PI / 2
        return 0.0

    def _atan(t: float) -> float: # Cria uma sub-função (closure) adaptada para o cálculo principal do arco-tangente.
        flip = False # Variável de estado que indicará se o algoritmo precisou inverter a fração para lidar com entradas grandes.
        if t < -1.0 or t > 1.0: # Se o valor absoluto da divisão (y/x) for maior que 1, a Série de Taylor comum se torna altamente instável ou diverge. A função inverte o termo e marca a flag flip.
            t    = 1.0 / t
            flip = True
        t_sq  = t * t
        t_pow = t
        res   = 0.0
        for n in range(60): # Segue o loop clássico de for n in range(60): calculando a série do arco-tangente com adaptatividade de erro ϵ.
            term = t_pow / (2*n+1)
            # Convergência adaptativa
            if term < 0:
                term = -term
            if n > 5 and term < 1e-15:
                break
            res  += t_pow / (2*n+1) if n % 2 == 0 else -t_pow / (2*n+1)
            t_pow *= t_sq
        if flip: # Aplica a identidade matemática: se o termo foi invertido antes do cálculo da série, o resultado final da sub-função precisa ser ajustado subtraindo-o de π/2.
            res = (PI/2 - res) if t >= 0 else (-PI/2 - res)
        return res

    angle = _atan(y / x) # Chama a sub-função criada logo acima, retornando a base do ângulo.
    # Ajuste de quadrante
    if x < 0: # Verifica em que quadrante do plano cartesiano o vetor repousa. Se o valor de X for negativo, adiciona ou subtrai π ao ângulo para rebater o valor para o outro lado do círculo unitário.
        angle += PI if y >= 0 else -PI
    return angle # Entrega o ângulo verdadeiro.


# -----------------------------------------------------------------------------
# MÓDULO DE COMPLEXO — |z| = √(re² + im²)
# -----------------------------------------------------------------------------
def cabs(re: float, im: float) -> float: # Recebe as partes real e imaginária de um número complexo.
    return sqrt_nr(re * re + im * im) # Eleva as duas componentes ao quadrado, realiza a soma e invoca nossa implementação de sqrt_nr (Raiz Quadrada de Newton-Raphson) criada anteriormente.