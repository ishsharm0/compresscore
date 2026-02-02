"""FFmpeg wrapper for video probing and encoding."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

__all__ = ["ToolMissing", "ProbeInfo", "probe", "has_videotoolbox_encoder", "run_ffmpeg"]


class ToolMissing(RuntimeError):
    """Raised when a required external tool (ffmpeg/ffprobe) is not found."""
    pass


@dataclass(frozen=True)
class ProbeInfo:
    """Container for video probe results."""
    duration_s: float
    has_audio: bool
    width: Optional[int]
    height: Optional[int]


@lru_cache(maxsize=4)
def _require_tool(name: str) -> str:
    """Find a tool in PATH, caching the result."""
    path = shutil.which(name)
    if not path:
        raise ToolMissing(f"Required tool not found in PATH: {name}")
    return path


def probe(input_path: Path) -> ProbeInfo:
    ffprobe = _require_tool("ffprobe")
    cmd = [
        ffprobe,
        "-v", "error",
        "-print_format", "json",
        "-show_format",
        "-show_streams",
        str(input_path),
    ]
    out = subprocess.check_output(cmd)
    j = json.loads(out.decode("utf-8", errors="replace"))

    fmt = j.get("format", {})
    duration_s = float(fmt.get("duration") or 0.0)
    if duration_s <= 0.0:
        raise RuntimeError("Could not determine duration from ffprobe output.")

    streams = j.get("streams", [])
    has_audio = any(s.get("codec_type") == "audio" for s in streams)

    vstreams = [s for s in streams if s.get("codec_type") == "video"]
    width = None
    height = None
    if vstreams:
        width = vstreams[0].get("width")
        height = vstreams[0].get("height")

    return ProbeInfo(duration_s=duration_s, has_audio=has_audio, width=width, height=height)


@lru_cache(maxsize=4)
def has_videotoolbox_encoder(codec: str) -> bool:
    """Check if a VideoToolbox encoder is available for the given codec.
    
    Args:
        codec: Either 'h264' or 'hevc'.
    
    Returns:
        True if the encoder is available.
    """
    ffmpeg = _require_tool("ffmpeg")
    enc = f"{codec}_videotoolbox"
    cmd = [ffmpeg, "-hide_banner", "-encoders"]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode("utf-8", errors="replace")
        return enc in out
    except subprocess.CalledProcessError:
        return False


def run_ffmpeg(
    cmd: list[str],
    *,
    quiet: bool = False,
    duration_s: float = 0.0,
    progress_callback: "Optional[callable]" = None,
) -> None:
    """Run an ffmpeg command with optional progress tracking.
    
    Args:
        cmd: FFmpeg arguments (without the 'ffmpeg' executable itself).
        quiet: If True, suppress progress output.
        duration_s: Total duration in seconds for progress calculation.
        progress_callback: Callable(percent: float, time_s: float) for progress updates.
    
    Raises:
        RuntimeError: If ffmpeg exits with a non-zero code.
        KeyboardInterrupt: If the user cancels the operation.
    """
    import re
    
    ffmpeg = _require_tool("ffmpeg")
    # Add progress output to stderr
    full = [ffmpeg, "-progress", "pipe:2", "-nostats", *cmd]
    
    try:
        p = subprocess.Popen(
            full,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  # Line buffered
        )

        time_pattern = re.compile(r"out_time_ms=(\d+)")
        
        if p.stderr is not None:
            while True:
                line = p.stderr.readline()
                if not line and p.poll() is not None:
                    break
                if not line:
                    continue
                    
                line = line.strip()
                
                # Parse progress info
                if progress_callback and duration_s > 0:
                    match = time_pattern.match(line)
                    if match:
                        time_us = int(match.group(1))
                        time_s = time_us / 1_000_000
                        percent = min(100.0, (time_s / duration_s) * 100)
                        progress_callback(percent, time_s)
                
                # Show raw output in verbose mode
                if not quiet and not line.startswith(("frame=", "fps=", "stream_", "out_time", "dup_", "drop_", "speed=", "progress=", "bitrate=")):
                    print(line)

        rc = p.wait()
        
        # Final progress update
        if progress_callback and duration_s > 0:
            progress_callback(100.0, duration_s)
        
        if rc != 0:
            raise RuntimeError(f"ffmpeg failed with exit code {rc}")
    except KeyboardInterrupt:
        p.terminate()
        p.wait()
        raise
