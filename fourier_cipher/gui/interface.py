# =============================================================================
# GUI — CustomTkinter + Pillow
# Pillow é usado exclusivamente para I/O e exibição de imagens.
# soundfile é usado para I/O de áudio (leitura/escrita WAV/FLAC/OGG).
# Toda a matemática vive nos módulos core/.
#
# OTIMIZAÇÕES:
#   - Imports limpos (sem __import__ inline)
#   - ProcessPoolExecutor para paralelizar os 3 canais RGB (~3x mais rápido)
#   - logging para log persistente em arquivo
# =============================================================================

import customtkinter as ctk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import soundfile as sf
import numpy as np
import array as _array
import threading
import logging
import os
from concurrent.futures import ProcessPoolExecutor, as_completed

from core.audio_cipher import cipher_audio
from core.image_cipher import cipher_channel
from gui.reconstruct_tab import ReconstructTab

# -----------------------------------------------------------------------------
# LOGGING — Log persistente em arquivo + console
# -----------------------------------------------------------------------------
_log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'logs')
os.makedirs(_log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(_log_dir, 'fourier_cipher.log'),
                            encoding='utf-8'),
    ]
)
_logger = logging.getLogger('fourier_cipher')

# -----------------------------------------------------------------------------
# APARÊNCIA
# -----------------------------------------------------------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

FONT_MONO = ("Consolas", 12)
FONT_BOLD = ("Consolas", 13, "bold")
FONT_HEAD = ("Consolas", 15, "bold")


# =============================================================================
# UTILITÁRIOS DE I/O
# =============================================================================

def load_audio(path: str) -> tuple:
    """Lê WAV com soundfile. Retorna (samples_por_canal, samplerate, subtype)."""
    data, sr = sf.read(path, dtype='int16', always_2d=True)
    subtype  = sf.info(path).subtype
    # data shape: (frames, channels) → lista de canais
    channels = [data[:, ch].tolist() for ch in range(data.shape[1])]
    return channels, sr, subtype


def save_audio(path: str, channels: list, sr: int) -> None:
    """Escreve WAV com soundfile."""
    n_ch    = len(channels)
    frames  = len(channels[0])
    # Intercala canais: [ch0_s0, ch1_s0, ch0_s1, ...]
    flat = []
    for i in range(frames):
        for ch in channels:
            flat.append(ch[i])
    data = _array.array('h', flat)
    sf.write(path,
             np.frombuffer(data, dtype='int16').reshape(frames, n_ch),
             sr, subtype='PCM_16')


def load_image(path: str) -> tuple:
    """
    Carrega imagem com Pillow.
    Retorna (canais, largura, altura) e também lê metadados de tamanho original
    embutidos pelo cifrador (chave 'fc_orig_size').
    Retorna: ([r, g, b], w, h, orig_w_or_None, orig_h_or_None)
    """
    img = Image.open(path).convert('RGB')
    w, h = img.size

    # Tenta ler metadado de tamanho original embutido ao cifrar
    orig_w, orig_h = None, None
    try:
        meta = img.info
        if 'fc_orig_size' in meta:
            ow, oh = meta['fc_orig_size'].split(',')
            orig_w, orig_h = int(ow), int(oh)
    except Exception:
        pass

    pixels = list(img.getdata())
    r = [[pixels[row*w + col][0] for col in range(w)] for row in range(h)]
    g = [[pixels[row*w + col][1] for col in range(w)] for row in range(h)]
    b = [[pixels[row*w + col][2] for col in range(w)] for row in range(h)]
    return [r, g, b], w, h, orig_w, orig_h


def save_image(path: str, channels: list, w: int, h: int,
               orig_w: int = None, orig_h: int = None) -> None:
    """
    Salva imagem RGB com Pillow.
    Se orig_w/orig_h forem fornecidos, embutidos como metadado no PNG
    para que o decifrador saiba o tamanho original antes da criptografia.
    """
    img = Image.new('RGB', (w, h))
    pixels = []
    for row in range(h):
        for col in range(w):
            pixels.append((channels[0][row][col],
                           channels[1][row][col],
                           channels[2][row][col]))
    img.putdata(pixels)

    if orig_w is not None and orig_h is not None and path.lower().endswith('.png'):
        from PIL.PngImagePlugin import PngInfo
        meta = PngInfo()
        meta.add_text('fc_orig_size', f'{orig_w},{orig_h}')
        img.save(path, pnginfo=meta)
    else:
        img.save(path)


