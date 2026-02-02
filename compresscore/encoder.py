"""Encoding plans and FFmpeg command building."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List


# Low bitrate threshold - below this we use more aggressive quality settings
LOW_BITRATE_KBPS = 500


@dataclass
class EncodePlan:
    """Configuration for a single encode attempt."""
    codec: str          # "h264" or "hevc"
    max_width: int
    fps: int
    audio_kbps: int     # 0 disables audio
    video_kbps: int     # target average bitrate
    safety_overhead: float


def build_ffmpeg_cmd(
    input_path: Path,
    output_path: Path,
    plan: EncodePlan,
) -> List[str]:
    """Construct an optimized FFmpeg command using VideoToolbox hardware encoding.
    
    Optimizations for quality:
        - Spatial AQ (adaptive quantization) for preserving static regions
        - Disabled realtime mode for better quality analysis
        - Higher reference frames for better motion compensation
        - Larger GOP for better compression of static content
        - Proper HDR to SDR conversion
        - High-quality lanczos scaling
        
    For low bitrate encodes:
        - Larger buffer for better rate distribution
        - Smaller headroom to stay closer to target
    """
    vcodec = f"{plan.codec}_videotoolbox"
    is_low_bitrate = plan.video_kbps < LOW_BITRATE_KBPS

    # Build video filter chain with high quality settings
    vf_parts = [
        # High quality lanczos scaling - best for text/UI
        f"scale='min({plan.max_width},iw)':-2:flags=lanczos+accurate_rnd",
        # Convert HDR to SDR if present
        "colorspace=all=bt709:iall=bt2020:fast=1",
        # Ensure compatible output format
        "format=yuv420p",
    ]
    vf = ",".join(vf_parts)

    # Calculate GOP size - larger GOP = better compression for static content
    # For low bitrates, use even larger GOP to maximize efficiency
    gop_multiplier = 6 if is_low_bitrate else 4
    gop_size = min(plan.fps * gop_multiplier, 300)
    
    # Rate control: for low bitrates, use tighter headroom
    # This gives more bits to static frames (better text quality)
    maxrate_mult = 1.5 if is_low_bitrate else 2.0
    bufsize_mult = 6 if is_low_bitrate else 4

    cmd = [
        "-y",
        "-i", str(input_path),
        # Explicit stream selection
        "-map", "0:v:0",
        "-map", "0:a:0?",
        "-map_metadata", "-1",
        "-movflags", "+faststart",
        "-vf", vf,
        "-r", str(plan.fps),
        "-c:v", vcodec,
        
        # === VideoToolbox Quality Optimizations ===
        # Average bitrate with headroom for complex frames
        "-b:v", f"{plan.video_kbps}k",
        "-maxrate", f"{int(plan.video_kbps * maxrate_mult)}k",
        "-bufsize", f"{int(plan.video_kbps * bufsize_mult)}k",
        
        # Spatial Adaptive Quantization - CRITICAL for screen recordings
        # Preserves quality in static regions, allows more compression in motion
        "-spatial_aq", "1",
        
        # Disable realtime mode - spend more time on quality
        "-realtime", "0",
        
        # Disable speed priority - maximize quality
        "-prio_speed", "0",
        
        # More reference frames for better motion estimation
        "-max_ref_frames", "4",
        
        # Keyframe interval - larger for static screen content
        "-g", str(gop_size),
        
        # Allow B-frames for better compression
        "-bf", "3",
        
        # Profile and format
        "-profile:v", "main",
        "-pix_fmt", "yuv420p",
        
        # Apple-compatible container tag
        "-tag:v", "hvc1" if plan.codec == "hevc" else "avc1",
    ]

    if plan.audio_kbps > 0:
        cmd += ["-c:a", "aac", "-b:a", f"{plan.audio_kbps}k"]
    else:
        cmd += ["-an"]

    cmd += [str(output_path)]
    return cmd
