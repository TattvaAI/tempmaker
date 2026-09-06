import os
import sys
import json
import subprocess
import cv2
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
from pipeline.scene_detector import detect_scenes

VISION_OCR_BIN = os.path.join(SCRIPT_DIR, 'bin', 'vision_ocr')

def sample_text_color(image_bgr, box_norm):
    """
    Sample representative text color from within normalized box [x, y, w, h].
    """
    h_img, w_img = image_bgr.shape[:2]
    x = max(0, int(box_norm['x'] * w_img))
    y = max(0, int(box_norm['y'] * h_img))
    w = min(w_img - x, int(box_norm['w'] * w_img))
    h = min(h_img - y, int(box_norm['h'] * h_img))
    
    if w <= 0 or h <= 0:
        return "#ffffff"
        
    roi = image_bgr[y:y+h, x:x+w]
    if roi.size == 0:
        return "#ffffff"
        
    # Find pixels that differ from ROI border background
    border_pixels = np.vstack([roi[0, :, :], roi[-1, :, :], roi[:, 0, :], roi[:, -1, :]])
    border_bgr = np.mean(border_pixels, axis=0)
    diffs = np.linalg.norm(roi.astype(float) - border_bgr, axis=2)
    
    # Text pixels are those with highest contrast against border
    threshold = np.percentile(diffs, 75)
    text_mask = diffs > max(20, threshold)
    
    if np.any(text_mask):
        text_bgr = np.mean(roi[text_mask], axis=0)
    else:
        text_bgr = np.mean(roi, axis=(0, 1))
        
    b, g, r = int(text_bgr[0]), int(text_bgr[1]), int(text_bgr[2])
    return f"#{r:02x}{g:02x}{b:02x}"

