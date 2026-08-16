#!/usr/bin/env python3
"""
Video Editor for PlotDetect 60-Second Screencast

Creates a 60-second video with text overlays from the source video.
Requires: FFmpeg installed at C:\\ffmpeg\\bin\\ffmpeg.exe

Usage:
1. First run with --preview to see what segments need to be identified
2. Update the SEGMENT_MAPPING with timestamps from source video
3. Run with --generate to create the final video
"""

import subprocess
import sys
import os
from dataclasses import dataclass
from typing import List, Optional

FFMPEG_PATH = r"C:\ffmpeg\bin\ffmpeg.exe"
FFPROBE_PATH = r"C:\ffmpeg\bin\ffprobe.exe"

# Source and output paths
SOURCE_VIDEO = r"C:\Users\lawre\Videos\Verifyfinal.mp4"
OUTPUT_VIDEO = r"C:\Users\lawre\Videos\PlotDetect_60sec.mp4"

@dataclass
class TextOverlay:
    """Text overlay specification"""
    text: str
    start_time: float  # seconds in OUTPUT video
    end_time: float    # seconds in OUTPUT video
    position: str = "center"  # center, top, bottom
    fontsize: int = 48
    fontcolor: str = "white"
    box: bool = True
    boxcolor: str = "black@0.6"


@dataclass
class Segment:
    """Video segment from source to include"""
    name: str
    source_start: float  # timestamp in SOURCE video (seconds)
    source_end: float    # timestamp in SOURCE video (seconds)
    target_duration: float  # how long it should be in OUTPUT (seconds)


# ============================================================================
# SCRIPT TIMING (OUTPUT VIDEO) - from SCREENCAST_SCRIPT_60_SEC_AI_CHAT.md
# ============================================================================
SCRIPT_SECTIONS = [
    ("Title", 0, 3, "Planning Assessment in 60 Seconds"),
    ("Property Search", 3, 8, "Enter any NSW address"),
    ("NSW Portal", 8, 14, "NSW Planning Portal data"),
    ("SEPP Tab", 14, 26, "SEPP Controls (State Level)"),
    ("LEP Tab", 26, 36, "LEP Controls (Local)"),
    ("DCP Tab", 36, 46, "DCP Provisions (Detailed)"),
    ("AI Chat", 46, 54, "AI Assistant"),
    ("End Card", 54, 60, "verify.plotdetect.au"),
]

# ============================================================================
# TEXT OVERLAYS - matches SCREENCAST_SCRIPT_60_SEC_AI_CHAT.md
# ============================================================================
TEXT_OVERLAYS = [
    # Title
    TextOverlay("Planning Assessment in 60 Seconds", 0, 3, "center", 64),

    # Property Search
    TextOverlay("Enter any NSW address", 3, 5, "bottom", 42),
    TextOverlay("[Address], [Suburb] NSW [Postcode]", 7, 8, "bottom", 36),

    # NSW Planning Portal
    TextOverlay("NSW Planning Portal data", 8, 10, "bottom", 42),
    TextOverlay("Zone | Lot Size | Frontage", 10, 12, "bottom", 36),
    TextOverlay("Constraints auto-detected", 12, 14, "bottom", 36),

    # SEPP Tab
    TextOverlay("SEPP Controls (State Level)", 14, 16, "bottom", 42),
    TextOverlay("Multi-Occupancy Eligibility", 16, 18, "bottom", 36),
    TextOverlay("Manor House | Dual Occ | Low-Rise", 18, 20, "bottom", 32),
    TextOverlay("TOD Provisions", 21, 23, "bottom", 36),
    TextOverlay("Parking Requirements", 24, 26, "bottom", 36),

    # LEP Tab
    TextOverlay("LEP Controls (Local)", 26, 28, "bottom", 42),
    TextOverlay("Height | FSR | Lot Size", 28, 30, "bottom", 36),
    TextOverlay("CDC Calculator", 31, 33, "bottom", 36),
    TextOverlay("Special Zones & Key Sites", 34, 36, "bottom", 36),

    # DCP Tab
    TextOverlay("DCP Provisions (Detailed)", 36, 38, "bottom", 42),
    TextOverlay("Filter by Topic", 38, 40, "bottom", 36),
    TextOverlay("View by TOC | Topic | Page", 41, 43, "bottom", 36),
    TextOverlay("Every provision → PDF page citation", 44, 46, "bottom", 32),

    # AI Chat
    TextOverlay("Got a question?", 46, 48, "bottom", 42),
    TextOverlay("AI Assistant", 48, 50, "bottom", 42),
    TextOverlay("Ask in plain English", 50, 52, "bottom", 36),
    TextOverlay("No hallucination - database lookups only", 52, 54, "bottom", 32),

    # End Card
    TextOverlay("Complete Planning Assessment", 54, 56, "center", 48),
    TextOverlay("SEPP → LEP → DCP", 56, 58, "center", 42),
    TextOverlay("verify.plotdetect.au", 58, 60, "center", 56),
]


