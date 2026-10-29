#!/usr/bin/env python3
"""StitchChart desktop shell (tkinter).
Pick a photo -> print-ready cross-stitch pattern pack."""
import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stitch_chart import run_stitchchart


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("StitchChart — Photo to Cross-Stitch Pattern Pack")
        self.geometry("700x580")
        self.image = tk.StringVar()
        self.width = tk.StringVar(value="100")
        self.colors = tk.StringVar(value="30")
        self.fabric = tk.StringVar(value="14")
        tk.Label(self, text="Photo (JPG / PNG):").pack(anchor="w", padx=12, pady=(12, 2))
        row = tk.Frame(self)
        row.pack(fill="x", padx=12)
        tk.Entry(row, textvariable=self.image).pack(side="left", fill="x", expand=True)
        tk.Button(row, text="Browse…", command=self.pick).pack(side="left", padx=6)
        tk.Label(self, text="Pattern width (stitches):").pack(anchor="w", padx=12, pady=(10, 2))
        ttk.Combobox(self, textvariable=self.width, values=["60", "80", "100", "120", "150", "200"],
                     state="readonly").pack(fill="x", padx=12)
        tk.Label(self, text="Max colours (DMC):").pack(anchor="w", padx=12, pady=(10, 2))
        ttk.Combobox(self, textvariable=self.colors, values=["12", "20", "30", "45", "60"],
                     state="readonly").pack(fill="x", padx=12)
        tk.Label(self, text="Fabric count (for finished size):").pack(anchor="w", padx=12, pady=(10, 2))
        ttk.Combobox(self, textvariable=self.fabric, values=["11", "14", "16", "18"],
                     state="readonly").pack(fill="x", padx=12)
        self.btn = tk.Button(self, text="Build Pattern Pack & Verify", command=self.run, height=2)
        self.btn.pack(pady=12)
        self.log = scrolledtext.ScrolledText(self, wrap="word")
        self.log.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.write("StitchChart converts your photo into a cross-stitch pattern pack:\n"
                   "a paginated symbol chart PDF, a DMC floss list with stitch counts\n"
                   "and skein estimates, and a CSV grid — then recounts every stitch\n"
                   "to prove the pattern adds up. Everything runs locally.\n")

    def write(self, s):
        self.log.insert("end", s)
        self.log.see("end")

    def pick(self):
        p = filedialog.askopenfilename(
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp"), ("All files", "*.*")])
        if p:
            self.image.set(p)

    def run(self):
        if not self.image.get():
            messagebox.showerror("StitchChart", "Pick a photo first.")
            return
        self.btn.config(state="disabled")
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self):
        try:
            outdir = os.path.join(os.path.dirname(os.path.abspath(self.image.get())),
                                  "stitchchart_output")
            s = run_stitchchart(self.image.get(), outdir,
                                width_stitches=int(self.width.get()),
                                max_colors=int(self.colors.get()),
                                fabric_count=int(self.fabric.get()))
            w, h = s["grid_size"]
            self.write(f"\nDone. Grid {w} x {h} = {w * h} stitches, {s['colors']} DMC colours.\n"
                       f"Verification: {'PASS' if s['verdict'] else 'FAIL — see report'}\n"
                       f"Pattern PDF: {s['pdf_path']}\nGrid CSV: {s['csv_path']}\n"
                       f"Report: {s['report_path']}\n")
        except Exception as e:
            self.write(f"\nError: {e}\n")
        finally:
            self.btn.config(state="normal")


if __name__ == "__main__":
    App().mainloop()
