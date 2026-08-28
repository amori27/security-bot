# Security Surveillance Bot

Motion detection surveillance system with Telegram alerts, video/audio recording, thermal heatmaps, and RTSP stream support.

## Quick Start

```bash
export TELEGRAM_TOKEN="your_bot_token"
export TELEGRAM_CHAT_ID="your_chat_id"
python bot.py
```

### Telegram Commands

- `/status` — System status
- `/photo` — Capture and send current frame
- `/live` — 5-second live loop GIF
- `/cleanup` — Remove all recorded files
- `/say <text>` — Text-to-speech alert

## How It Works

- **Motion detection** — OpenCV KNN background subtraction with bounding box overlay
- **Recording** — Threaded MP4 video + WAV audio capture
- **Heatmaps** — JET-colormap activity visualization per motion sequence
- **Cleanup** — Automatic 7-day file retention

## Requirements

- Python 3.8+, ffmpeg, webcam or RTSP camera
- Telegram Bot Token and Chat ID

## License

MIT
