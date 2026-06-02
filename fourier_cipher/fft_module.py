# Constante matemática PI calculada até 20 casas decimais para garantir alta precisão nos cálculos de ângulos.
MEU_PI = 3.14159265358979323846

def meu_sin(x):
    """
    Função: meu_sin(x)
    Objetivo: Calcula o seno de um ângulo 'x' (em radianos) usando a Série de Taylor.
    para calcular senos, que são essenciais para a fórmula de Euler na FFT.
    """
    # 1. Reduzimos o ângulo 'x' para o intervalo [-PI, PI].
    # Por que: A Série de Taylor para o seno converge muito mais rápido e com menos erro
    # quando o ângulo está próximo de zero.
    x = x % (2 * MEU_PI)
    if x > MEU_PI:
        # Se for maior que PI, subtraímos um círculo completo (2*PI) para trazê-lo ao negativo equivalente.
        x -= 2 * MEU_PI
        
    # Inicializamos o resultado com 0.0
    resultado = 0.0
    # O primeiro termo da série de Taylor do seno é o próprio 'x'
    termo = x
    # Calculamos x ao quadrado de antemão para não precisar recalcular a cada passo do loop
    x_quadrado = x * x
    
    # Executamos o loop 15 vezes (15 termos da série).
    # Por que 15? É o suficiente para atingir a precisão máxima do tipo 'float' no Python.
    for i in range(1, 16):
        # Adicionamos o termo atual ao resultado final
        resultado += termo
        # Calculamos o próximo termo da série.
        # A fórmula matemática da Série de Taylor multiplica o termo anterior por -(x^2) e 
        # divide pelos próximos dois números do fatorial: (2i) e (2i+1).
        termo = termo * (-x_quadrado) / ((2 * i) * (2 * i + 1))
        
    # Retorna o valor final do seno calculado matematicamente
    return resultado

def meu_cos(x):
    """
    Função: meu_cos(x)
    Objetivo: Calcula o cosseno de um ângulo 'x' em radianos.
    Por que: Necessário para a fórmula de Euler.
    """
    # Usamos uma identidade trigonométrica fundamental: cos(x) = sin(x + PI/2).
    return meu_sin(x + MEU_PI / 2)

def meu_exp_complex(angulo):
    """
    Função: meu_exp_complex(angulo)
    Objetivo: Calcula a exponencial complexa e^(i * angulo).
    Por que: A FFT rotaciona componentes no plano complexo. Essa função gera o 
    "twiddle factor" (fator de rotação).
    
    Exemplo de retorno:
        Para angulo = PI/2 (1.57079...), retorna o número complexo: (0.0 + 1.0j)
    """
    # Utilizamos a Fórmula de Euler: e^(ix) = cos(x) + i*sin(x).
    # A função 'complex' nativa do Python junta as duas partes real e imaginária.
    # Exemplo: se cos=0.0 e sin=1.0, retorna o objeto complex: (0.0 + 1.0j)
    return complex(meu_cos(angulo), meu_sin(angulo))

