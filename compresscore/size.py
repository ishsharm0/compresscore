"""Size parsing utilities."""

from __future__ import annotations


BYTES_PER_MB_DECIMAL = 1_000_000
BYTES_PER_MIB = 1024 * 1024


def parse_size_to_bytes(s: str) -> int:
    """Parse a human-friendly size string (e.g., 8MB, 7.9m, 8MiB) into bytes.
    
    Supports:
        - Raw integers (bytes)
        - MiB suffix (mebibytes, 1024*1024)
        - MB suffix (megabytes, 1,000,000)
        - M suffix (shorthand for MB)
        - KiB suffix (kibibytes, 1024)
        - KB/K suffix (kilobytes, 1000)
        - GiB/GB/G suffix (gigabytes)
    
    Raises:
        ValueError: If the format is unrecognized or value is non-positive.
    """
    raw = s.strip()
    if not raw:
        raise ValueError("Size cannot be empty")
    
    # Handle raw integer (bytes)
    if raw.isdigit():
        return int(raw)

    x = raw.lower().replace(" ", "")
    
    try:
        # Binary units first (longer suffixes)
        if x.endswith("gib"):
            value = float(x[:-3]) * BYTES_PER_MIB * 1024
        elif x.endswith("mib"):
            value = float(x[:-3]) * BYTES_PER_MIB
        elif x.endswith("kib"):
            value = float(x[:-3]) * 1024
        # Decimal units
        elif x.endswith("gb"):
            value = float(x[:-2]) * BYTES_PER_MB_DECIMAL * 1000
        elif x.endswith("mb"):
            value = float(x[:-2]) * BYTES_PER_MB_DECIMAL
        elif x.endswith("kb"):
            value = float(x[:-2]) * 1000
        # Single letter shortcuts (must be last)
        elif x.endswith("g"):
            value = float(x[:-1]) * BYTES_PER_MB_DECIMAL * 1000
        elif x.endswith("m"):
            value = float(x[:-1]) * BYTES_PER_MB_DECIMAL
        elif x.endswith("k"):
            value = float(x[:-1]) * 1000
        else:
            raise ValueError(f"Unrecognized size format: {s}")
        
        if value <= 0:
            raise ValueError(f"Size must be positive: {s}")
        
        return int(value)
    except ValueError as e:
        if "could not convert" in str(e).lower():
            raise ValueError(f"Invalid numeric value in size: {s}") from e
        raise
