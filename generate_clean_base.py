import cv2
import numpy as np
import subprocess
import os
import sys
import time

input_video = 'A1.mp4'
output_clean_video = 'clean_base.mp4'

cap = cv2.VideoCapture(input_video)
fps = cap.get(cv2.CAP_PROP_FPS)
width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

print(f"Video: {width}x{height}, {fps} fps, {total_frames} frames")

# Pre-extract clean reference patches
cap.set(cv2.CAP_PROP_POS_FRAMES, 160)
_, f160 = cap.read()
sc2_patch = f160[280:600, 420:660].copy()

cap.set(cv2.CAP_PROP_POS_FRAMES, 768)
_, f768 = cap.read()
# Haldi purple card clean patch
sc5_patch = f768[240:1120, 140:940].copy()

cap.set(cv2.CAP_PROP_POS_FRAMES, 1238)
_, f1238 = cap.read()
sc8_patch = f1238[180:880, 50:1030].copy()

# Setup ffmpeg pipe to encode clean video directly
ffmpeg_cmd = [
    'ffmpeg', '-y',
    '-f', 'rawvideo',
    '-vcodec', 'rawvideo',
    '-s', f'{width}x{height}',
    '-pix_fmt', 'bgr24',
    '-r', str(fps),
    '-i', '-',
    '-i', input_video,
    '-map', '0:v:0',
    '-map', '1:a:0',
    '-c:v', 'libx264',
    '-pix_fmt', 'yuv420p',
    '-preset', 'fast',
    '-crf', '18',
    '-c:a', 'copy',
    output_clean_video
]

proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)

cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))

start_time = time.time()

for idx in range(total_frames):
    ret, frame = cap.read()
    if not ret:
        break
    
    # Process by frame index
    if idx < 136:
        # Scene 1: pristine, no text
        pass
    elif idx < 240:
        # Scene 2: Monogram in arch
        frame[280:600, 420:660] = sc2_patch
    elif idx < 285:
        # Lotus transition
        pass
    elif idx < 411:
        # Scene 3: Lake sky text
        roi = frame[60:750, 150:930]
        edges = cv2.Canny(roi, 30, 100)
        dilated = cv2.dilate(edges, kernel, iterations=3)
        mask = np.zeros((height, width), dtype=np.uint8)
        mask[60:750, 150:930] = dilated
        frame = cv2.inpaint(frame, mask, 7, cv2.INPAINT_TELEA)
    elif idx < 763:
        # Scene 4: Parents invitation
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
        # Scene 5: Haldi purple card
        frame[240:1120, 140:940] = sc5_patch
    elif idx < 1093:
        # Scene 6: Mehendi
        roi = frame[450:1500, 260:820]
        edges = cv2.Canny(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 20, 80)
        mask = np.zeros((height, width), dtype=np.uint8)
        mask[450:1500, 260:820] = cv2.dilate(edges, kernel, iterations=3)
        frame = cv2.inpaint(frame, mask, 7, cv2.INPAINT_TELEA)
    elif idx < 1236:
        # Scene 7: Sangeet
        roi = frame[450:1350, 200:880]
        edges = cv2.Canny(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 20, 80)
        mask = np.zeros((height, width), dtype=np.uint8)
        mask[450:1350, 200:880] = cv2.dilate(edges, kernel, iterations=3)
        frame = cv2.inpaint(frame, mask, 7, cv2.INPAINT_TELEA)
    elif idx < 1432:
        # Scene 8: Wedding ceremony
        frame[180:880, 50:1030] = sc8_patch
    else:
        # Scene 9: Save The Date
        roi = frame[600:900, 180:900]
        edges = cv2.Canny(cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY), 20, 80)
        mask = np.zeros((height, width), dtype=np.uint8)
        mask[600:900, 180:900] = cv2.dilate(edges, kernel, iterations=3)
        frame = cv2.inpaint(frame, mask, 7, cv2.INPAINT_TELEA)

    proc.stdin.write(frame.tobytes())
    if idx % 150 == 0:
        print(f"Processed frame {idx}/{total_frames} ({idx/total_frames*100:.1f}%)")

proc.stdin.close()
proc.wait()
cap.release()
print(f"Finished generating clean base video in {time.time() - start_time:.2f}s")
