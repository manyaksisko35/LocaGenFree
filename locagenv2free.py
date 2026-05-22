import customtkinter as ctk
import json
import csv
import threading
import os
import webbrowser
import sys
import re
import requests  # <-- GitHub'dan güncelleme çekmek için
import subprocess # <-- Yeni inen exe'yi başlatmak için
import urllib.request # <-- İnternetten yeni sürüm dosyasını indiren kütüphane
from tkinter import messagebox

# --- KRİTİK HATA YAKALAYICI ---
try:
    from deep_translator import GoogleTranslator
except ImportError as e:
    import tkinter as tk
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Kritik Hata", f"deep-translator modülü bulunamadı!\n\nHata: {e}")
    sys.exit()

# --- VERSİYON BİLGİM ---
CURRENT_VERSION = "v2.0.0-Free"

# --- NEON VOID (HACKER) TEMA AYARLARIM ---
ctk.set_appearance_mode("Dark")

COLOR_BG = "#05010a"
COLOR_CARD = "#0a0214"
COLOR_ACCENT = "#1a3a42"
COLOR_BTN_MAIN = "#00f0ff"
COLOR_BTN_MAIN_HOVER = "#00c3cc"
COLOR_BTN_SEC = "#a2a8d3"
COLOR_TEXT_MAIN = "#f0e6ff"
COLOR_TEXT_SUB = "#6a4b8c"
COLOR_SUCCESS = "#00ffcc"

