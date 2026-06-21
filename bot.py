"""
Ultimate Security Surveillance Bot v2.0
Features: KNN Motion Detection, Bounding Boxes in Recording, Direct Link Streaming,
Thread-Safe Camera Access, Non-Blocking Commands, and Robust Error Handling.
"""

import datetime
import logging
import os
import queue
import re
import shutil
import subprocess
import threading
import time
import wave

import cv2
import imageio
import numpy as np
import requests
import pyaudio
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
from typing import Optional, Tuple

# ========================= Configuration =========================
TELEGRAM_TOKEN = os.environ.get(
    'TELEGRAM_TOKEN',
    '2023199633:AAFiyvCFN07qL0tLK2crugJNAF_8oM9PuIk'
)
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '934464446')
RECORDINGS_DIR = 'recordings'
LOG_FILE = 'security_log.txt'

AUDIO_FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024
VIDEO_FPS = 20
MOTION_THRESHOLD = 2500
OFF_DELAY_SECONDS = 30
ALERT_DELAY_SECONDS = 1.5
FILE_RETENTION_DAYS = 7
PHOTO_QUALITY = [int(cv2.IMWRITE_JPEG_QUALITY), 90]
GIF_DURATION_SECONDS = 5
HEATMAP_DECAY = 0.92
BOX_COLOR = (0, 0, 255)
BOX_THICKNESS = 2

URL_REGEX = re.compile(
    r'^(https?|rtsp|rtmp)://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
    r'localhost|\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?(?:/?|[/?]\S+)$',
    re.IGNORECASE,
)

if shutil.which('ffmpeg') is None:
    raise SystemExit("❌ Error: 'ffmpeg' not found in system PATH.")

os.makedirs(RECORDINGS_DIR, exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
)
logger = logging.getLogger(__name__)

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    raise SystemExit("❌ Error: Unable to open webcam.")

FRAME_WIDTH = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
FRAME_HEIGHT = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
FRAME_SIZE = (FRAME_WIDTH, FRAME_HEIGHT)

backSub = cv2.createBackgroundSubtractorKNN(dist2Threshold=1000, detectShadows=True)
heatmap = np.zeros((FRAME_HEIGHT, FRAME_WIDTH), dtype=np.float32)

lock = threading.Lock()
is_recording = False
manual_recording = False
manual_audio_active = False
last_motion_time = None
motion_count = 0
motion_start_time = None
auto_video_path = ''
auto_audio_path = ''
manual_video_path = ''
manual_audio_path = ''
video_recorder: Optional['VideoRecorder'] = None
audio_recorder: Optional['AudioRecorder'] = None
manual_video_rec: Optional['VideoRecorder'] = None
manual_audio_rec: Optional['AudioRecorder'] = None


def send_telegram_message(text: str, parse_mode: str = None) -> None:
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        params = {'chat_id': TELEGRAM_CHAT_ID, 'text': text}
        if parse_mode:
            params['parse_mode'] = parse_mode
        requests.get(url, params=params, timeout=10)
    except Exception as e:
        logger.error(f"Telegram msg error: {e}")


def send_telegram_file(path: str) -> None:
    if not os.path.exists(path):
        return
    size_mb = os.path.getsize(path) / (1024 * 1024)
    if size_mb > 49:
        send_telegram_message(f"⚠️ File too large ({size_mb:.1f}MB)")
        return
    try:
        with open(path, 'rb') as f:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendDocument"
            requests.post(
                url,
                files={'document': f},
                data={'chat_id': TELEGRAM_CHAT_ID},
                timeout=120,
            )
    except Exception as e:
        logger.error(f"File send error: {e}")


def send_telegram_file_threaded(path: str) -> None:
    threading.Thread(target=send_telegram_file, args=(path,), daemon=True).start()


def cleanup_old_files() -> None:
    cutoff = datetime.datetime.now() - datetime.timedelta(days=FILE_RETENTION_DAYS)
    for folder in os.listdir(RECORDINGS_DIR):
        path = os.path.join(RECORDINGS_DIR, folder)
        if not os.path.isdir(path):
            continue
        try:
            if datetime.datetime.fromisoformat(folder) < cutoff:
                shutil.rmtree(path)
                logger.info(f"Cleaned: {path}")
        except ValueError:
            continue


def make_paths(prefix: str = 'sec') -> Tuple[str, str, str]:
    now = datetime.datetime.now()
    ts = now.strftime('%Y%m%d_%H%M%S')
    folder = os.path.join(RECORDINGS_DIR, now.date().isoformat())
    os.makedirs(folder, exist_ok=True)
    return (
        folder,
        os.path.join(folder, f"{prefix}_v_{ts}.mp4"),
        os.path.join(folder, f"{prefix}_a_{ts}.wav"),
    )


def capture_photo(frame: np.ndarray = None) -> None:
    folder, _, _ = make_paths('photo')
    path = os.path.join(folder, f"alert_{datetime.datetime.now().strftime('%H%M%S')}.jpg")
    if frame is None:
        with lock:
            ret, frame = cap.read()
        if not ret:
            return
    cv2.imwrite(path, frame, PHOTO_QUALITY)
    send_telegram_file_threaded(path)


