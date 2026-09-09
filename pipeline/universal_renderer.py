import os
import sys
import json
import time
import subprocess
import multiprocessing as mp
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS_DIR = os.path.join(SCRIPT_DIR, "fonts")

def is_devanagari(text):
    return any(0x0900 <= ord(c) <= 0x097F or 0x0964 <= ord(c) <= 0x0965 for c in text)

def get_font_for_field(field_type, font_size, text="", custom_font=None):
    """
    Select appropriate font based on field type, text script, and desired size.
    Supports user-specified custom font overrides.
    """
    try:
        font_path = None
        if custom_font:
            candidate = os.path.join(FONTS_DIR, custom_font)
            if os.path.exists(candidate):
                font_path = candidate

        if not font_path:
            if is_devanagari(text):
                font_path = os.path.join(FONTS_DIR, "RozhaOne-Regular.ttf")
            elif field_type == "names":
                font_path = os.path.join(FONTS_DIR, "GreatVibes-Regular.ttf")
            elif field_type == "title":
                font_path = os.path.join(FONTS_DIR, "Cinzel.ttf")
            elif field_type == "date" or field_type == "time":
                font_path = os.path.join(FONTS_DIR, "Georgia Bold.ttf")
            elif field_type == "venue":
                font_path = os.path.join(FONTS_DIR, "Georgia.ttf")
            else:
                font_path = os.path.join(FONTS_DIR, "Georgia Italic.ttf")
            
        if not font_path or not os.path.exists(font_path):
            font_path = os.path.join(FONTS_DIR, "Georgia.ttf")
            
        return ImageFont.truetype(font_path, max(14, int(font_size)))
    except Exception:
        return ImageFont.load_default()

def parse_hex_color(hex_str, alpha=255):
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return (r, g, b, alpha)
    return (255, 255, 255, alpha)

def render_frame_with_template(base_bgr, frame_idx, scenes, video_w, video_h):
    # Find active scene
    active_scene = None
    for sc in scenes:
        if sc["start_frame"] <= frame_idx < sc["end_frame"]:
            active_scene = sc
            break
            
    if not active_scene or not active_scene.get("fields"):
        return base_bgr
        
    s_start = active_scene["start_frame"]
    # Fade in over first 20 frames of scene
    alpha_factor = min(1.0, max(0.0, (frame_idx - s_start) / 20.0))
    a_val = int(alpha_factor * 255)
    if a_val <= 0:
        return base_bgr
        
    overlay = Image.new("RGBA", (video_w, video_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    for f in active_scene.get("fields", []):
        text = f.get("value", "")
        if not text:
            continue
            
        font_size = f.get("font_size", 36)
        f_type = f.get("type", "text")
        font = get_font_for_field(f_type, font_size, text, custom_font=f.get("font"))
        
        color_rgba = parse_hex_color(f.get("color", "#ffffff"), a_val)
        
        # Calculate coordinate
        cx = int(f.get("x_percent", 50.0) / 100.0 * video_w)
        cy = int(f.get("y_percent", 50.0) / 100.0 * video_h)
        
        bbox = draw.textbbox((0, 0), text, font=font)
        bw = bbox[2] - bbox[0]
        bh = bbox[3] - bbox[1]
        
        align = f.get("align", "center")
        if align == "left":
            x = cx
        elif align == "right":
            x = cx - bw
        else: # center
            x = cx - bw // 2
            
        y = cy - bh // 2
        
        # Subtle drop shadow for crisp legibility
        shadow_rgba = (0, 0, 0, int(a_val * 0.45))
        draw.text((x + 2, y + 2), text, font=font, fill=shadow_rgba)
        draw.text((x, y), text, font=font, fill=color_rgba)
        
    base_pil = Image.fromarray(cv2.cvtColor(base_bgr, cv2.COLOR_BGR2RGB))
    base_pil.paste(overlay, (0, 0), overlay)
    return cv2.cvtColor(np.array(base_pil), cv2.COLOR_RGB2BGR)

def render_worker(task):
    part_id, start_frame, end_frame, clean_video_path, template_json_path, tmp_dir = task
    with open(template_json_path, "r", encoding="utf-8") as f:
        template = json.load(f)
        
    scenes = template.get("scenes", [])
    cap = cv2.VideoCapture(clean_video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    part_file = os.path.join(tmp_dir, f"render_part_{part_id:03d}.mp4")
    out = cv2.VideoWriter(part_file, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    
    for idx in range(start_frame, end_frame):
        ret, frame = cap.read()
        if not ret:
            break
        rendered = render_frame_with_template(frame, idx, scenes, w, h)
        out.write(rendered)
        
    cap.release()
    out.release()
    return part_file

def _do_render_template_video(clean_video_path, template_json_path, output_video_path, num_workers=None):
    if num_workers is None:
        num_workers = min(8, mp.cpu_count() or 4)
        
    cap = cv2.VideoCapture(clean_video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    
    tmp_dir = os.path.join(os.path.dirname(output_video_path), "tmp_universal_render")
    os.makedirs(tmp_dir, exist_ok=True)
    
    chunk_size = int(np.ceil(total_frames / num_workers))
    tasks = []
    for i in range(num_workers):
        s = i * chunk_size
        e = min(total_frames, (i + 1) * chunk_size)
        if s < total_frames:
            tasks.append((i, s, e, clean_video_path, template_json_path, tmp_dir))
            
    print(f"[*] Rendering {total_frames} frames across {len(tasks)} parallel workers...", flush=True)
    t0 = time.time()
    with mp.Pool(processes=len(tasks)) as pool:
        part_files = pool.map(render_worker, tasks)
        
    concat_list = os.path.join(tmp_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for p in part_files:
            f.write(f"file '{os.path.abspath(p)}'\n")
            
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list,
        "-i", clean_video_path,
        "-map", "0:v:0",
        "-map", "1:a:0?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        output_video_path
    ]
    subprocess.run(cmd, check=True)
    
    try:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass
        
    render_time = round(time.time() - t0, 2)
    print(f"[+] Render finished in {render_time}s: {output_video_path}", flush=True)
    return output_video_path

def render_template_video(clean_video_path, template_json_path, output_video_path, num_workers=None):
    cmd = [
        sys.executable,
        os.path.abspath(__file__),
        os.path.abspath(clean_video_path),
        os.path.abspath(template_json_path),
        os.path.abspath(output_video_path)
    ]
    subprocess.run(cmd, check=True)
    return output_video_path

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        _do_render_template_video(sys.argv[1], sys.argv[2], sys.argv[3])
    else:
        print("Usage: python universal_renderer.py <clean_video> <template_json> <output_video>")
