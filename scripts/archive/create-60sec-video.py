#!/usr/bin/env python3
"""
Create 60-Second PlotDetect Screencast

Maps segments from the 3:41 source video to a 60-second edit with text overlays.
Based on actual video content analysis.

Source video: C:/Users/lawre/Videos/Verifyfinal.mp4 (221 seconds)
Output: C:/Users/lawre/Videos/PlotDetect_60sec.mp4
"""

import subprocess
import os

FFMPEG = "C:/ffmpeg/bin/ffmpeg.exe"
SOURCE = "C:/Users/lawre/Videos/Verifyfinal.mp4"
OUTPUT = "C:/Users/lawre/Videos/PlotDetect_60sec.mp4"

# Segment mapping from source video to 60-second output
# Format: (source_start, source_end, output_duration, section_name)
SEGMENTS = [
    # Title - use first few seconds, slow down slightly
    (0, 3, 3, "Title"),

    # Property Search - address typing and autocomplete
    (2, 10, 5, "Property Search"),

    # NSW Planning Portal data (left column loads with property summary)
    (10, 18, 6, "NSW Portal"),

    # SEPP Tab - BASIX, Multi-occupancy, TOD, Parking (20-60s source)
    (18, 50, 12, "SEPP Tab"),

    # LEP Tab - Key Site, Heritage, FSR, PDF extracts (60-90s source)
    (60, 88, 10, "LEP Tab"),

    # DCP Tab - filtering, structure, provisions (90-150s source)
    (92, 130, 10, "DCP Tab"),

    # AI Chat/Quick Reference panel (190-221s source)
    (190, 215, 8, "AI Chat"),

    # End - use final frame with Quick Reference visible
    (218, 221, 6, "End Card"),
]

# Text overlays for the OUTPUT video (after segment assembly)
# Format: (text, start_time, end_time, position, fontsize)
TEXT_OVERLAYS = [
    # Opening
    ("Planning Assessment in 60 Seconds", 0, 3, "center", 56),

    # Property Search (3-8s)
    ("Enter any NSW address", 3, 6, "bottom", 40),
    ("185 Parramatta Rd, Annandale NSW 2038", 6, 8, "bottom", 36),

    # NSW Portal (8-14s)
    ("NSW Planning Portal data", 8, 11, "bottom", 40),
    ("Zone: E1 | Area: 168m2 | Heritage: Yes", 11, 14, "bottom", 32),

    # SEPP Tab (14-26s)
    ("SEPP Controls (State Level)", 14, 17, "bottom", 40),
    ("BASIX Water Target: 40%", 17, 19, "bottom", 32),
    ("TOD Provisions - Transit Oriented", 19, 22, "bottom", 32),
    ("Parking Requirements", 22, 26, "bottom", 32),

    # LEP Tab (26-36s)
    ("LEP Controls (Local)", 26, 29, "bottom", 40),
    ("Key Site | Heritage Conservation Area", 29, 32, "bottom", 32),
    ("Clause 5.10 with PDF page citation", 32, 36, "bottom", 32),

    # DCP Tab (36-46s)
    ("DCP Provisions (Detailed)", 36, 39, "bottom", 40),
    ("558 provisions applicable to this address", 39, 42, "bottom", 32),
    ("Filter by Topic | View by Page", 42, 46, "bottom", 32),

    # AI Chat (46-54s)
    ("Quick Reference", 46, 49, "bottom", 44),
    ("Ask planning questions in plain English", 49, 52, "bottom", 32),
    ("No hallucination - database lookups only", 52, 54, "bottom", 32),

    # End Card (54-60s)
    ("Complete Planning Assessment", 54, 56, "center", 44),
    ("SEPP - LEP - DCP - All in one view", 56, 58, "center", 36),
    ("verify.plotdetect.au", 58, 60, "center", 48),
]


def escape_text(text):
    """Escape text for FFmpeg drawtext filter"""
    return text.replace(":", "\\:").replace("'", "\\'").replace("|", "\\|")


def build_drawtext(text, start, end, position, fontsize):
    """Build a single drawtext filter"""
    escaped = escape_text(text)

    if position == "center":
        x, y = "(w-text_w)/2", "(h-text_h)/2"
    elif position == "top":
        x, y = "(w-text_w)/2", "60"
    else:  # bottom
        x, y = "(w-text_w)/2", "h-text_h-80"

    return (
        f"drawtext=text='{escaped}':"
        f"fontsize={fontsize}:"
        f"fontcolor=white:"
        f"x={x}:y={y}:"
        f"box=1:boxcolor=black@0.6:boxborderw=12:"
        f"enable='between(t,{start},{end})'"
    )


