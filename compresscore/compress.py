"""Core compression logic with iterative bitrate adjustment."""

from __future__ import annotations

import math
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple, TYPE_CHECKING

from .encoder import EncodePlan, build_ffmpeg_cmd
from .ffmpeg import has_videotoolbox_encoder, probe, run_ffmpeg

if TYPE_CHECKING:
    from .output import Console


# Bitrate thresholds in kbps
MIN_VIDEO_KBPS = 50       # Below this, quality is unusable

# Minimum bits per frame for acceptable quality (in bytes)
# Screen recordings with text need ~3-4 KB/frame for readable text
MIN_BYTES_PER_FRAME_TEXT = 3 * 1024  # 3 KB - minimum for readable text
GOOD_BYTES_PER_FRAME_TEXT = 5 * 1024  # 5 KB - good quality text


@dataclass
class CompressResult:
    """Result of a compression operation."""
    output_path: Path
    attempts: int
    width: int
    height: int
    fps: int
    video_kbps: int
    audio_kbps: int
    codec: str


def compute_video_kbps(
    target_bytes: int,
    duration_s: float,
    audio_kbps: int,
    overhead: float,
) -> int:
    """Derive video bitrate (kbps) to hit target size after container overhead.
    
    Args:
        target_bytes: Target file size in bytes.
        duration_s: Video duration in seconds.
        audio_kbps: Audio bitrate in kbps (0 if no audio).
        overhead: Container overhead fraction (e.g., 0.02 for 2%).
    
    Returns:
        Video bitrate in kbps, minimum MIN_VIDEO_KBPS.
    """
    if duration_s <= 0:
        raise ValueError("Duration must be positive")
    
    target_bits = target_bytes * 8.0 * (1.0 - overhead)
    audio_bps = audio_kbps * 1000.0
    video_bps = (target_bits / duration_s) - audio_bps
    return max(MIN_VIDEO_KBPS, int(video_bps / 1000.0))


def _optimal_fps_for_bitrate(available_kbps: int, max_fps: int) -> int:
    """Choose FPS based on available bitrate - lower FPS = more bits per frame.
    
    The key insight: screen recordings need sufficient bits per frame for
    readable text. We calculate the bytes-per-frame at different FPS options
    and choose the highest FPS that still gives acceptable quality.
    
    Target: ~3-5 KB per frame for readable text at 1080p+
    
    Args:
        available_kbps: Available video bitrate.
        max_fps: Maximum allowed FPS.
    
    Returns:
        Recommended FPS for the given bitrate.
    """
    # Calculate bytes per frame at different FPS levels
    # kbps * 1000 / 8 / fps = bytes per frame
    bytes_per_sec = available_kbps * 1000 / 8
    
    # Try FPS options from highest to lowest, pick first that gives good quality
    fps_options = [60, 30, 24]
    
    for fps in fps_options:
        if fps > max_fps:
            continue
        bytes_per_frame = bytes_per_sec / fps
        
        # If we get good bytes per frame at this FPS, use it
        if bytes_per_frame >= MIN_BYTES_PER_FRAME_TEXT:
            return fps
    
    # Fall back to lowest FPS for maximum quality
    return min(24, max_fps)


def _scaled_width(original_w: Optional[int], cap: int) -> int:
    """Cap width if known; fall back to cap when probe lacks dimensions."""
    if original_w is None or original_w <= 0:
        return cap
    return min(original_w, cap)


def _unique_preserve(seq: Iterable[int]) -> List[int]:
    """Order-preserving dedupe helper."""
    return list(dict.fromkeys(seq))


def _file_size(path: Path) -> int:
    """Get file size in bytes."""
    return path.stat().st_size


