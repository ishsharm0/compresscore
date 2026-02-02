# CompressCore

Compress videos to a target file size. Built for screen recordings that need to fit Discord's 8MB limit.

Uses FFmpeg with VideoToolbox hardware encoding on macOS.

## Install

```bash
curl -sSL https://raw.githubusercontent.com/ishsharm0/compresscore/main/install.sh | bash
```

Or clone and `pip install -e .`

Requires macOS, Python 3.9+, and FFmpeg (`brew install ffmpeg`).

## Usage

```bash
cpc video.mov                # compress to 8MB
cpc video.mov -t 25MB        # custom target
cpc video.mov -c             # copy result to clipboard
cpc video.mov -o out.mp4     # custom output path
```

The `-c` flag copies the output file to your clipboard so you can paste directly into Discord/Slack.

## Options

```
-t, --target     Target size (default: 8MB)
-o, --output     Output path (default: input_compressed.mp4)
-c, --copy       Copy to clipboard after compression
--codec          hevc (default) or h264
--max-width      Max width (default: 1920)
--fps            Max fps (default: 60)
-v, --verbose    Show ffmpeg output
-q, --quiet      Only print output path
```

## Benchmarks

On an M4 MacBook Air:

| Input | Target | Result | Time |
|-------|--------|--------|------|
| 425MB 1440p 60s | 8MB | 7.6MB (56x compression) | 8s |
| 1.1GB 4K 2min | 25MB | 24MB (47x compression) | 32s |
| 72MB 1080p 30s | 8MB | 7.6MB (9x compression) | 8s |

## How it works

1. Probes the input video for duration/resolution
2. Calculates the video bitrate needed to hit the target size
3. If the bitrate is too low for good quality, drops FPS (30fps instead of 60fps gives 2x more bits per frame)
4. Encodes with VideoToolbox (hardware accelerated HEVC/H.264)
5. If output is too big, lowers bitrate and retries

Quality features: spatial AQ (preserves text), lanczos scaling, HDR→SDR conversion, hvc1 tag for QuickTime compatibility.

## API

```python
from compresscore import compress, probe
from pathlib import Path

result = compress(
    input_path=Path("input.mov"),
    output_path=Path("output.mp4"),
    target_bytes=8 * 1024 * 1024,  # 8MB
)
```

## License

MIT