def speak_text(text: str) -> None:
    def _speak() -> None:
        try:
            tts = gTTS(text=text, lang='ar')
            temp = 'temp_speech.mp3'
            tts.save(temp)
            play(AudioSegment.from_mp3(temp))
            os.remove(temp)
        except Exception as e:
            logger.error(f"TTS error: {e}")

    threading.Thread(target=_speak, daemon=True).start()


def generate_heatmap(mask: np.ndarray) -> None:
    global heatmap
    heatmap = cv2.multiply(heatmap, HEATMAP_DECAY)
    heatmap = cv2.add(heatmap, mask.astype(np.float32))


def save_heatmap_image(folder: str) -> None:
    norm = cv2.normalize(heatmap, None, 0, 255, cv2.NORM_MINMAX)
    img = cv2.applyColorMap(norm.astype(np.uint8), cv2.COLORMAP_JET)
    path = os.path.join(folder, 'thermal_map.jpg')
    cv2.imwrite(path, img)
    send_telegram_file_threaded(path)


def merge_audio_video(video_path: str, audio_path: str, output_path: str) -> bool:
    try:
        cmd = [
            'ffmpeg',
            '-y',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-shortest',
            output_path,
        ]
        return subprocess.run(cmd, capture_output=True).returncode == 0
    except Exception as e:
        logger.error(f"Merge error: {e}")
        return False


def is_valid_stream_url(url: str) -> bool:
    return bool(URL_REGEX.match(url.strip()))


def play_stream_in_vlc(url: str) -> None:
    def _play() -> None:
        try:
            cmd = ['ffplay', '-nodisp', '-autoexit', '-window_title', 'Security Stream', url]
            if shutil.which('ffplay') is None:
                cmd = ['vlc', '--no-video-title-show', '--play-and-exit', url]

            logger.info(f"Playing stream: {url}")
            subprocess.run(cmd, capture_output=True)
            send_telegram_message('⏹️ Stream playback finished or stopped.')
        except Exception as e:
            logger.error(f"Stream play error: {e}")
            send_telegram_message(f"❌ Playback failed: {str(e)}")

    threading.Thread(target=_play, daemon=True).start()


class VideoRecorder(threading.Thread):
    def __init__(self, path: str):
        super().__init__(daemon=True)
        self.path = path
        self.running = True
        self.frame_queue: queue.Queue = queue.Queue(maxsize=VIDEO_FPS * 3)
        self.writer = cv2.VideoWriter(
            path,
            cv2.VideoWriter_fourcc(*'mp4v'),
            VIDEO_FPS,
            FRAME_SIZE,
        )
        self.duration = 0.0

    def put_frame(self, frame: np.ndarray) -> None:
        try:
            self.frame_queue.put_nowait(frame)
        except queue.Full:
            pass

    def run(self) -> None:
        start = time.time()
        while self.running or not self.frame_queue.empty():
            try:
                frame = self.frame_queue.get(timeout=0.5)
                self.writer.write(frame)
            except queue.Empty:
                if not self.running:
                    break
        self.writer.release()
        self.duration = time.time() - start

    def stop(self) -> None:
        self.running = False