def _build_quality_ladder(
    info_width: Optional[int],
    info_has_audio: bool,
    start_max_width: int,
    start_fps: int,
    start_audio_kbps: int,
    min_audio_kbps: int,
    available_kbps: int,
) -> Tuple[List[int], List[int], List[int]]:
    """Build degradation ladders for resolution, FPS, and audio.
    
    Key insight: For low bitrate targets, we should prioritize lower FPS
    to get more bits per frame (sharper text, clearer detail).
    
    Args:
        info_width: Original video width from probe.
        info_has_audio: Whether source has audio.
        start_max_width: User-specified max width.
        start_fps: User-specified max FPS.
        start_audio_kbps: Starting audio bitrate.
        min_audio_kbps: Minimum audio before disabling.
        available_kbps: Estimated available video bitrate.
    
    Returns:
        Tuple of (width_ladder, fps_ladder, audio_ladder).
    """
    # Resolution ladder - maintain as long as possible
    width_caps = [start_max_width, 1920, 1600, 1280, 1024, 854, 640]
    width_ladder = _unique_preserve(
        _scaled_width(info_width, cap) for cap in width_caps
    )
    
    # FPS ladder - smart ordering based on available bitrate
    # Always start with the optimal FPS calculated from bitrate
    optimal_fps = _optimal_fps_for_bitrate(available_kbps, start_fps)
    
    # Build ladder starting from optimal, then try alternatives
    fps_candidates = [optimal_fps, 24, 30, 60]
    fps_ladder = _unique_preserve(f for f in fps_candidates if f <= start_fps)
    
    # Audio ladder - audio is cheap, don't degrade aggressively
    if not info_has_audio:
        audio_ladder = [0]
    else:
        audio_candidates = [start_audio_kbps, 96, 64, min_audio_kbps, 0]
        audio_ladder = _unique_preserve(
            a for a in audio_candidates if (a == 0 or a >= min_audio_kbps)
        )
    
    return width_ladder, fps_ladder, audio_ladder


