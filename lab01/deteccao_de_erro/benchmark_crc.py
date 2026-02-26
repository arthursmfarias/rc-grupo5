#!/usr/bin/env python3
"""
Benchmark CRC: compara implementação manual (bit-a-bit) vs biblioteca crc (C-optimized).
Mede tempo (s) e pico de alocação do Python (KiB) usando time.perf_counter e tracemalloc.
Gera gráficos com matplotlib.
"""

import os
import time
import tracemalloc
import platform
import multiprocessing
import matplotlib.pyplot as plt

# Tente importar a biblioteca crc (instale com `pip install crc` se necessário).
try:
    from crc import Calculator, Crc16
    lib_available = True
    calculator_lib = Calculator(Crc16.MODBUS)
except Exception:
    lib_available = False
    calculator_lib = None

# ---------------------------
# Funções CRC (reutilizáveis)
# ---------------------------
def xor_bits(a: str, b: str) -> str:
    """XOR bit-a-bit entre strings de mesmo comprimento."""
    resultado = []
    for i in range(len(a)):
        resultado.append('0' if a[i] == b[i] else '1')
    return "".join(resultado)

def calcular_crc_manual(dados_bits: str, gerador_bits: str) -> str:
    """
    Implementação direta da divisão polinomial bit-a-bit para obter o resto (CRC).
    Retorna o resto (r bits) como string de '0'/'1'.
    """
    r = len(gerador_bits) - 1
    # mensagem_aumentada como lista para mutabilidade
    mensagem_aumentada = list(dados_bits + '0' * r)

    for i in range(len(dados_bits)):
        if mensagem_aumentada[i] == '1':
            inicio = i
            fim = i + r + 1
            janela_atual = "".join(mensagem_aumentada[inicio:fim])
            resultado_xor = xor_bits(janela_atual, gerador_bits)
            # Atualizar ignorando o primeiro bit (já processado)
            for j in range(1, len(resultado_xor)):
                mensagem_aumentada[i + j] = resultado_xor[j]

    # resto: últimos r bits
    if r == 0:
        return ""
    return "".join(mensagem_aumentada[-r:])

# Função auxiliar CRC16/MODBUS "equivalente" em Python puro (caso lib não esteja instalada)
def crc16_modbus_py(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

# ---------------------------
# Parâmetros do teste
# ---------------------------
tamanhos_bytes = [1500, 4500, 9000]  # conforme solicitado
# Gerador (ex.: CRC-16/MODBUS). É um exemplo; manter compatível com uso da biblioteca.
gerador_bits = "11000000000000101"  # 17 bits -> r = 16

resultados = []

# ---------------------------
# Informação da máquina (onde o script está rodando)
# ---------------------------
info_maquina = {
    "platform": platform.platform(),
    "machine": platform.machine(),
    "processor": platform.processor(),
    "python_version": platform.python_version(),
    "num_cores": multiprocessing.cpu_count()
}
print("Info da máquina detectada:")
for k, v in info_maquina.items():
    print(f"  {k}: {v}")
print("Biblioteca 'crc' disponível:", lib_available)
print()

# ---------------------------
# Loop de testes
# ---------------------------
for tamanho in tamanhos_bytes:
    print(f"== Teste: {tamanho} bytes ==")
    # Gere dados aleatórios (bytes) e converta para bits (apenas para a implementação bit-a-bit)
    mensagem_bytes = os.urandom(tamanho)
    mensagem_bits = "".join(format(byte, '08b') for byte in mensagem_bytes)  # len = tamanho*8

    # --- Medição: implementação manual (inclui apenas o cálculo, não a geração) ---
    tracemalloc.start()
    start_time = time.perf_counter()
    crc_manual = calcular_crc_manual(mensagem_bits, gerador_bits)
    end_time = time.perf_counter()
    mem_atual_manual, mem_pico_manual = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    tempo_manual = end_time - start_time

    print(f"Manual: tempo = {tempo_manual:.6f} s, pico mem (tracemalloc) = {mem_pico_manual/1024:.2f} KiB")

    # --- Medição: biblioteca crc (ou fallback) ---
    if lib_available:
        tracemalloc.start()
        start_time = time.perf_counter()
        # biblioteca espera bytes
        crc_lib = calculator_lib.checksum(mensagem_bytes)
        end_time = time.perf_counter()
        mem_atual_lib, mem_pico_lib = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        tempo_lib = end_time - start_time
        print(f"Biblioteca: tempo = {tempo_lib:.6f} s, pico mem (tracemalloc) = {mem_pico_lib/1024:.2f} KiB")
    else:
        # Fallback: uso da implementação em Python otimizada (byte-wise)
        tracemalloc.start()
        start_time = time.perf_counter()
        crc_lib = crc16_modbus_py(mensagem_bytes)
        end_time = time.perf_counter()
        mem_atual_lib, mem_pico_lib = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        tempo_lib = end_time - start_time
        print(f"Fallback (crc16_modbus_py): tempo = {tempo_lib:.6f} s, pico mem (tracemalloc) = {mem_pico_lib/1024:.2f} KiB")

    resultados.append({
        "tamanho": tamanho,
        "tempo_manual": tempo_manual,
        "mem_pico_manual_kib": mem_pico_manual / 1024,
        "tempo_lib": tempo_lib,
        "mem_pico_lib_kib": mem_pico_lib / 1024
    })

print("\n=== Resultados Consolidados ===")
for r in resultados:
    print(r)

# ---------------------------
# Plots
# ---------------------------
tamanhos = [r["tamanho"] for r in resultados]
tempos_manual = [r["tempo_manual"] for r in resultados]
tempos_lib = [r["tempo_lib"] for r in resultados]
mem_manual = [r["mem_pico_manual_kib"] for r in resultados]
mem_lib = [r["mem_pico_lib_kib"] for r in resultados]

plt.figure(figsize=(9,6))
plt.plot(tamanhos, tempos_manual, marker='o', label="Manual (bit-a-bit)")
plt.plot(tamanhos, tempos_lib, marker='o', label="Biblioteca (C) / fallback")
plt.xlabel("Tamanho da Mensagem (bytes)")
plt.ylabel("Tempo (s)")
plt.title("Tempo de Execução: Manual vs Biblioteca")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("tempo_crc.png", dpi=200)
plt.show()

plt.figure(figsize=(9,6))
plt.plot(tamanhos, mem_manual, marker='o', label="Manual (bit-a-bit)")
plt.plot(tamanhos, mem_lib, marker='o', label="Biblioteca (C) / fallback")
plt.xlabel("Tamanho da Mensagem (bytes)")
plt.ylabel("Pico de Memória (KiB) — tracemalloc")
plt.title("Pico de Memória: Manual vs Biblioteca")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.savefig("mem_crc.png", dpi=200)
plt.show()

# ---------------------------
# Observações finais impressas
# ---------------------------
print("\nObservações:")
print("- tracemalloc mede alocações do Python; extensões em C podem alocar memória externa não contabilizada por tracemalloc.")
print("- Para medir memória total do processo, considere psutil (psutil.Process().memory_info()).")
print("- Arquivos de imagem gerados: tempo_crc.png, mem_crc.png")
