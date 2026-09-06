import cv2
import numpy as np
import multiprocessing as mp
import subprocess
import os
import time

input_video = 'A1.mp4'
output_clean_video = 'clean_base.mp4'

cap = cv2.VideoCapture(input_video)
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

cap.set(cv2.CAP_PROP_POS_FRAMES, 160)
_, f160 = cap.read()
sc2_patch = f160[280:600, 420:660].copy()

cap.set(cv2.CAP_PROP_POS_FRAMES, 763)
_, f763 = cap.read()
sc5_patch = f763[190:1120, 50:1030].copy()
cap.release()

os.makedirs('tmp_parts', exist_ok=True)

def worker(task):
    part_id, start_frame, end_frame = task
    cap_local = cv2.VideoCapture(input_video)
    cap_local.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
    
    part_file = f'tmp_parts/part_{part_id:02d}.mp4'
    out = cv2.VideoWriter(part_file, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    kernel_sc8 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    sc8_bg = np.array([228, 244, 245], dtype=np.float32)
    
    for idx in range(start_frame, end_frame):
        ret, frame = cap_local.read()
        if not ret:
            break
        
        if idx < 136:
            pass
        elif idx < 240:
            frame[280:600, 420:660] = sc2_patch
        elif idx < 285:
            pass
        elif idx < 411:
            roi = frame[60:750, 150:930]
            edges = cv2.Canny(roi, 30, 100)
            dilated = cv2.dilate(edges, kernel, iterations=3)
            mask = np.zeros((height, width), dtype=np.uint8)
            mask[60:750, 150:930] = dilated
            frame = cv2.inpaint(frame, mask, 7, cv2.INPAINT_TELEA)
        elif idx < 763:
            roi = frame[220:1350, 50:1030]
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 30, 100)
            shloka_roi = frame[150:230, 380:700]
            shloka_edges = cv2.Canny(cv2.cvtColor(shloka_roi, cv2.COLOR_BGR2GRAY), 30, 100)
            
            mask = np.zeros((height, width), dtype=np.uint8)
            mask[220:1350, 50:1030] = cv2.dilate(edges, kernel, iterations=3)
            mask[150:230, 380:700] = cv2.dilate(shloka_edges, kernel, iterations=3)
            frame = cv2.inpaint(frame, mask, 7, cv2.INPAINT_TELEA)
        elif idx < 943:
            frame[190:1120, 50:1030] = sc5_patch
        elif idx < 1093:
            roi = frame[450:1500, 260:820]
            edges = cv2.Canny(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 20, 80)
            mask = np.zeros((height, width), dtype=np.uint8)
            mask[450:1500, 260:820] = cv2.dilate(edges, kernel, iterations=3)
            frame = cv2.inpaint(frame, mask, 7, cv2.INPAINT_TELEA)
        elif idx < 1236:
            roi = frame[450:1350, 200:880]
            edges = cv2.Canny(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 20, 80)
            mask = np.zeros((height, width), dtype=np.uint8)
            mask[450:1350, 200:880] = cv2.dilate(edges, kernel, iterations=3)
            frame = cv2.inpaint(frame, mask, 7, cv2.INPAINT_TELEA)
        elif idx < 1432:
            roi = frame[200:1050, 50:1030]
            diff = np.linalg.norm(roi.astype(np.float32) - sc8_bg, axis=2)
            text_mask = (diff > 18).astype(np.uint8) * 255
            dilated = cv2.dilate(text_mask, kernel_sc8, iterations=2)
            full_mask = np.zeros((height, width), dtype=np.uint8)
            full_mask[200:1050, 50:1030] = dilated
            frame = cv2.inpaint(frame, full_mask, 7, cv2.INPAINT_TELEA)
        else:
            roi = frame[600:900, 180:900]
            edges = cv2.Canny(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 20, 80)
            mask = np.zeros((height, width), dtype=np.uint8)
            mask[600:900, 180:900] = cv2.dilate(edges, kernel, iterations=3)
            frame = cv2.inpaint(frame, mask, 7, cv2.INPAINT_TELEA)
        
        out.write(frame)
        
    out.release()
    cap_local.release()
    return part_file

if __name__ == '__main__':
    t0 = time.time()
    num_workers = 8
    chunk_size = (total_frames + num_workers - 1) // num_workers
    tasks = []
    for i in range(num_workers):
        s = i * chunk_size
        e = min((i + 1) * chunk_size, total_frames)
        if s < total_frames:
            tasks.append((i, s, e))
            
    print(f"Starting parallel processing across {len(tasks)} workers...")
    with mp.Pool(num_workers) as pool:
        part_files = pool.map(worker, tasks)
        
    print(f"Frame processing finished in {time.time() - t0:.2f}s. Concatenating parts and muxing audio...")
    with open('tmp_parts/concat_list.txt', 'w') as f:
        for p in part_files:
            f.write(f"file '../{p}'\n")
            
    # Concatenate and re-encode to clean_base.mp4 with audio from A1.mp4
    subprocess.run([
        'ffmpeg', '-y',
        '-f', 'concat', '-safe', '0',
        '-i', 'tmp_parts/concat_list.txt',
        '-i', input_video,
        '-map', '0:v:0',
        '-map', '1:a:0',
        '-c:v', 'libx264',
        '-pix_fmt', 'yuv420p',
        '-preset', 'veryfast',
        '-crf', '18',
        '-c:a', 'copy',
        output_clean_video
    ], check=True)
    
    print(f"ALL DONE! '{output_clean_video}' created in {time.time() - t0:.2f}s total.")
