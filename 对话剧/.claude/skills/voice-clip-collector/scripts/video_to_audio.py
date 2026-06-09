#!/usr/bin/env python3
"""Extract audio from video files (mp3 + wav)."""

import subprocess
import sys
import os
import re
import shutil


def sanitize(s):
    """Make a string safe for filenames."""
    s = re.sub(r'[\\/:*?"<>|]', "", s)
    s = re.sub(r"\s+", "-", s)
    return s.strip("- ")


def get_duration(filepath):
    """Get media duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                filepath,
            ],
            capture_output=True, text=True, timeout=10
        )
        return float(result.stdout.strip())
    except Exception:
        return 0


def extract_audio(video_path, output_base, need_wav=False):
    """Extract audio as mp3 (and optionally wav)."""
    # Separate directory from filename for sanitization
    dir_part, file_part = os.path.split(output_base)
    base = os.path.join(dir_part, sanitize(file_part))
    mp3_path = f"{base}.mp3"
    wav_path = f"{base}.wav"

    # Extract as mp3
    print(f"Extracting MP3: {mp3_path}")
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn",                        # no video
        "-acodec", "libmp3lame",
        "-ab", "192k",                # 192kbps
        "-ar", "44100",
        "-ac", "2",
        mp3_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    duration = get_duration(mp3_path)
    print(f"  Duration: {duration:.1f}s")

    # Optionally convert to wav
    if need_wav:
        print(f"  Converting to WAV: {wav_path}")
        subprocess.run(
            ["ffmpeg", "-y", "-i", mp3_path, wav_path],
            check=True, capture_output=True, text=True
        )

    return mp3_path, wav_path if need_wav else None, duration


def main():
    if len(sys.argv) < 4:
        print(f"Usage: {sys.argv[0]} <video_file> <role_name> <work_name> [--wav]")
        sys.exit(1)

    video_path = sys.argv[1]
    role = sys.argv[2]
    work = sys.argv[3]
    need_wav = "--wav" in sys.argv

    if not os.path.isfile(video_path):
        print(f"File not found: {video_path}")
        sys.exit(1)

    # Check ffmpeg
    if not shutil.which("ffmpeg"):
        print("Error: ffmpeg not found. Install it first:")
        print("  macOS: brew install ffmpeg")
        print("  Ubuntu: apt install ffmpeg")
        sys.exit(1)

    # Build output name
    os.makedirs("clips", exist_ok=True)
    output_base = os.path.join("clips", f"{sanitize(work)}-{sanitize(role)}")

    # If file already exists, add sequence number
    seq = 1
    base = output_base
    while os.path.exists(f"{output_base}.mp3"):
        output_base = f"{base}-{seq}"
        seq += 1

    mp3, wav, dur = extract_audio(video_path, output_base, need_wav)

    print(f"\nDone!")
    print(f"  MP3:  {mp3} ({dur:.1f}s)")
    if wav:
        print(f"  WAV:  {wav}")


if __name__ == "__main__":
    main()
