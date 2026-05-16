import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from PIL import Image, ImageTk
import segno
import io
import os


def create_sepa_qr(name, iban, amount, reason, bic=""):
    amount_str = f"EUR{float(amount):.2f}"
    payload = [
        "BCD",
        "002",
        "1",
        "SCT",
        bic,
        name,
        iban.replace(" ", ""),
        amount_str,
        "",
        "",
        reason,
        ""
    ]
    qr_data = "\n".join(payload)
    qr = segno.make(qr_data, error='M')
    return qr


class SepaQRApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SEPA QR-Code Generator")
        self.resizable(False, False)
        self.configure(bg="#F5F5F0")

        self._qr_image = None
        self._qr_bytes = None
        self._build_ui()

    def _build_ui(self):
        FONT = ("Helvetica Neue", 11)
        FONT_LABEL = ("Helvetica Neue", 10)
        FONT_BOLD = ("Helvetica Neue", 11, "bold")
        BG = "#F5F5F0"
        CARD = "#FFFFFF"
        BORDER = "#DDDDD8"
        TEXT = "#1A1A18"
        MUTED = "#6B6B67"
        ACCENT = "#1A1A18"
        BTN_FG = "#FFFFFF"
        BTN_SAVE_FG = "#1A1A18"

        outer = tk.Frame(self, bg=BG, padx=24, pady=24)
        outer.pack()

        # --- Header ---
        header = tk.Frame(outer, bg=BG)
        header.grid(row=0, column=0, sticky="w", pady=(0, 16))
        tk.Label(header, text="SEPA Überweisung", font=("Helvetica Neue", 18, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")

        # --- Form card ---
        card = tk.Frame(outer, bg=CARD, relief="flat",
                        highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=1, column=0, sticky="ew")

        form = tk.Frame(card, bg=CARD, padx=20, pady=20)
        form.pack(fill="x")

        def labeled_entry(parent, row, label, placeholder, colspan=1, col=0, width=28):
            frame = tk.Frame(parent, bg=CARD)
            frame.grid(row=row, column=col, columnspan=colspan,
                       sticky="ew", padx=(0, 8 if col == 0 and colspan == 1 else 0), pady=5)
            tk.Label(frame, text=label, font=FONT_LABEL, fg=MUTED, bg=CARD,
                     anchor="w").pack(fill="x")
            entry = tk.Entry(frame, font=FONT, fg=TEXT, bg="#FAFAF8",
                             relief="flat", highlightbackground=BORDER,
                             highlightthickness=1, width=width, insertbackground=TEXT)
            entry.pack(fill="x", ipady=6)
            entry.insert(0, placeholder)
            entry.config(fg=MUTED)

            def on_focus_in(e):
                if entry.get() == placeholder:
                    entry.delete(0, "end")
                    entry.config(fg=TEXT)

            def on_focus_out(e):
                if entry.get() == "":
                    entry.insert(0, placeholder)
                    entry.config(fg=MUTED)

            entry.bind("<FocusIn>", on_focus_in)
            entry.bind("<FocusOut>", on_focus_out)
            return entry, placeholder

        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        self._name_entry, self._name_ph = labeled_entry(
            form, 0, "Empfänger Name", "Max Mustermann", colspan=2, col=0, width=56)
        self._iban_entry, self._iban_ph = labeled_entry(
            form, 1, "IBAN", "DE89 3704 0044 0532 0130 00", colspan=2, col=0, width=56)
        self._bic_entry, self._bic_ph = labeled_entry(
            form, 2, "BIC (optional)", "", colspan=1, col=0, width=26)
        self._amount_entry, self._amount_ph = labeled_entry(
            form, 2, "Betrag (EUR)", "0.00", colspan=1, col=1, width=26)
        self._reason_entry, self._reason_ph = labeled_entry(
            form, 3, "Verwendungszweck", "Rechnung 2024-001", colspan=2, col=0, width=56)

        # --- Buttons ---
        btn_frame = tk.Frame(outer, bg=BG)
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        btn_frame.columnconfigure(0, weight=1)
        btn_frame.columnconfigure(1, weight=1)

        self._btn_generate = tk.Button(
            btn_frame, text="⬛  QR-Code generieren",
            font=FONT_BOLD, fg=BTN_FG, bg=ACCENT,
            relief="flat", cursor="hand2", padx=16, pady=10,
            command=self._generate,
            activebackground="#333330", activeforeground=BTN_FG
        )
        self._btn_generate.grid(row=0, column=0, sticky="ew", padx=(0, 6))

        self._btn_save = tk.Button(
            btn_frame, text="↓  QR-Code speichern",
            font=FONT_BOLD, fg=BTN_SAVE_FG, bg=CARD,
            relief="flat", cursor="hand2", padx=16, pady=10,
            command=self._save, state="disabled",
            highlightbackground=BORDER, highlightthickness=1,
            activebackground="#EDEDEA"
        )
        self._btn_save.grid(row=0, column=1, sticky="ew", padx=(6, 0))

        # --- Preview ---
        preview_outer = tk.Frame(outer, bg=BG)
        preview_outer.grid(row=3, column=0, pady=(16, 0))

        self._preview_frame = tk.Frame(
            preview_outer, bg=CARD, width=220, height=220,
            highlightbackground=BORDER, highlightthickness=1
        )
        self._preview_frame.pack()
        self._preview_frame.pack_propagate(False)

        self._placeholder_label = tk.Label(
            self._preview_frame,
            text="QR-Code erscheint hier",
            font=FONT_LABEL, fg=MUTED, bg=CARD
        )
        self._placeholder_label.place(relx=0.5, rely=0.5, anchor="center")

        self._qr_label = tk.Label(self._preview_frame, bg=CARD)

    def _get_field(self, entry, placeholder):
        val = entry.get().strip()
        return "" if val == placeholder else val

    def _generate(self):
        name = self._get_field(self._name_entry, self._name_ph)
        iban = self._get_field(self._iban_entry, self._iban_ph)
        amount = self._get_field(self._amount_entry, self._amount_ph)
        reason = self._get_field(self._reason_entry, self._reason_ph)
        bic = self._get_field(self._bic_entry, self._bic_ph)

        if not name:
            return messagebox.showerror("Fehler", "Bitte Empfängername eingeben.")
        if not iban:
            return messagebox.showerror("Fehler", "Bitte IBAN eingeben.")
        if not amount:
            return messagebox.showerror("Fehler", "Bitte Betrag eingeben.")
        try:
            float_amount = float(amount.replace(",", "."))
            if float_amount <= 0:
                raise ValueError
        except ValueError:
            return messagebox.showerror("Fehler", "Bitte gültigen Betrag eingeben.")

        try:
            qr = create_sepa_qr(name, iban, float_amount, reason, bic)
        except Exception as e:
            return messagebox.showerror("Fehler beim Generieren", str(e))

        buf = io.BytesIO()
        qr.save(buf, kind="png", scale=8)
        self._qr_bytes = buf.getvalue()
        buf.seek(0)

        img = Image.open(buf).resize((200, 200), Image.NEAREST)
        self._qr_image = ImageTk.PhotoImage(img)

        self._placeholder_label.place_forget()
        self._qr_label.config(image=self._qr_image)
        self._qr_label.place(relx=0.5, rely=0.5, anchor="center")

        self._btn_save.config(state="normal")

    def _save(self):
        if not self._qr_bytes:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG-Bild", "*.png")],
            initialfile="ueberweisung.png",
            title="QR-Code speichern"
        )
        if path:
            with open(path, "wb") as f:
                f.write(self._qr_bytes)
            messagebox.showinfo("Gespeichert", f"QR-Code gespeichert:\n{path}")


if __name__ == "__main__":
    app = SepaQRApp()
    app.mainloop()