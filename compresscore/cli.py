from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from . import __version__
from .compress import compress, CompressResult
from .ffmpeg import ToolMissing, probe
from .output import Console, format_size, format_duration, format_bitrate
from .size import parse_size_to_bytes


def main() -> None:
    """Entry point for the cpc/compresscore CLI."""
    ap = argparse.ArgumentParser(
        prog="cpc",
        description="Size-targeted video compressor using VideoToolbox hardware encoding.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  cpc video.mov                     Compress to 8MB (Discord-friendly)
  cpc video.mov -t 25MB             Compress to 25MB
  cpc video.mov -o output.mp4       Specify output path
  cpc video.mov --codec h264        Use H.264 (more compatible)
  cpc video.mov -v                  Verbose output
""",
    )
    ap.add_argument(
        "input",
        type=str,
        help="Input video path",
    )
    ap.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Output path (default: <input>_compressed.mp4)",
    )
    ap.add_argument(
        "-t", "--target",
        type=str,
        default="8.0MB",
        help="Target size (e.g., 8MB, 7.9MB, 8MiB, 25000000). Default: 8MB",
    )
    ap.add_argument(
        "--codec",
        choices=["h264", "hevc"],
        default="hevc",
        help="Video codec. hevc is smaller, h264 is more compatible. Default: hevc",
    )
    ap.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Bitrate correction attempts per quality level. Default: 3",
    )
    ap.add_argument(
        "--overhead",
        type=float,
        default=0.02,
        help="Container overhead safety margin (0.0-0.1). Default: 0.02",
    )
    ap.add_argument(
        "--max-width",
        type=int,
        default=1920,
        help="Maximum output width. Default: 1920",
    )
    ap.add_argument(
        "--fps",
        type=int,
        default=60,
        help="Maximum FPS. Default: 60",
    )
    ap.add_argument(
        "--audio-kbps",
        type=int,
        default=96,
        help="Starting audio bitrate in kbps. Default: 96",
    )
    ap.add_argument(
        "--min-audio-kbps",
        type=int,
        default=48,
        help="Minimum audio bitrate before disabling audio. Default: 48",
    )
    ap.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed progress and ffmpeg output.",
    )
    ap.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Suppress all output except errors and final result.",
    )
    ap.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output.",
    )
    ap.add_argument(
        "-c", "--copy",
        action="store_true",
        help="Copy output file to clipboard (macOS only).",
    )
    ap.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = ap.parse_args()
    
    # Set up console
    if args.no_color:
        from .output import set_color_enabled
        set_color_enabled(False)
    
    console = Console(verbose=args.verbose, quiet=args.quiet)

    # Resolve paths
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        console.error(f"Input not found: {input_path}")
        sys.exit(1)
    
    if not input_path.is_file():
        console.error(f"Input is not a file: {input_path}")
        sys.exit(1)

    if args.output:
        output_path = Path(args.output).expanduser().resolve()
    else:
        output_path = input_path.with_name(f"{input_path.stem}_compressed.mp4")

    # Parse target size
    try:
        target_bytes = parse_size_to_bytes(args.target)
    except ValueError as e:
        console.error(str(e))
        sys.exit(1)
    
    # Validate parameters
    if args.max_width < 128:
        console.error("Max width must be at least 128 pixels")
        sys.exit(1)
    if args.fps < 1 or args.fps > 120:
        console.error("FPS must be between 1 and 120")
        sys.exit(1)
    if args.overhead < 0 or args.overhead > 0.5:
        console.error("Overhead must be between 0.0 and 0.5")
        sys.exit(1)

    # Show input info
    try:
        info = probe(input_path)
        input_size = input_path.stat().st_size
        
        console.info(f"Input: {input_path.name}")
        console.result("Size", format_size(input_size))
        console.result("Duration", format_duration(info.duration_s))
        if info.width and info.height:
            console.result("Resolution", f"{info.width}×{info.height}")
        console.result("Audio", "Yes" if info.has_audio else "No")
        console.blank()
        
        console.status(f"Compressing to {format_size(target_bytes)} ({args.codec.upper()})")
        
    except ToolMissing as e:
        console.error(str(e))
        console.debug("Install FFmpeg: brew install ffmpeg")
        sys.exit(1)
    except Exception as e:
        console.error(f"Failed to probe input: {e}")
        sys.exit(1)

    # Run compression
    start_time = time.perf_counter()
    try:
        result = compress(
            input_path=input_path,
            output_path=output_path,
            target_bytes=target_bytes,
            codec=args.codec,
            max_retries=args.max_retries,
            overhead=args.overhead,
            start_max_width=args.max_width,
            start_fps=args.fps,
            start_audio_kbps=args.audio_kbps,
            min_audio_kbps=args.min_audio_kbps,
            verbose=args.verbose,
            console=console,
        )
        
        elapsed = time.perf_counter() - start_time
        output_size = result.output_path.stat().st_size
        
        # Calculate stats
        compression_ratio = input_size / output_size if output_size > 0 else 0
        space_saved = input_size - output_size
        speed_factor = info.duration_s / elapsed if elapsed > 0 else 0
        
        # In quiet mode, just print the output path
        if args.quiet:
            print(result.output_path)
        else:
            console.blank()
            console.success(f"Compressed: {result.output_path.name}")
            console.result("Output size", f"{format_size(output_size)} ({output_size / target_bytes * 100:.1f}% of target)")
            console.result("Compression", f"{compression_ratio:.1f}x ({format_size(space_saved)} saved)")
            console.result("Settings", f"{result.width}×{result.height} @ {result.fps}fps, {format_bitrate(result.video_kbps)}")
            console.result("Time", f"{format_duration(elapsed)} ({speed_factor:.1f}x realtime)")
            console.result("Attempts", str(result.attempts))
        
        # Copy to clipboard if requested
        if args.copy:
            try:
                # use osascript to copy file to clipboard
                script = f'set the clipboard to (POSIX file "{result.output_path}")'
                subprocess.run(
                    ["osascript", "-e", script],
                    check=True,
                    capture_output=True,
                )
                console.success("Copied file to clipboard")
            except FileNotFoundError:
                console.warning("Clipboard copy failed: osascript not found (macOS only)")
            except subprocess.CalledProcessError:
                console.warning("Clipboard copy failed")
        
    except ToolMissing as e:
        console.error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        console.blank()
        console.warning("Compression cancelled by user")
        sys.exit(130)
    except RuntimeError as e:
        console.error(str(e))
        sys.exit(1)
    except ValueError as e:
        console.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
