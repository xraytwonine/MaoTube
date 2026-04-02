import os
import sys
import stat
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


def resource_path(*parts):
    if hasattr(sys, "_MEIPASS"):
        base = sys._MEIPASS
    else:
        base = os.path.abspath(".")
    return os.path.join(base, *parts)


class MaoTubeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MaoTube")
        self.root.geometry("760x560")
        self.root.minsize(700, 500)

        self.process = None

        self.url_var = tk.StringVar()
        self.path_var = tk.StringVar(value=os.path.join(os.path.expanduser("~"), "Downloads"))
        self.format_var = tk.StringVar(value="mp4")

        self.ytdlp_path = resource_path("bin", "yt-dlp.exe")
        self.ffmpeg_dir = resource_path("bin")
        self.ffmpeg_path = resource_path("bin", "ffmpeg.exe")
        self.ffprobe_path = resource_path("bin", "ffprobe.exe")

        self.build_ui()
        self.check_bundled_tools()

    def build_ui(self):
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill="both", expand=True)

        ttk.Label(main, text="YouTube URL").grid(row=0, column=0, sticky="w")
        ttk.Entry(main, textvariable=self.url_var, width=90).grid(
            row=1, column=0, columnspan=3, sticky="ew", pady=(4, 12)
        )

        ttk.Label(main, text="Save Location").grid(row=2, column=0, sticky="w")
        ttk.Entry(main, textvariable=self.path_var, width=70).grid(
            row=3, column=0, columnspan=2, sticky="ew", pady=(4, 12)
        )
        ttk.Button(main, text="Browse", command=self.browse_folder).grid(
            row=3, column=2, padx=(8, 0), sticky="ew"
        )

        ttk.Label(main, text="Output Type").grid(row=4, column=0, sticky="w")
        fmt = ttk.Frame(main)
        fmt.grid(row=5, column=0, columnspan=3, sticky="w", pady=(4, 12))
        ttk.Radiobutton(fmt, text="MP4 Video", variable=self.format_var, value="mp4").pack(side="left", padx=(0, 14))
        ttk.Radiobutton(fmt, text="MP3 Audio", variable=self.format_var, value="mp3").pack(side="left")

        buttons = ttk.Frame(main)
        buttons.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(0, 12))

        self.download_button = ttk.Button(buttons, text="Download", command=self.start_download)
        self.download_button.pack(side="left")

        self.stop_button = ttk.Button(buttons, text="Stop", command=self.stop_download, state="disabled")
        self.stop_button.pack(side="left", padx=(8, 0))

        ttk.Button(buttons, text="Clear Log", command=self.clear_log).pack(side="left", padx=(8, 0))

        self.status_label = ttk.Label(main, text="Ready")
        self.status_label.grid(row=7, column=0, columnspan=3, sticky="w", pady=(0, 8))

        ttk.Label(main, text="Output Log").grid(row=8, column=0, sticky="w")
        self.log_text = tk.Text(main, wrap="word", height=18)
        self.log_text.grid(row=9, column=0, columnspan=3, sticky="nsew")

        scrollbar = ttk.Scrollbar(main, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=9, column=3, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(9, weight=1)

    def browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.path_var.get())
        if folder:
            self.path_var.set(folder)

    def log(self, text):
        self.log_text.insert("end", text)
        self.log_text.see("end")

    def clear_log(self):
        self.log_text.delete("1.0", "end")

    def set_status(self, text):
        self.status_label.config(text=text)

    def ensure_executable(self, path):
        if os.name != "nt":
            try:
                mode = os.stat(path).st_mode
                if not (mode & stat.S_IXUSR):
                    os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except Exception as e:
                return False, str(e)
        return True, ""

    def check_bundled_tools(self):
        for tool in (self.ytdlp_path, self.ffmpeg_path, self.ffprobe_path):
            if os.path.isfile(tool):
                self.log(f"[OK] Bundled tool ready: {tool}\n")
            else:
                self.log(f"[WARNING] Missing bundled file: {tool}\n")

    def build_command(self, url, save_path, output_type):
        command = [self.ytdlp_path, "--ffmpeg-location", self.ffmpeg_dir]

        if output_type == "mp4":
            command.extend([
                "-f", "bv*+ba/b",
                "--merge-output-format", "mp4",
                "-P", save_path,
                url
            ])
        else:
            command.extend([
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "--no-keep-video",
                "-P", save_path,
                url
            ])

        return command

    def validate_before_run(self, output_type):
        required = [self.ytdlp_path]
        if output_type == "mp3":
            required.extend([self.ffmpeg_path, self.ffprobe_path])

        missing = [p for p in required if not os.path.isfile(p)]
        if missing:
            messagebox.showerror(
                "Missing Bundled Files",
                "These required files are missing:\n\n" + "\n".join(missing)
            )
            return False

        return True

    def start_download(self):
        url = self.url_var.get().strip()
        save_path = self.path_var.get().strip()
        output_type = self.format_var.get().strip()

        if not url:
            messagebox.showerror("Missing URL", "Please paste a YouTube URL.")
            return

        if not os.path.isdir(save_path):
            messagebox.showerror("Invalid Folder", "Selected save folder does not exist.")
            return

        if not self.validate_before_run(output_type):
            return

        command = self.build_command(url, save_path, output_type)

        self.download_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.set_status("Downloading...")

        self.log("\n" + "=" * 60 + "\n")
        self.log("Running command:\n")
        self.log(" ".join(f'"{p}"' if " " in p else p for p in command) + "\n\n")

        thread = threading.Thread(target=self.run_download, args=(command,), daemon=True)
        thread.start()

    def run_download(self, command):
        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

            for line in self.process.stdout:
                self.root.after(0, self.log, line)

            code = self.process.wait()

            if code == 0:
                self.root.after(0, self.set_status, "Done")
                self.root.after(0, self.log, "\n[COMPLETED] Download finished successfully.\n")
            else:
                self.root.after(0, self.set_status, "Failed")
                self.root.after(0, self.log, f"\n[ERROR] Process exited with code {code}.\n")

        except Exception as e:
            self.root.after(0, self.set_status, "Error")
            self.root.after(0, self.log, f"\n[EXCEPTION] {e}\n")

        finally:
            self.process = None
            self.root.after(0, lambda: self.download_button.config(state="normal"))
            self.root.after(0, lambda: self.stop_button.config(state="disabled"))

    def stop_download(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.log("\n[STOPPED] Download stopped by user.\n")
                self.set_status("Stopped")
            except Exception as e:
                self.log(f"\n[ERROR] Could not stop process: {e}\n")


def main():
    root = tk.Tk()
    app = MaoTubeApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()