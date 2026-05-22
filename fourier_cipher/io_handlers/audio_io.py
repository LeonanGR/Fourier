# =============================================================================
# AUDIO I/O — Leitura e Escrita de arquivos WAV sem bibliotecas externas
#
# O formato WAV (RIFF) é um container simples:
#   - Cabeçalho RIFF (12 bytes): "RIFF", tamanho, "WAVE"
#   - Chunk "fmt " (24 bytes): codec, canais, sample rate, bit depth
#   - Chunk "data" (N bytes): amostras PCM brutas
#
# Usamos apenas 'struct' da stdlib para desempacotar os bytes do cabeçalho.
# =============================================================================

import struct
import os


# -----------------------------------------------------------------------------
# LEITURA DE WAV
# -----------------------------------------------------------------------------

def read_wav(filepath: str) -> dict:
    """
    Lê um arquivo WAV e retorna um dicionário com:
      - 'sample_rate': int
      - 'num_channels': int
      - 'bit_depth': int
      - 'samples': lista de listas [[canal0, canal1, ...], ...]
                   Uma lista por amostra, cada sub-lista tem um valor por canal.
      - 'num_samples': int
    """
    with open(filepath, 'rb') as f:
        raw = f.read()

    # --- CABEÇALHO RIFF ---
    # Bytes 0-3:  "RIFF"
    # Bytes 4-7:  tamanho total - 8 (little-endian uint32)
    # Bytes 8-11: "WAVE"
    riff_id   = raw[0:4]
    wave_id   = raw[8:12]

    if riff_id != b'RIFF' or wave_id != b'WAVE':
        raise ValueError(f"Arquivo não é um WAV válido: {filepath}")

    # --- BUSCA PELOS CHUNKS ---
    # Percorre todos os chunks até encontrar 'fmt ' e 'data'
    pos        = 12   # início dos chunks (após RIFF header)
    fmt_data   = None
    audio_data = None

    while pos < len(raw):
        chunk_id   = raw[pos:pos+4]
        # Tamanho do chunk em little-endian uint32 (bytes pos+4 a pos+7)
        chunk_size = struct.unpack('<I', raw[pos+4:pos+8])[0]
        chunk_body = raw[pos+8: pos+8+chunk_size]

        if chunk_id == b'fmt ':
            fmt_data = chunk_body
        elif chunk_id == b'data':
            audio_data = chunk_body

        # Avança para o próximo chunk (alinhado a 2 bytes)
        pos += 8 + chunk_size + (chunk_size % 2)

    if fmt_data is None or audio_data is None:
        raise ValueError("Arquivo WAV corrompido: chunks 'fmt ' ou 'data' ausentes.")

    # --- PARSE DO CHUNK fmt  ---
    # Offset 0-1:  audio format (1 = PCM)
    # Offset 2-3:  num channels
    # Offset 4-7:  sample rate
    # Offset 8-11: byte rate
    # Offset 12-13: block align
    # Offset 14-15: bits per sample
    audio_format, num_channels, sample_rate, _, _, bit_depth = \
        struct.unpack('<HHIIHH', fmt_data[:16])

    if audio_format != 1:
        raise ValueError(f"Apenas PCM linear suportado (format=1). Encontrado: {audio_format}")

    # --- PARSE DAS AMOSTRAS PCM ---
    bytes_per_sample = bit_depth // 8
    fmt_char = {1: 'b', 2: 'h', 4: 'i'}.get(bytes_per_sample)
    if fmt_char is None:
        raise ValueError(f"Bit depth {bit_depth} não suportado.")

    # Desempacota todas as amostras de uma vez (little-endian com sinal)
    total_samples = len(audio_data) // bytes_per_sample
    all_samples   = list(struct.unpack(f'<{total_samples}{fmt_char}', audio_data))

    # Organiza por canal: [frame0_ch0, frame0_ch1, frame1_ch0, frame1_ch1, ...]
    # → canais separados: channels[0] = [frame0, frame1, ...]
    channels = [[] for _ in range(num_channels)]
    for i, sample in enumerate(all_samples):
        channels[i % num_channels].append(sample)

    return {
        'sample_rate' : sample_rate,
        'num_channels': num_channels,
        'bit_depth'   : bit_depth,
        'channels'    : channels,
        'num_samples' : len(channels[0]),
    }


# -----------------------------------------------------------------------------
# ESCRITA DE WAV
# -----------------------------------------------------------------------------

def write_wav(filepath: str, channels: list, sample_rate: int,
              bit_depth: int = 16) -> None:
    """
    Escreve canais de áudio PCM em arquivo WAV.
    channels: lista de canais, cada canal é lista de inteiros PCM.
    """
    num_channels     = len(channels)
    num_samples      = len(channels[0])
    bytes_per_sample = bit_depth // 8
    fmt_char         = {1: 'b', 2: 'h', 4: 'i'}[bytes_per_sample]

    # Intercala os canais: [ch0_s0, ch1_s0, ch0_s1, ch1_s1, ...]
    interleaved = []
    for i in range(num_samples):
        for ch in channels:
            interleaved.append(ch[i])

    # Serializa as amostras
    audio_data = struct.pack(f'<{len(interleaved)}{fmt_char}', *interleaved)

    # --- CONSTRÓI CABEÇALHO WAV ---
    data_size       = len(audio_data)
    byte_rate       = sample_rate * num_channels * bytes_per_sample
    block_align     = num_channels * bytes_per_sample
    chunk_size      = 36 + data_size   # tamanho total - 8

    # fmt  chunk
    fmt_chunk = struct.pack('<HHIIHH',
        1,              # PCM
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bit_depth,
    )

    with open(filepath, 'wb') as f:
        # RIFF header
        f.write(b'RIFF')
        f.write(struct.pack('<I', chunk_size))
        f.write(b'WAVE')
        # fmt  chunk
        f.write(b'fmt ')
        f.write(struct.pack('<I', 16))   # tamanho do fmt chunk (sempre 16 para PCM)
        f.write(fmt_chunk)
        # data chunk
        f.write(b'data')
        f.write(struct.pack('<I', data_size))
        f.write(audio_data)