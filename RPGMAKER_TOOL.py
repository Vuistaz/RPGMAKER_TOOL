# =======================================================================
# CHANGELOG
# =======================================================================
# V1.0 First release
# V1.1:
#⚙️ Optimizaciones de Lógica y CódigoCorrección de Bugs en la Interfaz Dinámica: 
#En la version 1.0, al cargar System.json o la clave manual, se intentaba actualizar el texto de elementos que aún no existían o que no se refrescaban correctamente si el usuario cambiaba de acción. 
#Ahora, la función centralizada refresh_ui_text() se encarga de revaluar y mantener sincronizados los estados visuales en todo momento.
#Simplificación en el Manejo de Bytes: 
#Eliminé la importación de la librería base64, ya que la conversión de la clave hexadecimal a bytes se realiza de forma nativa y directa con bytes.
#fromhex(), ahorrando recursos innecesarios en memoria.
#Control de Errores Centralizado (Try-Catch): 
#Se unificaron los bloques de validación al presionar "Desencriptar". 
#Ahora, si el usuario ingresa una clave manualmente en el campo de texto y presiona directamente el botón principal de desencriptado, el programa valida la estructura hexadecimal antes de lanzar el hilo de procesamiento, evitando cierres inesperados o estados corruptos.
#🧵 Mejoras en la Experiencia de Usuario 
#(UX)Actualización Fluida de la Barra de Progreso: 
#La barra de progreso de customtkinter trabaja con valores decimales de 0.0 a 1.0. 
#Modifiqué el ciclo de procesamiento para calcular dinámicamente el progreso exacto (i / total) y forzar la actualización de la interfaz con app.update_idletasks(). 
#Esto evita que la ventana se congele visualmente mientras trabaja.
#Restauración de Estados al Finalizar: 
#Al terminar la desencriptación (o si el proceso se detiene porque no se detectaron archivos), el estado de la aplicación se limpia de forma automática y vuelve a mostrar el mensaje "Esperando..." (o "Waiting..."), dejando la herramienta lista para una nueva tanda de archivos sin necesidad de reiniciar el programa.
#Distribución Espacial Mejorada: 
#Se redimensionó la ventana a 460x360 px para dar suficiente aire a los textos informativos en ambos idiomas, asegurando que ninguna ruta de archivo o mensaje de error quede cortado en los márgenes de la pantalla.
import os
import json
import threading
from pathlib import Path
import customtkinter as ctk
from tkinter import filedialog, messagebox

# =====================================================================
# CONFIGURACIÓN DE TRADUCCIONES (Español / Inglés)
# =====================================================================
LITERALS = {
    "es": {
        "title": "HERRAMIENTA RPG MAKER",
        "btn_system": "Seleccionar System.json",
        "btn_folder": "Seleccionar carpeta del juego",
        "btn_decrypt": "Desencriptar",
        "btn_manual_key": "Usar key manual",
        "lbl_key": "Clave de cifrado:",
        "status_wait": "Esperando...",
        "status_done": "¡Desencriptación completa!",
        "status_no_files": "No se encontraron archivos cifrados.",
        "status_processing": "Procesando {}/{}",
        "err_no_key_found": "No se encontró encryptionKey.",
        "err_key_len": "La key debe tener 32 caracteres hex.",
        "err_invalid_hex": "La key no es hexadecimal válida.",
        "warn_missing_key": "Selecciona System.json o pega la key.",
        "warn_missing_root": "Selecciona la carpeta del juego.",
        "msg_system_loaded": "System.json cargado",
        "msg_manual_loaded": "Key manual cargada",
        "msg_folder_loaded": "Carpeta seleccionada"
    },
    "en": {
        "title": "RPG MAKER TOOL",
        "btn_system": "Select System.json",
        "btn_folder": "Select Game Folder",
        "btn_decrypt": "Decrypt Files",
        "btn_manual_key": "Use manual key",
        "lbl_key": "Encryption Key:",
        "status_wait": "Waiting...",
        "status_done": "Decryption complete!",
        "status_no_files": "No encrypted files found.",
        "status_processing": "Processing {}/{}",
        "err_no_key_found": "encryptionKey not found.",
        "err_key_len": "Key must be 32 hex characters.",
        "err_invalid_hex": "Key is not a valid hex string.",
        "warn_missing_key": "Select System.json or paste the key.",
        "warn_missing_root": "Select the game folder.",
        "msg_system_loaded": "System.json loaded",
        "msg_manual_loaded": "Manual key loaded",
        "msg_folder_loaded": "Folder selected"
    }
}