def compress(
    input_path: Path,
    output_path: Path,
    target_bytes: int,
    codec: str = "hevc",
    max_retries: int = 3,
    overhead: float = 0.02,
    start_max_width: int = 1920,
    start_fps: int = 60,
    start_audio_kbps: int = 96,
    min_audio_kbps: int = 48,
    verbose: bool = False,
    console: Optional["Console"] = None,
) -> CompressResult:
    """Compress video to target size with iterative quality reduction.
    
    Uses a smart degradation ladder approach:
    1. Calculate available bitrate for target size
    2. Choose optimal FPS based on bitrate (lower FPS = more bits per frame)
    3. Try to hit target with calculated settings
    4. Reduce bitrate within current quality rung
    5. If still too large, step down resolution/fps/audio
    6. Repeat until target is met or options exhausted
    
    Args:
        input_path: Source video file.
        output_path: Destination for compressed video.
        target_bytes: Maximum file size in bytes.
        codec: Video codec ("h264" or "hevc").
        max_retries: Bitrate correction attempts per quality rung.
        overhead: Container overhead safety fraction.
        start_max_width: Initial maximum width.
        start_fps: Initial FPS cap.
        start_audio_kbps: Initial audio bitrate.
        min_audio_kbps: Minimum audio bitrate before disabling.
        verbose: Show detailed progress output.
        console: Console instance for styled output.
    
    Returns:
        CompressResult with output path and encoding details.
    
    Raises:
        ValueError: If codec is invalid.
        RuntimeError: If compression fails or target is unreachable.
    """
    info = probe(input_path)
    duration_s = info.duration_s

    # Validate codec
    if codec not in ("h264", "hevc"):
        raise ValueError("codec must be 'h264' or 'hevc'")
    if not has_videotoolbox_encoder(codec):
        raise RuntimeError(f"FFmpeg encoder not available: {codec}_videotoolbox")

    # Calculate initial available bitrate to inform FPS choice
    initial_audio = start_audio_kbps if info.has_audio else 0
    initial_video_kbps = compute_video_kbps(
        target_bytes, duration_s, initial_audio, overhead
    )
    
    # Build smart degradation ladders based on available bitrate
    width_ladder, fps_ladder, audio_ladder = _build_quality_ladder(
        info_width=info.width,
        info_has_audio=info.has_audio,
        start_max_width=start_max_width,
        start_fps=start_fps,
        start_audio_kbps=start_audio_kbps,
        min_audio_kbps=min_audio_kbps,
        available_kbps=initial_video_kbps,
    )
    
    # Calculate total combinations for progress
    total_rungs = len(width_ladder) * len(fps_ladder) * len(audio_ladder)
    
    # Calculate bytes per frame for quality assessment
    bytes_per_frame = (initial_video_kbps * 1000 / 8) / fps_ladder[0] if fps_ladder else 0
    is_quality_mode = fps_ladder[0] < start_fps  # True if we reduced FPS for quality
    
    if console:
        console.debug(f"Est. bitrate: {initial_video_kbps} kbps ({bytes_per_frame/1024:.1f} KB/frame at {fps_ladder[0]}fps)")
        console.debug(f"FPS: {fps_ladder} ({'quality' if is_quality_mode else 'smoothness'} mode)")
    elif verbose:
        print(f"Target: {target_bytes/1_000_000:.2f} MB, "
              f"Duration: {duration_s:.1f}s, "
              f"Est. video bitrate: {initial_video_kbps} kbps")
        print(f"FPS ladder: {fps_ladder} ({bytes_per_frame/1024:.1f} KB/frame)")

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    attempt = 0
    current_rung = 0
    with tempfile.TemporaryDirectory() as td:
        scratch = Path(td)
        
        for maxw in width_ladder:
            for fps in fps_ladder:
                for audio_kbps in audio_ladder:
                    current_rung += 1
                    
                    # Compute initial video bitrate for this rung
                    video_kbps = compute_video_kbps(
                        target_bytes, duration_s, audio_kbps, overhead
                    )
                    local_kbps = video_kbps

                    for retry in range(max_retries):
                        attempt += 1
                        candidate = scratch / f"attempt_{attempt}.mp4"

                        plan = EncodePlan(
                            codec=codec,
                            max_width=maxw,
                            fps=fps,
                            audio_kbps=audio_kbps,
                            video_kbps=local_kbps,
                            safety_overhead=overhead,
                        )

                        cmd = build_ffmpeg_cmd(input_path, candidate, plan)
                        
                        # Show progress
                        if console and not verbose:
                            label = f"{maxw}p {fps}fps {local_kbps}kbps"
                            console.progress(current_rung, total_rungs, label)
                        elif verbose:
                            if console:
                                console.debug(
                                    f"[{attempt}] {codec} w≤{maxw} {fps}fps "
                                    f"a={audio_kbps}k v={local_kbps}k"
                                )
                            else:
                                print(
                                    f"\n[attempt {attempt}] codec={codec} "
                                    f"width<={maxw} fps={fps} "
                                    f"audio={audio_kbps}k video={local_kbps}k "
                                    f"target={target_bytes:,} bytes"
                                )
                        
                        run_ffmpeg(cmd, quiet=not verbose)

                        size = _file_size(candidate)
                        
                        if verbose:
                            if console:
                                console.debug(f"[{attempt}] result: {size:,} bytes")
                            else:
                                print(f"[attempt {attempt}] result={size:,} bytes")

                        if size <= target_bytes:
                            if console and not verbose:
                                console.progress_done()
                            
                            os.replace(candidate, output_path)
                            
                            # Calculate output dimensions
                            out_info = probe(output_path)
                            out_width = out_info.width or maxw
                            out_height = out_info.height or (maxw * 9 // 16)
                            
                            return CompressResult(
                                output_path=output_path,
                                attempts=attempt,
                                width=out_width,
                                height=out_height,
                                fps=fps,
                                video_kbps=local_kbps,
                                audio_kbps=audio_kbps,
                                codec=codec,
                            )

                        # Adjust bitrate based on overshoot ratio
                        ratio = target_bytes / float(size)
                        margin = 0.96 if ratio < 0.85 else 0.98
                        new_kbps = int(max(
                            MIN_VIDEO_KBPS,
                            math.floor(local_kbps * ratio * margin)
                        ))
                        
                        # Force reduction to avoid infinite loops
                        if new_kbps >= local_kbps:
                            new_kbps = max(MIN_VIDEO_KBPS, local_kbps - 50)
                        
                        # Hit minimum - move to next rung
                        if new_kbps <= MIN_VIDEO_KBPS and local_kbps <= MIN_VIDEO_KBPS:
                            break
                        
                        local_kbps = new_kbps
    
    if console:
        console.progress_done()

    raise RuntimeError(
        "Could not compress under target size with allowed degradations. "
        "Try a smaller target, allow lower resolution/fps, reduce audio, "
        "or switch to HEVC codec."
    )
