"""Colored terminal output and progress display."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Color(Enum):
    """ANSI color codes."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    # Colors
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    
    # Bright colors
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_CYAN = "\033[96m"


def _supports_color() -> bool:
    """Check if the terminal supports color output."""
    # Check for NO_COLOR environment variable (https://no-color.org/)
    import os
    if os.environ.get("NO_COLOR"):
        return False
    
    # Check if stdout is a TTY
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        return False
    
    # Check for TERM
    term = os.environ.get("TERM", "")
    if term == "dumb":
        return False
    
    return True


# Global color support flag
_USE_COLOR = _supports_color()


def set_color_enabled(enabled: bool) -> None:
    """Enable or disable colored output."""
    global _USE_COLOR
    _USE_COLOR = enabled


def _colorize(text: str, *colors: Color) -> str:
    """Apply colors to text if color is enabled."""
    if not _USE_COLOR or not colors:
        return text
    prefix = "".join(c.value for c in colors)
    return f"{prefix}{text}{Color.RESET.value}"


@dataclass
class Console:
    """Styled console output handler."""
    
    verbose: bool = False
    quiet: bool = False
    
    def info(self, msg: str) -> None:
        """Print info message (blue)."""
        if not self.quiet:
            print(_colorize("ℹ", Color.BLUE), msg)
    
    def success(self, msg: str) -> None:
        """Print success message (green)."""
        if not self.quiet:
            print(_colorize("✓", Color.BRIGHT_GREEN), msg)
    
    def warning(self, msg: str) -> None:
        """Print warning message (yellow)."""
        print(_colorize("⚠", Color.YELLOW), msg, file=sys.stderr)
    
    def error(self, msg: str) -> None:
        """Print error message (red)."""
        print(_colorize("✗", Color.BRIGHT_RED), _colorize(msg, Color.RED), file=sys.stderr)
    
    def debug(self, msg: str) -> None:
        """Print debug message (dim) - only in verbose mode."""
        if self.verbose:
            print(_colorize(f"  {msg}", Color.DIM))
    
    def status(self, msg: str) -> None:
        """Print status update (cyan)."""
        if not self.quiet:
            print(_colorize("→", Color.CYAN), msg)
    
    def result(self, label: str, value: str) -> None:
        """Print a labeled result."""
        if not self.quiet:
            print(f"  {_colorize(label + ':', Color.DIM)} {value}")
    
    def progress(self, current: int, total: int, label: str = "") -> None:
        """Print a progress bar."""
        if self.quiet:
            return
        
        width = 30
        filled = int(width * current / total) if total > 0 else 0
        bar = "█" * filled + "░" * (width - filled)
        pct = (current / total * 100) if total > 0 else 0
        
        line = f"\r  {_colorize(bar, Color.CYAN)} {pct:5.1f}%"
        if label:
            line += f" {_colorize(label, Color.DIM)}"
        
        print(line, end="", flush=True)
    
    def encoding_progress(self, percent: float, label: str = "") -> None:
        """Print encoding progress with percentage."""
        if self.quiet:
            return
        
        width = 30
        filled = int(width * percent / 100)
        bar = "█" * filled + "░" * (width - filled)
        
        line = f"  {_colorize(bar, Color.CYAN)} {percent:5.1f}%"
        if label:
            line += f" {_colorize(label, Color.DIM)}"
        
        # Move cursor to beginning of line, clear line, print
        sys.stdout.write(f"\x1b[2K\r{line}")
        sys.stdout.flush()
    
    def progress_done(self) -> None:
        """Complete the progress bar line."""
        if not self.quiet:
            print()  # Newline after progress bar
    
    def blank(self) -> None:
        """Print a blank line."""
        if not self.quiet:
            print()


def format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / 1_000_000:.2f} MB"
    else:
        return f"{size_bytes / 1_000_000_000:.2f} GB"


def format_duration(seconds: float) -> str:
    """Format seconds as human-readable duration."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def format_bitrate(kbps: int) -> str:
    """Format bitrate as human-readable string."""
    if kbps < 1000:
        return f"{kbps} kbps"
    else:
        return f"{kbps / 1000:.1f} Mbps"