# ============================================================================
# SEGMENT MAPPING - FILL IN THESE TIMESTAMPS FROM SOURCE VIDEO
# Watch the 3:41 video and note when each section starts/ends
# ============================================================================
SEGMENT_MAPPING: List[Segment] = [
    # Example - UPDATE THESE with actual timestamps from source video!
    # The source video is 221 seconds long

    # Segment("Title", source_start, source_end, target_duration)
    Segment("Title", 0, 3, 3),  # Use first 3 seconds or create title card
    Segment("Property Search", 3, 15, 5),  # Find where address search happens
    Segment("NSW Portal Load", 15, 25, 6),  # Left column data loading
    Segment("SEPP Tab", 25, 60, 12),  # SEPP section
    Segment("LEP Tab", 60, 100, 10),  # LEP section
    Segment("DCP Tab", 100, 140, 10),  # DCP filtering
    Segment("AI Chat", 140, 180, 8),  # AI assistant demo
    Segment("End Card", 180, 221, 6),  # End card or create one
]


def build_drawtext_filter(overlay: TextOverlay) -> str:
    """Build FFmpeg drawtext filter for a single overlay"""

    # Position mapping
    if overlay.position == "center":
        x = "(w-text_w)/2"
        y = "(h-text_h)/2"
    elif overlay.position == "top":
        x = "(w-text_w)/2"
        y = "50"
    else:  # bottom
        x = "(w-text_w)/2"
        y = "h-text_h-80"

    # Escape text for FFmpeg
    text = overlay.text.replace(":", "\\:").replace("'", "\\'")

    filter_str = (
        f"drawtext=text='{text}':"
        f"fontsize={overlay.fontsize}:"
        f"fontcolor={overlay.fontcolor}:"
        f"x={x}:y={y}:"
        f"enable='between(t,{overlay.start_time},{overlay.end_time})'"
    )

    if overlay.box:
        filter_str += f":box=1:boxcolor={overlay.boxcolor}:boxborderw=10"

    return filter_str


def build_full_filter_chain() -> str:
    """Build complete filter chain for all text overlays"""
    filters = [build_drawtext_filter(o) for o in TEXT_OVERLAYS]
    return ",".join(filters)


def preview_segments():
    """Show what segments need to be identified in source video"""
    print("=" * 70)
    print("SEGMENT IDENTIFICATION GUIDE")
    print("=" * 70)
    print(f"\nSource video: {SOURCE_VIDEO}")
    print(f"Duration: 221 seconds (3:41)")
    print(f"\nWatch the video and note timestamps for each section:\n")

    total = 0
    for name, start, end, title in SCRIPT_SECTIONS:
        duration = end - start
        total += duration
        print(f"  [{start:2d}s - {end:2d}s] ({duration:2d}s) {name}: {title}")

    print(f"\n  Total: {total}s")
    print("\n" + "=" * 70)
    print("CURRENT SEGMENT MAPPING (UPDATE IN SCRIPT):")
    print("=" * 70)

    for seg in SEGMENT_MAPPING:
        print(f"  {seg.name}: source {seg.source_start:.1f}s - {seg.source_end:.1f}s → {seg.target_duration}s output")

    print("\n" + "=" * 70)
    print("INSTRUCTIONS:")
    print("=" * 70)
    print("""
1. Open the source video in a video player (VLC, etc.)
2. Note the timestamp when each section occurs:
   - When does address search start?
   - When does the left column (NSW Portal data) load?
   - When do they click the SEPP tab?
   - When do they click the LEP tab?
   - When do they click the DCP tab?
   - When do they open the AI assistant?
   - Where is a good ending point?

3. Update SEGMENT_MAPPING in this script with those timestamps

4. Run with --generate to create the final video
""")


def generate_video():
    """Generate the 60-second video with text overlays"""

    print(f"Generating 60-second video...")
    print(f"Source: {SOURCE_VIDEO}")
    print(f"Output: {OUTPUT_VIDEO}")

    # For now, create a simple version that:
    # 1. Trims to 60 seconds from start
    # 2. Adds text overlays

    filter_chain = build_full_filter_chain()

    cmd = [
        FFMPEG_PATH,
        "-y",  # Overwrite output
        "-i", SOURCE_VIDEO,
        "-t", "60",  # Trim to 60 seconds
        "-vf", filter_chain,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "23",
        "-c:a", "copy",
        OUTPUT_VIDEO
    ]

    print(f"\nRunning FFmpeg...")
    print(f"Filter chain has {len(TEXT_OVERLAYS)} text overlays")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"\n✓ Video generated: {OUTPUT_VIDEO}")
        else:
            print(f"\n✗ FFmpeg error:")
            print(result.stderr[-2000:])  # Last 2000 chars of error
    except Exception as e:
        print(f"\n✗ Error: {e}")


def generate_with_segments():
    """Generate video by concatenating specific segments with speed adjustment"""

    print("Generating video from segments...")

    # Build complex filter for segment extraction and concatenation
    # This requires identifying segments in the source video first

    # For each segment, we'll:
    # 1. Extract it from source
    # 2. Adjust speed if needed to fit target duration
    # 3. Concatenate all segments
    # 4. Add text overlays

    # This is more complex - for now, just do simple trim + overlays
    generate_video()


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python video-edit-60sec.py --preview   # Show segment guide")
        print("  python video-edit-60sec.py --generate  # Create video")
        print("  python video-edit-60sec.py --filter    # Show filter chain only")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--preview":
        preview_segments()
    elif arg == "--generate":
        generate_video()
    elif arg == "--filter":
        print("FFmpeg filter chain for text overlays:\n")
        print(build_full_filter_chain())
    else:
        print(f"Unknown argument: {arg}")
        sys.exit(1)


if __name__ == "__main__":
    main()
