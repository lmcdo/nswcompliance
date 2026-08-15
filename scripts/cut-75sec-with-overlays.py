#!/usr/bin/env python3
"""
PlotDetect Promo Video - Pain Point Driven Script
Frame-accurate timestamps with user-focused overlays.
"""

import subprocess

FFMPEG = "C:/ffmpeg/bin/ffmpeg.exe"
SOURCE = "C:/Users/lawre/Videos/Untitled video - Made with Clipchamp.mp4"
DATACARD = "C:/Users/lawre/Videos/datacard_segment.mp4"  # Pre-extracted data card
OUTPUT = "C:/Users/lawre/Videos/PlotDetect_promo.mp4"

# SOURCE VIDEO TIMESTAMP MAP (from frame analysis):
# Frame 1-10: Address typing
# Frame 15: SEPP tab at top with tabs visible
# Frame 52: LEP tab at top with tabs visible
# Frame 90: DCP tab at top, content loaded
# Frame 185-212: Quick Reference (AI)

# Video segments from SOURCE (212s)
# Format: (start, end, speed_factor, name)
# speed_factor: 1.0 = normal, 2.0 = 2x faster
SEGMENTS = [
    # Address entry - speed up typing
    (0, 12, 2.0, "Address"),           # 12s -> 6s

    # Portal loads, SEPP tab appears
    (12, 15, 1.0, "Portal"),           # 3s -> 3s

    # FREEZE: 1. SEPP at frame 15

    # SEPP content scrolling
    (15, 52, 3.0, "SEPP"),             # 37s -> ~12s

    # FREEZE: 2. LEP at frame 52

    # LEP content
    (52, 85, 3.0, "LEP"),              # 33s -> 11s

    # FREEZE: 3. DCP at frame 90

    # DCP content (skip loading 85-90)
    (90, 140, 2.5, "DCP"),             # 50s -> 20s

    # Quick Reference / AI
    (185, 210, 2.0, "AI"),             # 25s -> 12.5s

    # End card
    (210, 212, 0.5, "End"),            # 2s -> 4s
]

# Freeze frame settings
FREEZE_DURATION = 2  # seconds

# Freeze points: (source_timestamp, label_text)
FREEZE_POINTS = [
    (15, "1. SEPP: State Provisions"),
    (52, "2. LEP: Local Provisions"),
    (90, "3. DCP: Specific Provisions"),
]

# Text overlays - pain point driven
# Format: (text, start_output_time, end_output_time, position, fontsize)
# Output timeline: Address 0-6, Portal 6-9, Freeze 9-11, SEPP 11-23, Freeze 23-25,
#                  LEP 25-36, Freeze 36-38, DCP 38-58, AI 58-70.5, End 70.5-74.5
OVERLAYS = [
    # Address section (0-6s)
    ("2-4 hours cross-referencing? One address. Done.", 1, 6, "bottom", 28),

    # Portal section (6-9s)
    ("Live from NSW Planning Portal", 6, 9, "bottom", 26),

    # SEPP section (11-21s after freeze)
    ("TOD | ADG | CDC Calculations | Multi-Occupancy", 11, 17, "bottom", 24),
    ("Shown when applicable to your site", 17, 21, "bottom", 26),

    # LEP section (25-36s after freeze)
    ("Zone | FSR | Height | Heritage", 25, 31, "bottom", 28),
    ("No more scrolling 200-page PDFs", 31, 36, "bottom", 26),

    # DCP section (38-58s after freeze)
    ("Only provisions for YOUR site", 38, 46, "bottom", 28),
    ("Filter by Topic and Layer", 46, 56, "bottom_high", 26),
    ("Every control links to source PDF + page", 46, 56, "bottom", 26),

    # AI section (58-68s, ends before endcard)
    ("Ask anything. Get verified answers.", 58, 63, "bottom", 28),
    ("Citations, not hallucinations", 63, 68, "bottom", 26),

    # End card is now a separate black screen segment
]


def escape_text(text):
    return text.replace(":", "\\:").replace("'", "\\'").replace("|", "\\|")


def build_drawtext(text, start, end, position, fontsize, color="yellow"):
    """Build drawtext filter with fade in/out."""
    escaped = escape_text(text)

    # Position mapping
    if position == "center":
        x, y = "(w-text_w)/2", "(h-text_h)/2"
    elif position == "left":
        x, y = "40", "h-text_h-80"
    elif position == "left_top":
        # Big numbered labels - positioned upper left
        x, y = "40", "120"
    elif position == "bottom":
        x, y = "(w-text_w)/2", "h-text_h-60"
    elif position == "bottom_high":
        x, y = "(w-text_w)/2", "h-text_h-120"
    else:
        x, y = "(w-text_w)/2", "h-text_h-60"

    # Fade in/out (0.5s each)
    fade_in = 0.5
    fade_out = 0.5
    alpha_expr = (
        f"if(lt(t,{start + fade_in}),"
        f"(t-{start})/{fade_in},"
        f"if(gt(t,{end - fade_out}),"
        f"({end}-t)/{fade_out},"
        f"1))"
    )

    return (
        f"drawtext=text='{escaped}':"
        f"fontfile='C\\:/Windows/Fonts/arial.ttf':"
        f"fontsize={fontsize}:"
        f"fontcolor={color}:"
        f"alpha='{alpha_expr}':"
        f"x={x}:y={y}:"
        f"box=1:boxcolor=black@0.85:boxborderw=12:"
        f"enable='between(t,{start},{end})'"
    )


