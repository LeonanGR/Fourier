# =============================================================================
# IMAGE I/O — Leitura e Escrita de BMP sem bibliotecas externas
#
# O formato BMP (Windows Bitmap) é o mais simples de parsear manualmente:
#   - File Header (14 bytes): "BM", tamanho, reservados, offset dos pixels
#   - DIB Header (40 bytes, BITMAPINFOHEADER): dimensões, bit depth, etc.
#   - Pixel Data: rows de baixo para cima, alinhadas a 4 bytes (padding)
#
# Para PNG, usaremos tkinter.PhotoImage como ponte, pois parsear DEFLATE
# do zero exigiria um projeto separado — isso é tolerado como I/O estrutural.
# =============================================================================

import struct
import os


# -----------------------------------------------------------------------------
# LEITURA DE BMP
# -----------------------------------------------------------------------------

def read_bmp(filepath: str) -> dict:
    """
    Lê arquivo BMP 24-bit (RGB) ou 8-bit (grayscale) sem bibliotecas externas.
    Retorna:
      - 'width', 'height': int
      - 'channels': [R, G, B] — cada canal é lista 2D [row][col] de ints [0,255]
                    Para grayscale, retorna [Gray] (lista com 1 canal).
    """
    with open(filepath, 'rb') as f:
        raw = f.read()

    # --- FILE HEADER (14 bytes) ---
    sig       = raw[0:2]
    if sig != b'BM':
        raise ValueError(f"Arquivo não é BMP válido: {filepath}")

    # Offset onde os dados de pixel começam
    px_offset = struct.unpack('<I', raw[10:14])[0]

    # --- DIB HEADER (BITMAPINFOHEADER, 40 bytes a partir do byte 14) ---
    dib_size, width, height, planes, bit_count, compression = \
        struct.unpack('<IiiHHI', raw[14:34])

    if compression != 0:
        raise ValueError("BMP comprimido não suportado. Use BMP não comprimido.")

    # height negativo indica top-down; positivo = bottom-up (padrão)
    top_down = height < 0
    height   = abs(height)

    # --- LEITURA DOS PIXELS ---
    # Cada linha é alinhada a múltiplos de 4 bytes
    if bit_count == 24:
        bytes_per_pixel = 3
        row_size = ((bit_count * width + 31) // 32) * 4   # alinhamento de 4 bytes
    elif bit_count == 8:
        bytes_per_pixel = 1
        row_size = ((bit_count * width + 31) // 32) * 4
    else:
        raise ValueError(f"Bit depth {bit_count} não suportado. Use 24-bit ou 8-bit BMP.")

    # Inicializa canais
    if bit_count == 24:
        r_channel = [[0]*width for _ in range(height)]
        g_channel = [[0]*width for _ in range(height)]
        b_channel = [[0]*width for _ in range(height)]
    else:
        gray_channel = [[0]*width for _ in range(height)]

    for row_idx in range(height):
        # BMP bottom-up: primeira linha no arquivo é a última da imagem
        if top_down:
            img_row = row_idx
        else:
            img_row = height - 1 - row_idx

        row_start = px_offset + row_idx * row_size

        for col in range(width):
            px_start = row_start + col * bytes_per_pixel
            if bit_count == 24:
                # BMP 24-bit armazena em ordem BGR (não RGB)
                b = raw[px_start]
                g = raw[px_start + 1]
                r = raw[px_start + 2]
                r_channel[img_row][col] = r
                g_channel[img_row][col] = g
                b_channel[img_row][col] = b
            else:
                gray_channel[img_row][col] = raw[px_start]

    if bit_count == 24:
        return {'width': width, 'height': height,
                'channels': [r_channel, g_channel, b_channel],
                'mode': 'RGB'}
    else:
        return {'width': width, 'height': height,
                'channels': [gray_channel],
                'mode': 'L'}


# -----------------------------------------------------------------------------
# ESCRITA DE BMP
# -----------------------------------------------------------------------------

def write_bmp(filepath: str, channels: list, width: int, height: int,
              mode: str = 'RGB') -> None:
    """
    Escreve canais de pixel em arquivo BMP 24-bit ou 8-bit.
    channels: [R, G, B] para RGB ou [Gray] para grayscale.
    """
    if mode == 'RGB':
        bit_count = 24
        bytes_per_pixel = 3
    else:
        bit_count = 8
        bytes_per_pixel = 1

    row_size     = ((bit_count * width + 31) // 32) * 4
    pixel_data   = bytearray()

    # BMP escreve de baixo para cima (bottom-up)
    for row_idx in range(height - 1, -1, -1):
        row_bytes = bytearray()
        for col in range(width):
            if mode == 'RGB':
                r = channels[0][row_idx][col]
                g = channels[1][row_idx][col]
                b = channels[2][row_idx][col]
                row_bytes.extend([b, g, r])   # BGR order
            else:
                row_bytes.append(channels[0][row_idx][col])
        # Padding para alinhar a 4 bytes
        while len(row_bytes) % 4 != 0:
            row_bytes.append(0x00)
        pixel_data.extend(row_bytes)

    # Adiciona paleta de 256 cores para BMP 8-bit (grayscale)
    color_table = bytearray()
    if mode == 'L':
        for i in range(256):
            color_table.extend([i, i, i, 0])   # B, G, R, reserved

    # Cabeçalhos
    dib_header_size  = 40
    file_header_size = 14
    px_offset        = file_header_size + dib_header_size + len(color_table)
    file_size        = px_offset + len(pixel_data)

    file_header = struct.pack('<2sIHHI',
        b'BM', file_size, 0, 0, px_offset)

    dib_header = struct.pack('<IiiHHIIiiII',
        dib_header_size,
        width, -height,           # height negativo = top-down
        1,                        # planes
        bit_count,
        0,                        # compression = BI_RGB
        len(pixel_data),
        2835, 2835,               # pixels per meter (~72 DPI)
        256 if mode == 'L' else 0,
        256 if mode == 'L' else 0,
    )

    with open(filepath, 'wb') as f:
        f.write(file_header)
        f.write(dib_header)
        f.write(color_table)
        f.write(pixel_data)


# -----------------------------------------------------------------------------
# SUPORTE A PNG via Tkinter (I/O estrutural — sem processamento matemático)
# -----------------------------------------------------------------------------

def read_image_via_tk(filepath: str) -> dict:
    """
    Lê PNG ou outros formatos via Tkinter PhotoImage.
    Converte para lista 2D de canais compatível com o sistema.
    Tolerado pois Tkinter é I/O estrutural, não processamento matemático.
    """
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()   # esconde a janela auxiliar

    img  = tk.PhotoImage(file=filepath)
    w    = img.width()
    h    = img.height()

    r_ch = [[0]*w for _ in range(h)]
    g_ch = [[0]*w for _ in range(h)]
    b_ch = [[0]*w for _ in range(h)]

    for row in range(h):
        for col in range(w):
            # get() retorna string "#rrggbb"
            color = img.get(col, row)
            if isinstance(color, str):
                # Formato "#rrggbb"
                r_ch[row][col] = int(color[1:3], 16)
                g_ch[row][col] = int(color[3:5], 16)
                b_ch[row][col] = int(color[5:7], 16)
            else:
                # Alguns sistemas retornam tupla (r, g, b)
                r_ch[row][col], g_ch[row][col], b_ch[row][col] = color

    root.destroy()
    return {'width': w, 'height': h,
            'channels': [r_ch, g_ch, b_ch],
            'mode': 'RGB'}


def write_image_via_tk(filepath: str, channels: list,
                       width: int, height: int) -> None:
    """Escreve imagem RGB em PNG via Tkinter (apenas I/O)."""
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()

    img = tk.PhotoImage(width=width, height=height)

    # Monta string de pixels em lote (muito mais rápido que put() por pixel)
    rows_data = []
    for row in range(height):
        row_pixels = []
        for col in range(width):
            r = channels[0][row][col]
            g = channels[1][row][col]
            b = channels[2][row][col]
            row_pixels.append(f'#{r:02x}{g:02x}{b:02x}')
        rows_data.append('{' + ' '.join(row_pixels) + '}')

    img.put(' '.join(rows_data))
    img.write(filepath, format='png')
    root.destroy()