CURRENT_LANG = "es"

def t(key):
    return LITERALS[CURRENT_LANG].get(key, key)

# =====================================================================
# VARIABLES GLOBALES
# =====================================================================
KEY = ""
KEY_BYTES = None
ROOT = ""
valid_extensions = [".rpgmvp", ".rpgmvo", ".rpgmvm", ".png_", ".ogg_", ".m4a_", ".rpgmz"]
HEADER_LEN = 16
PNG_HEADER = b'\x89PNG\r\n\x1a\n'
JPG_HEADER = b'\xFF\xD8'

# =====================================================================
# LÓGICA DE DESENCRIPTADO
# =====================================================================
def decrypt_file(path):
    global KEY, KEY_BYTES
    if path.suffix.lower() not in valid_extensions:
        return
    try:
        if not KEY_BYTES:
            return
        key_bytes = KEY_BYTES
        if len(key_bytes) < HEADER_LEN:
            return
        if not path.exists():
            return
        file_size = path.stat().st_size
        if file_size <= HEADER_LEN:
            return
            
        with open(path, "rb") as f:
            data = bytearray(f.read())
            
        payload_preview = data[HEADER_LEN:HEADER_LEN+8]
        if payload_preview == PNG_HEADER or payload_preview == JPG_HEADER:
            return
            
        payload = data[HEADER_LEN:]
        if not payload:
            return
            
        limit = min(HEADER_LEN, len(payload))
        for i in range(limit):
            payload[i] ^= key_bytes[i]
            
        folder = path.parent.name.lower()
        if folder in ["img", "pictures", "characters", "tilesets", "sv_actors", "sv_enemies"]:
            new_ext = ".png"
        elif folder in ["audio", "bgm", "bgs", "se", "me"]:
            new_ext = ".ogg"
        else:
            new_ext = ".png"
            
        new_path = path.with_suffix(new_ext)
        if new_ext == ".png" and not payload.startswith(PNG_HEADER):
            print(f"Posible key incorrecta en {path.name}")
            
        if new_path.exists():
            return
            
        with open(new_path, "wb") as f:
            f.write(payload)
    except Exception as e:
        print(f"Error en {path}: {e}")

def decrypt_all_thread():
    files = [f for f in Path(ROOT).rglob("*") if f.suffix.lower() in valid_extensions]
    total = len(files)
    if total == 0:
        messagebox.showinfo("Info", t("status_no_files"))
        status_label.configure(text=t("status_wait"))
        return
        
    progress_bar.set(0)
    for i, file in enumerate(files, 1):
        decrypt_file(file)
        progress_bar.set(i / total)
        status_label.configure(text=t("status_processing").format(i, total))
        app.update_idletasks()
        
    messagebox.showinfo("Listo", t("status_done"))
    status_label.configure(text=t("status_wait"))

# =====================================================================
# ACCIONES DE LA INTERFAZ
# =====================================================================
def change_language(choice):
    global CURRENT_LANG
    CURRENT_LANG = "es" if choice in ["Español", "Spanish"] else "en"
    refresh_ui_text()

def refresh_ui_text():
    title_label.configure(text=t("title"))
    btn_system.configure(text=t("btn_system"))
    lbl_key.configure(text=t("lbl_key"))
    btn_manual.configure(text=t("btn_manual_key"))
    btn_folder.configure(text=t("btn_folder"))
    btn_decrypt.configure(text=t("btn_decrypt"))
    status_label.configure(text=t("status_wait"))
    
    # Actualizar estados dinámicos si ya contienen datos
    if KEY:
        system_label.configure(text=t("msg_system_loaded"))
    if ROOT:
        root_label.configure(text=t("msg_folder_loaded"))