def fft1d(x):
    """
    Função: fft1d(x)
    Objetivo: Calcula a Transformada Rápida de Fourier (FFT) para uma lista 1D de números.
    Por que: É o coração do algoritmo de criptografia, transformando o sinal do domínio espacial
    para o domínio das frequências.
    """
    # Descobre o tamanho da lista 'x'
    N = len(x)
    
    # Condição de parada da recursão: se a lista tiver tamanho 1 ou 0, a FFT dela é ela mesma.
    if N <= 1:
        return x
    
    # Algoritmo de Cooley-Tukey: Dividir e Conquistar
    # Pegamos todos os elementos de posições pares (0, 2, 4...) e rodamos a FFT neles
    pares = fft1d(x[0::2])
    # Pegamos todos os elementos de posições ímpares (1, 3, 5...) e rodamos a FFT neles
    impares = fft1d(x[1::2])
    
    # Calculamos o vetor de rotação 'T' para combinar os resultados pares e ímpares.
    # Para cada k de 0 até a metade do tamanho (N/2), multiplicamos o resultado ímpar
    # pelo ângulo respectivo no círculo complexo.
    T = []
    for k in range(N // 2):
        # 1. Calcula o ângulo de rotação para este passo k
        angulo = -2 * MEU_PI * k / N
        
        # 2. Gera o fator de rotação complexo (um ponto no círculo)
        fator_rotacao = meu_exp_complex(angulo)
        
        # 3. Multiplica o valor da lista 'impares' na posição k por esse fator
        elemento_rotacionado = fator_rotacao * impares[k]
        
        # 4. Adiciona o resultado na lista T
        T.append(elemento_rotacionado)
    
    # A primeira metade da FFT final é a soma dos pares com o fator de rotação T.
    # A segunda metade é a subtração (simetria do círculo complexo).
    # O caractere '\' indica que o código continua na linha de baixo.
    return [pares[k] + T[k] for k in range(N // 2)] + \
           [pares[k] - T[k] for k in range(N // 2)]

def ifft1d(x):
    """
    Função: ifft1d(x)
    Objetivo: Calcula a Inversa da Transformada Rápida de Fourier em 1D.
    Por que: Necessário para voltar do domínio da frequência (criptografado) para a imagem visível.
    """
    # Pega o tamanho do array
    N = len(x)
    
    # A Inversa da FFT pode ser calculada rodando a FFT normal
    # em cima dos "conjugados complexos" da entrada (invertendo o sinal da parte imaginária).
    x_conj = [X.conjugate() for X in x]
    
    # Executa a FFT normal, mas agora em cima dos valores conjugados
    X_conj = fft1d(x_conj)
    
    # Para finalizar a IFFT, tiramos o conjugado do resultado novamente
    # e dividimos tudo por N, pois a FFT amplifica os valores pelo tamanho da amostra.
    return [X.conjugate() / N for X in X_conj]

def fft2d(matriz):
    """
    Função: fft2d(matriz)
    Objetivo: Aplica a FFT em uma matriz bidimensional (como uma imagem).
    Por que: Imagens têm altura e largura, logo precisam de processamento em duas dimensões.
    """
    # Passo 1: Aplica a fft1d() em cada uma das linhas da matriz horizontalmente.
    linhas_fft = [fft1d(linha) for linha in matriz]
    
    # Passo 2: Precisamos aplicar a FFT nas colunas. Para facilitar, nós "transpomos" a matriz
    # (transformamos as linhas em colunas e vice-versa).
    colunas = [[linhas_fft[y][x] for y in range(len(linhas_fft))] for x in range(len(linhas_fft[0]))]
    
    # Passo 3: Agora que as colunas viraram linhas, rodamos a fft1d() de novo.
    colunas_fft = [fft1d(col) for col in colunas]
    
    # Passo 4: Desfazemos a transposição (giramos de volta) para retornar ao formato correto.
    resultado = [[colunas_fft[x][y] for x in range(len(colunas_fft))] for y in range(len(colunas_fft[0]))]
    
    # Retornamos a matriz final contendo o espectro de frequências 2D.
    return resultado

def ifft2d(matriz):
    """
    Função: ifft2d(matriz)
    Objetivo: Inverte a matriz 2D de frequências para recuperar os pixels 2D originais.
    Por que: Passo final da descriptografia da imagem.
    """
    # A lógica bidimensional é idêntica à da FFT2D, mas usamos a função ifft1d!
    # 1. IFFT nas linhas originais
    linhas_ifft = [ifft1d(linha) for linha in matriz]
    
    # 2. Transpõe a matriz (inverte X por Y)
    colunas = [[linhas_ifft[y][x] for y in range(len(linhas_ifft))] for x in range(len(linhas_ifft[0]))]
    
    # 3. IFFT nas colunas (que agora estão no formato de lista horizontal)
    colunas_ifft = [ifft1d(col) for col in colunas]
    
    # 4. Transpõe de volta ao formato matriz 2D clássico (Y, X)
    resultado = [[colunas_ifft[x][y] for x in range(len(colunas_ifft))] for y in range(len(colunas_ifft[0]))]
    
    # Retorna a matriz espacial pronta para virar pixels
    return resultado
