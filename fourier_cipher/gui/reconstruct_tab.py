# =============================================================================
# RECONSTRUCT TAB — Aba de Reconstrução Espectral (para uso no App principal)
#
# Decompõe um áudio em suas frequências (FFT), ordena pela magnitude
# (loudest first) e permite ao usuário controlar quantas são somadas
# para reconstruir o sinal original.
# =============================================================================

import os
import threading

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

# ── Cores / fontes (herdadas do tema do app) ──────────────────────────────────
BG      = "#0d1117"
BG2     = "#161b22"
BG3     = "#21262d"
ACCENT  = "#58a6ff"
GREEN   = "#3fb950"
ORANGE  = "#f0883e"
DIM     = "#8b949e"
WHITE   = "#e6edf3"

FONT_MONO  = ("Consolas", 12)
FONT_BOLD  = ("Consolas", 13, "bold")
FONT_SMALL = ("Consolas", 10)
FONT_TINY  = ("Consolas", 9)

MAX_SAMPLES = 88200   # máximo de 2 s de áudio


# =============================================================================
# ABA DE RECONSTRUÇÃO
# =============================================================================

class ReconstructTab(ctk.CTkFrame):
    """Aba de reconstrução espectral para embutir no CTkTabview do App."""

    def __init__(self, master, log, **kw):
        super().__init__(master, fg_color="transparent", **kw)
        self.log = log

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
        # Divide em sidebar + área de plots
        self._sidebar = ctk.CTkFrame(self, fg_color=BG2, width=270,
                                     corner_radius=8)
        self._sidebar.pack(side="left", fill="y", padx=(6, 4), pady=6)
        self._sidebar.pack_propagate(False)
        self._build_sidebar(self._sidebar)

        right = ctk.CTkFrame(self, fg_color="transparent")
        right.pack(side="left", fill="both", expand=True,
                   padx=(0, 6), pady=6)
        self._build_plots(right)

    def _build_sidebar(self, p):
        pad = {"padx": 14, "pady": 4}

        # ── Arquivo ──────────────────────────────────────────────────────────
        _sec(p, "ARQUIVO DE ÁUDIO")

        file_row = ctk.CTkFrame(p, fg_color="transparent")
        file_row.pack(fill="x", padx=14, pady=3)
        self._file_var = ctk.StringVar()
        ctk.CTkEntry(file_row, textvariable=self._file_var,
                     font=FONT_TINY,
                     placeholder_text="Selecione um .wav…"
                     ).pack(side="left", fill="x", expand=True)
        ctk.CTkButton(file_row, text="…", width=34,
                      command=self._pick_file).pack(side="left", padx=(4, 0))

        self._load_btn = ctk.CTkButton(
            p, text="CARREGAR & ANALISAR",
            font=FONT_BOLD, height=36,
            fg_color="#1f6feb", hover_color="#388bfd",
            command=self._load_audio)
        self._load_btn.pack(fill="x", padx=14, pady=(3, 10))

        _div(p)

        # ── Controle de frequências ───────────────────────────────────────────
        _sec(p, "FREQUÊNCIAS ATIVAS")

        self._n_label = ctk.CTkLabel(p, text="— / —",
                                     font=("Consolas", 22, "bold"),
                                     text_color=GREEN)
        self._n_label.pack(**pad)

        self._slider_var = ctk.DoubleVar(value=1)
        self._slider = ctk.CTkSlider(
            p, from_=1, to=100,
            variable=self._slider_var,
            command=self._on_slider,
            state="disabled",
            button_color=GREEN,
            button_hover_color="#56d364",
            progress_color="#2d6a4f")
        self._slider.pack(fill="x", padx=14, pady=(0, 3))

        # Entrada numérica direta
        row_n = ctk.CTkFrame(p, fg_color="transparent")
        row_n.pack(fill="x", padx=14, pady=2)
        ctk.CTkLabel(row_n, text="Ir para:", font=FONT_TINY,
                     text_color=DIM).pack(side="left")
        self._entry_n = ctk.CTkEntry(row_n, width=72, font=FONT_MONO,
                                     placeholder_text="N")
        self._entry_n.pack(side="left", padx=(5, 3))
        ctk.CTkButton(row_n, text="→", width=30, font=FONT_BOLD,
                      command=self._go_to_n).pack(side="left")

        # Barra de energia
        self._energy_lbl = ctk.CTkLabel(p, text="Energia: 0.0%",
                                        font=FONT_MONO, text_color=DIM)
        self._energy_lbl.pack(anchor="w", **pad)
        self._sim_bar = ctk.CTkProgressBar(p, progress_color=GREEN, height=8)
        self._sim_bar.pack(fill="x", padx=14, pady=(0, 6))
        self._sim_bar.set(0)

        _div(p)

        # ── Presets ───────────────────────────────────────────────────────────
        _sec(p, "PRESETS")

        for row_items in [
            [("1%", .01), ("5%", .05), ("10%", .10)],
            [("25%", .25), ("50%", .50), ("100%", 1.0)],
        ]:
            row = ctk.CTkFrame(p, fg_color="transparent")
            row.pack(fill="x", padx=14, pady=2)
            for lbl, pct in row_items:
                ctk.CTkButton(row, text=lbl, width=64, height=26,
                              font=FONT_SMALL,
                              command=lambda p_=pct: self._set_preset(p_)
                              ).pack(side="left", padx=2)

        _div(p)

        # ── Animação ──────────────────────────────────────────────────────────
        _sec(p, "ANIMAÇÃO")

        anim_row = ctk.CTkFrame(p, fg_color="transparent")
        anim_row.pack(fill="x", padx=14, pady=3)

        self._anim_btn = ctk.CTkButton(
            anim_row, text="▶ AUTO", width=84, font=FONT_BOLD,
            fg_color=BG3, hover_color="#30363d",
            command=self._toggle_anim)
        self._anim_btn.pack(side="left", padx=(0, 6))

        ctk.CTkLabel(anim_row, text="Passo:", font=FONT_TINY,
                     text_color=DIM).pack(side="left")
        self._step_var = ctk.StringVar(value="1")
        ctk.CTkOptionMenu(anim_row,
                          values=["1", "5", "10", "50", "100"],
                          variable=self._step_var,
                          width=58, font=FONT_TINY).pack(side="left", padx=3)

        _div(p)

        # ── Reprodução ────────────────────────────────────────────────────────
        _sec(p, "REPRODUÇÃO")

        self._play_btn = ctk.CTkButton(
            p, text="▶  OUVIR RECONSTRUÇÃO",
            font=FONT_BOLD, height=36,
            fg_color="#6e40c9", hover_color="#8957e5",
            command=self._play, state="disabled")
        self._play_btn.pack(fill="x", padx=14, pady=3)

        self._play_orig_btn = ctk.CTkButton(
            p, text="▶  OUVIR ORIGINAL",
            font=FONT_SMALL, height=28,
            fg_color=BG3, hover_color="#30363d",
            command=self._play_original, state="disabled")
        self._play_orig_btn.pack(fill="x", padx=14, pady=(0, 6))

        # Info
        self._info_lbl = ctk.CTkLabel(
            p, text="Carregue um arquivo WAV\npara começar.",
            font=FONT_TINY, text_color=DIM, justify="left")
        self._info_lbl.pack(anchor="w", padx=14, pady=8)

    def _build_plots(self, parent):
        fig = Figure(figsize=(9, 7), facecolor=BG)
        fig.subplots_adjust(hspace=0.50, top=0.96, bottom=0.06,
                            left=0.07, right=0.97)

        self._ax_spec = fig.add_subplot(3, 1, 1)
        self._ax_curr = fig.add_subplot(3, 1, 2)
        self._ax_wave = fig.add_subplot(3, 1, 3)

        for ax in (self._ax_spec, self._ax_curr, self._ax_wave):
            _style_ax(ax)

        self._ax_spec.set_title(
            "Espectro de Frequências — carregue um arquivo",
            color=DIM, fontsize=9, pad=5)
        self._ax_curr.set_title(
            "Componente sendo adicionado",
            color=DIM, fontsize=9, pad=5)
        self._ax_wave.set_title(
            "Reconstrução (top-k) vs Original",
            color=DIM, fontsize=9, pad=5)

        self._fig    = fig
        self._mpl_canvas = FigureCanvasTkAgg(fig, parent)
        self._mpl_canvas.get_tk_widget().pack(fill="both", expand=True)
        self._mpl_canvas.draw()

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
            samples  = (data[:, 0] if data.shape[1] == 1
                        else data.mean(axis=1))
            if len(samples) > MAX_SAMPLES:
                samples = samples[:MAX_SAMPLES]

            spectrum       = np.fft.rfft(samples)
            magnitudes     = np.abs(spectrum)
            sorted_indices = np.argsort(magnitudes)[::-1]

            self.samples        = samples
            self.sr             = sr
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
        self.log.write(
            f"Reconstrução: {fname} carregado — {n:,} componentes FFT")
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
        if nxt >= self.n_components:
            nxt = self.n_components
            self._animating = False
            self._anim_btn.configure(text="▶ AUTO")
        self._slider_var.set(nxt)
        self._render(nxt)
        if self._animating:
            delay = max(40, 200 - step * 5)
            self._anim_after = self.after(delay, self._anim_step)

    # ── Reprodução ────────────────────────────────────────────────────────────

    def _play(self):
        if not HAS_SD:
            messagebox.showinfo("Áudio",
                                "Instale sounddevice:\n"
                                "pip install sounddevice")
            return
        if self._reconstructed is None:
            return
        self._do_play(self._reconstructed.astype(np.float32),
                      self._play_btn, "▶  OUVIR RECONSTRUÇÃO")

    def _play_original(self):
        if not HAS_SD:
            messagebox.showinfo("Áudio",
                                "Instale sounddevice:\n"
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

        # Energia capturada
        active_mags = self.magnitudes[self.sorted_indices[:k]]
        energy_pct  = min(
            float(np.sum(active_mags ** 2) / self.total_energy * 100), 100.0)

        self._n_label.configure(text=f"{k:,} / {self.n_components:,}")
        self._energy_lbl.configure(
            text=f"Energia capturada: {energy_pct:.2f}%")
        self._sim_bar.set(energy_pct / 100)

        # Reconstrução IFFT
        new_spec = np.zeros_like(self.spectrum)
        new_spec[self.sorted_indices[:k]] = self.spectrum[
            self.sorted_indices[:k]]
        reconstructed = np.fft.irfft(new_spec, n=len(self.samples))
        self._reconstructed = reconstructed

        # Componente atual (k-ésima frequência isolada)
        curr_idx  = self.sorted_indices[k - 1]
        curr_spec = np.zeros_like(self.spectrum)
        curr_spec[curr_idx] = self.spectrum[curr_idx]
        curr_wave = np.fft.irfft(curr_spec, n=len(self.samples))

        freqs     = np.fft.rfftfreq(len(self.samples), 1.0 / self.sr)
        curr_freq = float(freqs[curr_idx])
        curr_mag  = float(self.magnitudes[curr_idx])

        # Downsampling para display
        N_PTS = 3000
        step  = max(1, len(self.samples) // N_PTS)
        t     = np.linspace(0, len(self.samples) / self.sr,
                            len(self.samples))
        t_d, orig_d = t[::step], self.samples[::step]
        rec_d, curr_d = reconstructed[::step], curr_wave[::step]

        # ── Plot 1: Espectro ──────────────────────────────────────────────────
        ax1 = self._ax_spec
        ax1.clear()
        _style_ax(ax1)

        step_f = max(1, len(freqs) // 2000)
        f_d, m_d = freqs[::step_f], self.magnitudes[::step_f]
        ax1.fill_between(f_d, m_d, alpha=0.18, color=DIM)
        ax1.plot(f_d, m_d, color=DIM, linewidth=0.5, alpha=0.5)

        # Frequências ativas
        act_idx   = self.sorted_indices[:k]
        act_freqs = freqs[act_idx]
        act_mags  = self.magnitudes[act_idx]
        if len(act_idx) > 800:
            s2        = len(act_idx) // 800
            act_freqs = act_freqs[::s2]
            act_mags  = act_mags[::s2]
        ax1.scatter(act_freqs, act_mags, color=ACCENT, s=2,
                    alpha=0.85, zorder=5, linewidths=0)

        # Componente atual — laranja
        ax1.scatter([curr_freq], [curr_mag], color=ORANGE, s=40, zorder=10,
                    edgecolors="white", linewidths=0.5)
        ax1.axvline(curr_freq, color=ORANGE, linewidth=0.8,
                    alpha=0.5, linestyle="--")

        ax1.set_title(
            f"Espectro  —  {k:,}/{self.n_components:,} freq. ativas  "
            f"[energia: {energy_pct:.1f}%]",
            color=WHITE, fontsize=9, pad=4)
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
            color=WHITE, fontsize=9, pad=4)
        ax2.set_xlabel("Tempo (s)", color=DIM, fontsize=7)
        ax2.set_xlim(t_d[0], t_d[-1])

        # ── Plot 3: Reconstrução vs Original ─────────────────────────────────
        ax3 = self._ax_wave
        ax3.clear()
        _style_ax(ax3)
        ax3.plot(t_d, orig_d, color=DIM, linewidth=0.8, alpha=0.55,
                 label="Original")
        ax3.plot(t_d, rec_d, color=GREEN, linewidth=1.1, alpha=0.92,
                 label=f"Reconstrução ({k:,} freq.)")
        ax3.axhline(0, color=DIM, linewidth=0.4, alpha=0.3)
        ax3.legend(loc="upper right", fontsize=7.5, facecolor=BG3,
                   edgecolor=DIM, labelcolor=WHITE, framealpha=0.8)
        ax3.set_title(
            f"Reconstrução vs Original  —  {energy_pct:.2f}% da energia",
            color=WHITE, fontsize=9, pad=4)
        ax3.set_xlabel("Tempo (s)", color=DIM, fontsize=7)
        ax3.set_xlim(t_d[0], t_d[-1])

        self._mpl_canvas.draw_idle()


# =============================================================================
# HELPERS
# =============================================================================

def _sec(parent, text):
    ctk.CTkLabel(parent, text=text,
                 font=("Consolas", 11, "bold"),
                 text_color=ACCENT).pack(anchor="w", padx=14, pady=(8, 2))


def _div(parent):
    ctk.CTkFrame(parent, height=1, fg_color="#30363d").pack(
        fill="x", padx=14, pady=5)


def _style_ax(ax):
    ax.set_facecolor(BG2)
    ax.tick_params(colors=DIM, labelsize=7, length=3)
    for spine in ("bottom", "left"):
        ax.spines[spine].set_color("#30363d")
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
