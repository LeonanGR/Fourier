import sys
import os

# Importando o módulo que cuida das funções de arquivos (ler/salvar, foto e texto)
from image_module import load_original_image, save_encrypted_txt, load_encrypted_txt, save_decrypted_image
# Importando o módulo do cálculo matemático pesado
from fft_module import fft2d, ifft2d
# Importando o módulo das leis do sistema e da matemática da nossa chave de segurança
from matrix_module import validate_password, generate_password_matrix, add_password_to_fft, sub_password_from_fft

def print_menu():
    """
    Função: print_menu()
    Objetivo: Mostrar a arte ASCII e o cabeçalho no console do sistema operacional.
    Por que: Sistemas CLI (Command Line Interfaces) precisam orientar a escolha do usuário.
    """
    print("=" * 60)
    print("       SISTEMA DE CRIPTOGRAFIA POR FFT (256x256)       ")
    print("=" * 60)
    print(" 1. Criptografar uma Imagem")
    print(" 2. Descriptografar uma Imagem")
    print(" 3. Sair")
    print("=" * 60)

def get_password():
    """
    Função: get_password()
    Objetivo: Aprisionar o usuário num loop infinito até que ele passe uma senha válida.
    Por que: Garantir que não entre lixo matemático no sistema que poderia dar crash.
    """
    # Loop 'While True' dura para sempre, a não ser que ache o comando 'return' ou 'break'
    while True:
        # Pede e captura a string escrita no terminal
        pwd = input("Digite a senha numérica (par, máx 8 dígitos): ")
        
        # Joga a senha no crivo de testes de regras (validações)
        valido, mensagem = validate_password(pwd)
        
        # Se 'valido' for True, ele obedeceu as regras e nós o deixamos sair do loop devolvendo a senha (return pwd)
        if valido:
            return pwd
        # Se não, printamos o erro exato e ele é forçado a tentar novamente.
        else:
            print(f"[ERRO] {mensagem}")

def encrypt_flow():
    """
    Função: encrypt_flow()
    Objetivo: O maestro que rege todo o passo a passo da Criptografia (Lê imagem -> FFT -> Senha -> Salva TXT)
    """
    # Pede o nome do arquivo que vai sofrer a criptografia
    # '.strip()' arranca os espaços sem querer gerados antes ou depois da string pelo usuário
    in_path = input("Caminho da imagem original (ex: original.png): ").strip()
    
    # Prevenção: O sistema quebra se tentarmos abrir um fantasma.
    if not os.path.exists(in_path):
        print("[ERRO] O arquivo especificado não existe!")
        return

    # Um bloco try/except protege o sistema. Se um erro grave ou fatal acontecer nas profundezas
    # da matemática, o sistema todo não quebra nem fecha, o except pega o erro e traduz pra tela amigavelmente.
    try:
        print("\n[*] Carregando imagem colorida e validando as dimensões (256x256)...")
        # 1. Abre a foto colorida convertendo para um vetor 3D RGB (Três canais)
        canais_imagem = load_original_image(in_path)

        # 2. Requisita e captura a senha do dono e chama a rotina que a 
        #    transforma naquela gigantesca Máscara 256x256 de pura repetição
        pwd = get_password()
        pwd_matrix = generate_password_matrix(pwd)

        print("[*] Criptografando canais (R, G, B) usando FFT...")
        print("    (Isso pode levar alguns segundos, por favor aguarde)")
        
        # Lista onde iremos colocar os canais processados da FFT 
        canais_cripto = []
        
        # Enumerate pega a lista 'canais_imagem' e para cada rodada ele cospe duas coisas:
        # 'i': o número da rodada atual (0, 1, 2...)
        # 'canal': o pacote de dados atual daquele ciclo
        for i, canal in enumerate(canais_imagem):
            # Usando uma lista rápida de nomes para printar exatamente qual cor está carregando
            nome_canal = ["Vermelho", "Verde", "Azul"][i]
            print(f"    -> Processando canal {nome_canal}...")
            
            # MATEMÁTICA PURA: 
            # A Transformada Rápida de Fourier desmonta o que era "Brilho e Cor" num determinado pedaço
            # da foto (Domínio do Tempo/Espaço) e mapeia nas ondas de senos e cossenos que geraram esse brilho (Frequência).
            fft_matrix = fft2d(canal)
            
            # Criptografia Visual no Domínio Incompreensível: 
            # A gente pega aquela frequência matemática e polui ela com as matrizes das senhas.
            encrypted_fft = add_password_to_fft(fft_matrix, pwd_matrix)
            
            # Salva a matriz de frequência já embaralhada e corrompida (Pela senha)
            canais_cripto.append(encrypted_fft)

        # A fase de salvar 
        out_name = input("\nNome do arquivo final criptografado (ex: cripto.txt): ").strip()
        
        # Caso o dono seja apressado e dê 'ENTER' de tela vazia, forçamos um nome padrão!
        if not out_name:
            out_name = "cripto.txt"
            
        # Esse processo fatiador da 'os.path' garante duas coisas maravilhosas:
        # Se o usuário digitou "foto.jpg", nós amputamos o jpg e forçamos ".txt", garantindo segurança.
        nome_arquivo = os.path.basename(out_name)
        nome_sem_ext, ext = os.path.splitext(nome_arquivo)
        nome_arquivo = nome_sem_ext + ".txt"
        
        # Forçar o salvamento na MESMA pasta em que o script Python (esse arquivo main.py) está
        projeto_dir = os.path.dirname(os.path.abspath(__file__))
        out_path = os.path.join(projeto_dir, nome_arquivo)

        print(f"[*] Salvando as matrizes complexas puras no formato TXT em:\n    -> {out_path}")
        
        # Escrevendo no disco rígido usando nossa função pesada criada
        save_encrypted_txt(canais_cripto, out_path)
        
        print("\n[SUCESSO] Operação finalizada com maestria! Arquivo TXT criptografado salvo na pasta do projeto!")
    except Exception as e:
        print(f"\n[ERRO CRÍTICO] Falha durante a criptografia: {e}")

