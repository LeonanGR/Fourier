<h1 align="center">
  <img src="https://img.shields.io/badge/Fourier-Cipher-58a6ff?style=for-the-badge&logo=python&logoColor=white" alt="Fourier Cipher"/>
</h1>

<p align="center">
  <b>Criptografia de áudio e imagem via Transformada de Fourier — FFT Cooley-Tukey implementada do zero em Python puro.</b>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python"/>
  <img src="https://img.shields.io/badge/GUI-CustomTkinter-blueviolet?style=flat-square"/>
  <img src="https://img.shields.io/badge/FFT-Cooley--Tukey-orange?style=flat-square"/>
  <img src="https://img.shields.io/badge/licença-MIT-green?style=flat-square"/>
</p>

---

## ✨ O que é o Fourier Cipher?

O **Fourier Cipher** é uma ferramenta que combina **criptografia** de áudio e imagens, utilizando a **Transformada Rápida de Fourier (FFT)** como base matemática.

O projeto possui **dois módulos principais**, acessíveis diretamente pela interface gráfica:

| Aba | Descrição |
|---|---|
| 🎵 **Áudio** | Cifra/decifra arquivos WAV por perturbação de fase 1D no domínio da frequência |
| 🖼 **Imagem** | Cifra/decifra imagens PNG/JPG/BMP por perturbação de fase 2D (FFT 2D por canal RGB) |

> 🔬 **Diferencial acadêmico:** toda a matemática (FFT, IFFT, seno, cosseno, π, √, atan2) foi implementada **do zero em Python puro**, sem usar `math`, `cmath` ou `numpy` para os cálculos internos.

---

## 🧠 Como funciona?

### Algoritmo de Criptografia (Áudio e Imagem)

```
Arquivo de entrada
       │
       ▼
  [1] Normalização (PCM-16 ou RGB → complexos)
       │
       ▼
  [2] FFT (1D para áudio / 2D para imagem)
       │
       ▼
  [3] Geração da Matriz-Chave da Senha (via seed → FFT)
       │
       ▼
  [4] Soma Matricial no Domínio da Frequência (cifrar: X + K / decifrar: X − K)
       │
       ▼
  [5] IFFT → retorna ao domínio do tempo/espaço
       │
       ▼
  Arquivo cifrado (visualmente/auditivamente caótico)
```

---

## 🗂 Módulos do Projeto

| Componente | Descrição |
|---|---|
| `math_engine.py` | π (fórmula de Machin), sin/cos (Taylor), √ (Newton-Raphson), atan2 — **zero imports de math** |
| `fft_engine.py` | FFT 1D e 2D iterativa (Radix-2 DIT, bit-reversal, twiddle factors pré-computados) |
| `key_engine.py` | Gera a matriz-chave da senha usando `random.seed(senha)` → FFT |
| `audio_cipher.py` | Aplica FFT 1D + soma/subtração da chave por canal |
| `image_cipher.py` | Aplica FFT 2D + soma/subtração da chave por canal RGB |
| `gui/interface.py` | App principal: abas Áudio e Imagem (CustomTkinter) |

---

## 🗂 Estrutura do Projeto

```
Fourier/
└── fourier_cipher/
    ├── main.py                    ← Ponto de entrada (GUI ou CLI)
    ├── install_deps.py            ← Instalador automático de dependências
    ├── requirements.txt           ← Dependências
    ├── core/
    │   ├── math_engine.py         ← Matemática do zero (π, sin, cos, √, atan2)
    │   ├── fft_engine.py          ← FFT/IFFT 1D e 2D (Cooley-Tukey)
    │   ├── key_engine.py          ← Geração de matriz-chave
    │   ├── audio_cipher.py        ← Cifra/decifra áudio WAV
    │   └── image_cipher.py        ← Cifra/decifra imagens RGB
    ├── gui/
    │   └── interface.py           ← Interface gráfica (App + abas Áudio/Imagem)
    ├── io_handlers/
    │   ├── audio_io.py            ← Leitura/escrita de áudio (legado/auxiliar)
    │   └── image_io.py            ← Leitura/escrita de imagens (legado/auxiliar)
    └── logs/
        └── fourier_cipher.log
```

---

## 🚀 Instalação

### Pré-requisitos
- Python **3.10 ou superior**
- pip

### 1. Clone o repositório

```bash
git clone https://github.com/LeonanGR/Fourier.git
cd Fourier/fourier_cipher
```

### 2. Instale as dependências

**Opção A — pip direto:**
```bash
pip install -r requirements.txt
```

As dependências são:

| Pacote | Uso |
|---|---|
| `customtkinter` | Interface gráfica moderna (dark mode) |
| `Pillow` | Leitura, exibição e escrita de imagens |
| `soundfile` | Leitura e escrita de áudio WAV (usado em scripts auxiliares de I/O) |
| `numpy` | Operações de array no módulo I/O auxiliar |

