from PIL import Image

def load_original_image(caminho):
    """
    Função: load_original_image(caminho)
    Objetivo: Lê a imagem colorida no disco e a transforma em formato matemático.
    Por que: A matemática da FFT exige números complexos, mas arquivos de imagem 
    fornecem apenas pixels (inteiros de 0 a 255).
    """
    try:
        # A biblioteca PIL (Pillow) serve apenas para nos ajudar a abrir a foto.
        # O '.convert('RGB')' garante que a imagem seja processada colorida (Vermelho, Verde e Azul).
        img = Image.open(caminho).convert('RGB')
    except Exception as e:
        # Se o usuário errar o nome ou o arquivo estiver corrompido, bloqueamos e avisamos.
        raise ValueError(f"Não foi possível abrir a imagem: {e}")

    # Extraímos a largura e altura em pixels da imagem lida
    largura, altura = img.size
    
    # Validação Restrita do Usuário: O sistema foi projetado para NÃO aceitar 
    # resoluções maiores ou menores que 256x256, visando segurança e performance do código manual.
    if largura != 256 or altura != 256:
        raise ValueError(f"A imagem deve ter EXATAMENTE 256x256 pixels. O arquivo tem: {largura}x{altura}")
        
    # 'load()' nos dá acesso direto a ler/modificar os pixels numa matriz rápida.
    pixels = img.load()
    
    # Criamos três listas separadas vazias. 
    # Cada uma vai segurar 100% da informação de uma cor (Canais R, G e B).
    matriz_r = [] # Canal Vermelho (Red)
    matriz_g = [] # Canal Verde (Green)
    matriz_b = [] # Canal Azul (Blue)
    
    # Loop de varredura bidimensional clássico (Passando por cada altura Y e cada largura X)
    for y in range(altura):
        # Cada linha nova no Y precisa de uma lista vazia correspondente aos canais
        linha_r = []
        linha_g = []
        linha_b = []
        
        for x in range(largura):
            # Lemos a cor RGB naquele pixel exato (ex: (255, 0, 100))
            r, g, b = pixels[x, y]
            
            # TRUQUE MATEMÁTICO: A função nativa `complex(real, imaginário)` 
            # transforma nossa cor (255) em um número complexo (255 + 0i).
            # Por que? Porque a FFT só pode ser alimentada por números complexos.
            linha_r.append(complex(r, 0))
            linha_g.append(complex(g, 0))
            linha_b.append(complex(b, 0))
            
        # Após ler todos os X daquela linha, empurramos as linhas prontas para suas matrizes mestre
        matriz_r.append(linha_r)
        matriz_g.append(linha_g)
        matriz_b.append(linha_b)
        
    # Retornamos as 3 matrizes empacotadas numa única lista
    return [matriz_r, matriz_g, matriz_b]

def save_encrypted_txt(canais_complexos, caminho):
    """
    Função: save_encrypted_txt(canais_complexos, caminho)
    Objetivo: Guardar as matrizes puras e gigantescas da FFT no disco rígido sem compactação (100% precisas).
    Por que: Salvar direto como "imagem .png" cortaria as casas decimais (só suporta 0 a 255),
    o que destruiria a parte matemática da criptografia impossibilitando a reversão.
    """
    # Desempacota a lista nas 3 matrizes referentes às 3 cores
    matriz_r, matriz_g, matriz_b = canais_complexos
    
    # Abre ou cria o arquivo de texto (.txt) em modo de gravação ('w' de write)
    with open(caminho, 'w') as f:
        # Loop sequencial: primeiro salva todo o Vermelho, depois todo o Verde, depois o Azul.
        for matriz in [matriz_r, matriz_g, matriz_b]:
            for y in range(256):
                # Guarda as strings de texto que compõem a linha
                linha_str = []
                for x in range(256):
                    # Pega o número complexo armazenado no processo
                    valor = matriz[y][x]
                    
                    # Formata em texto na estrutura matemática padrão: "Real,Imaginário".
                    # Exemplo de saída: "125000.123456,-504.654321".
                    # Os '.6f' forçam a exibir até 6 casas após a vírgula. Isso previne perdas.
                    linha_str.append(f"{valor.real:.6f},{valor.imag:.6f}")
                    
                # Une todos os números de uma linha do X separados por "espaço" (join)
                # e adiciona uma quebra de linha real "\n" (Enter) no arquivo TXT.
                f.write(" ".join(linha_str) + "\n")

