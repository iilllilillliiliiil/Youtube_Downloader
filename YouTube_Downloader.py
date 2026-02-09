# pyinstaller --onefile --noconsole --icon="youtube.ico" --add-data "config.json;." --add-binary "ffmpeg.exe;." recog_youtube7.py

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import subprocess
import json
from pytubefix import YouTube
import sys
import time

ctk.set_appearance_mode("system")
ctk.set_default_color_theme("dark-blue")

CONFIG_FILE = "config.json"

# --- 그라데이션 헤더 ---
class GradientHeader(ctk.CTkFrame):
    def __init__(self, parent, text, emoji="🎬", width=520, height=70, **kwargs):
        kwargs.pop("height", None)
        kwargs.pop("width", None)
        super().__init__(parent, fg_color=("gray12", "gray20"), width=width, height=height, **kwargs)
        self.configure(corner_radius=20)
        self.grid_propagate(False)
        self.label = ctk.CTkLabel(
            self,
            text=f"{emoji} {text}",
            font=ctk.CTkFont(size=28, weight="bold"),
            justify="left",
            text_color=("#F3D250", "#C0C0C0")
        )
        self.label.place(relx=0.03, rely=0.17)

# --- 알약형 버튼 ---
class PillButton(ctk.CTkButton):
    def __init__(self, *args, **kwargs):
        kwargs.pop("height", None)
        super().__init__(
            *args,
            **kwargs,
            corner_radius=20,
            fg_color="#FF416C",
            hover_color="#FF4B2B",
            text_color="white",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=45
        )