---

## 🖥 Uso — Interface Gráfica (GUI)

```bash
cd fourier_cipher
python main.py
```

A janela abre com **duas abas**:

---

### 🎵 Aba de Áudio — Criptografia

1. Clique em **`...`** e selecione um arquivo `.wav`
2. (Opcional) Defina o arquivo de saída — gerado automaticamente como `nome_enc.wav` / `nome_dec.wav`
3. Digite a **senha/chave** (clique em 👁 para revelar)
4. Selecione **Criptografar** ou **Descriptografar**
5. Clique em **EXECUTAR** e acompanhe o log

---

### 🖼 Aba de Imagem — Criptografia

1. Selecione uma imagem de entrada (`.png`, `.jpg`, `.bmp`)
2. (Opcional) Defina o arquivo de saída (salvo como `.png`)
3. Digite a senha
4. Selecione **Criptografar** ou **Descriptografar**
5. Clique em **EXECUTAR** — preview da imagem resultante aparece ao terminar

> ⚠ **Imagens grandes (> 256×256 px) podem demorar vários minutos** pois a FFT 2D é implementada em Python puro. Recomenda-se imagens pequenas.

---

## ⌨ Uso — Linha de Comando (CLI)

```bash
cd fourier_cipher
python main.py --mode <encrypt|decrypt> --type <audio|image> -i <arquivo> -k <senha> [-o <saída>]
```

### Argumentos

| Argumento | Obrigatório | Descrição |
|---|---|---|
| `--mode` | ✅ | `encrypt` ou `decrypt` |
| `--type` | ✅ | `audio` ou `image` |
| `-i` / `--input` | ✅ | Caminho do arquivo de entrada |
| `-k` / `--key` | ✅ | Senha/chave de criptografia |
| `-o` / `--output` | ❌ | Caminho de saída (gerado automaticamente se omitido) |

### Exemplos

```bash
# Criptografar um áudio
python main.py --mode encrypt --type audio -i musica.wav -k "minha_senha"
# → gera musica_enc.wav

# Descriptografar o áudio
python main.py --mode decrypt --type audio -i musica_enc.wav -k "minha_senha"

# Criptografar uma imagem
python main.py --mode encrypt --type image -i foto.png -k "chave_secreta"
# → gera foto_enc.png

# Descriptografar a imagem
python main.py --mode decrypt --type image -i foto_enc.png -k "chave_secreta"

# Definir saída manualmente
python main.py --mode encrypt --type audio -i a.wav -k "senha" -o saida.wav
```

---

## 🔄 Garantia de Reversibilidade

O cifrador é **perfeitamente reversível**: ao descriptografar com a mesma senha, o arquivo original é recuperado sem perda de dados.

- **Áudio**: usa aritmética modular 65536 (PCM-16) — sem clipping
- **Imagem**: usa aritmética modular 256 (8 bits por canal) — sem overflow

> ⚠ **Importante:** use a **mesma senha** para cifrar e decifrar. Senhas diferentes geram saídas incorretas.

---

## 🔬 Detalhes Técnicos

### FFT Cooley-Tukey (Radix-2 DIT)

- Implementação **iterativa** com bit-reversal permutation (sem recursão)
- **Twiddle factors pré-computados** e cacheados por tamanho N
- **Zero-padding** automático para a próxima potência de 2
- IFFT via conjugação: `ifft(X) = (1/N) · conj(fft(conj(X)))`
- FFT 2D por separabilidade: FFT nas linhas → transpõe → FFT nas colunas

### Matemática Pura (sem `import math`)

| Função | Método |
|---|---|
| π | Fórmula de Machin: `π = 16·arctan(1/5) − 4·arctan(1/239)` |
| sin(x) / cos(x) | Série de Taylor com normalização em `[−π, π]` |
| sincos(x) | Calcula sin e cos simultaneamente (-50% de operações) |
| √x | Newton-Raphson (12 iterações, convergência quadrática) |
| atan2(y, x) | Série de arctan com ajuste de quadrante |

---

## 📄 Licença

Este projeto está licenciado sob a **MIT License** — sinta-se livre para usar, modificar e distribuir.

---

## 👥 Créditos

<table align="center">
  <tr>
    <td align="center">
      <a href="https://github.com/LeonanGR">
        <img src="https://github.com/LeonanGR.png" width="80" style="border-radius:50%"/><br/>
        <b>LeonanGR</b>
      </a><br/>
    </td>
    <td align="center">
      <a href="https://github.com/jaozin30718">
        <img src="https://github.com/jaozin30718.png" width="80" style="border-radius:50%"/><br/>
        <b>jaozin30718</b>
      </a><br/>
    </td>
  </tr>
</table>

<p align="center">
  Feito com 🧮 e Python puro
</p>
