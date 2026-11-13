"""Diagnostico local de dependencias; nao usa internet."""
import struct
import sys

print("Python:", sys.version.split()[0])
print("Arquitetura:", struct.calcsize("P") * 8, "bits")
if sys.version_info[:2] != (3, 15):
    raise SystemExit("Este instalador requer Python 3.15.x")
if struct.calcsize("P") * 8 != 64:
    raise SystemExit("Este instalador requer Python 64 bits")

for nome in ("numpy", "pandas", "scipy", "matplotlib", "streamlit", "openpyxl", "pyarrow"):
    mod = __import__(nome)
    print(f"{nome}: {mod.__version__}")

import engine
import data_utils
print("Motor estatistico e importacao: OK")
print("Dependencias: OK")
