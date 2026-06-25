# Security Surveillance Bot v2.0

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)


A comprehensive motion-detection surveillance system with Telegram integration, video/audio recording, thermal heatmaps, and RTSP stream playback.

## Features

- **KNN Motion Detection**: Advanced background subtraction using OpenCV's KNN algorithm
- **Real-time Bounding Boxes**: Motion-detected regions highlighted in recordings
- **Video & Audio Recording**: Simultaneous MP4 video and WAV audio capture
- **Thermal Heatmaps**: Visual representation of motion activity
- **Telegram Integration**: Remote alerts and command control
- **RTSP Stream Support**: Direct stream playback and recording
- **Thread-Safe Operation**: Non-blocking multi-threaded architecture
- **Automatic File Cleanup**: 7-day retention policy with auto-deletion
- **Robust Error Handling**: Graceful failure recovery

## Requirements

- Python 3.8+
- ffmpeg (system dependency)
- Webcam or compatible video capture device
- Telegram Bot Token and Chat ID
- pyaudio dependencies (alsa-lib, portaudio, etc.)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/amori27/security-bot.git
cd security-bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Ensure ffmpeg is installed:
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# macOS
brew install ffmpeg
```

## Configuration

Set environment variables before running:

```bash
export TELEGRAM_TOKEN="your_bot_token_here"
export TELEGRAM_CHAT_ID="your_chat_id_here"
```

Or modify the defaults in `bot.py`:
- `TELEGRAM_TOKEN`: Telegram bot API token
- `TELEGRAM_CHAT_ID`: Target chat ID for alerts
- `MOTION_THRESHOLD`: Motion detection sensitivity (pixels)
- `VIDEO_FPS`: Video frame rate (default: 20)
- `RATE`: Audio sample rate (default: 44100)
- `FILE_RETENTION_DAYS`: Auto-cleanup interval (default: 7)

## Usage

```bash
python bot.py
```

### Telegram Commands

- `/help` - Display available commands
- `/status` - Get current system status
- `/photo` - Capture and send current frame
- `/live` - Get direct stream link
- `/say <text>` - Text-to-speech alert
- `/cleanup` - Remove all recorded files
- Stream URLs: `/stream <protocol>://<address>:<port>/<path>`

## Configuration Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `MOTION_THRESHOLD` | 2500px | Motion detection sensitivity |
| `VIDEO_FPS` | 20 | Recording frames per second |
| `RATE` | 44100 | Audio sample rate (Hz) |
| `ALERT_DELAY_SECONDS` | 1.5 | Delay before sending alerts |
| `FILE_RETENTION_DAYS` | 7 | Days to keep recordings |
| `PHOTO_QUALITY` | 90 | JPEG quality (0-100) |

## Architecture

- **VideoRecorder**: Thread-based MP4 encoder using cv2.VideoWriter
- **AudioRecorder**: Thread-based WAV recorder via pyaudio
- **Motion Detection Loop**: KNN background subtraction with bounding box overlay
- **Telegram Listener**: Long-polling update handler
- **Command Handler**: Non-blocking async command processor

## Performance

- Motion detection: ~30-50ms per frame
- Alert transmission: < 2 seconds
- Video codec: H.264 (mp4v)
- Audio codec: PCM WAV

## Troubleshooting

**Cannot open webcam**: Verify camera permissions and USB connection
**pyaudio issues**: Install portaudio: `sudo apt-get install portaudio19-dev`
**ffmpeg not found**: Install ffmpeg from system package manager
**Telegram connection**: Verify token, chat ID, and internet connectivity

## License

MIT License

## Author

Security Bot Development Team