# =============================================================================
# WORKER PARA PROCESSAMENTO PARALELO DE CANAIS
# =============================================================================

def _cipher_channel_worker(args):
    """Wrapper para cipher_channel que aceita args como tupla (pickle-friendly)."""
    channel, password, decrypt, salt, orig_size = args
    return cipher_channel(channel, password, decrypt=decrypt, salt=salt,
                          orig_size=orig_size)


# =============================================================================
# COMPONENTES REUTILIZÁVEIS
# =============================================================================

class LogBox(ctk.CTkTextbox):
    """Painel de log com scroll automático."""
    def __init__(self, master, **kw):
        super().__init__(master, state="disabled",
                         font=("Consolas", 11), **kw)

    def write(self, msg: str, tag: str = "INFO") -> None:
        label = {"INFO": "•", "OK": "✓", "ERR": "✗", "WARN": "⚠"}.get(tag, "•")
        self.configure(state="normal")
        self.insert("end", f"[{label}] {msg}\n")
        self.see("end")
        self.configure(state="disabled")
        # Também envia para o logger persistente
        log_level = {"INFO": logging.INFO, "OK": logging.INFO,
                     "ERR": logging.ERROR, "WARN": logging.WARNING}.get(tag, logging.INFO)
        _logger.log(log_level, msg)


class PasswordField(ctk.CTkFrame):
    """Campo de senha com botão de visibilidade."""
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        ctk.CTkLabel(self, text="Senha / Chave:", font=FONT_MONO).pack(anchor="w")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")
        self._var     = ctk.StringVar()
        self._visible = False
        self._entry   = ctk.CTkEntry(row, textvariable=self._var,
                                     show="•", font=FONT_MONO)
        self._entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="👁", width=36,
                      command=self._toggle).pack(side="left", padx=(6,0))

    def _toggle(self):
        self._visible = not self._visible
        self._entry.configure(show="" if self._visible else "•")

    def get(self) -> str:
        return self._var.get()


class ModeToggle(ctk.CTkFrame):
    """Seletor Criptografar / Descriptografar."""
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._var = ctk.StringVar(value="encrypt")
        ctk.CTkLabel(self, text="Operação:", font=FONT_MONO).pack(anchor="w")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(anchor="w")
        ctk.CTkRadioButton(row, text="Criptografar",
                           variable=self._var, value="encrypt",
                           font=FONT_MONO).pack(side="left", padx=(0,20))
        ctk.CTkRadioButton(row, text="Descriptografar",
                           variable=self._var, value="decrypt",
                           font=FONT_MONO).pack(side="left")

    def get(self) -> str:
        return self._var.get()


