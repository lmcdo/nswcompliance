#!/usr/bin/env python3
"""
65-Second PlotDetect Mastercut
Precise segment mapping following Compliance Priority: Portal > SEPP > LEP > DCP > AI

Based on detailed harvesting map with freeze frames and speed adjustments.
"""

import subprocess
import os

FFMPEG = "C:/ffmpeg/bin/ffmpeg.exe"
SOURCE = "C:/Users/lawre/Videos/Untitled video - Made with Clipchamp.mp4"
OUTPUT = "C:/Users/lawre/Videos/PlotDetect_65sec_mastercut.mp4"

# Segment mapping from harvesting map
# Format: (source_start, source_end, target_duration, speed_factor, name, freeze_at)
# freeze_at: seconds into this segment to add a 2s freeze frame (None = no freeze)
SEGMENTS = [
    # 0:00-0:05 Address typing fast forward + click button (source 0:00-0:12 -> 5s = 2.4x)
    (0, 12, 5, 2.4, "Portal", None),

    # 0:08-0:18 SEPP Multi-occ/TOD (source 0:25-0:55 = 30s -> 10s = 3x)
    (25, 55, 10, 3.0, "SEPP", None),

    # 0:18-0:28 LEP & CDC Calculator (source 1:10-1:45 = 35s -> 10s = 3.5x)
    # Freeze at 0:20 in output = 2s into this segment
    (70, 105, 10, 3.5, "LEP", 2),

    # 0:28-0:43 DCP Filtering & PDF (source 1:55-2:30 = 35s -> 15s = 2.33x)
    # Freeze at 0:35 in output = 7s into this segment
    (115, 150, 15, 2.33, "DCP", 7),

    # 0:43-0:58 AI Chat Overview (source 2:45-3:20 = 35s -> 15s = 2.33x)
    (165, 200, 15, 2.33, "AI", None),

    # 0:58-1:05 End Card (use last frames of video)
    (207, 212, 7, 0.71, "End", None),
]

# Text overlays with precise timing and styling
# Format: (text, start, end, position, fontsize, is_header)
# Adjusted timing: Portal now 0-5s (was 0-8s), shifts everything by -3s
OVERLAYS = [
    # 0:00-0:05 Site Foundation (address typing fast forward)
    ("185 Parramatta Rd", 1, 5, "bottom", 32, True),
    ("Zone E1 | 139m2 Lot", 2, 5, "bottom2", 24, False),

    # 0:05-0:15 Priority 1: SEPP (was 0:08-0:18)
    ("SEPP Controls - from Planning Portal", 5, 15, "bottom", 28, True),
    ("TOD, Multi-Occupancy, ADG, CDC calculations", 7, 12, "bottom2", 22, False),
    ("details when applicable to property address", 12, 15, "bottom2", 22, False),

    # 0:15-0:25 Priority 2: LEP (was 0:18-0:28)
    ("LEP Controls - Local Planning", 15, 25, "bottom", 28, True),
    ("Heritage: Parramatta Rd HCA", 17, 22, "bottom2", 22, False),
    ("FSR: 1.5:1 | Height: 14m", 22, 25, "bottom2", 22, False),

    # 0:25-0:40 Priority 3: DCP (was 0:28-0:43)
    ("DCP Provisions - Detailed Controls", 25, 40, "bottom", 28, True),
    ("Filter by Topic | Setbacks | Signage", 27, 34, "bottom2", 22, False),
    ("Linked PDF Citations", 34, 40, "bottom2", 22, False),

    # 0:40-0:55 Priority 4: AI Chat (was 0:43-0:58)
    ("AI Planning Assistant", 40, 55, "bottom", 28, True),
    ("Natural Language Query", 42, 49, "bottom2", 22, False),
    ("Sourced from Verified Data", 49, 55, "bottom2", 22, False),

    # 0:55-0:62 End Card (was 0:58-1:05)
    ("TRY YOUR ADDRESS", 55, 59, "center", 36, True),
    ("verify.plotdetect.au", 59, 62, "center", 40, True),
]


def escape_text(text):
    """Escape text for FFmpeg drawtext filter"""
    return text.replace(":", "\\:").replace("'", "\\'").replace("|", "\\|")


def build_drawtext(text, start, end, position, fontsize, is_header):
    """Build a single drawtext filter"""
    escaped = escape_text(text)

    # Position mapping - bottom2 is below bottom for subtitle effect
    if position == "center":
        x, y = "(w-text_w)/2", "(h-text_h)/2"
    elif position == "bottom":
        x, y = "(w-text_w)/2", "h-text_h-120"
    elif position == "bottom2":
        x, y = "(w-text_w)/2", "h-text_h-70"
    else:
        x, y = "(w-text_w)/2", "h-text_h-80"

    # Sans-serif font, black background, yellow text - best practices
    boxcolor = "black@0.85"
    fontcolor = "yellow"
    boxborder = 12 if is_header else 8

    return (
        f"drawtext=text='{escaped}':"
        f"fontfile='C\\:/Windows/Fonts/arial.ttf':"
        f"fontsize={fontsize}:"
        f"fontcolor={fontcolor}:"
        f"x={x}:y={y}:"
        f"box=1:boxcolor={boxcolor}:boxborderw={boxborder}:"
        f"enable='between(t,{start},{end})'"
    )