def build_freeze_label(text, duration, position, fontsize, color):
    """Build drawtext for freeze frame label (always visible during freeze)."""
    escaped = escape_text(text)

    if position == "left_top":
        x, y = "40", "120"
    else:
        x, y = "(w-text_w)/2", "(h-text_h)/2"

    return (
        f"drawtext=text='{escaped}':"
        f"fontfile='C\\:/Windows/Fonts/arial.ttf':"
        f"fontsize={fontsize}:"
        f"fontcolor={color}:"
        f"x={x}:y={y}:"
        f"box=1:boxcolor=black@0.85:boxborderw=15"
    )


def create_video():
    """Build video from SOURCE with freeze frames and text overlays."""
    print("Building from SOURCE with frame-accurate timestamps...\n")

    filter_parts = []
    concat_inputs = []
    idx = 0

    # Build explicit sequence with freezes between segments
    # Jerky camera at source ~21-28s removed
    sequence = [
        # (type, data)
        ("segment", (0, 12, 2.0, "Address")),
        ("segment", (12, 15, 1.0, "Portal")),
        ("freeze", (15, "1. SEPP: State Provisions")),
        ("segment", (15, 21, 3.0, "SEPP-1")),      # Before jerky
        ("segment", (28, 52, 3.0, "SEPP-2")),      # After jerky (skip 21-28)
        ("freeze", (52, "2. LEP: Local Provisions")),
        ("segment", (52, 85, 3.0, "LEP")),
        ("freeze", (90, "3. DCP: Specific Provisions")),
        ("segment", (90, 140, 2.5, "DCP")),
        ("segment", (185, 210, 2.0, "AI")),
        ("datacard", 7),  # 7 second data points card (already has verify URL at bottom)
    ]

    for item_type, data in sequence:
        if item_type == "segment":
            src_start, src_end, speed, name = data
            src_dur = src_end - src_start
            out_dur = src_dur / speed
            print(f"  {name}: {src_start}-{src_end}s @ {speed}x -> {out_dur:.1f}s")

            filter_parts.append(
                f"[0:v]trim=start={src_start}:end={src_end},"
                f"setpts=PTS-STARTPTS,setpts={1/speed}*PTS[v{idx}]"
            )
            concat_inputs.append(f"[v{idx}]")
            idx += 1

        elif item_type == "freeze":
            freeze_ts, label = data
            print(f"  FREEZE: {label} @ {freeze_ts}s")
            frames = int(FREEZE_DURATION * 30)
            label_filter = build_freeze_label(label, FREEZE_DURATION, "left_top", 48, "yellow")
            filter_parts.append(
                f"[0:v]trim=start={freeze_ts}:end={freeze_ts + 0.1},"
                f"setpts=PTS-STARTPTS,loop={frames}:1:0,setpts=N/30/TB,"
                f"{label_filter}[vf{idx}]"
            )
            concat_inputs.append(f"[vf{idx}]")
            idx += 1

        elif item_type == "datacard":
            duration = data
            print(f"  DATACARD: Data Points card ({duration}s) - scaled 1.06x")
            # Use pre-extracted datacard segment, scale up 1.06x
            # Crop from top-left (x=0,y=0) to preserve header and left column
            # Crops 77px from right and 43px from bottom (preserves URL)
            filter_parts.append(
                f"[1:v]trim=start=0:end={duration},setpts=PTS-STARTPTS,"
                f"scale=1357:763,crop=1280:720:0:0,setsar=1:1[vdc{idx}]"
            )
            concat_inputs.append(f"[vdc{idx}]")
            idx += 1

        elif item_type == "endcard":
            duration, text = data
            print(f"  ENDCARD: {text} ({duration}s)")
            escaped = escape_text(text)
            filter_parts.append(
                f"color=c=black:s=1280x720:d={duration}:r=30,"
                f"drawtext=text='{escaped}':"
                f"fontfile='C\\:/Windows/Fonts/arial.ttf':"
                f"fontsize=48:fontcolor=white:"
                f"x=(w-text_w)/2:y=(h-text_h)/2[ve{idx}]"
            )
            concat_inputs.append(f"[ve{idx}]")
            idx += 1

    # Concatenate all segments
    n = len(concat_inputs)
    filter_parts.append(f"{''.join(concat_inputs)}concat=n={n}:v=1:a=0[vconcat]")

    # Add text overlays
    overlay_filters = [build_drawtext(text, start, end, pos, size) for text, start, end, pos, size in OVERLAYS]
    overlay_chain = ",".join(overlay_filters)
    filter_parts.append(f"[vconcat]{overlay_chain}[vout]")

    filter_complex = ";".join(filter_parts)

    # Calculate duration
    seg_time = sum((d[1] - d[0]) / d[2] for t, d in sequence if t == "segment")
    freeze_time = sum(FREEZE_DURATION for t, _ in sequence if t == "freeze")
    print(f"\n  Expected: ~{seg_time + freeze_time:.0f}s ({seg_time:.0f}s + {freeze_time}s freezes)")
    print(f"  Overlays: {len(OVERLAYS)} text elements")

    cmd = [
        FFMPEG, "-y",
        "-i", SOURCE,
        "-i", DATACARD,  # Second input for data card
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "20",
        "-r", "30",
        OUTPUT
    ]

    print("\n  Running FFmpeg...")
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode == 0:
        probe = subprocess.run([
            "C:/ffmpeg/bin/ffprobe.exe", "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", OUTPUT
        ], capture_output=True, text=True)
        print(f"\n  Output: {float(probe.stdout.strip()):.1f}s")
        return True
    else:
        print(f"\n  Error: {result.stderr[-1500:]}")
        return False


def main():
    print("=" * 60)
    print("PlotDetect Promo - Pain Point Driven Script")
    print("=" * 60)
    print(f"\nSource: {SOURCE} (212s)")
    print(f"Output: {OUTPUT}\n")

    if create_video():
        print(f"\nSUCCESS: {OUTPUT}")
    else:
        print("\nFAILED")


if __name__ == "__main__":
    main()
