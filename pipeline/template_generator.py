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
from pipeline.ai_vision import extract_text_with_nim, load_nvidia_api_key

VISION_OCR_BIN = os.path.join(SCRIPT_DIR, 'bin', 'vision_ocr')

def sample_text_color(image_bgr, box_norm):
    """
    Sample representative text color from within normalized box [x, y, w, h].
    """
    h_img, w_img = image_bgr.shape[:2]
    x = max(0, int(box_norm[0] * w_img if isinstance(box_norm, (list, tuple)) else box_norm['x'] * w_img))
    y = max(0, int(box_norm[1] * h_img if isinstance(box_norm, (list, tuple)) else box_norm['y'] * h_img))
    w = min(w_img - x, int(box_norm[2] * w_img if isinstance(box_norm, (list, tuple)) else box_norm['w'] * w_img))
    h = min(h_img - y, int(box_norm[3] * h_img if isinstance(box_norm, (list, tuple)) else box_norm['h'] * h_img))
    
    if w <= 0 or h <= 0:
        return "#ffffff"
        
    roi = image_bgr[y:y+h, x:x+w]
    if roi.size == 0:
        return "#ffffff"
        
    border_pixels = np.vstack([roi[0, :, :], roi[-1, :, :], roi[:, 0, :], roi[:, -1, :]])
    border_bgr = np.mean(border_pixels, axis=0)
    diffs = np.linalg.norm(roi.astype(float) - border_bgr, axis=2)
    
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
    if font_size >= 75 or "&" in text or " weds " in text_lower or " and " in text_lower:
        return "names"
    elif text.startswith("#"):
        return "hashtag"
    elif any(k in text_lower for k in ["september", "october", "november", "december", "january", "february", "march", "april", "may", "june", "july", "august", "202", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]):
        return "date"
    elif any(k in text_lower for k in ["pm", "am", "onwards", "lunch", "dinner", "o'clock", "noon"]):
        return "time"
    elif any(k in text_lower for k in ["residence", "venue", "mandir", "auditorium", "road", "palace", "hotel", "resort", "hall", "farm"]):
        return "venue"
    elif any(k in text_lower for k in ["ceremony", "celebration", "sangeet", "haldi", "mehandi", "wedding", "save the date", "invitation", "shree ganesh"]):
        return "title"
    else:
        return "text"

def deduplicate_boxes(boxes, min_y_dist=0.035):
    """
    Remove duplicate boxes that sit on approximately the same vertical line.
    """
    if not boxes:
        return []
        
    sorted_boxes = sorted(boxes, key=lambda b: b["y"])
    unique = []
    
    for b in sorted_boxes:
        is_dup = False
        for u in unique:
            # If vertical centers are very close
            cy1 = b["y"] + b["h"] / 2.0
            cy2 = u["y"] + u["h"] / 2.0
            if abs(cy1 - cy2) < min_y_dist:
                is_dup = True
                # Keep the one with larger area or higher confidence
                if (b.get("confidence", 0) > u.get("confidence", 0)) or (b["w"] * b["h"] > u["w"] * u["h"]):
                    u["text"] = b["text"]
                    u["x"] = min(u["x"], b["x"])
                    u["y"] = min(u["y"], b["y"])
                    u["w"] = max(u["x"] + u["w"], b["x"] + b["w"]) - u["x"]
                    u["h"] = max(u["y"] + u["h"], b["y"] + b["h"]) - u["y"]
                break
        if not is_dup:
            unique.append(b)
            
    return sorted(unique, key=lambda b: b["y"])