# ---------------- 메인 UI ----------------
class YouTubeDownloader(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("🎬 YouTube Downloader")
        self.geometry("600x520")
        self.resizable(False, False)
        self.save_path = ctk.StringVar(value=self.load_last_folder())
        self.current_label = None
        self.configure(fg_color="#191c24")

        # 상단 헤더
        header = GradientHeader(self, text="YouTube Downloader", emoji="📥", width=int(0.86 * 600), height=70)
        header.place(relx=0.07, rely=0.045, relwidth=0.86)

        # URL 입력창
        entry_frame = ctk.CTkFrame(self, fg_color="#1B1E2A", corner_radius=16, width=482, height=54)
        entry_frame.place(relx=0.08, rely=0.18)
        self.url_entry = ctk.CTkEntry(
            entry_frame,
            placeholder_text="YouTube URL",
            width=450,
            height=40,
            font=ctk.CTkFont(size=16),
            border_width=0,
            fg_color="#1E2132",
            text_color="#FFFFFF",
            placeholder_text_color="#7A86B6"
        )
        self.url_entry.place(x=15, y=7)

        # 폴더 선택
        folder_frame = ctk.CTkFrame(self, fg_color="#23263a", corner_radius=16, width=482, height=48)
        folder_frame.place(relx=0.08, rely=0.31)
        ctk.CTkLabel(folder_frame, text="📂", width=38, anchor="center", font=ctk.CTkFont(size=18)).pack(side="left", padx=(8, 0), pady=7)
        ctk.CTkLabel(folder_frame, textvariable=self.save_path, width=285, anchor="w",
                    font=ctk.CTkFont(size=13), text_color="#F2F2F2").pack(side="left", padx=(6, 0))
        PillButton(folder_frame, text="폴더 선택", width=110, command=self.choose_folder).pack(side="right", padx=10, pady=4)

        # 다운로드 버튼
        self.download_button = PillButton(self, text="⬇️ 다운로드 시작", width=480, command=self.start_download_thread)
        self.download_button.place(relx=0.08, rely=0.46)

        # 진행률 바 2개
        self.progress_labels = {}
        self.progress_bars = {}
        for idx, label_text in enumerate(["영상 다운로드", "오디오 다운로드"]):
            prog_frame = ctk.CTkFrame(self, fg_color="#23263a", corner_radius=16, width=482, height=50)
            prog_frame.place(relx=0.08, rely=0.58 + idx * 0.12)
            color = "#7DF9FF" if label_text == "영상 다운로드" else "#EFB5FF"
            lbl = ctk.CTkLabel(prog_frame, text=f"{label_text}: 0.00%", font=ctk.CTkFont(size=13, weight="bold"),
                                text_color=color)
            lbl.pack(anchor="w", padx=18, pady=3)
            bar = ctk.CTkProgressBar(prog_frame, width=425, height=11,
                                    progress_color=color, fg_color="#191c24", border_color="#23263a")
            bar.set(0)
            bar.pack(pady=(0, 7), padx=18)
            self.progress_labels[label_text] = lbl
            self.progress_bars[label_text] = bar

        # 상태 라벨 (타이머)
        self.status_label = ctk.CTkLabel(self, text="⏱ 00:00:00", font=ctk.CTkFont(size=15, weight="bold"),
                                        text_color="#FFD460")
        self.status_label.place(relx=0.1, rely=0.81)

        # 병합 애니메이션 라벨
        self.merge_label = ctk.CTkLabel(self, text="", font=ctk.CTkFont(size=17, weight="bold"), text_color="#FFC300")
        self.merge_label.place(relx=0.5, rely=0.92, anchor="center")

        self.start_time = None
        self.timer_running = False
        self.merge_anim_running = False
        self.dot_count = 1
        self.dot_direction = 1

    # ---------------- 타이머 관련 ----------------
    def start_timer(self):
        self.start_time = time.time()
        self.timer_running = True
        self.update_timer()

    def reset_timer(self):
        self.start_time = time.time()

    def update_timer(self):
        if self.timer_running:
            elapsed = int(time.time() - self.start_time)
            h, m, s = elapsed // 3600, (elapsed % 3600) // 60, elapsed % 60
            self.status_label.configure(text=f"⏱ {h:02d}:{m:02d}:{s:02d}")
            self.after(1000, self.update_timer)

    def stop_timer(self):
        self.timer_running = False

    # ---------------- 병합 애니메이션 ----------------
    def start_merge_animation(self):
        self.merge_anim_running = True
        self.animate_merge_label()

    def animate_merge_label(self):
        if not self.merge_anim_running:
            return
        self.merge_label.configure(text=f"병합 중{'.' * self.dot_count}")
        if self.dot_count >= 3:
            self.dot_direction = -1
        elif self.dot_count <= 0:
            self.dot_direction = 1
        self.dot_count += self.dot_direction
        self.after(500, self.animate_merge_label)

    def stop_merge_animation(self):
        self.merge_anim_running = False
        self.merge_label.configure(text="")

    # ---------------- 기본 기능 ----------------
    def load_last_folder(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    last_path = data.get("last_folder", "")
                    if os.path.exists(last_path):
                        return last_path
            except:
                pass
        return os.getcwd()

    def save_last_folder(self, folder_path):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"last_folder": folder_path}, f, ensure_ascii=False, indent=2)

    def choose_folder(self):
        folder = filedialog.askdirectory(initialdir=self.save_path.get())
        if folder:
            self.save_path.set(folder)
            self.save_last_folder(folder)

    def update_progress(self, label_text, percent):
        self.progress_bars[label_text].set(percent / 100)
        color = "#7DF9FF" if label_text == "영상 다운로드" else "#EFB5FF"
        self.progress_labels[label_text].configure(text=f"{label_text}: {percent:.2f}%", text_color=color)
        self.update_idletasks()

    def on_progress(self, stream, chunk, bytes_remaining):
        total = stream.filesize
        percent = (1 - bytes_remaining / total) * 100
        if self.current_label:
            self.update_progress(self.current_label, percent)

    # ---------------- 병합 ----------------
    def merge_streams(self, video_path, audio_path, output_path):
        try:
            self.reset_timer()
            self.start_merge_animation()
            ffmpeg_path = get_ffmpeg_path()
            cmd = [ffmpeg_path, "-y", "-i", video_path, "-i", audio_path, "-c:v", "copy", "-c:a", "aac",
                    "-loglevel", "error", output_path]
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo)
            self.wait_for_merge(process, video_path, audio_path)
        except Exception as e:
            messagebox.showerror("병합 오류", f"FFmpeg 병합 중 오류 발생: {e}")
            self.status_label.configure(text="⚠️ 병합 실패", text_color="#FF4B2B")

    def wait_for_merge(self, process, video_path, audio_path):
        if process.poll() is None:
            self.after(500, lambda: self.wait_for_merge(process, video_path, audio_path))
        else:
            self.stop_merge_animation()
            if process.returncode == 0:
                for path in (video_path, audio_path):
                    try:
                        if os.path.exists(path):
                            os.remove(path)
                    except Exception:
                        pass
                self.stop_timer()
                self.status_label.configure(text="✅ 병합 완료!", text_color="#8cfa96")
                self.after(1500, lambda: self.destroy())
            else:
                self.stop_timer()
                self.status_label.configure(text="⚠️ 병합 실패", text_color="#FF4B2B")

    # ---------------- 다운로드 ----------------
    def start_download_thread(self):
        self.download_button.configure(state="disabled", text="⏳ 다운로드 중...")
        threading.Thread(target=self.download_video, daemon=True).start()

    def download_video(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("경고", "URL을 입력하세요.")
            self.download_button.configure(state="normal", text="⬇️ 다운로드 시작")
            return

        try:
            yt_video = YouTube(url, on_progress_callback=self.on_progress)
            yt_audio = YouTube(url, on_progress_callback=self.on_progress)

            video_stream = yt_video.streams.filter(adaptive=True, file_extension='mp4', only_video=True).order_by('resolution').desc().first()
            audio_stream = yt_audio.streams.filter(only_audio=True, file_extension='mp4').first()

            safe_title = "".join(c for c in yt_video.title if c not in r'\/:*?"<>|')
            base_path = os.path.join(self.save_path.get(), safe_title)
            video_path = base_path + "_video.mp4"
            audio_path = base_path + "_audio.mp4"
            final_path = base_path + ".mp4"

            # 🎥 영상 다운로드
            self.current_label = "영상 다운로드"
            self.start_timer()
            video_stream.download(output_path=self.save_path.get(), filename=os.path.basename(video_path))

            # 🎧 오디오 다운로드
            self.current_label = "오디오 다운로드"
            self.reset_timer()
            audio_stream.download(output_path=self.save_path.get(), filename=os.path.basename(audio_path))

            # 병합
            threading.Thread(target=self.merge_streams, args=(video_path, audio_path, final_path), daemon=True).start()

        except Exception as e:
            self.stop_timer()
            self.status_label.configure(text=f"⚠️ 오류 발생: {e}", text_color="#FF4B2B")
            self.download_button.configure(state="normal", text="⬇️ 다운로드 시작")

# ---------------- FFmpeg 경로 ----------------
def get_ffmpeg_path():
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(__file__)
    ffmpeg_path = os.path.join(base_path, "ffmpeg.exe")
    if not os.path.exists(ffmpeg_path):
        messagebox.showerror("FFmpeg 오류", "ffmpeg.exe 파일을 찾을 수 없습니다.")
        raise FileNotFoundError("ffmpeg.exe not found")
    return ffmpeg_path

if __name__ == "__main__":
    app = YouTubeDownloader()
    app.mainloop()