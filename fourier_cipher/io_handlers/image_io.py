# =============================================================================
# IMAGE I/O — Leitura e Escrita de Imagens (BMP, PNG) usando Pillow e numpy
# =============================================================================

from PIL import Image
import numpy as np


# -----------------------------------------------------------------------------
# AUXILIARES GENÉRICOS DE LEITURA E ESCRITA
# -----------------------------------------------------------------------------

def read_image(filepath: str) -> dict:
    """
    Lê qualquer imagem suportada pelo Pillow (PNG, BMP, JPG) de forma muito rápida.
    Retorna:
      - 'width', 'height': int
      - 'channels': [R, G, B] para RGB ou [Gray] para grayscale (listas 2D [row][col] de inteiros)
      - 'mode': 'RGB' ou 'L'
    """
    with Image.open(filepath) as img:
        mode = img.mode
        # Normaliza imagens não-padrão para RGB
        if mode not in ('RGB', 'L'):
            img = img.convert('RGB')
            mode = 'RGB'

        width, height = img.size
        img_np = np.array(img)

        if mode == 'RGB':
            # Divide os canais em R, G, B individuais
            r = img_np[:, :, 0].tolist()
            g = img_np[:, :, 1].tolist()
            b = img_np[:, :, 2].tolist()
            channels = [r, g, b]
        else:
            # Canal de tons de cinza único
            channels = [img_np.tolist()]

        return {
            'width': width,
            'height': height,
            'channels': channels,
            'mode': mode
        }


def write_image(filepath: str, channels: list, width: int, height: int,
                mode: str = 'RGB') -> None:
    """
    Salva uma imagem no caminho especificado usando Pillow.
    Deduze o formato automaticamente a partir da extensão do arquivo.
    """
    if mode == 'RGB':
        # Combina os 3 canais de cor em uma matriz 3D (altura, largura, 3)
        img_np = np.stack([
            np.array(channels[0]),
            np.array(channels[1]),
            np.array(channels[2])
        ], axis=-1).astype(np.uint8)
        img = Image.fromarray(img_np, mode='RGB')
    else:
        # Canal único para escala de cinza
        img_np = np.array(channels[0]).astype(np.uint8)
        img = Image.fromarray(img_np, mode='L')

    img.save(filepath)


# -----------------------------------------------------------------------------
# COMPATIBILIDADE BMP
# -----------------------------------------------------------------------------

def read_bmp(filepath: str) -> dict:
    """Lê arquivo BMP 24-bit (RGB) ou 8-bit (grayscale) usando Pillow."""
    return read_image(filepath)


def write_bmp(filepath: str, channels: list, width: int, height: int,
              mode: str = 'RGB') -> None:
    """Escreve canais de pixel em arquivo BMP usando Pillow."""
    write_image(filepath, channels, width, height, mode)


# -----------------------------------------------------------------------------
# COMPATIBILIDADE PNG (Substitui a ponte lenta via Tkinter PhotoImage)
# -----------------------------------------------------------------------------

def read_image_via_tk(filepath: str) -> dict:
    """
    Lê PNG ou outros formatos. Mantém compatibilidade de assinatura,
    mas executa de forma 100x mais rápida usando Pillow de fundo (sem abrir janelas Tk).
    """
    # Sempre lê em modo RGB para manter a compatibilidade com a implementação legado via Tkinter
    res = read_image(filepath)
    if res['mode'] != 'RGB':
        with Image.open(filepath).convert('RGB') as img:
            w, h = img.size
            img_np = np.array(img)
            r = img_np[:, :, 0].tolist()
            g = img_np[:, :, 1].tolist()
            b = img_np[:, :, 2].tolist()
            return {
                'width': w,
                'height': h,
                'channels': [r, g, b],
                'mode': 'RGB'
            }
    return res


def write_image_via_tk(filepath: str, channels: list,
                       width: int, height: int) -> None:
    """Escreve imagem RGB em PNG de forma extremamente rápida sem usar o Tkinter."""
    write_image(filepath, channels, width, height, mode='RGB')