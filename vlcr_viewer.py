#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VLCR Prohlížeč – druhá aplikace, ve které se otevírají soubory .vlcr."""
import sys
import tkinter as tk
from tkinter import filedialog, messagebox

import vlcr_codec


class Viewer(tk.Tk):
    def __init__(self, path=None):
        super().__init__()
        self.title("VLCR Prohlížeč")
        self.geometry("660x540")
        self.minsize(480, 420)

        top = tk.Frame(self)
        top.pack(fill="x", padx=10, pady=8)
        tk.Button(top, text="Otevřít soubor .vlcr…", command=self.open_file).pack(side="left")
        tk.Button(top, text="Rozluštit vložený text", command=self.decode_pasted).pack(side="left", padx=6)
        tk.Button(top, text="Kopírovat zprávu", command=self.copy_msg).pack(side="left")
        tk.Button(top, text="Vymazat", command=self.clear).pack(side="left", padx=6)

        tk.Label(self, text="Sem vložte obsah souboru .vlcr (Ctrl+V / Cmd+V):", anchor="w").pack(fill="x", padx=10)
        self.inp = tk.Text(self, height=8, wrap="char", font=("Courier", 10))
        self.inp.pack(fill="x", padx=10, pady=(0, 8))

        tk.Label(self, text="Zpráva:", anchor="w", font=("Helvetica", 11, "bold")).pack(fill="x", padx=10)
        self.out = tk.Text(self, wrap="word", font=("Helvetica", 15), state="disabled",
                           padx=10, pady=10, bg="#f4f4f4")
        self.out.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        if path:
            self.load(path)

    def show(self, text):
        self.out.configure(state="normal")
        self.out.delete("1.0", "end")
        self.out.insert("1.0", text)
        self.out.configure(state="disabled")

    def decode_text(self, raw):
        try:
            self.show(vlcr_codec.decode(raw))
        except ValueError as ex:
            self.show("")
            messagebox.showerror("Chyba", str(ex))

    def decode_pasted(self):
        self.decode_text(self.inp.get("1.0", "end"))

    def load(self, path):
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                raw = f.read()
        except OSError as ex:
            messagebox.showerror("Chyba", "Soubor nelze otevřít:\n%s" % ex)
            return
        self.inp.delete("1.0", "end")
        self.inp.insert("1.0", raw)
        self.decode_text(raw)

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Otevřít soubor .vlcr",
            filetypes=[("Soubory VLCR", "*.vlcr"), ("Všechny soubory", "*.*")])
        if path:
            self.load(path)

    def copy_msg(self):
        self.clipboard_clear()
        self.clipboard_append(self.out.get("1.0", "end").strip())

    def clear(self):
        self.inp.delete("1.0", "end")
        self.show("")


if __name__ == "__main__":
    Viewer(sys.argv[1] if len(sys.argv) > 1 else None).mainloop()