def create_mastercut():
    """Create the 65-second mastercut video"""

    print("Building FFmpeg complex filter for mastercut...")

    filter_parts = []
    concat_inputs = []
    stream_idx = 0

    for i, (src_start, src_end, target_dur, speed, name, freeze_at) in enumerate(SEGMENTS):
        src_dur = src_end - src_start
        actual_speed = src_dur / target_dur

        print(f"  Segment {i} ({name}): {src_start}s-{src_end}s -> {target_dur}s @ {actual_speed:.2f}x")

        if freeze_at is not None:
            # Split into before freeze, freeze frame, after freeze
            freeze_dur = 2  # 2 second freeze
            before_dur = freeze_at
            after_dur = target_dur - freeze_at - freeze_dur

            # Calculate source positions for split
            src_freeze_point = src_start + (freeze_at / target_dur) * src_dur

            # Before freeze
            filter_parts.append(
                f"[0:v]trim=start={src_start}:end={src_freeze_point},"
                f"setpts=PTS-STARTPTS,setpts={1/actual_speed}*PTS[v{stream_idx}a]"
            )

            # Freeze frame (single frame held for 2 seconds)
            filter_parts.append(
                f"[0:v]trim=start={src_freeze_point}:end={src_freeze_point + 0.1},"
                f"setpts=PTS-STARTPTS,loop=60:1:0,setpts=N/30/TB[v{stream_idx}b]"
            )

            # After freeze
            filter_parts.append(
                f"[0:v]trim=start={src_freeze_point}:end={src_end},"
                f"setpts=PTS-STARTPTS,setpts={1/actual_speed}*PTS[v{stream_idx}c]"
            )

            # Concat the three parts
            filter_parts.append(
                f"[v{stream_idx}a][v{stream_idx}b][v{stream_idx}c]concat=n=3:v=1:a=0[v{stream_idx}]"
            )
        else:
            # Simple trim and speed adjust
            filter_parts.append(
                f"[0:v]trim=start={src_start}:end={src_end},"
                f"setpts=PTS-STARTPTS,setpts={1/actual_speed}*PTS[v{stream_idx}]"
            )

        concat_inputs.append(f"[v{stream_idx}]")
        stream_idx += 1

    # Concatenate all segments
    num_segments = len(SEGMENTS)
    filter_parts.append(
        f"{''.join(concat_inputs)}concat=n={num_segments}:v=1:a=0[vconcat]"
    )

    # Add text overlays
    overlay_filters = [build_drawtext(*o) for o in OVERLAYS]
    overlay_chain = ",".join(overlay_filters)
    filter_parts.append(f"[vconcat]{overlay_chain}[vout]")

    # Build complete filter
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

    print(f"\n  Running FFmpeg...")
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
        print(f"\n  FFmpeg error:\n{result.stderr[-2500:]}")
        return False


def create_simple_mastercut():
    """Simplified version without freeze frames for testing"""

    print("\nCreating simplified mastercut (no freeze frames)...")

    filter_parts = []
    concat_inputs = []

    for i, (src_start, src_end, target_dur, speed, name, _) in enumerate(SEGMENTS):
        src_dur = src_end - src_start
        actual_speed = src_dur / target_dur

        filter_parts.append(
            f"[0:v]trim=start={src_start}:end={src_end},"
            f"setpts=PTS-STARTPTS,setpts={1/actual_speed}*PTS[v{i}]"
        )
        concat_inputs.append(f"[v{i}]")

    # Concatenate
    filter_parts.append(
        f"{''.join(concat_inputs)}concat=n={len(SEGMENTS)}:v=1:a=0[vconcat]"
    )

    # Add overlays
    overlay_filters = [build_drawtext(*o) for o in OVERLAYS]
    overlay_chain = ",".join(overlay_filters)
    filter_parts.append(f"[vconcat]{overlay_chain}[vout]")

    filter_complex = ";".join(filter_parts)

    simple_output = "C:/Users/lawre/Videos/PlotDetect_65sec_simple.mp4"

    cmd = [
        FFMPEG, "-y",
        "-i", SOURCE,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-r", "30",
        simple_output
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        probe_cmd = [
            "C:/ffmpeg/bin/ffprobe.exe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            simple_output
        ]
        duration = subprocess.run(probe_cmd, capture_output=True, text=True)
        print(f"  Simple version: {float(duration.stdout.strip()):.1f}s -> {simple_output}")
        return True
    else:
        print(f"  Error: {result.stderr[-1500:]}")
        return False


def main():
    print("=" * 65)
    print("PlotDetect 65-Second Mastercut Generator")
    print("Compliance Priority: Portal > SEPP > LEP > DCP > AI")
    print("=" * 65)
    print(f"\nSource: {SOURCE}")
    print(f"Output: {OUTPUT}")

    # Calculate total
    total = sum(s[2] for s in SEGMENTS)
    print(f"\nTarget duration: {total} seconds")
    print("\nSegment mapping:")

    # First create simple version (more reliable)
    create_simple_mastercut()

    # Then try with freeze frames
    print("\n" + "-" * 40)
    print("Creating version with freeze frames...")
    success = create_mastercut()

    if success:
        print(f"\nSUCCESS: {OUTPUT}")
    else:
        print(f"\nMastercut with freeze frames failed - use simple version")


if __name__ == "__main__":
    main()