class FileRow(ctk.CTkFrame):
    """Linha de seleção de arquivo (entrada ou saída)."""
    def __init__(self, master, label: str, types: list,
                 save: bool = False, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self._types = types
        self._save  = save
        self._var   = ctk.StringVar()
        ctk.CTkLabel(self, text=label, font=FONT_MONO).pack(anchor="w")
        row = ctk.CTkFrame(self, fg_color="transparent")
        row.pack(fill="x")
        ctk.CTkEntry(row, textvariable=self._var,
                     font=FONT_MONO).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(row, text="...", width=40,
                      command=self._browse).pack(side="left", padx=(6,0))

    def _browse(self):
        if self._save:
            p = filedialog.asksaveasfilename(filetypes=self._types,
                                             defaultextension=self._types[0][1])
        else:
            p = filedialog.askopenfilename(filetypes=self._types)
        if p:
            self._var.set(p)

    def get(self) -> str:
        return self._var.get()

    def set(self, v: str):
        self._var.set(v)


# =============================================================================
# ABA DE ÁUDIO
# =============================================================================

class AudioTab(ctk.CTkFrame):
    def __init__(self, master, log: LogBox, **kw):
        super().__init__(master, **kw)
        self.log = log
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="CIFRA DE ÁUDIO  —  Perturbação de Fase 1D",
                     font=FONT_HEAD).pack(pady=(18,10))

        self.f_in  = FileRow(self, "Arquivo de entrada (.wav):",
                             [("WAV","*.wav"),("Todos","*.*")])
        self.f_in.pack(fill="x", padx=20, pady=4)

        self.f_out = FileRow(self, "Arquivo de saída (.wav):",
                             [("WAV","*.wav")], save=True)
        self.f_out.pack(fill="x", padx=20, pady=4)

        self.pwd  = PasswordField(self)
        self.pwd.pack(fill="x", padx=20, pady=4)

        self.mode = ModeToggle(self)
        self.mode.pack(fill="x", padx=20, pady=4)

        self.bar = ctk.CTkProgressBar(self)
        self.bar.pack(fill="x", padx=20, pady=10)
        self.bar.set(0)

        self.btn = ctk.CTkButton(self, text="EXECUTAR",
                                  font=FONT_BOLD, height=42,
                                  command=self._run)
        self.btn.pack(padx=20, pady=(4,20))

    def _auto_out(self, path: str, mode: str) -> str:
        base, ext = os.path.splitext(path)
        tag = "_enc" if mode == "encrypt" else "_dec"
        return base + tag + (ext or ".wav")

    def _run(self):
        src = self.f_in.get()
        dst = self.f_out.get()
        pwd = self.pwd.get()
        mode= self.mode.get()

        if not src:
            messagebox.showwarning("Aviso", "Selecione o arquivo de entrada.")
            return
        if not pwd:
            messagebox.showwarning("Aviso", "Digite a chave.")
            return
        if not dst:
            dst = self._auto_out(src, mode)
            self.f_out.set(dst)
        elif not os.path.splitext(dst)[1]:
            dst += ".wav"
            self.f_out.set(dst)

        self.btn.configure(state="disabled", text="Processando…")
        self.bar.set(0.05)
        threading.Thread(target=self._process,
                         args=(src, dst, pwd, mode), daemon=True).start()

    def _process(self, src, dst, pwd, mode):
        try:
            self.log.write(f"Lendo: {os.path.basename(src)}")
            channels, sr, _ = load_audio(src)
            self.log.write(f"  {len(channels)} canal(is) · {sr} Hz · "
                           f"{len(channels[0])} amostras")

            out_channels = []
            for i, ch in enumerate(channels):
                self.log.write(f"  Canal {i+1}/{len(channels)} → FFT + rotação complexa…")
                out_channels.append(
                    cipher_audio(ch, pwd, decrypt=(mode=="decrypt")))
                self.bar.set(0.1 + 0.8 * (i+1) / len(channels))

            save_audio(dst, out_channels, sr)
            self.bar.set(1.0)
            self.log.write(f"Salvo em: {dst}", "OK")

        except Exception as e:
            self.log.write(str(e), "ERR")
            _logger.exception("Erro no processamento de áudio")
        finally:
            self.after(0, lambda: self.btn.configure(
                state="normal", text="EXECUTAR"))


# =============================================================================
# ABA DE IMAGEM
# =============================================================================

