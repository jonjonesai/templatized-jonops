#!/usr/bin/env python3
"""
Taiwan Merch Video Renderer (FFmpeg + Pillow)
v2: Bilingual subtitles (EN + Traditional Chinese), brand fonts

Usage: python3 render-ffmpeg.py --config lantern-v2.json
"""

import json, os, subprocess, sys, tempfile, shutil
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Binary paths (env-configurable) ---
# IMPORTANT: Remotion ships a stripped-down ffmpeg (audio-only: no fade, zoompan,
# overlay, crop, scale-video filters). We need a full build for video rendering.
# Priority: FFMPEG_PATH env > /home/agent/local-libs/ffmpeg (full static build)
# > Remotion's bundled ffmpeg (audio-only — will fail on video filters).
def _resolve_bin(env_var, name):
    if os.environ.get(env_var):
        return os.environ[env_var]
    local = f"/home/agent/local-libs/{name}"
    if os.path.exists(local):
        return local
    remotion = os.path.join(
        SCRIPT_DIR, "node_modules", "@remotion", "compositor-linux-x64-gnu", name
    )
    return remotion

FFMPEG = _resolve_bin("FFMPEG_PATH", "ffmpeg")
FFPROBE = _resolve_bin("FFPROBE_PATH", "ffprobe")

# --- Directory paths (env-configurable, CLI-overridable in main) ---
PUBLIC = os.environ.get("REMOTION_PUBLIC_DIR") or os.path.join(SCRIPT_DIR, "public")
OUT_DIR = os.environ.get("REMOTION_OUT_DIR") or os.path.join(SCRIPT_DIR, "out")
FONTS_DIR = os.environ.get("FONTS_DIR") or "/home/agent/local-libs/fonts"

# Brand colors
NAVY = (34, 44, 136)
DARK_BLUE = (33, 83, 135)
RED = (255, 24, 29)
ORANGE = (247, 106, 12)
WARM = (254, 243, 231)
WHITE = (255, 255, 255)

FORMATS = {
    "ReelShort": (1080, 1920),
    "YouTube": (1920, 1080),
    "SquarePost": (1080, 1080),
}


def get_duration(path):
    r = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", path],
                       capture_output=True, text=True)
    return float(r.stdout.strip())


def run_ff(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"\n  FFMPEG ERROR:\n{r.stderr[-800:]}", file=sys.stderr)
        raise RuntimeError("ffmpeg failed")


# --- Font loading ---

def font_heading(size):
    """Righteous font for headings."""
    p = os.path.join(FONTS_DIR, "Righteous.ttf")
    if os.path.exists(p):
        return ImageFont.truetype(p, size)
    return _fallback_font(size)

def font_en(size):
    """Inter font for English body text."""
    p = os.path.join(FONTS_DIR, "Inter.ttf")
    if os.path.exists(p):
        return ImageFont.truetype(p, size)
    return _fallback_font(size)

def font_zh(size):
    """Noto Sans TC for Traditional Chinese."""
    p = os.path.join(FONTS_DIR, "NotoSansTC.ttf")
    if os.path.exists(p):
        return ImageFont.truetype(p, size)
    return _fallback_font(size)

def _fallback_font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


# --- Gradient ---

def make_gradient(w, h, color_top, color_bot):
    img = Image.new("RGB", (w, h))
    for y in range(h):
        ratio = y / h
        r = int(color_top[0] + (color_bot[0] - color_top[0]) * ratio)
        g = int(color_top[1] + (color_bot[1] - color_top[1]) * ratio)
        b = int(color_top[2] + (color_bot[2] - color_top[2]) * ratio)
        for x in range(w):
            img.putpixel((x, y), (r, g, b))
    return img


# --- Title card (bilingual) ---