def select_system():
    global KEY, KEY_BYTES
    path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
    if not path:
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        KEY = data.get("encryptionKey", "").strip().upper()
        if not KEY:
            messagebox.showerror("Error", t("err_no_key_found"))
            return
        if len(KEY) != 32:
            messagebox.showerror("Error", t("err_key_len"))
            return
            
        KEY_BYTES = bytes.fromhex(KEY)
        key_entry.delete(0, ctk.END)
        key_entry.insert(0, KEY)
        system_label.configure(text=t("msg_system_loaded"))
    except Exception as e:
        messagebox.showerror("Error", str(e))

def use_manual_key():
    global KEY, KEY_BYTES
    manual_key = key_entry.get().strip().upper()
    if not manual_key:
        return
    try:
        bytes.fromhex(manual_key)
    except ValueError:
        messagebox.showerror("Error", t("err_invalid_hex"))
        return
    if len(manual_key) != 32:
        messagebox.showerror("Error", t("err_key_len"))
        return
    KEY = manual_key
    KEY_BYTES = bytes.fromhex(KEY)
    system_label.configure(text=t("msg_manual_loaded"))

def select_root():
    global ROOT
    path = filedialog.askdirectory()
    if not path:
        return
    ROOT = path
    root_label.configure(text=t("msg_folder_loaded"))

def start_decrypt():
    global KEY, KEY_BYTES
    entry_key = key_entry.get().strip().upper()
    if entry_key:
        try:
            bytes.fromhex(entry_key)
        except ValueError:
            messagebox.showerror("Error", t("err_invalid_hex"))
            return
        if len(entry_key) != 32:
            messagebox.showerror("Error", t("err_key_len"))
            return
        KEY = entry_key
        KEY_BYTES = bytes.fromhex(KEY)
        
    if not KEY:
        messagebox.showwarning("Warning", t("warn_missing_key"))
        return
    if not ROOT:
        messagebox.showwarning("Warning", t("warn_missing_root"))
        return
        
    threading.Thread(target=decrypt_all_thread, daemon=True).start()

# =====================================================================
# DISEÑO DE LA INTERFAZ (CustomTkinter - Dark Mode)
# =====================================================================
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.title("RPG MAKER TOOL by Vuistaz v1.1")
app.geometry("460x360")
app.resizable(False, False)

# Selector de Idioma (Arriba a la derecha)
lang_frame = ctk.CTkFrame(app, fg_color="transparent")
lang_frame.pack(fill="x", padx=15, pady=(10, 0))
lang_menu = ctk.CTkOptionMenu(lang_frame, values=["Español", "English"], command=change_language, width=90)
lang_menu.pack(side="right")

# Título Principal
title_label = ctk.CTkLabel(app, text="", font=("Segoe UI", 18, "bold"))
title_label.pack(pady=(0, 10))

# Sección System.json
btn_system = ctk.CTkButton(app, text="", command=select_system, width=220)
btn_system.pack(pady=5)
system_label = ctk.CTkLabel(app, text="", text_color="gray")
system_label.pack()

# Sección de la Key Manual
key_frame = ctk.CTkFrame(app, fg_color="transparent")
key_frame.pack(pady=5, padx=15, fill="x")
lbl_key = ctk.CTkLabel(key_frame, text="")
lbl_key.pack(side="left", padx=5)
key_entry = ctk.CTkEntry(key_frame, width=180)
key_entry.pack(side="left", padx=5, expand=True, fill="x")
btn_manual = ctk.CTkButton(key_frame, text="", command=use_manual_key, width=110)
btn_manual.pack(side="left", padx=5)

# Sección de Carpeta del Juego
btn_folder = ctk.CTkButton(app, text="", command=select_root, width=220)
btn_folder.pack(pady=5)
root_label = ctk.CTkLabel(app, text="", text_color="gray")
root_label.pack()

# Botón Desencriptar
btn_decrypt = ctk.CTkButton(app, text="", command=start_decrypt, fg_color="#2c82c9", hover_color="#1f5c8e", width=220, font=("Segoe UI", 13, "bold"))
btn_decrypt.pack(pady=15)

# Progreso y Estado
progress_bar = ctk.CTkProgressBar(app, width=350)
progress_bar.pack(pady=5)
progress_bar.set(0)

status_label = ctk.CTkLabel(app, text="")
status_label.pack()

# Inicializar textos en español
refresh_ui_text()

app.mainloop()


