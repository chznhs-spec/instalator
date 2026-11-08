#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""VLCR Stahovač 2000 – záměrně otravný pětikrokový instalátor.

Stáhne (= rozbalí) druhou aplikaci "VLCR Prohlížeč", ve které jde otevřít .vlcr.
Pro rychlé testování spusťte s proměnnou prostředí VLCR_FAST=1 (25× rychlejší).
"""
import math
import os
import random
import shutil
import subprocess
import sys
import tarfile
import threading
import tkinter as tk
import urllib.request
from tkinter import filedialog, messagebox, ttk

import vlcr_codec

LOGO_URL = "https://vzdelanylid.cz/logo_VLCR.png"
SPEED = 25.0 if os.environ.get("VLCR_FAST") else 1.0

# Časování "stahování" v sekundách: fronta -> pomalý pruh -> zaseknuto na 99 %
QUEUE_END, BAR_END, HOLD_END = 40.0, 100.0, 125.0
TERMS_COUNTDOWN = 12.0

UGLY_BG = ["#fafaf8"]
UGLY_FG = ["#000000"]
FONT_NAME = "Times New Roman"

TITLES = [
    "Ověření, že nejste robot",
    "Podmínky užívání (přečtěte všechny)",
    "Povinná registrace",
    "Stahování",
    "Dokončení",
]

CLAUSES = [
    "Uživatel bere na vědomí, že tlačítko 'Další' nemusí být tam, kde ho očekává.",
    "Poskytovatel neodpovídá za ztracený čas, ztracenou trpělivost ani ztracenou víru v lidstvo.",
    "Uživatel se zavazuje nedívat se na hodinky déle než šestkrát za minutu.",
    "Stahováním souhlasíte s tím, že budete souhlasit i s budoucími podmínkami, které ještě nevznikly.",
    "Kontrolní součet bude ověřen jiným kontrolním součtem, který ověří třetí kontrolní součet.",
    "Poskytovatel si vyhrazuje právo zpomalit stahování, pokud by bylo příliš rychlé.",
    "Veškeré bajty jsou stahovány ručně a jednotlivě, proto prosíme o shovívavost.",
    "Uživatel nesmí aplikaci používat k vytváření zpráv, které by byly příliš čitelné.",
    "V případě pochybností platí tyto podmínky, v případě nepochybností také.",
    "Soubory .vlcr jsou svou povahou záhadné a poskytovatel jejich záhadnost nepopírá.",
    "Spor ze smlouvy bude řešen křížovkou, nejlépe tajenkou o délce 14 písmen.",
    "Uživatel potvrzuje, že má po ruce dostatek čaje, kávy nebo jiné trpělivostní tekutiny.",
]

STATUS_MSGS = [
    "Načítání..."
]
HOLD_MSGS = [
    "Načítání..."
]
ETA_MSGS = [
    "Načítání..."
]


def resource_dir():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def terms_text():
    rnd = random.Random(42)
    parts = []
    for i in range(1, 61):
        parts.append("Článek %d.  %s" % (i, " ".join(rnd.choice(CLAUSES) for _ in range(3))))
    return "\n\n".join(parts) + "\n\nKonec podmínek."


def do_install(dest_root):
    """Skutečně 'nainstaluje' prohlížeč. Vrací (cílová složka, spouštěč, ukázkový soubor)."""
    target = os.path.join(dest_root, "VLCR_Prohlizec")
    os.makedirs(target, exist_ok=True)
    res = resource_dir()
    tar_path = os.path.join(res, "payload.tar.gz")
    if os.path.exists(tar_path):
        with tarfile.open(tar_path) as tf:
            try:
                tf.extractall(target, filter="data")
            except TypeError:  # starší Python bez parametru filter
                tf.extractall(target)
        if sys.platform == "darwin":
            name = "VLCR_Viewer.app"
        elif os.name == "nt":
            name = "VLCR_Viewer.exe"
        else:
            name = "VLCR_Viewer"
        launcher = os.path.join(target, name)
    else:  # záloha: běží se ze zdrojáků, zkopírují se .py soubory
        for f in ("vlcr_viewer.py", "vlcr_codec.py"):
            shutil.copy2(os.path.join(res, f), target)
        launcher = os.path.join(target, "vlcr_viewer.py")
    sample = os.path.join(target, "ukazka.vlcr")
    with open(sample, "w", encoding="utf-8") as fh:
        fh.write(vlcr_codec.encode(
            "Gratulujeme! Prošli jste všemi 5 kroky a rozluštili jste soubor .vlcr. "
            "Vzdělaný lid děkuje za Vaši trpělivost."))
    return target, launcher, sample


def launch_viewer(path):
    try:
        if path.endswith(".py"):
            py = sys.executable if not getattr(sys, "frozen", False) else (
                shutil.which("python3") or shutil.which("python"))
            subprocess.Popen([py, path])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen([path])
    except Exception as ex:
        messagebox.showerror("Spuštění selhalo", "Prohlížeč se nepodařilo spustit:\n%s" % ex)


class Installer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VLCR Stahovač – Instalační Průvodce Průvodce")
        self.geometry("680x530")
        self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.speed = SPEED
        self.step = 0
        self.s = {}
        self.install_result = None
        self.dest_choice = os.path.expanduser("~")
        self._after = None
        self.bg = random.choice(UGLY_BG)

        # logo (stahuje se na pozadí)
        self._logo_bytes = None
        self._logo_done = False
        self._logo_img = None
        self.logo_label = None
        threading.Thread(target=self._fetch_logo, daemon=True).start()

        self.header = tk.Frame(self)
        self.header.place(x=0, y=0, width=680, height=92)
        self.body = tk.Frame(self)
        self.body.place(x=10, y=98, width=660, height=365)

        btn = dict(font=(FONT_NAME, 10, "bold"), relief="ridge", bd=6)
        self.next_btn = tk.Button(self, text="Další >>", command=self.next_click, bg="#ffc654", **btn)
        self.back_btn = tk.Button(self, text="<< Zpět", command=self.back_click, bg="#ffc654", **btn)
        self.cancel_btn = tk.Button(self, text="Zrušit", command=self.cancel_click, bg="#ffc654", **btn)

        self.after(300, self._poll_logo)
        self.show_step(0)

    # ---------- pomocné ----------
    def lbl(self, parent, text, size=11, **kw):
        kw.setdefault("bg", self.bg)
        kw.setdefault("fg", random.choice(UGLY_FG))
        kw.setdefault("justify", "left")
        return tk.Label(parent, text=text, font=(FONT_NAME, size, "bold"), **kw)

    def later(self, ms, fn):
        self._after = self.after(ms, fn)

    def stop_timer(self):
        if self._after is not None:
            self.after_cancel(self._after)
            self._after = None

    def set_next(self, enabled):
        self.next_btn.configure(state="normal" if enabled else "disabled")

    # ---------- logo ----------
    def _fetch_logo(self):
        try:
            req = urllib.request.Request(LOGO_URL, headers={"User-Agent": "VLCR-Stahovac/2000"})
            with urllib.request.urlopen(req, timeout=10) as r:
                self._logo_bytes = r.read()
        except Exception:
            self._logo_bytes = None
        self._logo_done = True

    def _poll_logo(self):
        if not self._logo_done:
            self.after(300, self._poll_logo)
            return
        if self._logo_bytes:
            try:
                import base64
                img = tk.PhotoImage(data=base64.b64encode(self._logo_bytes))
                f = max(math.ceil(img.width() / 180), math.ceil(img.height() / 80), 1)
                self._logo_img = img.subsample(f, f) if f > 1 else img
            except tk.TclError:
                self._logo_img = None
        self.apply_logo()

    def apply_logo(self):
        lab = self.logo_label
        if lab is None or not lab.winfo_exists():
            return
        if self._logo_img is not None:
            lab.configure(image=self._logo_img, text="")
        elif self._logo_done:
            lab.configure(text="[ LOGO NEDOSTUPNÉ ]", image="")
        else:
            lab.configure(text="[ načítám logo… ]", image="")

    # ---------- navigace ----------
    def show_step(self, n):
        self.stop_timer()
        self.step = n
        self.s = {}
        self.bg = random.choice(UGLY_BG)
        self.configure(bg=self.bg)
        for fr in (self.header, self.body):
            fr.configure(bg=self.bg)
            for w in fr.winfo_children():
                w.destroy()

        left_first = n % 2 == 0
        self.logo_label = tk.Label(self.header, bg=self.bg, fg="#000000", font=(FONT_NAME, 9, "bold"))
        self.logo_label.place(relx=[0.02, 0.62, 0.30, 0.62, 0.02][n], y=4)
        self.apply_logo()
        tx = 0.62 if left_first else 0.02
        self.lbl(self.header, "KROK %d Z 5" % (n + 1), 14).place(relx=tx, y=6)
        self.lbl(self.header, TITLES[n], 11, wraplength=250).place(relx=tx, y=40)

        # tlačítka si každý krok mění místo
        self.next_btn.place(relx=0.70 if left_first else 0.04, y=475, width=170, height=40)
        self.cancel_btn.place(relx=0.04 if left_first else 0.70, y=475, width=170, height=40)
        self.back_btn.place(relx=0.40, y=480, width=110, height=30)
        self.next_btn.configure(text="Další >>")
        self.set_next(False)
        self.back_btn.configure(state="normal" if n in (1, 2) else "disabled")

        [self.step_robot, self.step_terms, self.step_register,
         self.step_download, self.step_done][n]()

    def next_click(self):
        if self.step == 4:
            self.finish()
        elif messagebox.askyesno("Potvrzení", "Opravdu chcete pokračovat na další krok?"):
            self.show_step(self.step + 1)

    def back_click(self):
        if messagebox.askyesno("Potvrzení", "Opravdu se chcete vrátit? Vše, co jste v tomto kroku udělali, se smaže."):
            self.show_step(self.step - 1)

    def cancel_click(self):
        if not messagebox.askyesno("Zrušení", "Opravdu chcete zrušit instalaci?"):
            return
        if not messagebox.askyesno("Zrušení", "Jste si naprosto jistý/á? Přijdete o veškerý postup."):
            return
        messagebox.showwarning(
            "Zrušení se nezdařilo",
            "Zrušení vyžaduje schválení oddělení pro zrušení.\n"
            "Vaše žádost je ve frontě na pozici č. %d.\n\n"
            "Pokud opravdu chcete odejít, zavřete okno křížkem." % random.randint(1000, 9999))

    def on_close(self):
        if messagebox.askyesno("Zavřít", "Opravdu chcete zavřít Průvodce Průvodce?"):
            self.destroy()

    # ---------- krok 1: robot ----------
    def step_robot(self):
        b = self.body
        s = self.s
        s.update(math_ok=False, clicks=0)
        self.lbl(b, "Než začneme, musíme ověřit, že nejste robot.\n"
                    , 11, wraplength=620).pack(pady=(6, 14))

        self.q = [random.randint(6, 19), random.randint(3, 9), random.randint(10, 99)]
        self.q_lbl = self.lbl(b, "", 16)
        self.q_lbl.pack()
        self._set_question()
        self.ans = tk.StringVar()
        tk.Entry(b, textvariable=self.ans, font=(FONT_NAME, 14), width=8, justify="center",
                 bg="#ffffaa").pack(pady=8)
        tk.Button(b, text="Zkontrolovat", font=(FONT_NAME, 10, "bold"), bg="#ffc654",
                  command=self.check_math).pack()
        self.math_status = self.lbl(b, "", 10)
        self.math_status.pack(pady=6)
        self.robot_btn = tk.Button(b, text="Nejsem robot (0/3)", state="disabled", bg="#ffc654",
                                   font=(FONT_NAME, 11, "bold"), relief="groove", bd=8,
                                   command=self.robot_click)
        self.robot_btn.pack(pady=14)

    def _set_question(self):
        a, bb, c = self.q
        self.q_lbl.configure(text="%d × %d + %d = ?" % (a, bb, c))

    def check_math(self):
        a, bb, c = self.q
        try:
            ok = int(self.ans.get().strip()) == a * bb + c
        except ValueError:
            ok = False
        if ok:
            self.s["math_ok"] = True
            self.math_status.configure(text="Správně.")
            self.robot_btn.configure(state="normal")
        else:
            self.q = [random.randint(6, 19), random.randint(3, 9), random.randint(10, 99)]
            self._set_question()
            self.ans.set("")
            self.math_status.configure(text="Ne, zkus to znovu.")

    def robot_click(self):
        texts = ["Nejsem robot (1/3)", "Nejsem robot (2/3)", "Nejsem robot (3/3)"]
        self.s["clicks"] += 1
        n = self.s["clicks"]
        if n >= 3:
            self.robot_btn.configure(text="Ověřeno", state="disabled")
            self.set_next(True)
        else:
            self.robot_btn.configure(text=texts[n])

    # ---------- krok 2: podmínky ----------
    def step_terms(self):
        b = self.body
        self.s.update(bottom=False, cd=None)
        frame = tk.Frame(b, bg=self.bg)
        frame.pack(pady=(2, 4))
        self.txt = tk.Text(frame, width=84, height=9, font=("Courier", 8), wrap="word",
                           bg="#ffffcc", fg="#990000")
        sb = tk.Scrollbar(frame, command=self.txt.yview, width=8)
        self.txt.configure(yscrollcommand=sb.set)
        self.txt.pack(side="left")
        sb.pack(side="left", fill="y")
        self.txt.insert("1.0", terms_text())
        self.txt.configure(state="disabled")

        self.vars = [tk.IntVar() for _ in range(3)]
        labels = ["Přečetl/a jsem všech 87 stran (prokazatelně dolistováno)",
                  "Souhlasím s podmínkami užívání",
                  "Souhlasím s tím, že souhlasím s podmínkami užívání"]
        self.cbs = []
        for var, text in zip(self.vars, labels):
            cb = tk.Checkbutton(b, text=text, variable=var, command=self.terms_changed,
                                state="disabled", bg=self.bg, activebackground=self.bg,
                                font=(FONT_NAME, 9, "bold"), fg=random.choice(UGLY_FG))
            cb.pack(anchor="w", padx=20)
            self.cbs.append(cb)
        self.cd_lbl = self.lbl(b, "Nejdřív dolistujte podmínky až na konec.", 10, wraplength=620)
        self.cd_lbl.pack(pady=8)
        self.later(200, self.tick_terms)

    def terms_changed(self):
        v = self.vars
        if not v[0].get():
            v[1].set(0)
        if not v[1].get():
            v[2].set(0)
        self.refresh_terms()

    def refresh_terms(self):
        v = self.vars
        self.cbs[0].configure(state="normal" if self.s["bottom"] else "disabled")
        self.cbs[1].configure(state="normal" if v[0].get() else "disabled")
        self.cbs[2].configure(state="normal" if v[1].get() else "disabled")

    def tick_terms(self):
        s = self.s
        if self.txt.yview()[1] >= 0.995:
            s["bottom"] = True
        self.refresh_terms()
        done = False
        if self.vars[2].get():
            s["cd"] = (TERMS_COUNTDOWN if s["cd"] is None else s["cd"]) - 0.2 * self.speed
            if s["cd"] <= 0:
                done = True
                self.cd_lbl.configure(text="Teď můžete pokračovat. Děkujeme za váš čas.")
            else:
                self.cd_lbl.configure(
                    text="Tlačítko Další se odemkne za %d s. Čtěte pozorně." % math.ceil(s["cd"]))
        else:
            s["cd"] = None
            self.cd_lbl.configure(
                text="Zaškrtněte všechna políčka popořadě." if s["bottom"]
                else "Nejdřív dolistujte podmínky až na konec.")
        self.set_next(done)
        self.later(200, self.tick_terms)

    # ---------- krok 3: registrace ----------
    def step_register(self):
        b = self.body
        self.s.update(dest="")
        self.code = "".join(random.choice("ABCDEFGHJKLMNPQRSTUVWXYZ23456789") for _ in range(8))
        self.name_v, self.how_v, self.code_v = tk.StringVar(), tk.StringVar(), tk.StringVar()

        self.lbl(b, "Vaše jméno", 10).pack(anchor="w", padx=20, pady=(4, 0))
        tk.Entry(b, textvariable=self.name_v, width=40, bg="#ffffaa").pack(anchor="w", padx=20)

        

        self.lbl(b, "Opište přesně kontrolní kód (rozlišují se velká a malá písmena):", 10).pack(
            anchor="w", padx=20, pady=(8, 0))
        tk.Label(b, text="   ".join(self.code), font=("Courier", 20, "bold overstrike"),
                 bg="#000000", fg="#33ff33").pack(anchor="w", padx=20, pady=2)
        tk.Entry(b, textvariable=self.code_v, width=14, bg="#ffc654").pack(anchor="w", padx=20)

        row = tk.Frame(b, bg=self.bg)
        row.pack(anchor="w", padx=20, pady=10)
        tk.Button(row, text="Vybrat složku (povinné)", bg="#ffc654", font=(FONT_NAME, 9, "bold"),
                  command=self.pick_dir).pack(side="left")
        self.dest_lbl = self.lbl(row, "  zatím nevybráno", 9, wraplength=380)
        self.dest_lbl.pack(side="left")

        for v in (self.name_v, self.how_v, self.code_v):
            v.trace_add("write", lambda *_: self.validate_register())

    def pick_dir(self):
        d = filedialog.askdirectory(title="Kam nainstalovat VLČR Prohlížeč?")
        if d:
            self.s["dest"] = d
            self.dest_choice = d
            self.dest_lbl.configure(text="  " + d)
            self.validate_register()

    def validate_register(self):
        ok = (len(self.name_v.get().strip()) >= 2 and self.code_v.get() == self.code and self.s["dest"])
        self.set_next(bool(ok))

    # ---------- krok 4: stahování ----------
    def step_download(self):
        b = self.body
        self.s.update(t=0.0, done=False, error=None)
        self.back_btn.configure(state="disabled")
        self.lbl(b, "Stahuji aplikaci: VLČR Prohlížeč™ (zdarma*)", 12).pack(pady=(6, 4))
        self.status = self.lbl(b, "Načítání...", 10, wraplength=620)
        self.status.pack(pady=4)
        self.queue_lbl = self.lbl(b, "", 12)
        self.queue_lbl.pack(pady=4)
        self.pbar = ttk.Progressbar(b, length=560, maximum=100)
        self.pbar.pack(pady=10)
        self.pct_lbl = self.lbl(b, "0 %", 14)
        self.pct_lbl.pack()
        self.eta_lbl = self.lbl(b, ETA_MSGS[0], 10)
        self.eta_lbl.pack(pady=6)
        self.lbl(b, "* Za zdarma se považuje to, co nestojí peníze.", 8).pack(side="bottom")
        self.later(100, self.tick_download)

    def tick_download(self):
        s = self.s
        s["t"] += 0.1 * self.speed
        t = s["t"]
        pct = 0.0
        if t < QUEUE_END:
            pos = max(1, 23 - int(t / QUEUE_END * 22))
            self.queue_lbl.configure(text="Jste %d. ve frontě na stahování" % pos)
            self.status.configure(text="Čekáte ve frontě. Nezavírejte okno.")
        elif t < BAR_END:
            x = (t - QUEUE_END) / (BAR_END - QUEUE_END)
            pct = max(0.0, 99 * x - 12 * max(0.0, math.sin(t * 0.8)) * (1 - x))
            self.queue_lbl.configure(text="Fronta vyřízena. Gratulujeme, jste na řadě!")
            self.status.configure(text=STATUS_MSGS[int(t / 6) % len(STATUS_MSGS)])
        elif t < HOLD_END:
            pct = 99.0
            self.queue_lbl.configure(text="Skoro hotovo!")
            self.status.configure(text=HOLD_MSGS[int(t / 5) % len(HOLD_MSGS)])
        else:
            try:
                s["result"] = do_install(self.dest_choice)
            except Exception as ex:  # noqa: BLE001
                s["error"] = str(ex)
            self.install_result = dict(s)
            self.pbar["value"] = 100
            self.pct_lbl.configure(text="100 %")
            self.queue_lbl.configure(text="Hotovo!")
            self.status.configure(text="Stahování dokončeno. Konečně.")
            self.eta_lbl.configure(text="")
            self.set_next(True)
            return
        self.pbar["value"] = pct
        self.pct_lbl.configure(text="%d %%" % pct)
        self.eta_lbl.configure(text=ETA_MSGS[int(t / 7) % len(ETA_MSGS)])
        self.later(100, self.tick_download)

    # ---------- krok 5: dokončení ----------
    def step_done(self):
        b = self.body
        r = self.install_result or {}
        self.next_btn.configure(text="Dokončit")
        self.set_next(True)
        self.back_btn.configure(state="disabled")
        self.launch_v = tk.IntVar(value=1)
        if r.get("error"):
            self.lbl(b, "Instalace se nezdařila:\n%s" % r["error"], 11, wraplength=620).pack(pady=20)
            return
        target, launcher, sample = r["result"]
        self.lbl(b, "Instalace je dokončena!", 13,
                 wraplength=620).pack(pady=(10, 6))
        self.lbl(b, "VLCR Prohlížeč je ve složce:\n%s" % target, 10, wraplength=620).pack(pady=4)
        self.lbl(b, "Ukázkový soubor ukazka.vlcr najdete ve stejné složce.\n"
                    "Otevřete ho v Prohlížeči (nebo jeho obsah vložte do okna).", 10,
                 wraplength=620).pack(pady=4)
        self._launcher = launcher
        tk.Checkbutton(b, text="Spustit VLCR Prohlížeč po dokončení", variable=self.launch_v,
                       bg=self.bg, activebackground=self.bg, font=(FONT_NAME, 10, "bold")).pack(pady=(14, 2))
        self.toolbar_v = tk.IntVar(value=1)
        tk.Checkbutton(b, text="Nainstalovat zbytečný panel nástrojů",
                       variable=self.toolbar_v, bg=self.bg, activebackground=self.bg,
                       font=(FONT_NAME, 9, "bold")).pack()

    def finish(self):
        if not messagebox.askyesno("Dokončit", "Opravdu chcete dokončit instalaci, kterou jste právě dokončili?"):
            return
        if getattr(self, "_launcher", None) and self.launch_v.get():
            launch_viewer(self._launcher)
        self.destroy()


if __name__ == "__main__":
    Installer().mainloop()