class LocaGenAppFree(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title(f"LocaGen FREE - Terminal Edition [{CURRENT_VERSION}]")
        self.geometry("540x800") 
        self.configure(fg_color=COLOR_BG)
        self.resizable(False, True)
        self.attributes("-alpha", 0.0)

        target_icon = "app_icon.ico"
        if os.path.exists(target_icon):
            try: self.iconbitmap(target_icon)
            except: pass

        self.languages = {
            "🇺🇸 English": "en", "🇹🇷 Turkish": "tr", "🇩🇪 German": "de", "🇪🇸 Spanish": "es",
            "🇫🇷 French": "fr", "🇮🇹 Italian": "it"
        }

        self.loaded_data = None
        self.file_path = None
        self.file_extension = None
        
        self._setup_ui()
        self.cleanup_old_versions()
        self.fade_in()
        
        # Free sürüm güncelleme kontrolcüsü
        threading.Thread(target=self.check_for_updates, daemon=True).start()

    # ==========================================
    # 🔄 NİNJA AUTO-UPDATE (FREE SÜRÜM)
    # ==========================================
    def cleanup_old_versions(self):
        exe_name = sys.executable
        old_exe = exe_name.replace(".exe", "_old.exe")
        if os.path.exists(old_exe):
            try: os.remove(old_exe)
            except: pass

    def check_for_updates(self):
        try:
            # Free sürüm public repo olduğu için headers'a gerek yok
            api_url = "https://api.github.com/repos/manyaksisko35/LocaGenFree/releases/latest"
            response = requests.get(api_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data["tag_name"] != CURRENT_VERSION:
                    download_url = data["assets"][0]["browser_download_url"]
                    self.after(2000, self.prompt_update, data["tag_name"], download_url)
        except Exception as e:
            print("Update Check Failed:", e)

    def prompt_update(self, latest_version, download_url):
        if messagebox.askyesno("Update LocaGen Free", f"New version {latest_version} available. Update now?"):
            self.update_status(f"Downloading {latest_version}...", COLOR_BTN_MAIN)
            self.btn_start.configure(state="disabled")
            threading.Thread(target=self.perform_update, args=(download_url,), daemon=True).start()

    def perform_update(self, download_url):
        try:
            exe_path = sys.executable
            old_path = exe_path.replace(".exe", "_old.exe")
            response = requests.get(download_url)
            os.rename(exe_path, old_path)
            with open(exe_path, "wb") as f: f.write(response.content)
            subprocess.Popen([exe_path])
            sys.exit(0)
        except Exception as e:
            if os.path.exists(old_path) and not os.path.exists(exe_path): os.rename(old_path, exe_path)
            self.after(0, lambda: messagebox.showerror("Update Error", f"Failed: {e}"))
            self.after(0, lambda: self.btn_start.configure(state="normal"))

    # ==========================================
    # 🎬 ANİMASYON MOTORLARI
    # ==========================================
    def fade_in(self):
        alpha = self.attributes("-alpha")
        if alpha < 1.0:
            alpha += 0.05
            self.attributes("-alpha", min(alpha, 1.0))
            self.after(20, self.fade_in)

    def type_text_animation(self, widget, text, index=0):
        if index < len(text):
            widget.configure(text=text[:index+1] + "_")
            self.after(25, self.type_text_animation, widget, text, index+1)
        else:
            widget.configure(text=text)

    def update_status(self, text, color):
        self.status_label.configure(text_color=color)
        self.type_text_animation(self.status_label, text)

    def bind_hover_animation(self, widget, base_text, style="file"):
        widget.bind("<Enter>", lambda e: self.play_hover(widget, base_text, style, True))
        widget.bind("<Leave>", lambda e: self.play_hover(widget, base_text, style, False))

    def play_hover(self, widget, base_text, style, is_enter, step=0):
        try:
            if widget.cget("state") == "disabled": return
        except: pass
        if hasattr(widget, "_hover_anim"): self.after_cancel(widget._hover_anim)
        if style == "file": frames_in = [f"[ {base_text} ]", f"> {base_text} <", f">> {base_text} <<"]
        elif style == "start": frames_in = [f"{base_text}", f"> {base_text} <", f">> {base_text} <<"]
        frames = frames_in if is_enter else list(reversed(frames_in))
        if step < len(frames):
            widget.configure(text=frames[step])
            widget._hover_anim = self.after(35, self.play_hover, widget, base_text, style, is_enter, step+1)

    # ==========================================
    # 💻 ARAYÜZ (UI) KURULUMU
    # ==========================================
    def _setup_ui(self):
        font_h1 = ("Consolas", 34, "bold")
        font_h2 = ("Consolas", 12, "bold")
        font_p = ("Consolas", 13)
        font_small = ("Consolas", 11)

        self.frame_header = ctk.CTkFrame(self, fg_color="transparent")
        self.frame_header.pack(pady=(40, 25))
        self.lbl_title = ctk.CTkLabel(self.frame_header, text="LOCAGEN_FREE", font=font_h1, text_color=COLOR_BTN_MAIN)
        self.lbl_title.pack()
        self.lbl_subtitle = ctk.CTkLabel(self.frame_header, text="", font=font_p, text_color=COLOR_TEXT_SUB)
        self.lbl_subtitle.pack(pady=(0, 0))
        self.type_text_animation(self.lbl_subtitle, f"sys.basic_translator_{CURRENT_VERSION}")

        self.card_file = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_ACCENT)
        self.card_file.pack(pady=15, padx=25, fill="x")
        self.lbl_step1 = ctk.CTkLabel(self.card_file, text=">_ SOURCE_FILE (JSON ONLY)", font=font_h2, text_color=COLOR_BTN_MAIN)
        self.lbl_step1.pack(pady=(20, 5), padx=20, anchor="w")
        self.btn_load = ctk.CTkButton(self.card_file, text="[ SELECT_FILE ]", command=self.load_file, 
                                      fg_color="transparent", border_width=1, border_color=COLOR_BTN_SEC, hover_color=COLOR_ACCENT, 
                                      text_color=COLOR_BTN_SEC, height=50, corner_radius=5, font=font_p)
        self.btn_load.pack(pady=10, padx=20, fill="x")
        self.bind_hover_animation(self.btn_load, "SELECT_FILE", "file")
        self.lbl_filename = ctk.CTkLabel(self.card_file, text="Awaiting input...", text_color=COLOR_TEXT_SUB, font=font_small)
        self.lbl_filename.pack(pady=(0, 20))

        self.card_settings = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=10, border_width=1, border_color=COLOR_ACCENT)
        self.card_settings.pack(pady=15, padx=25, fill="x")
        self.lbl_step2 = ctk.CTkLabel(self.card_settings, text=">_ CONFIGURATION", font=font_h2, text_color=COLOR_BTN_MAIN)
        self.lbl_step2.pack(pady=(20, 5), padx=20, anchor="w")
        self.lbl_engine = ctk.CTkLabel(self.card_settings, text="AI_Engine", font=font_p, text_color=COLOR_TEXT_MAIN)
        self.lbl_engine.pack(pady=(10, 0), padx=20, anchor="w")
        self.combo_engine = ctk.CTkComboBox(self.card_settings, values=["Google_Translate (Free)"], 
                                            height=35, corner_radius=5, fg_color=COLOR_BG, border_color=COLOR_ACCENT, button_color=COLOR_ACCENT, text_color=COLOR_TEXT_MAIN, font=font_p, dropdown_font=font_p)
        self.combo_engine.set("Google_Translate (Free)")
        self.combo_engine.pack(pady=(5, 10), padx=20, fill="x")

        self.frame_langs = ctk.CTkFrame(self.card_settings, fg_color="transparent")
        self.frame_langs.pack(pady=10, padx=20, fill="x")
        self.combo_source = ctk.CTkComboBox(self.frame_langs, values=["Auto-Detect"], height=35, width=140, 
                                            corner_radius=5, fg_color=COLOR_BG, border_color=COLOR_ACCENT, text_color=COLOR_TEXT_SUB, font=font_p, dropdown_font=font_p)
        self.combo_source.set("Auto-Detect")
        self.combo_source.pack(side="left", padx=(0, 10))
        self.lbl_arrow = ctk.CTkLabel(self.frame_langs, text=">>", font=font_h2, text_color=COLOR_BTN_SEC)
        self.lbl_arrow.pack(side="left")
        self.combo_lang = ctk.CTkComboBox(self.frame_langs, values=list(self.languages.keys()), height=35, 
                                          corner_radius=5, fg_color=COLOR_BG, border_color=COLOR_ACCENT, button_color=COLOR_ACCENT, text_color=COLOR_TEXT_MAIN, font=font_p, dropdown_font=font_p)
        self.combo_lang.set("🇺🇸 English")
        self.combo_lang.pack(side="left", fill="x", expand=True, padx=(10, 0))
        
        self.lbl_pro_ad = ctk.CTkLabel(self.card_settings, text="★ Get LocaGen PRO for CSV/TXT support and Glossary ★", text_color="#F4D03F", font=font_small, cursor="hand2")
        self.lbl_pro_ad.pack(pady=(15, 15))
        self.lbl_pro_ad.bind("<Button-1>", lambda e: webbrowser.open("https://manyaksisko35.itch.io/locagen-pro-universal-game-localization-tool"))

        self.btn_start = ctk.CTkButton(self, text="I N I T I A T E", command=self.initiate_save_process, 
                                       fg_color=COLOR_BTN_MAIN, hover_color=COLOR_BTN_MAIN_HOVER, height=60, corner_radius=5, 
                                       font=("Consolas", 18, "bold"), text_color="#000000")
        self.btn_start.pack(pady=(25, 10), padx=25, fill="x")
        self.bind_hover_animation(self.btn_start, "I N I T I A T E", "start")
        
        self.progress_bar = ctk.CTkProgressBar(self, height=2, corner_radius=0, fg_color=COLOR_CARD, progress_color=COLOR_BTN_MAIN)
        self.progress_bar.pack(pady=(0, 10), padx=30, fill="x")
        self.progress_bar.set(0)

        self.status_label = ctk.CTkLabel(self, text="", text_color=COLOR_TEXT_SUB, font=font_small)
        self.status_label.pack(side="bottom", pady=(0, 30))
        self.update_status("System standby.", COLOR_TEXT_SUB)
        self.lbl_footer = ctk.CTkLabel(self, text="Coded by Hasan Alp Güngör", text_color=COLOR_ACCENT, font=font_small, cursor="hand2")
        self.lbl_footer.pack(side="bottom", pady=10)
        self.lbl_footer.bind("<Button-1>", lambda e: self.open_github())

    def open_github(self):
        webbrowser.open("https://github.com/manyaksisko35")

    def initiate_save_process(self):
        if not self.loaded_data:
            self.update_status("Err: Source missing.", "#ff0055") 
            return
        selected_lang_name = self.combo_lang.get()
        default_name = f"translated_{selected_lang_name.split()[1]}{self.file_extension}"
        save_path = ctk.filedialog.asksaveasfilename(initialfile=default_name, title="Save As", filetypes=[(f"{self.file_extension.upper()} File", f"*{self.file_extension}")])
        if save_path:
            self.start_translation_thread(save_path)
        else:
            self.update_status("Aborted.", COLOR_TEXT_SUB)

    def start_translation_thread(self, save_path):
        threading.Thread(target=self.translate_process, args=(save_path,), daemon=True).start()

    def translate_process(self, save_path):
        self.btn_start.configure(state="disabled", text="P R O C E S S I N G", fg_color=COLOR_ACCENT)
        self.progress_bar.set(0)
        selected_lang_name = self.combo_lang.get()
        target_code = self.languages[selected_lang_name]
        self.update_status(f"Translating -> {selected_lang_name}", COLOR_BTN_MAIN)
        try:
            if self.file_extension == ".json":
                total_items = len(self.loaded_data)
                if isinstance(self.loaded_data, dict):
                    final_data = {}
                    for index, (key, value) in enumerate(self.loaded_data.items()):
                        final_data[key] = self.perform_translation(str(value), target_code)
                        self.progress_bar.set((index + 1) / total_items) 
                elif isinstance(self.loaded_data, list):
                    final_data = []
                    for index, item in enumerate(self.loaded_data):
                        if isinstance(item, dict):
                            temp_dict = {}
                            for k, v in item.items():
                                temp_dict[k] = self.perform_translation(str(v), target_code)
                            final_data.append(temp_dict)
                        else:
                            final_data.append(self.perform_translation(str(item), target_code))
                        self.progress_bar.set((index + 1) / total_items)
                else: final_data = self.loaded_data
                with open(save_path, "w", encoding="utf-8") as f: json.dump(final_data, f, ensure_ascii=False, indent=4)
            self.progress_bar.set(1.0) 
            self.update_status(f"Success. Output saved.", COLOR_SUCCESS)
        except Exception as e:
            self.update_status(f"Critical Error: {e}", "#ff0055")
        self.btn_start.configure(state="normal", text="I N I T I A T E", fg_color=COLOR_BTN_MAIN)

    def perform_translation(self, text, target_code):
        pattern = re.compile(r'(\{.*?\}|<.*?>|%[sd])')
        matches = pattern.findall(text)
        temp_text = text
        placeholders = {}
        for i, match in enumerate(matches):
            placeholder = f"[VAR_{i}]"
            placeholders[placeholder] = match
            temp_text = temp_text.replace(match, placeholder)
        try:
            translated_text = GoogleTranslator(source='auto', target=target_code).translate(temp_text)
        except: return text
        if translated_text:
            for placeholder, original_var in placeholders.items():
                translated_text = translated_text.replace(placeholder, original_var)
                translated_text = translated_text.replace(placeholder.lower(), original_var)
            return translated_text
        return text

    def load_file(self):
        self.file_path = ctk.filedialog.askopenfilename(filetypes=[("JSON Files", "*.json")])
        if self.file_path:
            self.file_extension = os.path.splitext(self.file_path)[1].lower()
            if self.file_extension != ".json":
                self.update_status("Err: Only JSON supported.", "#ff0055")
                self.file_path = None
                return
            self.lbl_filename.configure(text=f">> {self.file_path.split('/')[-1]}", text_color=COLOR_BTN_SEC)
            try:
                with open(self.file_path, "r", encoding="utf-8") as f: self.loaded_data = json.load(f)
                self.update_status("File mounted.", COLOR_BTN_MAIN)
                self.progress_bar.set(0) 
            except Exception as e: self.update_status("Err: Parse failed", "#ff0055")

if __name__ == "__main__":
    try:
        app = LocaGenAppFree()
        app.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)