import os
import json
import base64
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog

# =============================
# Variables globales
# =============================
KEY = ""
KEY_BYTES = None
ROOT = ""

valid_extensions = [".rpgmvp", ".rpgmvo", ".rpgmvm", ".png_", ".ogg_", ".m4a_", ".rpgmz"]

HEADER_LEN = 16
PNG_HEADER = b'\x89PNG\r\n\x1a\n'
JPG_HEADER = b'\xFF\xD8'

# =============================
# Funciones de desencriptado
# =============================
def decrypt_file(path):
    global KEY, KEY_BYTES

    if path.suffix.lower() not in valid_extensions:
        return

    try:
        # =============================
        # Validar key primero
        # =============================
        if not KEY_BYTES:
            print("⚠️ KEY_BYTES vacía")
            return

        key_bytes = KEY_BYTES

        if len(key_bytes) < HEADER_LEN:
            print("❌ KEY demasiado corta")
            return

        # =============================
        # Leer archivo
        # =============================
        if not path.exists():
            return

        file_size = path.stat().st_size
        if file_size <= HEADER_LEN:
            return

        with open(path, "rb") as f:
            data = bytearray(f.read())

        # =============================
        # Detectar si ya está desencriptado
        # =============================
        payload_preview = data[HEADER_LEN:HEADER_LEN+8]
        if payload_preview == PNG_HEADER or payload_preview == JPG_HEADER:
            return
        # =============================
        # Remover fake header
        # =============================
        payload = data[HEADER_LEN:]

        if not payload:
            return

        # =============================
        # XOR solo primeros 16 bytes
        # =============================
        limit = min(HEADER_LEN, len(payload))
        for i in range(limit):
            payload[i] ^= key_bytes[i]

        # =============================
        # Detectar extensión destino
        # =============================
        folder = path.parent.name.lower()

        if folder in ["img", "pictures", "characters", "tilesets", "sv_actors", "sv_enemies"]:
            new_ext = ".png"
        elif folder in ["audio", "bgm", "bgs", "se", "me"]:
            new_ext = ".ogg"
        else:
            new_ext = ".png"
        new_path = path.with_suffix(new_ext)
        # =============================
        # En caso de key incorrecta
        # =============================
        if new_ext == ".png" and not payload.startswith(PNG_HEADER):
            print(f"⚠️ Posible key incorrecta en {path.name}")

        # =============================
        # Evitar sobrescribir si existe
        # =============================
        if new_path.exists():
            return

        # =============================
        # Guardar archivo
        # =============================
        with open(new_path, "wb") as f:
            f.write(payload)

    except PermissionError:
        print(f"❌ Sin permisos: {path}")
    except Exception as e:
        print(f"❌ Error en {path}: {e}")


def decrypt_all(progress_bar, status_label):
    files = [f for f in Path(ROOT).rglob("*") if f.suffix.lower() in valid_extensions]

    total = len(files)
    if total == 0:
        messagebox.showinfo("Info", "No se encontraron archivos cifrados.")
        return

    progress_bar["maximum"] = total

    for i, file in enumerate(files, 1):
        decrypt_file(file)
        progress_bar["value"] = i
        status_label.config(text=f"Procesando {i}/{total}")
        status_label.update()

    messagebox.showinfo("Listo", "¡Desencriptación completa!")

# =============================
# GUI acciones
# =============================
def select_system():
    global KEY, KEY_BYTES
    path = filedialog.askopenfilename(
        title="Seleccionar System.json",
        filetypes=[("JSON files", "*.json")]
    )
    if not path:
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        KEY = data.get("encryptionKey", "").strip().upper()
        KEY_BYTES = bytes.fromhex(KEY)

        if not KEY:
            messagebox.showerror("Error", "No se encontró encryptionKey.")
            return

        if len(KEY) != 32:
            messagebox.showerror("Error", "La key debe tener 32 caracteres hex.")
            return

        # rellenar campo visual
        key_entry.delete(0, tk.END)
        key_entry.insert(0, KEY)

        system_label.config(text="System.json cargado ✅")

    except Exception as e:
        messagebox.showerror("Error", str(e))


def select_root():
    global ROOT
    path = filedialog.askdirectory(title="Seleccionar carpeta del juego")
    if not path:
        return

    ROOT = path
    root_label.config(text="Carpeta seleccionada ✅")


def start_decrypt():
    global KEY, KEY_BYTES

    entry_key = key_entry.get().strip().upper()
    if entry_key:
        try:
            bytes.fromhex(entry_key)
        except ValueError:
            messagebox.showerror("Key inválida", "La key no es hexadecimal válida.")
            return

        if len(entry_key) != 32:
            messagebox.showerror("Key inválida", "La key debe tener 32 caracteres hex.")
            return

        KEY = entry_key
        KEY_BYTES = bytes.fromhex(KEY)

    if not KEY:
        messagebox.showwarning("Falta key", "Selecciona System.json o pega la key.")
        return

    if not ROOT:
        messagebox.showwarning("Falta carpeta", "Selecciona la carpeta del juego")
        return

    thread = threading.Thread(
        target=decrypt_all,
        args=(progress, status),
        daemon=True
    )
    thread.start()


def use_manual_key():
    global KEY, KEY_BYTES
    manual_key = key_entry.get().strip().upper()

    if not manual_key:
        messagebox.showwarning("Key vacía", "Ingresa una encryptionKey.")
        return

    try:
        bytes.fromhex(manual_key)
    except ValueError:
        messagebox.showerror("Key inválida", "La key no es hexadecimal válida.")
        return

    if len(manual_key) != 32:
        messagebox.showerror("Key inválida", "La key debe tener 32 caracteres hex.")
        return

    KEY = manual_key
    KEY_BYTES = bytes.fromhex(KEY)
    system_label.config(text="Key manual cargada ✅")

# =============================
# Ventana principal
# =============================
app = tk.Tk()
app.title("RPG MAKER TOOL by Vuistaz v1.0")
app.geometry("420x260")
app.resizable(False, False)

title = tk.Label(app, text="RPG MAKER TOOL", font=("Segoe UI", 14, "bold"))
title.pack(pady=10)

tk.Button(app, text="Seleccionar System.json", command=select_system).pack(pady=5)
system_label = tk.Label(app, text="No cargado")
system_label.pack()

key_frame = tk.Frame(app)
key_frame.pack(pady=5)

tk.Label(key_frame, text="Encryption Key:").pack(side="left")

key_entry = tk.Entry(key_frame, width=32)
key_entry.pack(side="left", padx=5)

tk.Button(key_frame, text="Usar key manual", command=use_manual_key).pack(side="left", padx=5)

tk.Button(app, text="Seleccionar carpeta del juego", command=select_root).pack(pady=5)
root_label = tk.Label(app, text="No seleccionada")
root_label.pack()

tk.Button(app, text="🚀 Desencriptar", command=start_decrypt).pack(pady=10)

progress = ttk.Progressbar(app, length=300)
progress.pack(pady=5)

status = tk.Label(app, text="Esperando...")
status.pack()

app.mainloop()
