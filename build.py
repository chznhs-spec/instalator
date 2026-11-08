#!/usr/bin/env python3
"""Sestaví instalátor pro AKTUÁLNÍ systém (Windows / macOS / Linux).

Nejdřív se přes PyInstaller zabalí VLCR Prohlížeč, ten se zabalí do
payload.tar.gz a ten se vloží dovnitř instalátoru (VLCR_Stahovac_2000).
Výsledek je ve složce dist/.   Požadavky: Python 3.9+ s tkinter, pip install pyinstaller
"""
import os
import shutil
import subprocess
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
B = os.path.join(HERE, "build")
SEP = ";" if os.name == "nt" else ":"


def pyi(*args):
    subprocess.check_call([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", *args], cwd=HERE)


shutil.rmtree(B, ignore_errors=True)
shutil.rmtree(os.path.join(HERE, "dist"), ignore_errors=True)

# 1) druhá aplikace – prohlížeč
pyi("--onefile", "--windowed", "--name", "VLCR_Viewer",
    "--distpath", os.path.join(B, "viewer"), "--workpath", os.path.join(B, "w1"),
    "--specpath", B, os.path.join(HERE, "vlcr_viewer.py"))

out = None
for name in ("VLCR_Viewer.app", "VLCR_Viewer.exe", "VLCR_Viewer"):
    cand = os.path.join(B, "viewer", name)
    if os.path.exists(cand) and (sys.platform == "darwin") == name.endswith(".app"):
        out = cand
        break
if out is None:
    sys.exit("Sestavení prohlížeče se nepovedlo.")

payload = os.path.join(B, "payload.tar.gz")
with tarfile.open(payload, "w:gz") as tf:
    tf.add(out, arcname=os.path.basename(out))

# 2) instalátor s vloženým payloadem
pyi("--onefile", "--windowed", "--name", "VLCR_Stahovac_2000",
    "--distpath", os.path.join(HERE, "dist"), "--workpath", os.path.join(B, "w2"),
    "--specpath", B, "--add-data", payload + SEP + ".", os.path.join(HERE, "installer.py"))
print("\nHotovo – instalátor je ve složce dist/")