class ImageTab(ctk.CTkFrame):
    def __init__(self, master, log: LogBox, **kw):
        super().__init__(master, **kw)
        self.log = log
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="CIFRA DE IMAGEM  —  Perturbação de Fase 2D",
                     font=FONT_HEAD).pack(pady=(18,10))

        # Linha superior: controles + preview
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=20)

        # -- Coluna de controles --
        ctrl = ctk.CTkFrame(body, fg_color="transparent")
        ctrl.pack(side="left", fill="y")

        self.f_in  = FileRow(ctrl, "Imagem de entrada:",
                             [("Imagens","*.png *.jpg *.bmp"),("Todos","*.*")])
        self.f_in.pack(fill="x", pady=4)

        self.f_out = FileRow(ctrl, "Imagem de saída:",
                             [("PNG","*.png"),("BMP","*.bmp")], save=True)
        self.f_out.pack(fill="x", pady=4)

        self.pwd  = PasswordField(ctrl)
        self.pwd.pack(fill="x", pady=4)

        self.mode = ModeToggle(ctrl)
        self.mode.pack(fill="x", pady=4)

        ctk.CTkLabel(ctrl,
            text="⚠ Imagens grandes = FFT 2D lenta.\nRecomendado: ≤ 256×256.",
            font=("Consolas",10), text_color="orange").pack(anchor="w", pady=6)

        self.bar = ctk.CTkProgressBar(ctrl)
        self.bar.pack(fill="x", pady=6)
        self.bar.set(0)

        self.btn = ctk.CTkButton(ctrl, text="EXECUTAR",
                                  font=FONT_BOLD, height=42,
                                  command=self._run)
        self.btn.pack(pady=(4,10))

        # -- Coluna de preview --
        prev = ctk.CTkFrame(body)
        prev.pack(side="left", fill="both", expand=True, padx=(20,0))
        ctk.CTkLabel(prev, text="Preview", font=FONT_MONO).pack(pady=6)
        self.preview_label = ctk.CTkLabel(prev, text="")
        self.preview_label.pack(expand=True)

    def _auto_out(self, path: str, mode: str) -> str:
        base, _ = os.path.splitext(path)
        tag = "_enc" if mode == "encrypt" else "_dec"
        return base + tag + ".png"

    def _run(self):
        src  = self.f_in.get()
        dst  = self.f_out.get()
        pwd  = self.pwd.get()
        mode = self.mode.get()

        if not src:
            messagebox.showwarning("Aviso", "Selecione a imagem de entrada.")
            return
        if not pwd:
            messagebox.showwarning("Aviso", "Digite a chave.")
            return
        if not dst:
            dst = self._auto_out(src, mode)
            self.f_out.set(dst)
        elif not os.path.splitext(dst)[1]:
            dst += ".png"
            self.f_out.set(dst)

        self.btn.configure(state="disabled", text="Processando…")
        self.bar.set(0.05)
        threading.Thread(target=self._process,
                         args=(src, dst, pwd, mode), daemon=True).start()

    def _show_preview(self, path: str):
        """Exibe thumbnail do resultado na GUI."""
        try:
            img   = Image.open(path)
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=(220, 220))
            self.preview_label.configure(image=photo, text="")
            self.preview_label.image = photo   # evita garbage collection
        except Exception:
            pass

    def _process(self, src, dst, pwd, mode):
        try:
            self.log.write(f"Lendo: {os.path.basename(src)}")
            channels, w, h, orig_w, orig_h = load_image(src)
            self.log.write(f"  {w}×{h} px · 3 canais RGB")

            decrypt  = (mode == "decrypt")
            labels   = ["R", "G", "B"]
            salts    = ["fc_img_v1", "fc_img_v1", "fc_img_v1"]

            from core.image_cipher import get_padded_size

            if not decrypt:
                # ── CIFRAR ────────────────────────────────────────────────────
                # Ao cifrar, cipher_channel retorna a imagem no tamanho padded
                # (ex: 225×225 → 256×256). Isso evita valores negativos de borda
                # que seriam irrecuperáveis em PNG de 8 bits com zero-padding.
                pad_h, pad_w = get_padded_size(h, w)
                out_w, out_h = pad_w, pad_h
                orig_size = None

                if pad_h != h or pad_w != w:
                    self.log.write(
                        f"  Saída será {out_w}×{out_h} px "
                        f"(próxima potência de 2 — necessário para FFT)")

            else:
                # ── DECIFRAR ──────────────────────────────────────────────────
                # A imagem cifrada já está em tamanho pow2. Ao decifrar, passamos
                # orig_size para que cipher_channel crope para o tamanho original.
                if orig_w is not None and orig_h is not None:
                    orig_size = (orig_h, orig_w)   # (linhas, colunas)
                    out_w, out_h = orig_w, orig_h
                    self.log.write(
                        f"  Tamanho original: {orig_w}×{orig_h} px (metadado embutido)")
                else:
                    orig_size = None
                    out_w, out_h = w, h
                    self.log.write(
                        "  ⚠ Metadado de tamanho original não encontrado — "
                        "saída terá tamanho da imagem cifrada.", "WARN")

            self.log.write("  Processando canais RGB em paralelo…")

            # Processa os 3 canais em paralelo usando ProcessPoolExecutor
            args_list = [
                (channels[i], pwd, decrypt, salts[i], orig_size)
                for i in range(3)
            ]

            out_ch = [None, None, None]
            try:
                with ProcessPoolExecutor(max_workers=3) as pool:
                    futures = {
                        pool.submit(_cipher_channel_worker, args): i
                        for i, args in enumerate(args_list)
                    }
                    for future in as_completed(futures):
                        idx = futures[future]
                        out_ch[idx] = future.result()
                        self.log.write(f"  Canal {labels[idx]} concluído ✓")
                        self.bar.set(0.1 + 0.8 * (sum(1 for c in out_ch if c is not None)) / 3)
            except Exception:
                # Fallback sequencial
                self.log.write("  Paralelismo indisponível, processando sequencialmente…", "WARN")
                for i, ch in enumerate(channels):
                    self.log.write(f"  Canal {labels[i]} → FFT 2D + rotação…")
                    out_ch[i] = cipher_channel(ch, pwd, decrypt=decrypt,
                                               orig_size=orig_size)
                    self.bar.set(0.1 + 0.8 * (i+1) / 3)

            # Salva resultado (ao cifrar: inclui metadado do tamanho original)
            if not decrypt:
                save_image(dst, out_ch, out_w, out_h, orig_w=w, orig_h=h)
            else:
                save_image(dst, out_ch, out_w, out_h)

            self.bar.set(1.0)
            self.log.write(f"Salvo em: {dst}", "OK")

            # Atualiza preview na thread principal
            self.after(0, lambda: self._show_preview(dst))

        except Exception as e:
            self.log.write(str(e), "ERR")
            _logger.exception("Erro no processamento de imagem")
        finally:
            self.after(0, lambda: self.btn.configure(
                state="normal", text="EXECUTAR"))



