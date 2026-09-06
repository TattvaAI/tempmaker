import os
import cv2
import numpy as np
import json

def detect_scenes(video_path, output_dir=None, min_scene_len=30, threshold=0.45):
    """
    Detect scene cuts in a video using HSV color histogram correlation.
    Extracts a representative keyframe for each scene.
    """
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError(f"Cannot open video file: {video_path}")
        
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    prev_hist = None
    cuts = [0]
    frame_idx = 0
    step = 2  # Sample every 2 frames for speed
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        if frame_idx % step == 0:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [32, 32], [0, 180, 0, 256])
            cv2.normalize(hist, hist, alpha=0, beta=1, norm_type=cv2.NORM_MINMAX)
            
            if prev_hist is not None:
                corr = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CORREL)
                if corr < threshold:
                    if frame_idx - cuts[-1] >= min_scene_len:
                        cuts.append(frame_idx)
            prev_hist = hist
            
        frame_idx += 1
        
    cap.release()
    
    # Check for long scenes and sub-divide if significant content changes occurred
    final_cuts = [cuts[0]]
    for i in range(len(cuts) - 1):
        s_start = cuts[i]
        s_end = cuts[i + 1]
        
        # If scene is longer than 8 seconds (240 frames), check for intra-scene cut
        if s_end - s_start > 240:
            # Check frame difference at intervals of 30 frames
            cap_check = cv2.VideoCapture(video_path)
            cap_check.set(cv2.CAP_PROP_POS_FRAMES, s_start)
            prev_sample = None
            split_frame = None
            max_diff = 0
            
            for f in range(s_start + 60, s_end - 60, 15):
                cap_check.set(cv2.CAP_PROP_POS_FRAMES, f)
                ret, frame = cap_check.read()
                if not ret:
                    break
                gray = cv2.cvtColor(cv2.resize(frame, (160, 90)), cv2.COLOR_BGR2GRAY)
                if prev_sample is not None:
                    diff = np.mean(cv2.absdiff(prev_sample, gray))
                    if diff > max_diff:
                        max_diff = diff
                        if diff > 12: # Significant change
                            split_frame = f
                prev_sample = gray
            cap_check.release()
            
            if split_frame and (split_frame - s_start >= min_scene_len) and (s_end - split_frame >= min_scene_len):
                final_cuts.append(split_frame)
                
        final_cuts.append(s_end)
        
    cuts = sorted(list(set(final_cuts)))
        
    scenes = []
    cap = cv2.VideoCapture(video_path)
    
    for i in range(len(cuts) - 1):
        s_start = cuts[i]
        s_end = cuts[i + 1]
        
        # Pick keyframe at ~60% into scene duration (after text intro transition)
        keyframe_idx = s_start + int((s_end - s_start) * 0.6)
        if keyframe_idx >= s_end:
            keyframe_idx = s_start + (s_end - s_start) // 2
            
        cap.set(cv2.CAP_PROP_POS_FRAMES, keyframe_idx)
        ret, kframe = cap.read()
        keyframe_path = None
        if ret and output_dir:
            keyframe_path = os.path.join(output_dir, f"scene_{i+1:02d}_keyframe.jpg")
            cv2.imwrite(keyframe_path, kframe)
            
        scenes.append({
            "scene_num": i + 1,
            "start_frame": s_start,
            "end_frame": s_end,
            "start_time_sec": round(s_start / fps, 2),
            "end_time_sec": round(s_end / fps, 2),
            "duration_sec": round((s_end - s_start) / fps, 2),
            "keyframe_frame": keyframe_idx,
            "keyframe_time_sec": round(keyframe_idx / fps, 2),
            "keyframe_path": keyframe_path
        })
        
    cap.release()
    
    return {
        "video_info": {
            "path": video_path,
            "fps": fps,
            "total_frames": total_frames,
            "duration_sec": round(total_frames / fps, 2),
            "width": width,
            "height": height
        },
        "scenes": scenes
    }

if __name__ == "__main__":
    import sys
    video_file = sys.argv[1] if len(sys.argv) > 1 else "A1.mp4"
    result = detect_scenes(video_file, output_dir="tmp_scenes")
    print(json.dumps(result, indent=2))
