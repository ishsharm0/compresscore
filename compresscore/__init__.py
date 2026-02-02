"""CompressCore - Size-targeted video compression with VideoToolbox."""

from .compress import compress, CompressResult
from .ffmpeg import ToolMissing, probe, ProbeInfo
from .output import Console, format_size, format_duration, format_bitrate
from .size import parse_size_to_bytes

__all__ = [
    "__version__",
    "compress",
    "CompressResult",
    "Console",
    "format_bitrate",
    "format_duration",
    "format_size",
    "parse_size_to_bytes",
    "probe",
    "ProbeInfo",
    "ToolMissing",
]
__version__ = "0.1.0"
