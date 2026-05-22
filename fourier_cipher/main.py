# =============================================================================
# FOURIER CIPHER — Ponto de entrada
#
# Modos de uso:
#   GUI:  python main.py
#   CLI:  python main.py --mode encrypt --type audio --input a.wav --key "senha"
# =============================================================================

import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def _run_gui():
    """Inicia a interface gráfica."""
    from gui.interface import App
    App().mainloop()


def _run_cli(args):
    """Executa via linha de comando."""
    from core.audio_cipher import cipher_audio
    from core.image_cipher import cipher_channel

    decrypt = (args.mode == "decrypt")
    tag     = "_enc" if args.mode == "encrypt" else "_dec"

    if args.type == "audio":
        from gui.interface import load_audio, save_audio

        print(f"[•] Lendo: {args.input}")
        channels, sr, _ = load_audio(args.input)
        print(f"[•] {len(channels)} canal(is) · {sr} Hz · "
              f"{len(channels[0])} amostras")

        out_channels = []
        for i, ch in enumerate(channels):
            print(f"[•] Canal {i+1}/{len(channels)} → FFT + rotação complexa…")
            out_channels.append(cipher_audio(ch, args.key, decrypt=decrypt))

        out_path = args.output
        if not out_path:
            base, ext = os.path.splitext(args.input)
            out_path = base + tag + (ext or ".wav")

        save_audio(out_path, out_channels, sr)
        print(f"[✓] Salvo em: {out_path}")

    elif args.type == "image":
        from gui.interface import load_image, save_image
        from core.image_cipher import get_padded_size

        print(f"[•] Lendo: {args.input}")
        channels, w, h, orig_w, orig_h = load_image(args.input)
        print(f"[•] {w}×{h} px · 3 canais RGB")

        # Determina orig_size para descriptografia
        if decrypt and orig_w is not None and orig_h is not None:
            orig_size = (orig_h, orig_w)
            print(f"[•] Tamanho original detectado: {orig_w}×{orig_h} px")
        else:
            orig_size = None

        # Determina tamanho de saída
        if not decrypt:
            pad_h, pad_w = get_padded_size(h, w)
            out_w, out_h = pad_w, pad_h
            print(f"[•] Tamanho de saída (padded): {out_w}×{out_h} px")
        else:
            out_h, out_w = (orig_size[0], orig_size[1]) if orig_size else (h, w)

        out_ch = []
        labels = ["R", "G", "B"]
        for i, ch in enumerate(channels):
            print(f"[•] Canal {labels[i]} → FFT 2D + rotação complexa…")
            out_ch.append(cipher_channel(ch, args.key, decrypt=decrypt,
                                         orig_size=orig_size))

        out_path = args.output
        if not out_path:
            base, _ = os.path.splitext(args.input)
            out_path = base + tag + ".png"

        if not decrypt:
            save_image(out_path, out_ch, out_w, out_h, orig_w=w, orig_h=h)
        else:
            save_image(out_path, out_ch, out_w, out_h)
        print(f"[✓] Salvo em: {out_path}")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fourier Cipher - Criptografia via Perturbacao de Fase (FFT)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Exemplos:
  python main.py                                                  => Abre a GUI
  python main.py --mode encrypt --type audio -i a.wav -k "senha"  => Cifra audio
  python main.py --mode decrypt --type audio -i a_enc.wav -k "senha"
  python main.py --mode encrypt --type image -i img.png -k "chave"
        """)

    parser.add_argument("--mode", choices=["encrypt", "decrypt"],
                        help="Operacao: encrypt ou decrypt")
    parser.add_argument("--type", choices=["audio", "image"],
                        help="Tipo de midia: audio ou image")
    parser.add_argument("-i", "--input", help="Arquivo de entrada")
    parser.add_argument("-o", "--output", help="Arquivo de saida (opcional)")
    parser.add_argument("-k", "--key", help="Chave/senha de criptografia")

    args = parser.parse_args()

    # Se nenhum argumento CLI foi fornecido → abre a GUI
    if args.mode is None and args.type is None:
        _run_gui()
    else:
        # Validação de argumentos CLI
        if not args.mode:
            parser.error("--mode e obrigatorio no modo CLI")
        if not args.type:
            parser.error("--type e obrigatorio no modo CLI")
        if not args.input:
            parser.error("--input / -i e obrigatorio no modo CLI")
        if not args.key:
            parser.error("--key / -k e obrigatorio no modo CLI")
        _run_cli(args)