def decrypt_flow():
    """
    Função: decrypt_flow()
    Objetivo: O fluxo que inverte as Leis (Lê TXT -> Subtrai Senha -> IFFT -> Salva Imagem)
    """
    in_path = input("Caminho do arquivo TXT criptografado (ex: cripto.txt): ").strip()
    
    # Se o texto ou os diretórios apontarem para o Vazio
    if not os.path.exists(in_path):
        print("[ERRO] Arquivo não encontrado!")
        return

    try:
        print("\n[*] Lendo matrizes complexas do arquivo TXT...")
        # 1. Reconstrói os imensos dados de ponto flutuante originais.
        # Nós já caímos de cabeça, com as variáveis agora dentro do "Mundo da Frequência".
        canais_cripto = load_encrypted_txt(in_path)

        # 2. Pede e recria o Labirinto com a senha do Desbravador
        pwd = get_password()
        pwd_matrix = generate_password_matrix(pwd)

        print("[*] Descriptografando canais (R, G, B) usando IFFT...")
        print("    (Calculando, por favor aguarde alguns segundos)")
        
        canais_decripto = []
        for i, canal in enumerate(canais_cripto):
            nome_canal = ["Vermelho", "Verde", "Azul"][i]
            print(f"    -> Processando canal {nome_canal}...")
            
            # MATEMÁTICA PURA DA DESCRIPTOGRAFIA:
            # Como a nossa entrada 'canal' LIDA DAQUELE TXT já é uma Transformada de Fourier,
            # nós só precisamos arrancar o vírus imposto nela com a Subtração, liberando
            # as frequências imaculadas originais.
            decrypted_fft = sub_password_from_fft(canal, pwd_matrix)
            
            # IFFT: Agora sim, com a frequência limpa da senha, pedimos a ferramenta IFFT
            # para fazer o "Reverse Engineering" transformando as ondas na matriz que compõe nossa
            # querida Imagem 2D Espacial Real.
            decripto_espacial = ifft2d(decrypted_fft)
            
            # Matrizes finalmente guardadas
            canais_decripto.append(decripto_espacial)

        out_name = input("\nNome da imagem recuperada (ex: decripto.png): ").strip()
        
        # Garante nome e formatação
        if not out_name:
            out_name = "decripto.png"
            
        nome_arquivo = os.path.basename(out_name)
        nome_sem_ext, ext = os.path.splitext(nome_arquivo)
        nome_arquivo = nome_sem_ext + ".png"
        
        projeto_dir = os.path.dirname(os.path.abspath(__file__))
        out_path = os.path.join(projeto_dir, nome_arquivo)

        print(f"[*] Remontando pixels coloridos originais e salvando em:\n    -> {out_path}")
        
        # 3. Empacota todas as grandezas, normaliza tudo, espeta a extensão e cospe como foto
        save_decrypted_image(canais_decripto, out_path)
        
        print("\n[SUCESSO] A imagem foi restaurada e salva com sucesso!")
    except Exception as e:
        print(f"\n[ERRO CRÍTICO] Falha na descriptografia. Senha incorreta ou arquivo modificado?\nDetalhe: {e}")

def main():
    """
    Função: main()
    Objetivo: Ser o elo principal entre o Computador (CLI) e o Programa.
    Ela que comanda a máquina de estados base (o Menu) até que a ordem de sair chegue.
    """
    while True:
        print_menu()
        opcao = input("Selecione sua escolha (1/2/3): ").strip()
        
        if opcao == '1':
            encrypt_flow()
        elif opcao == '2':
            decrypt_flow()
        elif opcao == '3':
            print("Encerrando o programa. Até logo!")
            break
        else:
            print("[AVISO] Opção inválida, tente novamente.")

# O "idioma místico" do Python que avisa para a máquina que, SE ela invocar ou abrir  
# esse arquivo 'main.py' pelo CMD, ela deve disparar a função main() que programamos ali em cima.
if __name__ == "__main__":
    main()
