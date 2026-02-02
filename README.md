# CompressCore

<p align="center">
  <strong>🎬 Size-targeted video compression with hardware acceleration</strong>
</p>

<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.9+-blue.svg" alt="Python 3.9+"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-green.svg" alt="MIT License"></a>
  <a href="https://www.apple.com/macos/"><img src="https://img.shields.io/badge/platform-macOS-lightgrey.svg" alt="macOS"></a>
</p>

<p align="center">
  Compress any video to an exact file size. Perfect for Discord, Slack, email, or any platform with upload limits.<br>
  Uses Apple VideoToolbox for <strong>blazing fast</strong> hardware-accelerated encoding.
</p>

---

## ⚡ Quick Demo

```bash
# Compress a 500MB screen recording to Discord's 8MB limit
cpc recording.mov -c

# Output copied to clipboard, ready to paste!
```

## 🚀 Performance

Tested on MacBook Air M4 — **up to 7x faster than realtime**:

| Input | Size | Target | Output | Compression | Time |
|-------|------|--------|--------|-------------|------|
| 60s 1440p screen recording | 425 MB | 8 MB | 7.6 MB | **55.9x smaller** | 8.4s |
| 2min 4K video | 1.1 GB | 25 MB | 24 MB | **46.9x smaller** | 32.5s |
| 30s 1080p clip | 72 MB | 8 MB | 7.6 MB | **9.5x smaller** | 8.5s |

> Smart FPS optimization automatically reduces framerate for low-bitrate targets to keep text sharp and readable.

---

## ✨ Features

- **📦 Size-targeted** — Specify exact output size (8MB, 25MB, etc.)
- **⚡ Hardware accelerated** — Uses Apple VideoToolbox for fast encoding
- **🧠 Smart quality** — Automatically trades FPS for quality at low bitrates
- **🖥️ Screen recording optimized** — Spatial AQ preserves text and UI elements
- **🎨 HDR compatible** — Auto-converts HDR to SDR for compatibility
- **📋 Clipboard copy** — Copy output with `-c` for instant sharing

---

## 📦 Installation

### One-liner (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/ishsharm0/compresscore/main/install.sh | bash
```

### From source

```bash
git clone https://github.com/ishsharm0/compresscore.git
cd compresscore
pip install -e .
```

### Requirements

- **macOS** (VideoToolbox is macOS-only)
- **Python 3.9+**
- **FFmpeg** — `brew install ffmpeg`

---

## 🎯 Usage

```bash
# Basic — compress to 8MB (Discord default)
cpc video.mov

# Copy to clipboard after compression
cpc video.mov -c

# Custom target size
cpc video.mov -t 25MB

# Specify output path
cpc video.mov -o compressed.mp4

# Use H.264 for maximum compatibility
cpc video.mov --codec h264

# Verbose mode (see FFmpeg output)
cpc video.mov -v
```

### All Options

| Option | Default | Description |
|--------|---------|-------------|
| `-t, --target` | `8MB` | Target size (8MB, 25MB, 100MB, etc.) |
| `-o, --output` | `<input>_compressed.mp4` | Output file path |
| `-c, --copy` | | Copy output to clipboard (macOS) |
| `--codec` | `hevc` | Video codec (`hevc` or `h264`) |
| `--max-width` | `1920` | Maximum output width |
| `--fps` | `60` | Maximum framerate |
| `-v, --verbose` | | Show detailed FFmpeg output |
| `-q, --quiet` | | Output only the result path |

---

## 📊 Example Output

```
ℹ Input: screen_recording.mov
  Size: 443.55 MB
  Duration: 57.3s
  Resolution: 2940×1912
  Audio: No

→ Compressing to 8.00 MB (HEVC)
  ██████████████████████████████ 100.0% 1920×1248 30fps

✓ Compressed: screen_recording_compressed.mp4
  Output size: 7.84 MB (98.0% of target)
  Compression: 56.6x (435.71 MB saved)
  Settings: 1920×1248 @ 30fps, 1.1 Mbps
  Time: 11.2s (5.1x realtime)
✓ Copied to clipboard
```

---

## 🔧 How It Works

1. **Analyze** — Probe input for duration, resolution, and audio
2. **Calculate** — Determine available bitrate from target size
3. **Optimize** — For low bitrates, reduce FPS for sharper frames
4. **Encode** — Hardware-accelerated VideoToolbox encoding
5. **Verify** — Check output size, adjust if needed

### Quality Optimizations

| Feature | Why It Matters |
|---------|----------------|
| **Spatial AQ** | Preserves text and UI in screen recordings |
| **Lanczos scaling** | Sharp downscaling, ideal for text |
| **Smart FPS** | Lower FPS = more bits per frame = sharper image |
| **HDR→SDR** | Automatic colorspace conversion |
| **hvc1 tag** | QuickTime/iOS compatibility |

---

## 🐍 Python API

```python
from compresscore import compress, probe, parse_size_to_bytes
from pathlib import Path

# Check video info
info = probe(Path("input.mov"))
print(f"{info.duration_s}s, {info.width}x{info.height}")

# Compress to target size
result = compress(
    input_path=Path("input.mov"),
    output_path=Path("output.mp4"),
    target_bytes=parse_size_to_bytes("8MB"),
)
print(f"Compressed to {result.video_kbps} kbps")
```

---

## 📄 License

MIT © 2026