def generate_template(video_path, template_dir, template_name=None):
    """
    Production-Ready Template Generator:
    1. Detect scene cuts and select golden keyframes (settled frame at 75-80%)
    2. Extract pixel-precise text boxes with Apple Vision OCR
    3. Enhance with NVIDIA NIM AI Vision for Hindi/Devanagari scripts and roles
    4. Remove duplicate animation boxes
    5. Generate structured, clean template.json
    """
    os.makedirs(template_dir, exist_ok=True)
    frames_dir = os.path.join(template_dir, "preview_frames")
    os.makedirs(frames_dir, exist_ok=True)
    
    print(f"[*] Step 1: Detecting scene cuts for: {video_path}")
    scene_data = detect_scenes(video_path, output_dir=frames_dir)
    v_info = scene_data["video_info"]
    scenes = scene_data["scenes"]
    
    cap = cv2.VideoCapture(video_path)
    golden_frames = []
    
    for sc in scenes:
        s_start = sc["start_frame"]
        s_end = sc["end_frame"]
        duration = s_end - s_start
        # Select settled golden frame at ~75% of scene
        golden_fnum = s_start + int(duration * 0.75) if duration > 10 else s_start + duration // 2
        golden_fnum = min(s_end - 1, max(s_start, golden_fnum))
        
        cap.set(cv2.CAP_PROP_POS_FRAMES, golden_fnum)
        ret, fr = cap.read()
        if ret:
            golden_path = os.path.join(frames_dir, f"scene_{sc['scene_num']:02d}_golden.jpg")
            cv2.imwrite(golden_path, fr)
            sc["golden_frame"] = golden_fnum
            sc["golden_path"] = golden_path
            golden_frames.append(golden_path)
        else:
            sc["golden_frame"] = sc.get("keyframe_frame", s_start)
            sc["golden_path"] = sc.get("keyframe_path")
            if sc["golden_path"]:
                golden_frames.append(sc["golden_path"])
                
    cap.release()
    
    # Step 2: Extract text bounding boxes with Apple Vision OCR
    print(f"[*] Step 2: Running high-precision text box detection on {len(golden_frames)} scenes...")
    ocr_results = {}
    if os.path.exists(VISION_OCR_BIN) and golden_frames:
        cmd = [VISION_OCR_BIN] + golden_frames
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            try:
                ocr_data = json.loads(proc.stdout)
                for item in ocr_data:
                    ocr_results[item["image"]] = item["boxes"]
            except Exception as e:
                print(f"[-] OCR parse error: {e}")
                
    # Step 3: NVIDIA NIM AI Vision Enhancement
    has_nim = load_nvidia_api_key() is not None
    if has_nim:
        print("[*] Step 3: NVIDIA NIM AI Vision active. Enhancing keyframes with Llama-3.2 Vision...")
    else:
        print("[-] Step 3: NVIDIA NIM not configured, using native OCR.")
        
    template_scenes = []
    total_fields = 0
    
    for sc in scenes:
        sc_num = sc["scene_num"]
        golden_path = sc.get("golden_path")
        if not golden_path or not os.path.exists(golden_path):
            continue
            
        img_bgr = cv2.imread(golden_path)
        raw_boxes = ocr_results.get(golden_path, [])
        # Deduplicate raw OCR boxes
        clean_boxes = deduplicate_boxes(raw_boxes)
        
        # Query NIM for this golden frame if available
        nim_items = []
        if has_nim:
            try:
                nim_items = extract_text_with_nim(golden_path)
                print(f"    - Scene {sc_num}: NIM extracted {len(nim_items)} elements")
            except Exception as e:
                print(f"    - Scene {sc_num} NIM warning: {e}")
                
        # Build field list by merging NIM & OCR boxes
        fields_list = []
        
        if clean_boxes:
            # Sort OCR boxes top to bottom
            clean_boxes = sorted(clean_boxes, key=lambda b: b["y"])
            
            for f_idx, b in enumerate(clean_boxes, 1):
                text_clean = b["text"].strip()
                if len(text_clean) < 1:
                    continue
                    
                center_x = b["x"] + b["w"] / 2.0
                center_y = b["y"] + b["h"] / 2.0
                
                # Proportional font size
                font_size = max(22, int(b["h"] * v_info["height"] * 0.8))
                color_hex = sample_text_color(img_bgr, b)
                
                align = "center"
                if center_x < 0.35:
                    align = "left"
                elif center_x > 0.65:
                    align = "right"
                    
                field_role = categorize_field(text_clean, font_size)
                
                # Check if NIM has a better match or Hindi transcription
                if nim_items:
                    # Match by vertical position proximity
                    best_nim = None
                    best_dist = 999.0
                    for n in nim_items:
                        dist = abs(n["y_percent"] - (center_y * 100))
                        if dist < best_dist and dist < 18.0:
                            best_dist = dist
                            best_nim = n
                            
                    if best_nim:
                        # Use NIM's transcription and role
                        text_clean = best_nim["text"]
                        field_role = best_nim.get("role", field_role)
                        align = best_nim.get("align", align)
                        
                total_fields += 1
                role_label = field_role.replace("_", " ").title()
                fields_list.append({
                    "id": f"field_{sc_num}_{f_idx}",
                    "label": f"{role_label} {f_idx}: {text_clean[:22]}",
                    "value": text_clean,
                    "default_value": text_clean,
                    "type": field_role,
                    "box": [round(b["x"], 3), round(b["y"], 3), round(b["w"], 3), round(b["h"], 3)],
                    "x_percent": round(center_x * 100, 1),
                    "y_percent": round(center_y * 100, 1),
                    "font_size": font_size,
                    "color": color_hex,
                    "align": align
                })
        elif nim_items:
            # If native OCR found no boxes (e.g. pure Hindi), create fields from NIM directly
            for f_idx, n in enumerate(nim_items, 1):
                total_fields += 1
                t = n["text"]
                role_label = n.get("role", "general").replace("_", " ").title()
                cy = n.get("y_percent", 50.0)
                font_size = max(24, int(v_info["height"] * 0.035))
                fields_list.append({
                    "id": f"field_{sc_num}_{f_idx}",
                    "label": f"{role_label} {f_idx}: {t[:22]}",
                    "value": t,
                    "default_value": t,
                    "type": n.get("role", "general"),
                    "box": [0.1, round((cy - 2.5) / 100.0, 3), 0.8, 0.05],
                    "x_percent": 50.0,
                    "y_percent": round(cy, 1),
                    "font_size": font_size,
                    "color": "#ffffff",
                    "align": n.get("align", "center")
                })
                
        template_scenes.append({
            "scene_id": f"scene_{sc_num}",
            "scene_num": sc_num,
            "name": f"Scene {sc_num} ({sc['start_time_sec']}s - {sc['end_time_sec']}s)",
            "start_frame": sc["start_frame"],
            "end_frame": sc["end_frame"],
            "start_time_sec": sc["start_time_sec"],
            "end_time_sec": sc["end_time_sec"],
            "duration_sec": sc["duration_sec"],
            "preview_frame": sc.get("golden_frame", sc["start_frame"]),
            "preview_path": golden_path,
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
        
    print(f"[+] Successfully generated template schema with {len(template_scenes)} scenes and {total_fields} clean editable fields!")
    print(f"    Saved to: {template_json_path}")
    return template_data

if __name__ == "__main__":
    v_path = sys.argv[1] if len(sys.argv) > 1 else "A1.mp4"
    t_dir = sys.argv[2] if len(sys.argv) > 2 else "tmp_template_test"
    generate_template(v_path, t_dir)
