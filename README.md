# CompressCore

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)

A size-targeted video compressor using FFmpeg with Apple VideoToolbox hardware acceleration.

## Features

- **Size-targeted** — Specify exact output size (8MB, 25MB, etc.)
- **Hardware accelerated** — Uses Apple VideoToolbox for fast encoding
- **Smart quality** — Automatically trades FPS for quality at low bitrates
- **Screen recording optimized** — Spatial AQ preserves text and UI elements
- **HDR compatible** — Auto-converts HDR to SDR for compatibility

## Installation

### Quick Install (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/ishsharm0/compresscore/main/install.sh | bash
```

This automatically installs CompressCore and adds it to your PATH.

### From source

```bash
git clone https://github.com/ishsharm0/compresscore.git
cd compresscore
pip install -e .
```

## Quick Start

```bash
# Compress to 8MB (Discord-friendly)
cpc video.mov
# Or use the module directly:
python -m compresscore video.mov

# Compress to 25MB
cpc video.mov -t 25MB

# Specify output path
cpc video.mov -o compressed.mp4
```

## Usage

```bash
# Basic usage
cpc input.mov                      # → input_compressed.mp4 (8MB)
cpc input.mov -t 25MB              # Custom target size
cpc input.mov -o output.mp4        # Custom output path

# Codec selection
cpc input.mov --codec hevc         # HEVC/H.265 (default, smaller)
cpc input.mov --codec h264         # H.264 (more compatible)

# Quality controls
cpc input.mov --max-width 1280     # Limit resolution
cpc input.mov --fps 30             # Limit framerate
cpc input.mov --audio-kbps 128     # Higher audio quality

# Output modes
cpc input.mov -v                   # Verbose (show FFmpeg output)
cpc input.mov -q                   # Quiet (print path only)
cpc input.mov --no-color           # Disable colors
```

## Options

| Option | Default | Description |
|--------|---------|-------------|
| `-o, --output` | `<input>_compressed.mp4` | Output file path |
| `-t, --target` | `8MB` | Target size (`8MB`, `7.9MiB`, `25000000`) |
| `--codec` | `hevc` | Video codec (`h264` or `hevc`) |
| `--max-width` | `1920` | Maximum output width |
| `--fps` | `60` | Maximum framerate |
| `--audio-kbps` | `96` | Starting audio bitrate (kbps) |
| `--min-audio-kbps` | `48` | Minimum audio before muting |
| `--max-retries` | `3` | Bitrate attempts per quality level |
| `--overhead` | `0.02` | Container overhead margin |
| `-v, --verbose` | | Show FFmpeg output and debug info |
| `-q, --quiet` | | Output only the result path |
| `--no-color` | | Disable colored terminal output |
| `--version` | | Show version number |

## Example Output

```
ℹ Input: video.mov
  Size: 443.55 MB
  Duration: 57.3s
  Resolution: 2940×1912
  Audio: No

→ Compressing to 8.00 MB (HEVC)

✓ Compressed: video_compressed.mp4
  Output size: 7.84 MB (98.0% of target)
  Compression: 56.6x (435.71 MB saved)
  Settings: 1920×1248 @ 30fps, 1.1 Mbps
  Time: 11.2s (5.1x realtime)
  Attempts: 1
```

## How It Works

CompressCore uses a smart iterative approach:

1. **Analyze** — Probe input for duration, resolution, and audio
2. **Calculate** — Determine available bitrate from target size
3. **Optimize FPS** — For low bitrates, prefer lower FPS for sharper frames
4. **Encode** — Hardware-accelerated encoding with VideoToolbox
5. **Verify** — Check output size, adjust bitrate if needed
6. **Degrade** — If still too large, reduce resolution/FPS/audio

### Quality Features

| Feature | Benefit |
|---------|---------|
| **Spatial AQ** | Preserves static regions (text, UI) |
| **Lanczos scaling** | Sharp downscaling, ideal for text |
| **HDR→SDR** | Automatic colorspace conversion |
| **Large GOP** | Better compression for static content |
| **B-frames** | Improved compression efficiency |
| **hvc1 tag** | QuickTime/iOS compatibility |

## Requirements

- **macOS** (VideoToolbox is macOS-only)
- **Python 3.9+**
- **FFmpeg** with VideoToolbox support

```bash
# Install FFmpeg via Homebrew
brew install ffmpeg
```

## API Usage

```python
from compresscore import compress, probe, parse_size_to_bytes
from pathlib import Path

# Probe video info
info = probe(Path("input.mov"))
print(f"Duration: {info.duration_s}s, Resolution: {info.width}x{info.height}")

# Compress video
result = compress(
    input_path=Path("input.mov"),
    output_path=Path("output.mp4"),
    target_bytes=parse_size_to_bytes("8MB"),
    codec="hevc",
)
print(f"Output: {result.output_path} ({result.video_kbps} kbps)")
```

## License

MIT © 2026