# =============================================================================
# JANELA PRINCIPAL
# =============================================================================

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Fourier Cipher")
        self.geometry("1100x720")
        self.minsize(900, 620)
        self._build()

    def _build(self):
        # Cabeçalho
        hdr = ctk.CTkFrame(self, corner_radius=0, fg_color="#0d1117")
        hdr.pack(fill="x")
        ctk.CTkLabel(hdr, text="◈ FOURIER CIPHER",
                     font=("Consolas",17,"bold"),
                     text_color="#58a6ff").pack(side="left", padx=20, pady=12)
        # Abas
        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=14, pady=(10,0))
        tabs.add("🎵  Áudio")
        tabs.add("🖼  Imagem")
        tabs.add("📊  Reconstrução")

        # Log compartilhado (não mostrado na aba Reconstrução, que tem os próprios gráficos)
        log_frame = ctk.CTkFrame(self)
        log_frame.pack(fill="x", padx=14, pady=(6,10))
        ctk.CTkLabel(log_frame, text="LOG",
                     font=("Consolas",10,"bold")).pack(anchor="w", padx=8, pady=(4,0))
        self.log = LogBox(log_frame, height=80)
        self.log.pack(fill="x", padx=8, pady=(0,8))

        AudioTab(tabs.tab("🎵  Áudio"), log=self.log).pack(
            fill="both", expand=True)
        ImageTab(tabs.tab("🖼  Imagem"), log=self.log).pack(
            fill="both", expand=True)
        ReconstructTab(tabs.tab("📊  Reconstrução"), log=self.log).pack(
            fill="both", expand=True)

        self.log.write("Sistema pronto. ")