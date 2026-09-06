import cv2
import numpy as np
import multiprocessing as mp
import time

def process_chunk(args):
    start_idx, count = args
    cap = cv2.VideoCapture('A1.mp4')
    cap.set(cv2.CAP_PROP_POS_FRAMES, start_idx)
    frames = []
    for _ in range(count):
        ret, frame = cap.read()
        if not ret:
            break
        # Quick dummy processing
        frames.append(frame[0, 0, 0])
    cap.release()
    return len(frames)

if __name__ == '__main__':
    t0 = time.time()
    with mp.Pool(8) as p:
        res = p.map(process_chunk, [(i * 200, 200) for i in range(8)])
    print('Read 1600 frames across 8 cores in:', time.time() - t0, 's')