def load_encrypted_txt(caminho):
    """
    Função: load_encrypted_txt(caminho)
    Objetivo: Ler o TXT gigante da criptografia e reconstruir os números para a memória viva (RAM).
    Por que: A IFFT precisa dos dados exatamente na mesma casa decimal que pararam na hora de criptografar.
    """
    # Abre o TXT em modo leitura ('r' de read) e extrai todas as linhas de texto para uma lista.
    with open(caminho, 'r') as f:
        linhas = f.readlines()
        
    # Validação de integridade: Como a imagem é 256x256 e temos 3 cores...
    # Esperamos que o arquivo de texto tenha obrigatoriamente 256 * 3 = 768 linhas completas.
    if len(linhas) != 256 * 3:
        raise ValueError("O arquivo TXT está corrompido ou tem o tamanho errado. Ele deve ter 768 linhas (256 por canal RGB).")
        
    # Função auxiliar criada dentro da principal (closure) apenas para poupar digitação redundante
    def converter_bloco_para_matriz(bloco_linhas):
        matriz = []
        for linha in bloco_linhas:
            # O .strip() tira os pulos de linha e espaços das bordas, e o .split(" ")
            # quebra a linha imensa de texto gerando uma listinha de pedaços ["1,2", "3,4"...]
            elementos = linha.strip().split(" ")
            linha_complexa = []
            
            for el in elementos:
                # Agora o split(',') separa "Real,Imaginário" para variáveis independentes usando string
                real_str, imag_str = el.split(",")
                # O float() converte o texto para matemática e a função complex() finaliza a mágica
                linha_complexa.append(complex(float(real_str), float(imag_str)))
                
            matriz.append(linha_complexa)
        return matriz
        
    # Dividimos o arquivo TXT gigante baseados na ordem exata de escrita:
    # Do começo ao 256 é R. Da linha 256 ao 512 é G. Da linha 512 ao 768 é B.
    matriz_r = converter_bloco_para_matriz(linhas[0:256])
    matriz_g = converter_bloco_para_matriz(linhas[256:512])
    matriz_b = converter_bloco_para_matriz(linhas[512:768])
    
    # Entrega os dados empacotados, prontos para a matemática da Inversa (IFFT)
    return [matriz_r, matriz_g, matriz_b]

def save_decrypted_image(canais_complexos, caminho):
    """
    Função: save_decrypted_image(canais_complexos, caminho)
    Objetivo: Finalizar o programa, devolvendo a matriz complexa de volta à vida na forma
    de uma imagem visível, bela e colorida, que pode ser mandada para redes sociais!
    Por que: Os canais que chegam aqui são a Inversa da Transformada (IFFT), eles devem 
    virar pixels de 0 a 255.
    """
    # Desempacota
    matriz_r, matriz_g, matriz_b = canais_complexos
    
    # Criamos uma imagem 100% preta de tamanho 256x256 no formato Colorido (RGB) para receber os dados
    img = Image.new('RGB', (256, 256))
    pixels = img.load()
    
    # Loop duplo para percorrer tela inteira
    for y in range(256):
        for x in range(256):
            # abs() é a função absoluta (Magnitude). 
            # A IFFT gera pequenos "ruídos imaginários" por causa do arredondamento do ponto flutuante do PC.
            # abs() limpa esses ruídos e converte o complexo em um inteiro confiável!
            r = int(round(abs(matriz_r[y][x])))
            g = int(round(abs(matriz_g[y][x])))
            b = int(round(abs(matriz_b[y][x])))
            
            # max(0, min(255, valor)) é a técnica de "Clipping"
            # Se a cor explodir pra 258 ou afundar pra -10, esse código obriga a ficar dentro do limite das cores
            # suportadas pelo computador moderno.
            pixels[x, y] = (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
            
    # Ao final da pintura, gravamos a imagem nova na pasta destino apontada pelo usuário!
    img.save(caminho)
