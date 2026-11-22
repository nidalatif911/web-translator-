"""
Modern, Professional CustomTkinter UI
Web Translator
"""

import os
import sys
import time
import logging
import threading
from datetime import datetime
from typing import Optional

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import speech_recognition as sr

from app.config import (
    APP_NAME,
    APP_SUBTITLE,
    APP_VERSION,
    GITHUB_URL,
    LANGUAGES,
    LANGUAGE_NAMES,
)
from app.audio_recorder import AudioRecorder, list_microphones
from app.translator import translate_text
from app.tts_engine import tts_service

logger = logging.getLogger(__name__)

# Permanent Light Mode
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


class ModernTranslatorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Setup
        self.title(f"{APP_NAME}")
        self.geometry("980x780")
        self.minsize(840, 680)

        # Set App Icon if exists
        base_dir = os.path.dirname(os.path.dirname(__file__))
        icon_path = os.path.join(base_dir, "assets", "icon.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(base_dir, "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # Backend Services
        self.recorder = AudioRecorder()
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True

        # State Variables
        self.is_listening = False
        self.auto_speak_var = ctk.BooleanVar(value=True)
        self.selected_source_lang = ctk.StringVar(value="English")
        self.selected_target_lang = ctk.StringVar(value="Spanish")
        self.history_records = []

        # Connect Recorder Callbacks
        self.recorder.on_audio_level = self._on_audio_level_threadsafe
        self.recorder.on_phrase_complete = self._on_phrase_recorded
        self.recorder.on_status_change = self._set_status_threadsafe

        # Build UI Layout
        self._build_header()
        self._build_controls_card()
        self._build_translation_cards()
        self._build_visualizer_and_actions()
        self._build_history_section()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # -------------------------------------------------------------
    # UI Building Blocks
    # -------------------------------------------------------------
    def _build_header(self):
        """Top navigation and title header."""
        header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        header_frame.pack(fill="x", padx=24, pady=(16, 10))

        # Title + Author Badge
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left")

        app_title = ctk.CTkLabel(
            title_box,
            text=f"🌐 {APP_NAME}",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold")
        )
        app_title.pack(anchor="w")

        subtitle = ctk.CTkLabel(
            title_box,
            text=f"{APP_SUBTITLE}",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="gray40"
        )
        subtitle.pack(anchor="w")

        # Top Right Controls: About
        actions_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        actions_box.pack(side="right")

        about_btn = ctk.CTkButton(
            actions_box,
            text="ℹ️ About",
            width=80,
            height=30,
            command=self._show_about_dialog,
            fg_color="gray85",
            text_color="black",
            hover_color="gray75"
        )
        about_btn.pack(side="left")

    def _build_controls_card(self):
        """Card containing language selectors, swap button, and mic options."""
        card = ctk.CTkFrame(self, corner_radius=12)
        card.pack(fill="x", padx=24, pady=8)

        grid_frame = ctk.CTkFrame(card, fg_color="transparent")
        grid_frame.pack(fill="x", padx=16, pady=12)

        # Source Language Dropdown
        src_box = ctk.CTkFrame(grid_frame, fg_color="transparent")
        src_box.pack(side="left", fill="x", expand=True, padx=(0, 8))
        src_label = ctk.CTkLabel(
            src_box,
            text="Input Language (Spoken)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        src_label.pack(anchor="w", pady=(0, 4))

        src_options = [f"{LANGUAGES[l]['flag']} {l}" for l in LANGUAGE_NAMES]
        self.src_combo = ctk.CTkComboBox(
            src_box,
            values=src_options,
            command=self._on_source_lang_changed,
            height=36,
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.src_combo.set(f"{LANGUAGES['English']['flag']} English")
        self.src_combo.pack(fill="x")

        # Language Swap Button
        swap_btn = ctk.CTkButton(
            grid_frame,
            text="⇄",
            width=42,
            height=36,
            command=self._swap_languages,
            font=ctk.CTkFont(size=18, weight="bold"),
            fg_color="gray85",
            hover_color="gray75",
            text_color="black"
        )
        swap_btn.pack(side="left", padx=8, pady=(20, 0))

        # Target Language Dropdown
        tgt_box = ctk.CTkFrame(grid_frame, fg_color="transparent")
        tgt_box.pack(side="left", fill="x", expand=True, padx=(8, 16))
        tgt_label = ctk.CTkLabel(
            tgt_box,
            text="Output Language (Translated)",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        tgt_label.pack(anchor="w", pady=(0, 4))

        self.tgt_combo = ctk.CTkComboBox(
            tgt_box,
            values=src_options,
            command=self._on_target_lang_changed,
            height=36,
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.tgt_combo.set(f"{LANGUAGES['Spanish']['flag']} Spanish")
        self.tgt_combo.pack(fill="x")

        # Microphone Selector
        mic_box = ctk.CTkFrame(grid_frame, fg_color="transparent")
        mic_box.pack(side="left", fill="x", expand=True, padx=(8, 0))
        mic_label = ctk.CTkLabel(
            mic_box,
            text="Microphone Input",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        )
        mic_label.pack(anchor="w", pady=(0, 4))

        self.mic_devices = list_microphones()
        mic_names = [f"🎤 {m[1][:30]}" for m in self.mic_devices]
        self.mic_combo = ctk.CTkComboBox(
            mic_box,
            values=mic_names if mic_names else ["Default Mic"],
            command=self._on_mic_device_changed,
            height=36,
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        if mic_names:
            self.mic_combo.set(mic_names[0])
        self.mic_combo.pack(fill="x")

    def _build_translation_cards(self):
        """Main text areas for input and translation."""
        boxes_container = ctk.CTkFrame(self, fg_color="transparent")
        boxes_container.pack(fill="both", expand=True, padx=24, pady=6)
        boxes_container.columnconfigure(0, weight=1)
        boxes_container.columnconfigure(1, weight=1)
        boxes_container.rowconfigure(0, weight=1)

        # ----------------- Input Card (Left) -----------------
        input_card = ctk.CTkFrame(boxes_container, corner_radius=12)
        input_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8), pady=0)

        in_header = ctk.CTkFrame(input_card, fg_color="transparent")
        in_header.pack(fill="x", padx=14, pady=(12, 6))

        in_title = ctk.CTkLabel(
            in_header,
            text="🗣️ Recognized Speech / Text",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        )
        in_title.pack(side="left")

        in_clear_btn = ctk.CTkButton(
            in_header,
            text="Clear",
            width=50,
            height=24,
            command=self._clear_input,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            text_color="gray30"
        )
        in_clear_btn.pack(side="right", padx=(6, 0))

        in_copy_btn = ctk.CTkButton(
            in_header,
            text="Copy",
            width=50,
            height=24,
            command=lambda: self._copy_text(self.input_text.get("1.0", "end-1c")),
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            text_color="gray30"
        )
        in_copy_btn.pack(side="right")

        self.input_text = ctk.CTkTextbox(
            input_card,
            font=ctk.CTkFont(family="Segoe UI", size=14),
            wrap="word",
            corner_radius=8
        )
        self.input_text.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        # Bottom of Input Card: Translate manual typed text button
        in_footer = ctk.CTkFrame(input_card, fg_color="transparent")
        in_footer.pack(fill="x", padx=14, pady=(0, 10))

        manual_translate_btn = ctk.CTkButton(
            in_footer,
            text="Translate Typed Text ➔",
            height=30,
            command=self._translate_manual_text,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        manual_translate_btn.pack(side="right")

        # ----------------- Output Card (Right) -----------------
        output_card = ctk.CTkFrame(boxes_container, corner_radius=12)
        output_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0), pady=0)

        out_header = ctk.CTkFrame(output_card, fg_color="transparent")
        out_header.pack(fill="x", padx=14, pady=(12, 6))

        out_title = ctk.CTkLabel(
            out_header,
            text="🌐 Translated Output",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        )
        out_title.pack(side="left")

        out_copy_btn = ctk.CTkButton(
            out_header,
            text="Copy",
            width=50,
            height=24,
            command=lambda: self._copy_text(self.output_text.get("1.0", "end-1c")),
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            text_color="gray30"
        )
        out_copy_btn.pack(side="right", padx=(6, 0))

        self.replay_btn = ctk.CTkButton(
            out_header,
            text="🔊 Listen",
            width=65,
            height=24,
            command=self._replay_audio,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#27ae60",
            hover_color="#219d54"
        )
        self.replay_btn.pack(side="right")

        self.output_text = ctk.CTkTextbox(
            output_card,
            font=ctk.CTkFont(family="Segoe UI", size=14),
            wrap="word",
            corner_radius=8
        )
        self.output_text.pack(fill="both", expand=True, padx=14, pady=(0, 10))

        out_footer = ctk.CTkFrame(output_card, fg_color="transparent")
        out_footer.pack(fill="x", padx=14, pady=(0, 10))

        auto_speak_switch = ctk.CTkSwitch(
            out_footer,
            text="Auto-Speak Translation",
            variable=self.auto_speak_var,
            font=ctk.CTkFont(size=12)
        )
        auto_speak_switch.pack(side="left")

    def _build_visualizer_and_actions(self):
        """Audio visualizer bar and main action buttons."""
        action_card = ctk.CTkFrame(self, corner_radius=12)
        action_card.pack(fill="x", padx=24, pady=8)

        # Status & Level Meter Row
        status_row = ctk.CTkFrame(action_card, fg_color="transparent")
        status_row.pack(fill="x", padx=16, pady=(10, 6))

        self.status_dot = ctk.CTkLabel(
            status_row,
            text="●",
            text_color="#10b981",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.status_dot.pack(side="left", padx=(0, 6))

        self.status_label = ctk.CTkLabel(
            status_row,
            text="Ready — Click 'Start Listening' to begin",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        )
        self.status_label.pack(side="left")

        # Audio Level Visualizer Meter
        self.level_meter = ctk.CTkProgressBar(
            status_row,
            width=220,
            height=12,
            corner_radius=6,
            progress_color="#3b82f6"
        )
        self.level_meter.set(0.0)
        self.level_meter.pack(side="right")

        level_label = ctk.CTkLabel(
            status_row,
            text="Mic Level: ",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray40"
        )
        level_label.pack(side="right", padx=(0, 6))

        # Buttons Row
        buttons_row = ctk.CTkFrame(action_card, fg_color="transparent")
        buttons_row.pack(fill="x", padx=16, pady=(4, 12))

        self.listen_button = ctk.CTkButton(
            buttons_row,
            text="🎙️  Start Listening",
            height=46,
            command=self._toggle_listening,
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            fg_color="#3b82f6",
            hover_color="#2563eb",
            corner_radius=10
        )
        self.listen_button.pack(side="left", fill="x", expand=True, padx=(0, 8))

        clear_all_btn = ctk.CTkButton(
            buttons_row,
            text="🗑️ Clear All",
            width=110,
            height=46,
            command=self._clear_all,
            font=ctk.CTkFont(size=13),
            fg_color="gray85",
            hover_color="gray75",
            text_color="black",
            corner_radius=10
        )
        clear_all_btn.pack(side="left", padx=4)

        save_log_btn = ctk.CTkButton(
            buttons_row,
            text="💾 Save Log",
            width=110,
            height=46,
            command=self._export_log,
            font=ctk.CTkFont(size=13),
            fg_color="gray85",
            hover_color="gray75",
            text_color="black",
            corner_radius=10
        )
        save_log_btn.pack(side="left", padx=(4, 0))

    def _build_history_section(self):
        """Collapsible or preview section for translation history."""
        hist_frame = ctk.CTkFrame(self, corner_radius=8, height=36, fg_color="transparent")
        hist_frame.pack(fill="x", padx=26, pady=(0, 10))

        self.history_status_label = ctk.CTkLabel(
            hist_frame,
            text="Translations logged: 0",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray40"
        )
        self.history_status_label.pack(side="left")

        footer_credit = ctk.CTkLabel(
            hist_frame,
            text=f"© 2026 {APP_NAME}. All rights reserved.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="gray45"
        )
        footer_credit.pack(side="right")

    # -------------------------------------------------------------
    # Event Handlers & Core Workflow
    # -------------------------------------------------------------
    def _on_source_lang_changed(self, choice: str):
        name = choice.split(" ", 1)[-1]
        self.selected_source_lang.set(name)

    def _on_target_lang_changed(self, choice: str):
        name = choice.split(" ", 1)[-1]
        self.selected_target_lang.set(name)

    def _swap_languages(self):
        src = self.selected_source_lang.get()
        tgt = self.selected_target_lang.get()

        self.selected_source_lang.set(tgt)
        self.selected_target_lang.set(src)

        self.src_combo.set(f"{LANGUAGES[tgt]['flag']} {tgt}")
        self.tgt_combo.set(f"{LANGUAGES[src]['flag']} {src}")

        in_content = self.input_text.get("1.0", "end-1c").strip()
        out_content = self.output_text.get("1.0", "end-1c").strip()
        if in_content and out_content:
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", out_content)
            self.output_text.delete("1.0", "end")
            self.output_text.insert("1.0", in_content)

    def _on_mic_device_changed(self, choice: str):
        for idx, name in self.mic_devices:
            if choice.replace("🎤 ", "").strip() in name:
                self.recorder.set_device(idx)
                break

    def _toggle_listening(self):
        if not self.is_listening:
            self._start_listening()
        else:
            self._stop_listening()

    def _start_listening(self):
        try:
            self.recorder.start()
            self.is_listening = True
            self.listen_button.configure(
                text="⏹️  Stop Listening",
                fg_color="#dc2626",
                hover_color="#b91c1c"
            )
            self.status_dot.configure(text_color="#3b82f6")
            self.status_label.configure(text="Listening for voice... Speak now!")
        except Exception as e:
            messagebox.showerror("Microphone Error", f"Could not access microphone:\n{e}")

    def _stop_listening(self):
        self.recorder.stop()
        self.is_listening = False
        self.listen_button.configure(
            text="🎙️  Start Listening",
            fg_color="#3b82f6",
            hover_color="#2563eb"
        )
        self.status_dot.configure(text_color="#10b981")
        self.status_label.configure(text="Ready — Idle")
        self.level_meter.set(0.0)

    def _on_phrase_recorded(self, audio_data: sr.AudioData):
        src_lang_name = self.selected_source_lang.get()
        tgt_lang_name = self.selected_target_lang.get()
        stt_code = LANGUAGES.get(src_lang_name, {}).get("stt", "en-US")

        self.after(0, lambda: self._set_status("Transcribing speech...", "#eab308"))

        try:
            recognized_text = self.recognizer.recognize_google(audio_data, language=stt_code)
            if not recognized_text or not recognized_text.strip():
                self.after(0, lambda: self._set_status("Speech not recognized", "#9ca3af"))
                return

            clean_speech = recognized_text.strip()
            self.after(0, lambda: self._append_input_text(clean_speech))

            if clean_speech.lower() in ["exit", "stop listening", "quit", "stop"]:
                self.after(0, self._stop_listening)
                return

            self.after(0, lambda: self._set_status("Translating...", "#f97316"))
            translated = translate_text(clean_speech, src_lang_name, tgt_lang_name)

            self.after(0, lambda: self._append_output_text(translated))
            self.after(0, lambda: self._log_history(clean_speech, translated, src_lang_name, tgt_lang_name))

            if self.auto_speak_var.get() and translated:
                self.after(0, lambda: self._set_status("Speaking translation...", "#a855f7"))
                tts_service.speak(
                    translated,
                    tgt_lang_name,
                    async_play=True,
                    on_finish=lambda: self.after(0, lambda: self._set_status("Listening for voice...", "#3b82f6"))
                )
            else:
                self.after(0, lambda: self._set_status("Listening for voice...", "#3b82f6"))

        except sr.UnknownValueError:
            self.after(0, lambda: self._set_status("Could not understand audio", "#9ca3af"))
        except sr.RequestError as e:
            self.after(0, lambda: self._set_status(f"Network error: {e}", "#ef4444"))
        except Exception as ex:
            logger.error(f"Error processing phrase: {ex}")
            self.after(0, lambda: self._set_status("Error processing speech", "#ef4444"))

    def _translate_manual_text(self):
        raw_text = self.input_text.get("1.0", "end-1c").strip()
        if not raw_text:
            return

        src_lang = self.selected_source_lang.get()
        tgt_lang = self.selected_target_lang.get()

        self._set_status("Translating text...", "#f97316")

        def _worker():
            translated = translate_text(raw_text, src_lang, tgt_lang)
            self.after(0, lambda: self._append_output_text(translated))
            self.after(0, lambda: self._log_history(raw_text, translated, src_lang, tgt_lang))

            if self.auto_speak_var.get() and translated:
                self.after(0, lambda: self._set_status("Speaking translation...", "#a855f7"))
                tts_service.speak(
                    translated,
                    tgt_lang,
                    async_play=True,
                    on_finish=lambda: self.after(0, lambda: self._set_status("Ready", "#10b981"))
                )
            else:
                self.after(0, lambda: self._set_status("Ready", "#10b981"))

        threading.Thread(target=_worker, daemon=True).start()

    def _replay_audio(self):
        out_text = self.output_text.get("1.0", "end-1c").strip()
        if not out_text:
            return

        tgt_lang = self.selected_target_lang.get()
        self._set_status("Playing audio...", "#a855f7")

        if not tts_service.replay_last(
            on_finish=lambda: self.after(0, lambda: self._set_status("Ready", "#10b981"))
        ):
            tts_service.speak(
                out_text,
                tgt_lang,
                async_play=True,
                on_finish=lambda: self.after(0, lambda: self._set_status("Ready", "#10b981"))
            )

    # -------------------------------------------------------------
    # Thread-Safe UI Helpers
    # -------------------------------------------------------------
    def _on_audio_level_threadsafe(self, level: float):
        self.after(0, lambda: self.level_meter.set(level))

    def _set_status_threadsafe(self, text: str):
        self.after(0, lambda: self._set_status(text))

    def _set_status(self, text: str, dot_color: Optional[str] = None):
        self.status_label.configure(text=text)
        if dot_color:
            self.status_dot.configure(text_color=dot_color)

    def _append_input_text(self, text: str):
        current = self.input_text.get("1.0", "end-1c").strip()
        if current:
            self.input_text.insert("end", f"\n{text}")
        else:
            self.input_text.delete("1.0", "end")
            self.input_text.insert("1.0", text)
        self.input_text.see("end")

    def _append_output_text(self, text: str):
        current = self.output_text.get("1.0", "end-1c").strip()
        if current:
            self.output_text.insert("end", f"\n{text}")
        else:
            self.output_text.delete("1.0", "end")
            self.output_text.insert("1.0", text)
        self.output_text.see("end")

    def _clear_input(self):
        self.input_text.delete("1.0", "end")

    def _clear_all(self):
        self.input_text.delete("1.0", "end")
        self.output_text.delete("1.0", "end")
        self.status_label.configure(text="Cleared all text")

    def _copy_text(self, text: str):
        if not text.strip():
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update()
        self._set_status("Copied to clipboard!", "#10b981")

    def _log_history(self, src: str, tgt: str, src_l: str, tgt_l: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.history_records.append({
            "time": ts,
            "source_lang": src_l,
            "target_lang": tgt_l,
            "source_text": src,
            "target_text": tgt
        })
        self.history_status_label.configure(
            text=f"Translations logged: {len(self.history_records)}  (Latest: {ts})"
        )

    def _export_log(self):
        if not self.history_records:
            messagebox.showinfo("Export Log", "No translation history to export yet.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text File", "*.txt"), ("Markdown File", "*.md"), ("All Files", "*.*")],
            title="Save Translation History"
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"=== {APP_NAME} Translation Log ===\n")
                f.write(f"Exported on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                for item in self.history_records:
                    f.write(f"[{item['time']}] {item['source_lang']} -> {item['target_lang']}\n")
                    f.write(f"Input:      {item['source_text']}\n")
                    f.write(f"Translated: {item['target_text']}\n")
                    f.write("-" * 50 + "\n")
            messagebox.showinfo("Export Successful", f"History saved successfully to:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not save file:\n{e}")

    def _show_about_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title(f"About {APP_NAME}")
        dialog.geometry("480x400")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        content = ctk.CTkFrame(dialog, corner_radius=12)
        content.pack(fill="both", expand=True, padx=20, pady=20)

        title = ctk.CTkLabel(
            content,
            text=f"🌐 {APP_NAME}",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold")
        )
        title.pack(pady=(16, 4))

        ver = ctk.CTkLabel(
            content,
            text=f"Version {APP_VERSION}",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        ver.pack(pady=(0, 12))

        desc = ctk.CTkLabel(
            content,
            text=(
                f"{APP_NAME} is an intelligent, real-time voice, text, document,\n"
                "and web translation platform designed for seamless cross-lingual\n"
                "communication with low latency and high accuracy.\n\n"
                "• Audio Engine: SoundDevice PortAudio Stream\n"
                "• Speech Recognition: Web Speech API & Neural STT\n"
                "• Translation Engine: Multi-Engine Fallback Cascade\n"
                "• Speech Synthesis: Neural TTS & SAPI5\n\n"
                f"© 2026 {APP_NAME}. All rights reserved."
            ),
            font=ctk.CTkFont(family="Segoe UI", size=13),
            justify="center"
        )
        desc.pack(padx=16, pady=10)

        close_btn = ctk.CTkButton(
            content,
            text="Close",
            width=120,
            command=dialog.destroy,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        close_btn.pack(pady=(16, 10))

    def _on_close(self):
        self._stop_listening()
        tts_service.stop_playback()
        self.destroy()
