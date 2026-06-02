import random

def validate_password(senha):
    """
    Função: validate_password(senha)
    Objetivo: Garantir que a senha digitada obedece às 4 regras rígidas do sistema.
    """
    if not senha.isdigit():
        return False, "A senha deve conter apenas números (sem letras, espaços ou caracteres especiais)."
        
    if len(senha) > 8:
        return False, "A senha não pode passar de 8 números."
        
    if len(senha) % 2 != 0:
        return False, "A quantidade de números na senha deve ser par."
        
    if len(senha) == 0:
        return False, "A senha não pode estar vazia."
        
    return True, ""

def generate_password_matrix(senha_str, largura=256, altura=256):
    """
    Função: generate_password_matrix(senha_str, largura, altura)
    Objetivo: Transformar a senha (ex: "1234") em uma semente (Seed) determinística 
    para gerar um campo de força de 256x256 de puro caos e ruído aleatório.
    Por que: Senhas baseadas em SEED garantem que a EXATA mesma senha gerará 
    a EXATA mesma matriz de ruído no futuro, permitindo a descriptografia.
    Se o usuário errar um único número da senha, a matemática gerará um caos
    completamente diferente, tornando a imagem irrecuperável!
    """
    # 1. Transformamos a string da senha num número inteiro que será a Semente
    seed_inteira = int(senha_str)
    
    # 2. Injetamos a Semente na biblioteca 'random' do Python.
    # O random do Python é "pseudo-aleatório". Ou seja, ele parece caos, mas é determinístico.
    random.seed(seed_inteira)
    
    # 3. Construímos a matriz gigante de 256x256 pixels
    matriz = []
    for y in range(altura):
        linha = []
        for x in range(largura):
            # Sorteamos um número aleatório gigantesco (entre -1 Milhão e +1 Milhão)
            # para servir de ruído. Como a Seed foi configurada, esse sorteio será SEMPRE
            # igual se a senha for igual
            ruido = random.randint(-1000000, 1000000)
            linha.append(ruido)
        matriz.append(linha)
        
    return matriz

def add_password_to_fft(matriz_fft, matriz_senha):
    """
    Função: add_password_to_fft(matriz_fft, matriz_senha)
    Objetivo: Aplica a criptografia efetiva! Mistura a matriz caótica gerada pela senha 
    com as frequências da imagem.
    """
    altura = len(matriz_fft)
    largura = len(matriz_fft[0])
    resultado = []
    
    for y in range(altura):
        nova_linha = [] 
        for x in range(largura):
            valor_fft = matriz_fft[y][x]
            # Como a nossa matriz de senha agora é puro caos 2D gerado por Seed,
            # não precisamos mais de fórmulas matemáticas para espalhar o ruído.
            valor_senha = matriz_senha[y][x]
            
            # Somamos o caos da senha tanto na parte Real quanto na Imaginária
            # para destruir completamente qualquer padrão identificável 
            novo_valor = complex(valor_fft.real + valor_senha, valor_fft.imag + valor_senha)
            nova_linha.append(novo_valor)
            
        resultado.append(nova_linha)
        
    return resultado

def sub_password_from_fft(matriz_criptografada, matriz_senha):
    """
    Função: sub_password_from_fft(matriz_criptografada, matriz_senha)
    Objetivo: Remover a fechadura criptográfica usando a Seed correta.
    """
    altura = len(matriz_criptografada)
    largura = len(matriz_criptografada[0])
    resultado = []
    
    for y in range(altura):
        nova_linha = []
        for x in range(largura):
            valor_cripto = matriz_criptografada[y][x]
            # O gerador de senhas reconstruiu a EXATA matriz de caos se a senha estiver certa.
            valor_senha = matriz_senha[y][x]
            
            # Subtraímos o ruído aleatório.
            # Se a senha for a correta, a matriz será subtraída perfeitamente, anulando o caos.
            # subtração de matrizes diferentes apenas adicionará MAIS ruído à imagem, destruindo-a.
            novo_valor = complex(valor_cripto.real - valor_senha, valor_cripto.imag - valor_senha)
            nova_linha.append(novo_valor)
            
        resultado.append(nova_linha)
        
    return resultado
