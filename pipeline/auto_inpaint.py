import os
import sys
import json
import time
import subprocess
import multiprocessing as mp
import cv2
import numpy as np

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def create_scene_masks(frame_shape, scene_fields):
    """
    Build binary mask covering all detected text fields for this scene.
    Dilated slightly to ensure anti-aliased font edges are completely covered.
    """
    h, w = frame_shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    
    for f in scene_fields:
        box = f.get("box")
        if not box or len(box) != 4:
            continue
            
        bx, by, bw, bh = box
        # Add a 4% margin around the detected box
        pad_x = bw * 0.04
        pad_y = bh * 0.06
        
        x1 = max(0, int((bx - pad_x) * w))
        y1 = max(0, int((by - pad_y) * h))
        x2 = min(w, int((bx + bw + pad_x) * w))
        y2 = min(h, int((by + bh + pad_y) * h))
        
        if x2 > x1 and y2 > y1:
            mask[y1:y2, x1:x2] = 255
            
    # Smooth and dilate mask
    if np.any(mask):
        mask = cv2.dilate(mask, kernel, iterations=2)
        
    return mask

def inpaint_worker(task):
    """
    Worker function to inpaint a chunk of frames in parallel.
    """
    part_id, start_frame, end_frame, video_path, template_json_path, tmp_dir = task
    
    with open(template_json_path, "r", encoding="utf-8") as f:
        template = json.load(f)
        
    scenes = template.get("scenes", [])
    
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    part_file = os.path.join(tmp_dir, f"part_{part_id:03d}.mp4")
    out = cv2.VideoWriter(part_file, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
    
    # Pre-compute masks for each scene
    scene_masks = {}
    for sc in scenes:
        scene_masks[sc["scene_id"]] = create_scene_masks((h, w), sc.get("fields", []))
        
    for f_idx in range(start_frame, end_frame):
        ret, frame = cap.read()
        if not ret:
            break
            
        # Find which scene this frame belongs to
        active_mask = None
        for sc in scenes:
            if sc["start_frame"] <= f_idx < sc["end_frame"]:
                active_mask = scene_masks.get(sc["scene_id"])
                break
                
        if active_mask is not None and np.any(active_mask):
            # Inpaint text areas
            inpainted = cv2.inpaint(frame, active_mask, 7, cv2.INPAINT_TELEA)
            out.write(inpainted)
        else:
            out.write(frame)
            
    cap.release()
    out.release()
    return part_file

def generate_clean_video(video_path, template_json_path, output_clean_path, num_workers=None, progress_callback=None):
    """
    Generate clean_base.mp4 using multi-core parallel inpainting.
    Preserves original audio track with ffmpeg.
    """
    if num_workers is None:
        num_workers = min(8, mp.cpu_count() or 4)
        
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    cap.release()
    
    tmp_dir = os.path.join(os.path.dirname(output_clean_path), "tmp_inpaint")
    os.makedirs(tmp_dir, exist_ok=True)
    
    chunk_size = int(np.ceil(total_frames / num_workers))
    tasks = []
    
    for i in range(num_workers):
        s = i * chunk_size
        e = min(total_frames, (i + 1) * chunk_size)
        if s < total_frames:
            tasks.append((i, s, e, video_path, template_json_path, tmp_dir))
            
    print(f"[*] Inpainting {total_frames} frames across {len(tasks)} parallel workers...")
    
    with mp.Pool(processes=len(tasks)) as pool:
        part_files = pool.map(inpaint_worker, tasks)
        
    # Create concat list for ffmpeg
    concat_list_path = os.path.join(tmp_dir, "concat_list.txt")
    with open(concat_list_path, "w") as f:
        for p in part_files:
            f.write(f"file '{os.path.abspath(p)}'\n")
            
    print("[*] Concatenating parts and muxing original audio...")
    # Fast ffmpeg concat & mux audio
    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", concat_list_path,
        "-i", video_path,
        "-map", "0:v:0",
        "-map", "1:a:0?",
        "-c:v", "libx264", "-preset", "ultrafast", "-crf", "18",
        "-c:a", "copy",
        "-pix_fmt", "yuv420p",
        output_clean_path
    ]
    
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Cleanup tmp files
    try:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass
        
    print(f"[+] Clean background video generated: {output_clean_path}")
    return output_clean_path

if __name__ == "__main__":
    v_in = sys.argv[1] if len(sys.argv) > 1 else "A1.mp4"
    t_json = sys.argv[2] if len(sys.argv) > 2 else "tmp_template_test/template.json"
    v_out = sys.argv[3] if len(sys.argv) > 3 else "tmp_template_test/clean_base.mp4"
    generate_clean_video(v_in, t_json, v_out)
