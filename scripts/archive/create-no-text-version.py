#!/usr/bin/env python3
"""Create video without text overlays."""

import subprocess

FFMPEG = "C:/ffmpeg/bin/ffmpeg.exe"
SOURCE = "C:/Users/lawre/Videos/Untitled video - Made with Clipchamp.mp4"
OUTPUT = "C:/Users/lawre/Videos/PlotDetect_no_text.mp4"

SEGMENTS = [
    (0, 10, 5, "Address"),
    (10, 30, 12, "Portal"),
    (30, 55, 5, "SEPP"),
    (64, 79, 18, "LEP"),
    (85, 125, 36, "DCP"),
    (129, 175, 14, "AI"),
    (175, 185, 10, "End"),
]

OPENING_FREEZE = 3
SEPP_FREEZE = 2
SEPP_FREEZE_SOURCE = 30

filter_parts = []
concat_inputs = []
stream_idx = 0

# Opening freeze
frames = int(OPENING_FREEZE * 30)
filter_parts.append(
    f"[0:v]trim=start=0:end=0.1,setpts=PTS-STARTPTS,"
    f"loop={frames}:1:0,setpts=N/30/TB[vfreeze_open]"
)
concat_inputs.append("[vfreeze_open]")

for i, (src_start, src_end, target_dur, name) in enumerate(SEGMENTS):
    src_dur = src_end - src_start
    speed = src_dur / target_dur
    print(f"  {name}: {src_start}s-{src_end}s -> {target_dur}s @ {speed:.2f}x")

    filter_parts.append(
        f"[0:v]trim=start={src_start}:end={src_end},"
        f"setpts=PTS-STARTPTS,setpts={1/speed}*PTS[v{stream_idx}]"
    )
    concat_inputs.append(f"[v{stream_idx}]")
    stream_idx += 1

    # Insert SEPP freeze after Portal
    if i == 1:
        sepp_frames = int(SEPP_FREEZE * 30)
        filter_parts.append(
            f"[0:v]trim=start={SEPP_FREEZE_SOURCE}:end={SEPP_FREEZE_SOURCE + 0.1},"
            f"setpts=PTS-STARTPTS,loop={sepp_frames}:1:0,setpts=N/30/TB[vfreeze_sepp]"
        )
        concat_inputs.append("[vfreeze_sepp]")

n = len(concat_inputs)
filter_parts.append(f"{''.join(concat_inputs)}concat=n={n}:v=1:a=0[vout]")
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

print("Creating video without text overlays...")
result = subprocess.run(cmd, capture_output=True, text=True)

if result.returncode == 0:
    probe = subprocess.run([
        "C:/ffmpeg/bin/ffprobe.exe", "-v", "quiet",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", OUTPUT
    ], capture_output=True, text=True)
    print(f"\nSUCCESS: {OUTPUT}")
    print(f"Duration: {float(probe.stdout.strip()):.1f}s")
else:
    print(f"Error: {result.stderr[-1000:]}")