class AudioRecorder(threading.Thread):
    def __init__(self, path: str):
        super().__init__(daemon=True)
        self.path = path
        self.running = True
        self.duration = 0.0

    def run(self) -> None:
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=AUDIO_FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )
        frames = []
        start = time.time()
        while self.running:
            try:
                frames.append(stream.read(CHUNK, exception_on_overflow=False))
            except Exception:
                break
        stream.stop_stream()
        stream.close()
        audio.terminate()
        try:
            with wave.open(self.path, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(audio.get_sample_size(AUDIO_FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(b''.join(frames))
        except Exception as e:
            logger.error(f"WAV error: {e}")
        self.duration = time.time() - start

    def stop(self) -> None:
        self.running = False


def automatic_motion_loop() -> None:
    global is_recording, last_motion_time, video_recorder, audio_recorder
    global auto_video_path, auto_audio_path, motion_count, motion_start_time, heatmap

    while True:
        with lock:
            ret, frame = cap.read()
        if not ret:
            time.sleep(0.1)
            continue

        fg_mask = backSub.apply(frame)
        _, thresh = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        display_frame = frame.copy()
        motion_detected = False
        active_boxes = 0

        for c in contours:
            area = cv2.contourArea(c)
            if area > MOTION_THRESHOLD:
                motion_detected = True
                active_boxes += 1
                x, y, w, h = cv2.boundingRect(c)
                cv2.rectangle(display_frame, (x, y), (x + w, y + h), BOX_COLOR, BOX_THICKNESS)
                cv2.putText(
                    display_frame,
                    f"ALERT {area}px",
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    BOX_COLOR,
                    2,
                )

        ts_text = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(
            display_frame,
            ts_text,
            (10, FRAME_HEIGHT - 20),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (255, 255, 255),
            2,
        )

        now = datetime.datetime.now()
        if motion_detected:
            if motion_start_time is None:
                motion_start_time = now
            elif (now - motion_start_time).total_seconds() >= ALERT_DELAY_SECONDS:
                if not is_recording:
                    motion_count += 1
                    _, auto_video_path, auto_audio_path = make_paths('auto')
                    video_recorder = VideoRecorder(auto_video_path)
                    audio_recorder = AudioRecorder(auto_audio_path)
                    video_recorder.start()
                    audio_recorder.start()
                    is_recording = True

                    send_telegram_message(
                        f"🚨 *SECURITY ALERT #{motion_count}*\n"
                        f"Active Zones: {active_boxes}\n"
                        f"Time: {now:%H:%M:%S}",
                        parse_mode='Markdown',
                    )
                    threading.Thread(
                        target=capture_photo,
                        args=(display_frame.copy(),),
                        daemon=True,
                    ).start()
                generate_heatmap(thresh)
            last_motion_time = now

        else:
            motion_start_time = None

        if is_recording and video_recorder:
            video_recorder.put_frame(display_frame)

        if (
            is_recording
            and last_motion_time is not None
            and (now - last_motion_time).total_seconds() > OFF_DELAY_SECONDS
        ):
            if video_recorder:
                video_recorder.stop()
            if audio_recorder:
                audio_recorder.stop()
            if video_recorder:
                video_recorder.join(timeout=15)
            if audio_recorder:
                audio_recorder.join(timeout=15)
            is_recording = False
            last_motion_time = None
            motion_start_time = None

            merged = auto_video_path.replace('.mp4', '_merged.mp4')
            if merge_audio_video(auto_video_path, auto_audio_path, merged):
                send_telegram_file_threaded(merged)
            else:
                send_telegram_file_threaded(auto_video_path)
            send_telegram_file_threaded(auto_audio_path)
            save_heatmap_image(os.path.dirname(merged))


def handle_command(cmd: str) -> str:
    global manual_audio_active, manual_audio_rec, manual_audio_path
    global manual_video_rec, manual_video_path, manual_recording, motion_count

    cmd = cmd.strip()
    if is_valid_stream_url(cmd):
        play_stream_in_vlc(cmd)
        return f"▶️ *Starting Stream...*\n`{cmd[:50]}...`"

    if cmd in ['/start', '/help']:
        return (
            "🛡️ *Security Bot v2.0*\n\n"
            "/status - System Status\n"
            "/photo - Snap Alert Photo\n"
            "/live - 5s Live GIF\n"
            "/say <txt> - Audio Warning\n"
            "/cleanup - Purge Old Logs\n\n"
            "*Direct Play:* Send any RTSP/HTTP link to play it locally."
        )
    elif cmd == '/status':
        return (
            f"🛡️ *Security Status*\n"
            f"Alerts: `{motion_count}`\n"
            f"Auto-Rec: `{'ACTIVE' if is_recording else 'STANDBY'}`\n"
            f"Retention: `{FILE_RETENTION_DAYS} Days`"
        )
    elif cmd == '/photo':
        threading.Thread(target=capture_photo, daemon=True).start()
        return "📸 Capturing security snapshot..."
    elif cmd.startswith('/say '):
        speak_text(cmd[5:].strip())
        return "🔊 Broadcasting audio warning..."
    elif cmd == '/live':
        def _gif() -> None:
            folder, _, _ = make_paths('live')
            gif_path = os.path.join(folder, 'live.gif')
            frames = []
            for _ in range(GIF_DURATION_SECONDS * VIDEO_FPS):
                with lock:
                    ret, fr = cap.read()
                if ret:
                    frames.append(cv2.cvtColor(fr, cv2.COLOR_BGR2RGB))
                time.sleep(1.0 / VIDEO_FPS)
            if frames:
                imageio.mimsave(gif_path, frames, duration=1.0 / VIDEO_FPS)
                send_telegram_file_threaded(gif_path)

        threading.Thread(target=_gif, daemon=True).start()
        return "🎞️ Generating tactical GIF..."
    elif cmd == '/cleanup':
        cleanup_old_files()
        return "🧹 Archives purged."
    return "❓ Unknown command. Use /help"


def telegram_listener() -> None:
    last_id = None
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
            params = {'timeout': 30}
            if last_id:
                params['offset'] = last_id + 1
            for u in requests.get(url, params=params, timeout=35).json().get('result', []):
                last_id = u['update_id']
                msg = u.get('message', {})
                if str(msg.get('chat', {}).get('id')) == TELEGRAM_CHAT_ID:
                    txt = msg.get('text', '')
                    if txt:
                        send_telegram_message(handle_command(txt), parse_mode='Markdown')
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            logger.error(f"Listener error: {e}")
            time.sleep(5)


def main() -> None:
    logger.info('Security System Initializing...')
    send_telegram_message('🛡️ *Security System Online*\nMonitoring Active.', parse_mode='Markdown')
    threading.Thread(target=automatic_motion_loop, daemon=True).start()
    threading.Thread(target=telegram_listener, daemon=True).start()
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        cap.release()


if __name__ == '__main__':
    main()