def create_segment_files():
    """Extract segments from source video into temp files"""
    temp_files = []

    for i, (src_start, src_end, out_dur, name) in enumerate(SEGMENTS):
        temp_file = f"C:/Users/lawre/Videos/temp_seg_{i:02d}.mp4"
        src_duration = src_end - src_start
        speed = src_duration / out_dur

        print(f"  Extracting segment {i}: {name} ({src_start}s-{src_end}s -> {out_dur}s)")

        # Extract and speed-adjust segment
        cmd = [
            FFMPEG, "-y",
            "-ss", str(src_start),
            "-i", SOURCE,
            "-t", str(src_duration),
            "-filter:v", f"setpts={1/speed}*PTS",
            "-an",  # No audio in source
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            temp_file
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"    Error: {result.stderr[-500:]}")
            return None

        temp_files.append(temp_file)

    return temp_files


def concatenate_segments(temp_files):
    """Concatenate temp segment files"""
    concat_file = "C:/Users/lawre/Videos/concat_list.txt"
    concat_output = "C:/Users/lawre/Videos/temp_concat.mp4"

    # Write concat list
    with open(concat_file, "w") as f:
        for tf in temp_files:
            f.write(f"file '{tf}'\n")

    print("  Concatenating segments...")

    cmd = [
        FFMPEG, "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        concat_output
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    Error: {result.stderr[-500:]}")
        return None

    return concat_output


def add_text_overlays(input_file):
    """Add text overlays to the concatenated video"""
    print("  Adding text overlays...")

    # Build filter chain
    filters = [build_drawtext(*overlay) for overlay in TEXT_OVERLAYS]
    filter_chain = ",".join(filters)

    cmd = [
        FFMPEG, "-y",
        "-i", input_file,
        "-vf", filter_chain,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        OUTPUT
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    Error: {result.stderr[-1000:]}")
        return False

    return True


def cleanup(temp_files, concat_file, concat_output):
    """Remove temporary files"""
    print("  Cleaning up temp files...")
    for f in temp_files + [concat_file, concat_output]:
        if f and os.path.exists(f):
            try:
                os.remove(f)
            except:
                pass


def create_simple_version():
    """
    Simpler approach: Just trim first 60s and add overlays
    Use this if segment extraction is too slow
    """
    print("\n=== Creating Simple 60-Second Version ===")
    print("  (First 60 seconds + text overlays)")

    # Build filter chain
    filters = [build_drawtext(*overlay) for overlay in TEXT_OVERLAYS]
    filter_chain = ",".join(filters)

    simple_output = r"C:\Users\lawre\Videos\PlotDetect_60sec_simple.mp4"

    cmd = [
        FFMPEG, "-y",
        "-i", SOURCE,
        "-t", "60",
        "-vf", filter_chain,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        simple_output
    ]

    print(f"  Running FFmpeg...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"\nSIMPLE VERSION CREATED: {simple_output}")
        print("  (Uses first 60 seconds of source video)")
        return True
    else:
        print(f"  Error: {result.stderr[-1000:]}")
        return False


def main():
    print("=" * 60)
    print("PlotDetect 60-Second Screencast Generator")
    print("=" * 60)
    print(f"\nSource: {SOURCE}")
    print(f"Output: {OUTPUT}")

    # First try simple version (faster, good for testing)
    create_simple_version()

    print("\n" + "=" * 60)
    print("Creating Segment-Based Version (with proper timing)")
    print("=" * 60)

    print("\nStep 1: Extracting segments from source video...")
    temp_files = create_segment_files()

    if not temp_files:
        print("ERROR: Failed to extract segments")
        return

    print("\nStep 2: Concatenating segments...")
    concat_output = concatenate_segments(temp_files)

    if not concat_output:
        print("ERROR: Failed to concatenate segments")
        cleanup(temp_files, None, None)
        return

    print("\nStep 3: Adding text overlays...")
    success = add_text_overlays(concat_output)

    if success:
        print(f"\nSUCCESS! Output: {OUTPUT}")
    else:
        print("\nERROR: Failed to add text overlays")

    # Cleanup
    cleanup(temp_files, "C:/Users/lawre/Videos/concat_list.txt", concat_output)


if __name__ == "__main__":
    main()
