import sys
import subprocess

def install_requirements():
    print("=== Instalador de Dependencias para Fourier Cipher ===")
    dependencies = ["customtkinter", "Pillow", "soundfile", "numpy"]
    
    print("\n[•] Verificando e instalando dependencias...")
    
    for dep in dependencies:
        try:
            if dep == "Pillow":
                import PIL
            else:
                __import__(dep)
            print(f"[✓] {dep} ja esta instalado.")
        except ImportError:
            print(f"[!] {dep} nao encontrado. Instalando...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
                print(f"[✓] {dep} instalado com sucesso!")
            except Exception as e:
                print(f"[✗] Erro ao instalar {dep}: {e}")
                
    print("\n[✓] Processo concluido! Agora voce pode rodar o programa com:")
    print("    python main.py")

if __name__ == "__main__":
    install_requirements()
