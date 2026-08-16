#!/usr/bin/env python3
"""
Add text overlays to the 75-second PlotDetect screencast.
Assumes video is already edited (no segment cutting needed).
"""

import subprocess

FFMPEG = "C:/ffmpeg/bin/ffmpeg.exe"
SOURCE = "C:/Users/lawre/Videos/Untitled video - Made with Clipchamp.mp4"
OUTPUT = "C:/Users/lawre/Videos/PlotDetect_75sec_final.mp4"

# Text overlays - sans-serif, yellow on black, best practices sizing
# Format: (text, start, end, position, fontsize)
OVERLAYS = [
    # 0:00-0:08 Address input to button click
    ("Enter any Inner West address", 2, 8, "bottom", 28),

    # 0:08-0:12 Portal data loads
    ("Live data from NSW Planning Portal", 8, 12, "bottom", 28),

    # 0:12-0:28 SEPP panel
    ("SEPP Controls", 12, 16, "bottom", 30),
    ("TOD | ADG | CDC | Multi-Occupancy", 16, 22, "bottom", 26),
    ("Shown when applicable to this address", 22, 28, "bottom", 24),

    # 0:28-0:40 LEP Tab - Key Site, Heritage, PDFs
    ("LEP Local Controls", 28, 32, "bottom", 30),
    ("Key Site | Heritage Conservation Area", 32, 36, "bottom", 26),
    ("PDF citations with page extracts", 36, 40, "bottom", 24),

    # 0:40-0:55 DCP Tab - TOC, filters, layers
    ("DCP Provisions", 40, 44, "bottom", 30),
    ("Filter by topic | View by section", 44, 49, "bottom", 26),
    ("Layer filtering for site-specific controls", 49, 55, "bottom", 24),

    # 0:55-0:65 DCP PDF modal
    ("Every provision links to source PDF", 55, 65, "bottom", 26),

    # 0:65-0:73 AI Chat
    ("AI Planning Assistant", 65, 69, "bottom", 30),
    ("Preset questions | Verified answers only", 69, 73, "bottom", 24),

    # 0:73-0:75 End
    ("verify.plotdetect.au", 73, 75, "center", 36),
]


def escape_text(text):
    """Escape text for FFmpeg drawtext filter"""
    return text.replace(":", "\\:").replace("'", "\\'").replace("|", "\\|")


def build_drawtext(text, start, end, position, fontsize):
    """Build drawtext filter - sans-serif, yellow on black"""
    escaped = escape_text(text)

    if position == "center":
        x, y = "(w-text_w)/2", "(h-text_h)/2"
    else:  # bottom
        x, y = "(w-text_w)/2", "h-text_h-60"

    return (
        f"drawtext=text='{escaped}':"
        f"fontfile='C\\:/Windows/Fonts/arial.ttf':"
        f"fontsize={fontsize}:"
        f"fontcolor=yellow:"
        f"x={x}:y={y}:"
        f"box=1:boxcolor=black@0.85:boxborderw=10:"
        f"enable='between(t,{start},{end})'"
    )


def get_video_duration(path):
    """Get video duration in seconds"""
    cmd = [
        "C:/ffmpeg/bin/ffprobe.exe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return float(result.stdout.strip())


def add_overlays():
    """Add text overlays to the video"""

    # Check source duration
    duration = get_video_duration(SOURCE)
    print(f"Source video: {duration:.1f} seconds")

    # Adjust overlay timing if video is shorter/longer than 75s
    scale = duration / 75.0

    adjusted_overlays = []
    for text, start, end, pos, size in OVERLAYS:
        adj_start = start * scale
        adj_end = min(end * scale, duration - 0.5)
        if adj_start < duration:
            adjusted_overlays.append((text, adj_start, adj_end, pos, size))

    # Build filter chain
    filters = [build_drawtext(*o) for o in adjusted_overlays]
    filter_chain = ",".join(filters)

    cmd = [
        FFMPEG, "-y",
        "-i", SOURCE,
        "-vf", filter_chain,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-c:a", "copy",
        OUTPUT
    ]

    print(f"Adding {len(adjusted_overlays)} text overlays...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        out_duration = get_video_duration(OUTPUT)
        print(f"\nSUCCESS: {OUTPUT}")
        print(f"Duration: {out_duration:.1f}s")
        return True
    else:
        print(f"Error: {result.stderr[-1500:]}")
        return False


def main():
    print("=" * 60)
    print("PlotDetect 75-Second Screencast - Add Overlays")
    print("=" * 60)
    print(f"\nSource: {SOURCE}")
    print(f"Output: {OUTPUT}\n")

    add_overlays()


if __name__ == "__main__":
    main()
