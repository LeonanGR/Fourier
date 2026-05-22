# =============================================================================
# FOURIER RECONSTRUCT — Visualizador de Reconstrução Espectral
#
# Decompõe um áudio em suas frequências (FFT), ordena pela magnitude (loudest first)
# e permite ao usuário controlar quantas frequências são somadas para reconstruir
# o sinal original.
#
# Uso: python fourier_reconstruct.py
# =============================================================================

import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
import soundfile as sf
import customtkinter as ctk
from tkinter import filedialog, messagebox

from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# Reprodução de áudio (opcional)
try:
    import sounddevice as sd
    HAS_SD = True
except ImportError:
    HAS_SD = False

# =============================================================================
# TEMA / CORES
# =============================================================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

BG       = "#0d1117"
BG2      = "#161b22"
BG3      = "#21262d"
ACCENT   = "#58a6ff"
GREEN    = "#3fb950"
ORANGE   = "#f0883e"
RED      = "#f85149"
DIM      = "#8b949e"
WHITE    = "#e6edf3"

FONT_MONO  = ("Consolas", 12)
FONT_BOLD  = ("Consolas", 13, "bold")
FONT_HEAD  = ("Consolas", 15, "bold")
FONT_SMALL = ("Consolas", 10)
FONT_TINY  = ("Consolas", 9)

MAX_SAMPLES = 88200   # Máximo de 2 segundos de áudio para análise


# =============================================================================
# APLICAÇÃO PRINCIPAL
# =============================================================================

class FourierReconstructApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Fourier Reconstruct — Reconstrução Espectral")
        self.geometry("1280x820")
        self.minsize(1000, 680)
        self.configure(fg_color=BG)

        # Estado
        self.samples        = None
        self.sr             = None
        self.spectrum       = None
        self.magnitudes     = None
        self.sorted_indices = None
        self.n_components   = 0
        self.total_energy   = 1.0
        self._reconstructed = None
        self._playing       = False
        self._animating     = False
        self._anim_after    = None

        self._build()

    # -------------------------------------------------------------------------
    # CONSTRUÇÃO DA INTERFACE
    # -------------------------------------------------------------------------

    def _build(self):
        # --- Cabeçalho ---
        hdr = ctk.CTkFrame(self, corner_radius=0, fg_color=BG2, height=52)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        ctk.CTkLabel(hdr, text="◈ FOURIER RECONSTRUCT",
                     font=("Consolas", 18, "bold"),
                     text_color=ACCENT).pack(side="left", padx=22, pady=12)
        ctk.CTkLabel(hdr,
                     text="Decomposição Espectral  ·  Ordenação por Magnitude  ·  "
                          "Reconstrução Progressiva",
                     font=FONT_TINY, text_color=DIM).pack(side="left")

        # --- Corpo principal ---
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)

        # Sidebar esquerda
        sidebar = ctk.CTkFrame(body, fg_color=BG2, width=280, corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        self._build_sidebar(sidebar)

        # Área de plots
        right = ctk.CTkFrame(body, fg_color=BG, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)
        self._build_plots(right)

    def _build_sidebar(self, p):
        pad = {"padx": 18, "pady": 5}

        # ── Arquivo ──────────────────────────────────────────────────────────
        _section(p, "ARQUIVO DE ÁUDIO")

        file_row = ctk.CTkFrame(p, fg_color="transparent")
        file_row.pack(fill="x", padx=18, pady=4)
        self._file_var = ctk.StringVar()
        ctk.CTkEntry(file_row, textvariable=self._file_var,
                     font=FONT_TINY, placeholder_text="Selecione um .wav…"
                     ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(file_row, text="…", width=36,
                      command=self._pick_file).pack(side="left", padx=(4, 0))

        self._load_btn = ctk.CTkButton(
            p, text="CARREGAR & ANALISAR",
            font=FONT_BOLD, height=40,
            fg_color="#1f6feb", hover_color="#388bfd",
            command=self._load_audio)
        self._load_btn.pack(fill="x", padx=18, pady=(4, 14))

        _divider(p)

        # ── Controle de frequências ───────────────────────────────────────────
        _section(p, "FREQUÊNCIAS ATIVAS")

        self._n_label = ctk.CTkLabel(p, text="— / —",
                                     font=("Consolas", 26, "bold"),
                                     text_color=GREEN)
        self._n_label.pack(**pad)

        # Slider
        self._slider_var = ctk.DoubleVar(value=1)
        self._slider = ctk.CTkSlider(p, from_=1, to=100,
                                     variable=self._slider_var,
                                     command=self._on_slider,
                                     state="disabled",
                                     button_color=GREEN,
                                     button_hover_color="#56d364",
                                     progress_color="#2d6a4f")
        self._slider.pack(fill="x", padx=18, pady=(0, 4))

        # Entrada numérica direta
        row_n = ctk.CTkFrame(p, fg_color="transparent")
        row_n.pack(fill="x", padx=18, pady=2)
        ctk.CTkLabel(row_n, text="Ir para:", font=FONT_TINY,
                     text_color=DIM).pack(side="left")
        self._entry_n = ctk.CTkEntry(row_n, width=80, font=FONT_MONO,
                                     placeholder_text="N")
        self._entry_n.pack(side="left", padx=(6, 4))
        ctk.CTkButton(row_n, text="→", width=32, font=FONT_BOLD,
                      command=self._go_to_n).pack(side="left")

        # Barra de energia / similaridade
        self._energy_label = ctk.CTkLabel(p, text="Energia: 0.0%",
                                          font=FONT_MONO, text_color=DIM)
        self._energy_label.pack(anchor="w", **pad)
        self._sim_bar = ctk.CTkProgressBar(p, progress_color=GREEN,
                                           height=10)
        self._sim_bar.pack(fill="x", padx=18, pady=(0, 8))
        self._sim_bar.set(0)

        _divider(p)

        # ── Presets ───────────────────────────────────────────────────────────
        _section(p, "PRESETS")

        row1 = ctk.CTkFrame(p, fg_color="transparent")
        row1.pack(fill="x", padx=18, pady=3)
        row2 = ctk.CTkFrame(p, fg_color="transparent")
        row2.pack(fill="x", padx=18, pady=3)

        for i, (label, pct) in enumerate(
                [("1%", .01), ("5%", .05), ("10%", .10),
                 ("25%", .25), ("50%", .50), ("100%", 1.0)]):
            row = row1 if i < 3 else row2
            ctk.CTkButton(row, text=label, width=68, height=28,
                          font=FONT_SMALL,
                          command=lambda p_=pct: self._set_preset(p_)
                          ).pack(side="left", padx=2)

        _divider(p)

        # ── Animação ──────────────────────────────────────────────────────────
        _section(p, "ANIMAÇÃO")

        anim_row = ctk.CTkFrame(p, fg_color="transparent")
        anim_row.pack(fill="x", padx=18, pady=4)

        self._anim_btn = ctk.CTkButton(anim_row, text="▶ AUTO",
                                       width=90, font=FONT_BOLD,
                                       fg_color=BG3, hover_color="#30363d",
                                       command=self._toggle_anim)
        self._anim_btn.pack(side="left", padx=(0, 6))

        ctk.CTkLabel(anim_row, text="Passo:", font=FONT_TINY,
                     text_color=DIM).pack(side="left")
        self._step_var = ctk.StringVar(value="1")
        ctk.CTkOptionMenu(anim_row, values=["1", "5", "10", "50", "100"],
                          variable=self._step_var,
                          width=60, font=FONT_TINY).pack(side="left", padx=4)

        _divider(p)

        # ── Reprodução ────────────────────────────────────────────────────────
        _section(p, "REPRODUÇÃO")

        self._play_btn = ctk.CTkButton(
            p, text="▶  OUVIR RECONSTRUÇÃO",
            font=FONT_BOLD, height=40,
            fg_color="#6e40c9", hover_color="#8957e5",
            command=self._play, state="disabled")
        self._play_btn.pack(fill="x", padx=18, pady=4)

        self._play_orig_btn = ctk.CTkButton(
            p, text="▶  OUVIR ORIGINAL",
            font=FONT_SMALL, height=32,
            fg_color=BG3, hover_color="#30363d",
            command=self._play_original, state="disabled")
        self._play_orig_btn.pack(fill="x", padx=18, pady=(0, 8))

        # Info
        self._info_lbl = ctk.CTkLabel(
            p, text="Carregue um arquivo WAV\npara começar.",
            font=FONT_TINY, text_color=DIM, justify="left")
        self._info_lbl.pack(anchor="w", padx=18, pady=10)

    def _build_plots(self, parent):
        fig = Figure(figsize=(9, 7.5), facecolor=BG)
        fig.subplots_adjust(hspace=0.52, top=0.96, bottom=0.06,
                            left=0.07, right=0.97)

        self._ax_spec  = fig.add_subplot(3, 1, 1)   # Espectro
        self._ax_curr  = fig.add_subplot(3, 1, 2)   # Componente atual
        self._ax_wave  = fig.add_subplot(3, 1, 3)   # Reconstrução vs Original

        for ax in (self._ax_spec, self._ax_curr, self._ax_wave):
            _style_ax(ax)

        self._ax_spec.set_title("Espectro de Frequências — carregue um arquivo",
                                color=DIM, fontsize=9, pad=5)
        self._ax_curr.set_title("Componente sendo adicionado — —",
                                color=DIM, fontsize=9, pad=5)
        self._ax_wave.set_title("Reconstrução (top-k) vs Original",
                                color=DIM, fontsize=9, pad=5)

        self._fig    = fig
        self._canvas = FigureCanvasTkAgg(fig, parent)
        self._canvas.get_tk_widget().pack(fill="both", expand=True,
                                          padx=6, pady=6)
        self._canvas.draw()

    # -------------------------------------------------------------------------
    # CARREGAMENTO DE ÁUDIO
    # -------------------------------------------------------------------------

    def _pick_file(self):
        path = filedialog.askopenfilename(
            filetypes=[("WAV", "*.wav"), ("Todos", "*.*")])
        if path:
            self._file_var.set(path)

    def _load_audio(self):
        path = self._file_var.get().strip()
        if not path or not os.path.isfile(path):
            messagebox.showwarning("Aviso", "Selecione um arquivo WAV válido.")
            return
        self._load_btn.configure(state="disabled", text="Analisando…")
        threading.Thread(target=self._do_load, args=(path,),
                         daemon=True).start()

    def _do_load(self, path):
        try:
            data, sr = sf.read(path, dtype='float32', always_2d=True)
            # Mono
            samples = (data[:, 0] if data.shape[1] == 1
                       else data.mean(axis=1))
            # Limita a MAX_SAMPLES
            if len(samples) > MAX_SAMPLES:
                samples = samples[:MAX_SAMPLES]

            self.samples = samples
            self.sr      = sr

            # FFT
            spectrum   = np.fft.rfft(samples)
            magnitudes = np.abs(spectrum)

            # Ordena por magnitude descrescente
            sorted_indices = np.argsort(magnitudes)[::-1]

            self.spectrum       = spectrum
            self.magnitudes     = magnitudes
            self.sorted_indices = sorted_indices
            self.n_components   = len(spectrum)
            self.total_energy   = float(np.sum(magnitudes ** 2)) or 1.0

            self.after(0, self._on_loaded)
        except Exception as exc:
            self.after(0, lambda: messagebox.showerror("Erro", str(exc)))
            self.after(0, lambda: self._load_btn.configure(
                state="normal", text="CARREGAR & ANALISAR"))

    def _on_loaded(self):
        self._load_btn.configure(state="normal", text="CARREGAR & ANALISAR")
        n   = self.n_components
        dur = len(self.samples) / self.sr

        self._slider.configure(state="normal", from_=1, to=n)
        self._slider_var.set(1)
        self._play_btn.configure(state="normal")
        self._play_orig_btn.configure(state="normal")

        fname = os.path.basename(self._file_var.get())
        self._info_lbl.configure(
            text=f"{fname}\n"
                 f"Amostras: {len(self.samples):,}\n"
                 f"Taxa: {self.sr:,} Hz\n"
                 f"Duração: {dur:.2f}s\n"
                 f"Componentes FFT: {n:,}")

        self._render(1)

    # -------------------------------------------------------------------------
    # CONTROLES
    # -------------------------------------------------------------------------

    def _on_slider(self, value):
        self._render(int(value))

    def _go_to_n(self):
        try:
            n = int(self._entry_n.get())
        except ValueError:
            return
        n = max(1, min(n, self.n_components))
        self._slider_var.set(n)
        self._render(n)

    def _set_preset(self, pct):
        if self.n_components == 0:
            return
        n = max(1, int(self.n_components * pct))
        self._slider_var.set(n)
        self._render(n)

    # ── Animação ──────────────────────────────────────────────────────────────

    def _toggle_anim(self):
        if self._animating:
            self._animating = False
            if self._anim_after:
                self.after_cancel(self._anim_after)
            self._anim_btn.configure(text="▶ AUTO")
        else:
            if self.n_components == 0:
                return
            self._animating = True
            self._anim_btn.configure(text="■ PARAR")
            self._anim_step()

    def _anim_step(self):
        if not self._animating:
            return
        step = int(self._step_var.get())
        cur  = int(self._slider_var.get())
        nxt  = cur + step
        if nxt > self.n_components:
            nxt = self.n_components
            self._animating = False
            self._anim_btn.configure(text="▶ AUTO")
        self._slider_var.set(nxt)
        self._render(nxt)
        if self._animating:
            delay = max(40, 200 - step * 5)   # mais rápido com step maior
            self._anim_after = self.after(delay, self._anim_step)

    # ── Reprodução ────────────────────────────────────────────────────────────

    def _play(self):
        if not HAS_SD:
            messagebox.showinfo("Áudio",
                                "Instale sounddevice para reprodução:\n"
                                "pip install sounddevice")
            return
        if self._reconstructed is None:
            return
        self._do_play(self._reconstructed.astype(np.float32),
                      self._play_btn, "▶  OUVIR RECONSTRUÇÃO")

    def _play_original(self):
        if not HAS_SD:
            messagebox.showinfo("Áudio",
                                "Instale sounddevice para reprodução:\n"
                                "pip install sounddevice")
            return
        if self.samples is None:
            return
        self._do_play(self.samples.astype(np.float32),
                      self._play_orig_btn, "▶  OUVIR ORIGINAL")

    def _do_play(self, data, btn, label):
        if self._playing:
            sd.stop()
            self._playing = False
            btn.configure(text=label)
            return
        self._playing = True
        btn.configure(text="■  PARAR")

        def _worker():
            sd.play(data, self.sr)
            sd.wait()
            self._playing = False
            self.after(0, lambda: btn.configure(text=label))

        threading.Thread(target=_worker, daemon=True).start()

    # -------------------------------------------------------------------------
    # RENDERIZAÇÃO
    # -------------------------------------------------------------------------

    def _render(self, k: int):
        if self.samples is None:
            return
        k = max(1, min(k, self.n_components))

        # ── Energia capturada ────────────────────────────────────────────────
        active_mags  = self.magnitudes[self.sorted_indices[:k]]
        energy_pct   = float(np.sum(active_mags ** 2) / self.total_energy * 100)
        energy_pct   = min(energy_pct, 100.0)

        self._n_label.configure(text=f"{k:,} / {self.n_components:,}")
        self._energy_label.configure(text=f"Energia capturada: {energy_pct:.2f}%")
        self._sim_bar.set(energy_pct / 100)

        # ── Reconstrução IFFT ────────────────────────────────────────────────
        new_spec = np.zeros_like(self.spectrum)
        new_spec[self.sorted_indices[:k]] = self.spectrum[self.sorted_indices[:k]]
        reconstructed = np.fft.irfft(new_spec, n=len(self.samples))
        self._reconstructed = reconstructed

        # ── Componente atual (apenas a k-ésima frequência) ───────────────────
        curr_idx  = self.sorted_indices[k - 1]
        curr_spec = np.zeros_like(self.spectrum)
        curr_spec[curr_idx] = self.spectrum[curr_idx]
        curr_wave = np.fft.irfft(curr_spec, n=len(self.samples))

        freqs     = np.fft.rfftfreq(len(self.samples), 1.0 / self.sr)
        curr_freq = float(freqs[curr_idx])
        curr_mag  = float(self.magnitudes[curr_idx])

        # ── Downsampling para display ─────────────────────────────────────────
        N_POINTS = 3000
        step     = max(1, len(self.samples) // N_POINTS)
        t        = np.linspace(0, len(self.samples) / self.sr,
                               len(self.samples))
        t_d      = t[::step]
        orig_d   = self.samples[::step]
        rec_d    = reconstructed[::step]
        curr_d   = curr_wave[::step]

        # ── Plot 1: Espectro ──────────────────────────────────────────────────
        ax1 = self._ax_spec
        ax1.clear()
        _style_ax(ax1)

        step_f = max(1, len(freqs) // 2000)
        f_d    = freqs[::step_f]
        m_d    = self.magnitudes[::step_f]

        # Espectro completo (fundo)
        ax1.fill_between(f_d, m_d, alpha=0.18, color=DIM)
        ax1.plot(f_d, m_d, color=DIM, linewidth=0.5, alpha=0.5)

        # Frequências ativas (top-k) — destacadas em azul
        act_idx   = self.sorted_indices[:k]
        act_freqs = freqs[act_idx]
        act_mags  = self.magnitudes[act_idx]
        # Limita marcadores para performance
        if len(act_idx) > 800:
            step_a    = len(act_idx) // 800
            act_freqs = act_freqs[::step_a]
            act_mags  = act_mags[::step_a]
        ax1.scatter(act_freqs, act_mags, color=ACCENT, s=2, alpha=0.85,
                    zorder=5, linewidths=0)

        # Componente atual — laranja
        ax1.scatter([curr_freq], [curr_mag], color=ORANGE, s=45, zorder=10,
                    edgecolors="white", linewidths=0.5)
        ax1.axvline(curr_freq, color=ORANGE, linewidth=0.8, alpha=0.5,
                    linestyle="--")

        ax1.set_title(
            f"Espectro  —  {k:,} / {self.n_components:,} frequências  "
            f"[energia: {energy_pct:.1f}%]",
            color=WHITE, fontsize=9, pad=5)
        ax1.set_xlabel("Frequência (Hz)", color=DIM, fontsize=7)
        ax1.set_ylabel("Magnitude", color=DIM, fontsize=7)
        ax1.set_xlim(0, self.sr / 2)
        ax1.set_ylim(bottom=0)

        # ── Plot 2: Componente atual ──────────────────────────────────────────
        ax2 = self._ax_curr
        ax2.clear()
        _style_ax(ax2)

        ax2.plot(t_d, curr_d, color=ORANGE, linewidth=1.2)
        ax2.axhline(0, color=DIM, linewidth=0.5, alpha=0.4)
        ax2.set_title(
            f"Componente #{k:,}  —  {curr_freq:.1f} Hz  "
            f"(magnitude: {curr_mag:.4f})",
            color=WHITE, fontsize=9, pad=5)
        ax2.set_xlabel("Tempo (s)", color=DIM, fontsize=7)
        ax2.set_xlim(t_d[0], t_d[-1])

        # ── Plot 3: Reconstrução vs Original ─────────────────────────────────
        ax3 = self._ax_wave
        ax3.clear()
        _style_ax(ax3)

        ax3.plot(t_d, orig_d, color=DIM,   linewidth=0.8,  alpha=0.55,
                 label="Original")
        ax3.plot(t_d, rec_d,  color=GREEN, linewidth=1.1,  alpha=0.92,
                 label=f"Reconstrução ({k:,} freq.)")
        ax3.axhline(0, color=DIM, linewidth=0.4, alpha=0.3)

        ax3.legend(loc="upper right", fontsize=7.5, facecolor=BG3,
                   edgecolor=DIM, labelcolor=WHITE, framealpha=0.8)
        ax3.set_title(
            f"Reconstrução vs Original  —  {energy_pct:.2f}% da energia",
            color=WHITE, fontsize=9, pad=5)
        ax3.set_xlabel("Tempo (s)", color=DIM, fontsize=7)
        ax3.set_xlim(t_d[0], t_d[-1])

        self._canvas.draw_idle()


# =============================================================================
# HELPERS DE UI
# =============================================================================

def _section(parent, text: str):
    ctk.CTkLabel(parent, text=text, font=("Consolas", 11, "bold"),
                 text_color=ACCENT).pack(anchor="w", padx=18, pady=(10, 2))


def _divider(parent):
    ctk.CTkFrame(parent, height=1, fg_color="#30363d").pack(
        fill="x", padx=18, pady=6)


def _style_ax(ax):
    ax.set_facecolor(BG2)
    ax.tick_params(colors=DIM, labelsize=7, length=3)
    for spine in ("bottom", "left"):
        ax.spines[spine].set_color("#30363d")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)


# =============================================================================
# PONTO DE ENTRADA
# =============================================================================

if __name__ == "__main__":
    app = FourierReconstructApp()
    app.mainloop()
