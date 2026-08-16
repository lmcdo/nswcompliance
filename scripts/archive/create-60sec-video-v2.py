#!/usr/bin/env python3
"""
Create 60-Second PlotDetect Screencast - V2
Fixed segment duration handling using proper trim and speed adjustment.
"""

import subprocess
import os
import sys

FFMPEG = "C:/ffmpeg/bin/ffmpeg.exe"
SOURCE = "C:/Users/lawre/Videos/Verifyfinal.mp4"
OUTPUT = "C:/Users/lawre/Videos/PlotDetect_60sec_v2.mp4"
TEMP_DIR = "C:/Users/lawre/Videos/temp"

# Segment mapping: (source_start, source_end, target_duration, name)
# Total target: 60 seconds
# Cut 0:12-0:16 from original = skip source 12-16s
SEGMENTS = [
    (0, 8, 5, "Search"),        # Address search -> 5s
    (10, 12, 2, "Portal1"),     # Property loads -> 2s (before cut)
    (16, 22, 4, "Portal2"),     # After cut, SEPP starting -> 4s
    (22, 55, 12, "SEPP"),       # SEPP content -> 12s
    (62, 88, 10, "LEP"),        # LEP tab content -> 10s
    (95, 140, 12, "DCP"),       # DCP tab content -> 12s
    (192, 220, 12, "AI"),       # AI/Quick Reference -> 12s
    (218, 221, 3, "End"),       # End frame -> 3s
]

# Text overlays for OUTPUT (60-second video)
# SEPP Controls starts at 0:19, rest follows
OVERLAYS = [
    # Search section (0-5s)
    ("Planning Assessment in 60 Seconds", 0, 3, "center", 52),
    ("Enter any address in Inner West LGA", 3, 5, "bottom", 36),

    # Portal section (5-11s)
    ("185 Parramatta Rd, Annandale", 5, 8, "bottom", 36),
    ("NSW Planning Portal data", 8, 11, "bottom", 38),

    # Portal continued + SEPP starts (11-19s) - visual transition, no text
    ("Zone | Lot Size | Heritage", 11, 15, "bottom", 34),
    ("Constraints auto-detected", 15, 19, "bottom", 34),

    # SEPP section - text starts at 0:19
    ("SEPP Controls (State Level)", 19, 22, "bottom", 38),
    ("BASIX | TOD | Parking", 22, 25, "bottom", 34),
    ("Multi-Occupancy Eligibility", 25, 28, "bottom", 34),

    # LEP section (28-38s)
    ("LEP Controls (Local)", 28, 31, "bottom", 38),
    ("Key Site | Heritage Conservation", 31, 34, "bottom", 34),
    ("PDF citations with page numbers", 34, 38, "bottom", 34),

    # DCP section (38-48s)
    ("DCP Provisions (Detailed)", 38, 41, "bottom", 38),
    ("558 provisions for this address", 41, 44, "bottom", 34),
    ("Filter by Topic | View by Page", 44, 48, "bottom", 34),

    # AI section (48-57s)
    ("Quick Reference", 48, 51, "bottom", 40),
    ("Instant lookup of planning requirements", 51, 54, "bottom", 32),
    ("No hallucination - database lookups only", 54, 57, "bottom", 32),

    # End (57-60s)
    ("verify.plotdetect.au", 57, 60, "center", 48),
]


def escape_text(text):
    """Escape text for FFmpeg drawtext filter"""
    return text.replace(":", "\\:").replace("'", "\\'").replace("|", "\\|")


def build_drawtext(text, start, end, position, fontsize):
    """Build a single drawtext filter string"""
    escaped = escape_text(text)

    if position == "center":
        x, y = "(w-text_w)/2", "(h-text_h)/2"
    else:  # bottom
        x, y = "(w-text_w)/2", "h-text_h-80"

    return (
        f"drawtext=text='{escaped}':"
        f"fontsize={fontsize}:"
        f"fontcolor=white:"
        f"x={x}:y={y}:"
        f"box=1:boxcolor=black@0.6:boxborderw=10:"
        f"enable='between(t,{start},{end})'"
    )


def create_video():
    """Create the 60-second video using FFmpeg complex filter"""

    os.makedirs(TEMP_DIR, exist_ok=True)

    # Build complex filter graph
    # For each segment: trim, setpts to reset timestamps, then speed adjust
    filter_parts = []
    concat_inputs = []

    for i, (src_start, src_end, target_dur, name) in enumerate(SEGMENTS):
        src_dur = src_end - src_start
        speed = src_dur / target_dur  # >1 means speed up, <1 means slow down

        print(f"  Segment {i} ({name}): {src_start}s-{src_end}s ({src_dur}s) -> {target_dur}s (speed: {speed:.2f}x)")

        # Trim to segment, reset PTS, then adjust speed
        filter_parts.append(
            f"[0:v]trim=start={src_start}:end={src_end},setpts=PTS-STARTPTS,setpts={1/speed}*PTS[v{i}]"
        )
        concat_inputs.append(f"[v{i}]")

    # Concatenate all segments
    concat_filter = f"{''.join(concat_inputs)}concat=n={len(SEGMENTS)}:v=1:a=0[vconcat]"
    filter_parts.append(concat_filter)

    # Add text overlays
    overlay_filters = [build_drawtext(*o) for o in OVERLAYS]
    overlay_chain = ",".join(overlay_filters)
    filter_parts.append(f"[vconcat]{overlay_chain}[vout]")

    # Complete filter graph
    filter_complex = ";".join(filter_parts)

    cmd = [
        FFMPEG, "-y",
        "-i", SOURCE,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-r", "30",
        OUTPUT
    ]

    print(f"\n  Running FFmpeg with complex filter...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        # Verify duration
        probe_cmd = [
            "C:/ffmpeg/bin/ffprobe.exe",
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            OUTPUT
        ]
        duration = subprocess.run(probe_cmd, capture_output=True, text=True)
        print(f"\n  Output duration: {float(duration.stdout.strip()):.1f} seconds")
        return True
    else:
        print(f"\n  FFmpeg error:\n{result.stderr[-2000:]}")
        return False


def main():
    print("=" * 60)
    print("PlotDetect 60-Second Screencast Generator v2")
    print("=" * 60)
    print(f"\nSource: {SOURCE} (221 seconds)")
    print(f"Output: {OUTPUT}")
    print(f"\nSegment mapping:")

    total_target = sum(s[2] for s in SEGMENTS)
    print(f"  Target total: {total_target} seconds\n")

    success = create_video()

    if success:
        print(f"\nSUCCESS: {OUTPUT}")
    else:
        print(f"\nFAILED - check error above")
        sys.exit(1)


if __name__ == "__main__":
    main()