def create_title_card(w, h, title, title_en, subtitle, path):
    img = make_gradient(w, h, NAVY, DARK_BLUE)
    draw = ImageDraw.Draw(img)

    is_vert = h > w
    # Chinese title (large) — slightly smaller in portrait to leave room for wrapping
    zh_size = int(h * 0.065) if not is_vert else int(h * 0.038)
    f_zh = font_zh(zh_size)
    # English title (smaller)
    en_size = int(zh_size * 0.55)
    f_en = font_heading(en_size)
    # Subtitle
    sub_size = int(zh_size * 0.35)
    f_sub = font_en(sub_size)

    # Max text width: 80% of canvas (leaves comfortable margins)
    max_text_w = int(w * 0.80)
    line_gap = 8

    # Wrap all text blocks for the available width
    zh_lines = _wrap_text(draw, title, f_zh, max_text_w)
    en_text = title_en or ""
    en_lines = _wrap_text(draw, en_text, f_en, max_text_w) if en_text else []

    sub_lines = []
    f_sub_zh = font_zh(sub_size)
    if subtitle:
        sub_lines = _wrap_text(draw, subtitle, f_sub_zh, max_text_w)

    # Measure total block height
    zh_block_h = len(zh_lines) * (zh_size + line_gap)
    en_block_h = len(en_lines) * (en_size + line_gap)
    sub_block_h = len(sub_lines) * (sub_size + line_gap)

    spacing_zh_en = 24
    spacing_en_sub = 36
    total_height = zh_block_h
    if en_lines:
        total_height += spacing_zh_en + en_block_h
    if sub_lines:
        total_height += spacing_en_sub + sub_block_h

    y = (h - total_height) // 2

    # Draw Chinese title (wrapped, centered per line, with shadow)
    for line in zh_lines:
        bbox = draw.textbbox((0, 0), line, font=f_zh)
        lw = bbox[2] - bbox[0]
        x = (w - lw) // 2
        draw.text((x + 2, y + 2), line, fill=(0, 0, 0, 80), font=f_zh)
        draw.text((x, y), line, fill=WHITE, font=f_zh)
        y += zh_size + line_gap

    # Draw English title (wrapped, centered per line)
    if en_lines:
        y += spacing_zh_en - line_gap
        for line in en_lines:
            bbox = draw.textbbox((0, 0), line, font=f_en)
            lw = bbox[2] - bbox[0]
            draw.text(((w - lw) // 2, y), line, fill=WARM, font=f_en)
            y += en_size + line_gap

    # Draw subtitle (wrapped, centered per line)
    if sub_lines:
        y += spacing_en_sub - line_gap
        for line in sub_lines:
            bbox = draw.textbbox((0, 0), line, font=f_sub_zh)
            lw = bbox[2] - bbox[0]
            draw.text(((w - lw) // 2, y), line, fill=(200, 200, 220), font=f_sub_zh)
            y += sub_size + line_gap

    img.save(path)


# --- Outro card ---

def create_outro_card(w, h, path, logo_path=None):
    img = make_gradient(w, h, DARK_BLUE, NAVY)
    draw = ImageDraw.Draw(img)

    is_vert = h > w
    main_size = int(h * 0.05) if not is_vert else int(h * 0.035)
    sub_size = int(main_size * 0.5)
    btn_size = int(main_size * 0.5)

    f_main = font_heading(main_size)
    f_sub = font_en(sub_size)
    f_btn = font_heading(btn_size)

    # Logo (if provided)
    y = int(h * 0.2)
    if logo_path and os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        # Scale logo to fit nicely (max 40% of width)
        max_logo_w = int(w * 0.4)
        if logo.width > max_logo_w:
            ratio = max_logo_w / logo.width
            logo = logo.resize((max_logo_w, int(logo.height * ratio)), Image.LANCZOS)
        logo_x = (w - logo.width) // 2
        img.paste(logo, (logo_x, y), logo)
        y += logo.height + 30

    # "Visit us today!"
    visit_text = "Visit us today!"
    bbox = draw.textbbox((0, 0), visit_text, font=f_main)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) // 2, y), visit_text, fill=WARM, font=f_main)
    y += main_size + 15

    # Domain
    domain = "taiwanmerch.co"
    bbox = draw.textbbox((0, 0), domain, font=f_main)
    tw = bbox[2] - bbox[0]
    draw.text(((w - tw) // 2, y), domain, fill=WHITE, font=f_main)
    y += main_size + 30

    # CTA button
    btn_text = "  Shop Now  "
    bbox = draw.textbbox((0, 0), btn_text, font=f_btn)
    btw = bbox[2] - bbox[0]
    bth = bbox[3] - bbox[1]
    pad = 15
    bx = (w - btw) // 2 - pad
    draw.rounded_rectangle([bx, y - pad, bx + btw + pad * 2, y + bth + pad], radius=8, fill=RED)
    draw.text(((w - btw) // 2, y), btn_text, fill=WHITE, font=f_btn)

    img.save(path)


# --- Bilingual caption overlay ---

def create_caption_overlay(w, h, caption_en, caption_zh, path):
    """Create a transparent PNG with bilingual caption at the bottom."""
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    is_vert = h > w
    en_size = int(h * 0.032) if not is_vert else int(h * 0.022)
    zh_size = int(en_size * 1.1)

    f_en_cap = font_en(en_size)
    f_zh_cap = font_zh(zh_size)

    # Measure both lines
    en_lines = _wrap_text(draw, caption_en, f_en_cap, int(w * 0.85))
    zh_lines = _wrap_text(draw, caption_zh, f_zh_cap, int(w * 0.85)) if caption_zh else []

    en_total_h = len(en_lines) * (en_size + 6)
    zh_total_h = len(zh_lines) * (zh_size + 6)
    gap = 8
    total_h = en_total_h + (gap + zh_total_h if zh_lines else 0)

    # Position at bottom
    pad_x = int(w * 0.06)
    pad_y = 18
    y_bar_bottom = int(h * 0.95) if not is_vert else int(h * 0.88)
    y_bar_top = y_bar_bottom - total_h - pad_y * 2

    # Semi-transparent background bar
    draw.rounded_rectangle(
        [pad_x, y_bar_top, w - pad_x, y_bar_bottom],
        radius=14, fill=(0, 0, 0, 180)
    )

    # Draw English text
    y = y_bar_top + pad_y
    for line in en_lines:
        bbox = draw.textbbox((0, 0), line, font=f_en_cap)
        tw = bbox[2] - bbox[0]
        draw.text(((w - tw) // 2, y), line, fill=WHITE, font=f_en_cap)
        y += en_size + 6

    # Draw Chinese text
    if zh_lines:
        y += gap
        for line in zh_lines:
            bbox = draw.textbbox((0, 0), line, font=f_zh_cap)
            tw = bbox[2] - bbox[0]
            draw.text(((w - tw) // 2, y), line, fill=(220, 220, 240), font=f_zh_cap)
            y += zh_size + 6

    img.save(path)


def _wrap_text(draw, text, font, max_width):
    words = text.split()
    if not words:
        return [text]
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [text]


# --- Video/image conversion ---

def image_to_video(png_path, duration, w, h, output_path, fade=True):
    vf = f"scale={w}:{h}"
    if fade:
        vf += f",fade=t=in:st=0:d=0.5,fade=t=out:st={duration-0.5}:d=0.5"
    run_ff([
        FFMPEG, "-y", "-loop", "1", "-i", png_path,
        "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(duration), "-vf", vf,
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", output_path
    ])


def process_video_slide(slide, w, h, caption_png, output_path):
    file_path = os.path.join(PUBLIC, slide["file"])
    dur = slide.get("durationSec", 4)

    # Scale to fill target (handles any aspect ratio), then crop to exact size
    scale_crop = (
        f"fps=30,scale={w}:{h}:force_original_aspect_ratio=increase,"
        f"crop={w}:{h},"
        f"fade=t=in:st=0:d=0.3,fade=t=out:st={dur-0.3}:d=0.3"
    )

    if caption_png and (slide.get("caption") or slide.get("caption_zh")):
        tmp_scaled = output_path + ".tmp.mp4"
        run_ff([
            FFMPEG, "-y", "-i", file_path,
            "-t", str(dur),
            "-vf", scale_crop,
            "-an", "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            tmp_scaled
        ])
        run_ff([
            FFMPEG, "-y", "-i", tmp_scaled, "-i", caption_png,
            "-filter_complex", "[0:v][1:v]overlay=0:0[out]",
            "-map", "[out]", "-an",
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            output_path
        ])
        os.remove(tmp_scaled)
    else:
        run_ff([
            FFMPEG, "-y", "-i", file_path,
            "-t", str(dur),
            "-vf", scale_crop,
            "-an", "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            output_path
        ])


def process_image_slide(slide, w, h, caption_png, output_path):
    file_path = os.path.join(PUBLIC, slide["file"])
    dur = slide.get("durationSec", 4)
    zoom = slide.get("zoom", "in")
    frames = int(dur * 30)

    if zoom == "out":
        zp = f"zoompan=z='1.15-0.15*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps=30"
    elif zoom == "none":
        zp = f"zoompan=z=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps=30"
    else:
        zp = f"zoompan=z='1+0.15*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={w}x{h}:fps=30"

    if caption_png and (slide.get("caption") or slide.get("caption_zh")):
        tmp_zoom = output_path + ".tmp.mp4"
        run_ff([
            FFMPEG, "-y", "-loop", "1", "-i", file_path,
            "-t", str(dur),
            "-vf", f"scale=2000:-1,{zp},fade=t=in:st=0:d=0.3,fade=t=out:st={dur-0.3}:d=0.3",
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            tmp_zoom
        ])
        run_ff([
            FFMPEG, "-y", "-i", tmp_zoom, "-i", caption_png,
            "-filter_complex", "[0:v][1:v]overlay=0:0[out]",
            "-map", "[out]",
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            output_path
        ])
        os.remove(tmp_zoom)
    else:
        run_ff([
            FFMPEG, "-y", "-loop", "1", "-i", file_path,
            "-t", str(dur),
            "-vf", f"scale=2000:-1,{zp},fade=t=in:st=0:d=0.3,fade=t=out:st={dur-0.3}:d=0.3",
            "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
            output_path
        ])


def concat_clips_video_only(clips, output_path):
    """Concat video clips into a single video-only file."""
    concat_file = os.path.join(tempfile.gettempdir(), "concat.txt")
    with open(concat_file, "w") as f:
        for p in clips:
            f.write(f"file '{p}'\n")
    run_ff([
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c:v", "copy", "-an", output_path
    ])
    os.remove(concat_file)


def mix_audio(video_path, output_path, bgm_path, bgm_vol,
              narration_path=None, narr_delay=3.0,
              voice_tracks=None):
    """
    Mix audio tracks onto a video-only file.

    voice_tracks: list of {"audio_path": str, "start_time": float} for
                  original audio from clips (e.g., Jon's voice)
    """
    vid_dur = get_duration(video_path)
    fade_start = max(0, vid_dur - 2)

    inputs = ["-i", video_path]
    input_idx = 1  # 0 = video

    # BGM
    bgm_full = os.path.join(PUBLIC, bgm_path)
    inputs += ["-stream_loop", "-1", "-i", bgm_full]
    bgm_idx = input_idx
    input_idx += 1

    # Narration
    narr_idx = None
    if narration_path:
        narr_full = os.path.join(PUBLIC, narration_path)
        inputs += ["-i", narr_full]
        narr_idx = input_idx
        input_idx += 1

    # Voice tracks (Jon's original audio)
    vt_indices = []
    if voice_tracks:
        for vt in voice_tracks:
            inputs += ["-i", vt["audio_path"]]
            vt_indices.append((input_idx, vt["start_time"], vt.get("duration", 30)))
            input_idx += 1

    # Build filter complex
    filters = []
    amix_inputs = []
    amix_count = 1  # at least bgm

    # BGM: duck volume during voice tracks
    if vt_indices:
        # Build volume expression that ducks during voice sections
        vol_parts = []
        for _, start, dur in vt_indices:
            end = start + dur
            vol_parts.append(f"between(t,{start:.1f},{end:.1f})")
        duck_expr = "+".join(vol_parts)
        # When any voice is active: duck to 50% of normal vol. Otherwise: full vol
        filters.append(
            f"[{bgm_idx}:a]volume='{bgm_vol}*if({duck_expr},0.4,1.0)':eval=frame,"
            f"afade=t=in:st=0:d=1,afade=t=out:st={fade_start}:d=2[bgm]"
        )
    else:
        filters.append(
            f"[{bgm_idx}:a]volume={bgm_vol},"
            f"afade=t=in:st=0:d=1,afade=t=out:st={fade_start}:d=2[bgm]"
        )
    amix_inputs.append("[bgm]")

    # Narration
    if narr_idx is not None:
        delay_ms = int(narr_delay * 1000)
        filters.append(
            f"[{narr_idx}:a]adelay={delay_ms}|{delay_ms},volume=1.2[narr]"
        )
        amix_inputs.append("[narr]")
        amix_count += 1

    # Voice tracks
    for i, (idx, start, dur) in enumerate(vt_indices):
        delay_ms = int(start * 1000)
        filters.append(
            f"[{idx}:a]adelay={delay_ms}|{delay_ms},volume=1.0[vt{i}]"
        )
        amix_inputs.append(f"[vt{i}]")
        amix_count += 1

    # Mix all audio
    amix_in = "".join(amix_inputs)
    filters.append(
        f"{amix_in}amix=inputs={amix_count}:duration=first:dropout_transition=2[aout]"
    )

    filter_str = ";".join(filters)

    run_ff([
        FFMPEG, "-y",
        *inputs,
        "-filter_complex", filter_str,
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
        "-t", str(vid_dur),
        output_path
    ])


def main():
    global PUBLIC, OUT_DIR
    config_path = None
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--config" and i + 1 < len(args):
            config_path = args[i + 1]
            i += 2
        elif a == "--public-dir" and i + 1 < len(args):
            PUBLIC = os.path.abspath(args[i + 1])
            i += 2
        elif a == "--out-dir" and i + 1 < len(args):
            OUT_DIR = os.path.abspath(args[i + 1])
            i += 2
        else:
            i += 1
    if not config_path:
        print("Usage: python3 render-ffmpeg.py --config config.json [--public-dir DIR] [--out-dir DIR]")
        sys.exit(1)

    # Validate binary paths early so failures are obvious
    for name, path in [("ffmpeg", FFMPEG), ("ffprobe", FFPROBE)]:
        if not os.path.exists(path):
            print(f"ERROR: {name} binary not found at {path}", file=sys.stderr)
            print(f"  Set {name.upper()}_PATH env var to override.", file=sys.stderr)
            sys.exit(1)

    with open(config_path) as f:
        config = json.load(f)

    comp = config.get("composition", "ReelShort")
    w, h = FORMATS.get(comp, (1080, 1920))
    title = config.get("title", "Taiwan Merch")
    title_en = config.get("title_en", "")
    subtitle = config.get("subtitle", "")
    output_file = config.get("outputFile", "output.mp4")
    slides = config.get("slides", [])
    bgm = config.get("bgMusicFile")
    bgm_vol = config.get("bgMusicVolume", 0.3)
    show_intro = config.get("showIntro", True)
    show_outro = config.get("showOutro", True)
    outro_dur = config.get("outroDuration", 3)
    narration_file = config.get("narrationFile")
    narration_delay = config.get("narrationDelay", 3.0)
    logo_file = config.get("logoFile")

    os.makedirs(OUT_DIR, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="twm-render-")

    print(f"\n🎬 Taiwan Merch Video Renderer v3 (FFmpeg + Pillow)")
    print(f"  Format: {comp} ({w}x{h})")
    print(f"  Title: {title}")
    if title_en:
        print(f"  Title EN: {title_en}")
    print(f"  Slides: {len(slides)}")
    if narration_file:
        print(f"  Narration: {narration_file}")
    print(f"  Output: {output_file}\n")

    clips = []
    clip_durations = []  # track actual durations for timestamp calculation
    voice_tracks = []    # clips with keepAudio
    idx = 0

    # Intro
    if show_intro:
        idx += 1
        print(f"  [{idx:2d}] Intro card...", end="", flush=True)
        intro_png = os.path.join(tmp, "intro.png")
        intro_mp4 = os.path.join(tmp, f"{idx:02d}_intro.mp4")
        create_title_card(w, h, title, title_en, subtitle, intro_png)
        image_to_video(intro_png, 3, w, h, intro_mp4)
        clips.append(intro_mp4)
        clip_durations.append(get_duration(intro_mp4))
        print(" done")

    # Slides
    for slide in slides:
        idx += 1
        is_video = slide["file"].lower().endswith((".mp4", ".mov", ".webm"))
        print(f"  [{idx:2d}] {slide['file']}...", end="", flush=True)

        cap_png = None
        caption_en = slide.get("caption", "")
        caption_zh = slide.get("caption_zh", "")
        if caption_en or caption_zh:
            cap_png = os.path.join(tmp, f"{idx:02d}_cap.png")
            create_caption_overlay(w, h, caption_en, caption_zh, cap_png)

        out = os.path.join(tmp, f"{idx:02d}_slide.mp4")
        if is_video:
            process_video_slide(slide, w, h, cap_png, out)
        else:
            process_image_slide(slide, w, h, cap_png, out)
        clips.append(out)

        actual_dur = get_duration(out)
        clip_durations.append(actual_dur)

        # Track keepAudio clips for voice mixing
        if slide.get("keepAudio") and is_video:
            start_time = sum(clip_durations[:-1])
            orig_audio = os.path.join(tmp, f"{idx:02d}_voice.aac")
            # Extract original audio from source file
            orig_path = os.path.join(PUBLIC, slide["file"])
            run_ff([
                FFMPEG, "-y", "-i", orig_path,
                "-vn", "-c:a", "aac", "-b:a", "192k",
                "-t", str(slide.get("durationSec", actual_dur)),
                orig_audio
            ])
            voice_dur = get_duration(orig_audio)
            voice_tracks.append({
                "audio_path": orig_audio,
                "start_time": start_time,
                "duration": voice_dur
            })
            print(f" done (voice @ {start_time:.1f}s)")
        else:
            print(" done")

    # Outro
    if show_outro:
        idx += 1
        print(f"  [{idx:2d}] Outro card...", end="", flush=True)
        outro_png = os.path.join(tmp, "outro.png")
        outro_mp4 = os.path.join(tmp, f"{idx:02d}_outro.mp4")
        logo_path = os.path.join(PUBLIC, logo_file) if logo_file else None
        create_outro_card(w, h, outro_png, logo_path=logo_path)
        image_to_video(outro_png, outro_dur, w, h, outro_mp4)
        clips.append(outro_mp4)
        clip_durations.append(get_duration(outro_mp4))
        print(" done")

    # Concat video (no audio)
    tmp_video = os.path.join(tmp, "concat_video.mp4")
    print(f"\n  Concatenating {len(clips)} video clips...", end="", flush=True)
    concat_clips_video_only(clips, tmp_video)
    print(" done")

    # Mix audio
    output_path = os.path.join(OUT_DIR, output_file)
    if bgm:
        print(f"  Mixing audio (BGM + narration + {len(voice_tracks)} voice track(s))...",
              end="", flush=True)
        mix_audio(
            tmp_video, output_path,
            bgm_path=bgm, bgm_vol=bgm_vol,
            narration_path=narration_file, narr_delay=narration_delay,
            voice_tracks=voice_tracks if voice_tracks else None
        )
        print(" done")
    else:
        shutil.copy2(tmp_video, output_path)

    shutil.rmtree(tmp, ignore_errors=True)

    size_mb = os.path.getsize(output_path) / 1024 / 1024
    dur = get_duration(output_path)
    print(f"\n✅ Done!")
    print(f"  Output: {output_path}")
    print(f"  Duration: {dur:.1f}s | Size: {size_mb:.1f} MB")
    print(f"  Timeline: {' + '.join(f'{d:.1f}s' for d in clip_durations)}\n")


if __name__ == "__main__":
    main()