def categorize_field(text, font_size):
    text_lower = text.lower()
    if font_size >= 90:
        return "names"
    elif any(k in text_lower for k in ["september", "october", "november", "december", "january", "february", "march", "april", "may", "june", "july", "august", "202", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
        return "date"
    elif any(k in text_lower for k in ["pm", "am", "onwards", "lunch", "dinner", "o'clock"]):
        return "time"
    elif any(k in text_lower for k in ["residence", "venue", "mandir", "auditorium", "road", "palace", "hotel", "resort", "hall"]):
        return "venue"
    elif any(k in text_lower for k in ["ceremony", "celebration", "sangeet", "haldi", "mehandi", "wedding", "save the date", "invitation"]):
        return "title"
    else:
        return "text"

def generate_template(video_path, template_dir, template_name=None):
    """
    Full automated pipeline:
    1. Detect scenes and extract keyframes
    2. Run Swift Vision OCR
    3. Sample colors, bounding boxes, typography
    4. Produce structured template.json
    """
    os.makedirs(template_dir, exist_ok=True)
    frames_dir = os.path.join(template_dir, "preview_frames")
    os.makedirs(frames_dir, exist_ok=True)
    
    print(f"[*] Step 1: Analyzing video & scene boundaries: {video_path}")
    scene_data = detect_scenes(video_path, output_dir=frames_dir)
    v_info = scene_data["video_info"]
    scenes = scene_data["scenes"]
    
    # Extract multiple keyframes per scene to catch staged animations
    cap = cv2.VideoCapture(video_path)
    ocr_inputs = []
    
    for sc in scenes:
        s_start = sc["start_frame"]
        s_end = sc["end_frame"]
        duration = s_end - s_start
        
        # Sample at 40%, 65%, 85% of scene
        sample_points = [
            s_start + int(duration * 0.4),
            s_start + int(duration * 0.65),
            s_start + int(duration * 0.85)
        ]
        
        sc_samples = []
        for p_idx, f_num in enumerate(sample_points):
            cap.set(cv2.CAP_PROP_POS_FRAMES, f_num)
            ret, fr = cap.read()
            if ret:
                sample_path = os.path.join(frames_dir, f"scene_{sc['scene_num']:02d}_s{p_idx}.jpg")
                cv2.imwrite(sample_path, fr)
                sc_samples.append((f_num, sample_path))
                ocr_inputs.append(sample_path)
        sc["sample_frames"] = sc_samples
        
    cap.release()
    
    print(f"[*] Step 2: Running native Apple Vision OCR on {len(ocr_inputs)} keyframes...")
    ocr_results = {}
    if os.path.exists(VISION_OCR_BIN) and ocr_inputs:
        cmd = [VISION_OCR_BIN] + ocr_inputs
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            try:
                ocr_data = json.loads(proc.stdout)
                for item in ocr_data:
                    ocr_results[item["image"]] = item["boxes"]
            except Exception as e:
                print(f"[-] OCR parse error: {e}")
                
    print(f"[*] Step 3: Structuring fields and typography...")
    template_scenes = []
    total_fields = 0
    
    for sc in scenes:
        sc_num = sc["scene_num"]
        # Merge OCR observations from this scene's samples
        seen_texts = {}
        
        for f_num, img_path in sc.get("sample_frames", []):
            boxes = ocr_results.get(img_path, [])
            img_bgr = cv2.imread(img_path)
            
            for b in boxes:
                text_clean = b["text"].strip()
                if len(text_clean) < 1:
                    continue
                    
                # De-duplicate by normalized text
                norm_key = "".join(text_clean.lower().split())
                if norm_key not in seen_texts or b["confidence"] > seen_texts[norm_key]["confidence"]:
                    # Compute pixel font size estimate
                    font_size = max(24, int(b["h"] * v_info["height"] * 0.82))
                    color_hex = sample_text_color(img_bgr, b)
                    center_x = b["x"] + b["w"] / 2.0
                    center_y = b["y"] + b["h"] / 2.0
                    
                    align = "center"
                    if center_x < 0.35:
                        align = "left"
                    elif center_x > 0.65:
                        align = "right"
                        
                    field_type = categorize_field(text_clean, font_size)
                    
                    seen_texts[norm_key] = {
                        "text": text_clean,
                        "confidence": b["confidence"],
                        "box": [round(b["x"], 3), round(b["y"], 3), round(b["w"], 3), round(b["h"], 3)],
                        "center_x_percent": round(center_x * 100, 1),
                        "center_y_percent": round(center_y * 100, 1),
                        "font_size": font_size,
                        "color": color_hex,
                        "align": align,
                        "type": field_type
                    }
                    
        # Convert seen_texts into ordered fields (sorted by vertical Y position)
        ordered_fields = sorted(seen_texts.values(), key=lambda x: x["center_y_percent"])
        fields_list = []
        for f_idx, f_info in enumerate(ordered_fields, 1):
            total_fields += 1
            fields_list.append({
                "id": f"field_{sc_num}_{f_idx}",
                "label": f"{f_info['type'].capitalize()} {f_idx}: {f_info['text'][:20]}",
                "value": f_info["text"],
                "default_value": f_info["text"],
                "type": f_info["type"],
                "box": f_info["box"],
                "x_percent": f_info["center_x_percent"],
                "y_percent": f_info["center_y_percent"],
                "font_size": f_info["font_size"],
                "color": f_info["color"],
                "align": f_info["align"]
            })
            
        best_preview = sc.get("keyframe_path")
        if not best_preview and sc.get("sample_frames"):
            best_preview = sc["sample_frames"][0][1]
            
        template_scenes.append({
            "scene_id": f"scene_{sc_num}",
            "scene_num": sc_num,
            "name": f"Scene {sc_num} ({sc['start_time_sec']}s - {sc['end_time_sec']}s)",
            "start_frame": sc["start_frame"],
            "end_frame": sc["end_frame"],
            "start_time_sec": sc["start_time_sec"],
            "end_time_sec": sc["end_time_sec"],
            "duration_sec": sc["duration_sec"],
            "preview_frame": sc.get("keyframe_frame", sc["start_frame"]),
            "preview_path": best_preview,
            "fields": fields_list
        })
        
    template_data = {
        "template_id": os.path.basename(template_dir),
        "title": template_name or f"Template ({os.path.basename(video_path)})",
        "source_video": video_path,
        "video_info": v_info,
        "total_fields": total_fields,
        "scenes": template_scenes
    }
    
    template_json_path = os.path.join(template_dir, "template.json")
    with open(template_json_path, "w", encoding="utf-8") as f:
        json.dump(template_data, f, indent=2, ensure_ascii=False)
        
    print(f"[+] Step 4: Successfully generated template schema with {len(template_scenes)} scenes and {total_fields} editable fields!")
    print(f"    Saved to: {template_json_path}")
    return template_data

if __name__ == "__main__":
    v_path = sys.argv[1] if len(sys.argv) > 1 else "A1.mp4"
    t_dir = sys.argv[2] if len(sys.argv) > 2 else "tmp_template_test"
    generate_template(v_path, t_dir)
