#!/usr/bin/env python3
"""
Wedding Invitation Video Web Studio
Provides a local web interface to customize text, preview scenes, and render final video.
"""

import os
import sys
import json
import time
import shutil
import threading
import subprocess
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import cv2
import numpy as np
from PIL import Image

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, 'video_text.json')
CLEAN_VIDEO = os.path.join(SCRIPT_DIR, 'clean_base.mp4')
OUTPUT_VIDEO = os.path.join(SCRIPT_DIR, 'custom_invitation.mp4')

# Import rendering functions from render_video
sys.path.insert(0, SCRIPT_DIR)
from render_video import load_fonts, render_frame_text

# Global fonts cache & state
FONTS = None
RENDER_STATE = {
    'rendering': False,
    'progress': 0,
    'message': 'Ready',
    'last_render_time': None,
    'error': None
}

SCENE_FRAMES = {
    '2': 200,   # Monogram
    '3': 360,   # Announcement
    '4': 680,   # Main Invitation
    '5': 850,   # Haldi
    '6': 1020,  # Mehendi
    '7': 1170,  # Sangeet
    '8': 1340,  # Mandha Ceremony
    '9': 1534,  # Wedding Ceremony
    '10': 1694  # Save the Date + RSVP
}

def get_fonts():
    global FONTS
    if FONTS is None:
        FONTS = load_fonts()
    return FONTS

def render_single_scene_frame(scene_num, config):
    frame_idx = SCENE_FRAMES.get(str(scene_num), 360)
    cap = cv2.VideoCapture(CLEAN_VIDEO)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError(f"Could not read frame {frame_idx}")

    fonts = get_fonts()
    
    # Pre-render shloka if needed for Scene 4
    shloka_img = None
    shloka_png = os.path.join(SCRIPT_DIR, 'tmp_render', 'shloka.png')
    if os.path.exists(shloka_png):
        try:
            shloka_img = Image.open(shloka_png).convert('RGBA')
        except Exception:
            shloka_img = None

    rendered = render_frame_text(frame, frame_idx, config, fonts, shloka_img=shloka_img)
    ret, jpeg = cv2.imencode('.jpg', rendered, [cv2.IMWRITE_JPEG_QUALITY, 92])
    return jpeg.tobytes()

def background_render_worker(config_data):
    global RENDER_STATE
    try:
        RENDER_STATE['rendering'] = True
        RENDER_STATE['progress'] = 5
        RENDER_STATE['message'] = 'Preparing fonts and assets...'
        RENDER_STATE['error'] = None

        # Save config
        with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)

        # Pre-render shloka
        shloka_text = config_data.get('scene_4_invitation', {}).get('shloka', '')
        render_bin = os.path.join(SCRIPT_DIR, 'bin', 'render_text')
        os.makedirs(os.path.join(SCRIPT_DIR, 'tmp_render'), exist_ok=True)
        if os.path.exists(render_bin) and shloka_text:
            subprocess.run([
                render_bin, shloka_text, 'Rozha One', '42', '214,123,39',
                os.path.join(SCRIPT_DIR, 'tmp_render', 'shloka.png')
            ], check=True)

        RENDER_STATE['progress'] = 20
        RENDER_STATE['message'] = 'Rendering video frames in parallel...'
        
        cmd = [
            os.path.join(SCRIPT_DIR, '.venv', 'bin', 'python'),
            os.path.join(SCRIPT_DIR, 'render_video.py'),
            '--config', CONFIG_PATH,
            '--output', OUTPUT_VIDEO
        ]

        t0 = time.time()
        proc = subprocess.run(cmd, cwd=SCRIPT_DIR, capture_output=True, text=True)
        elapsed = round(time.time() - t0, 1)

        if proc.returncode != 0:
            RENDER_STATE['error'] = proc.stderr
            RENDER_STATE['message'] = 'Render failed'
        else:
            RENDER_STATE['progress'] = 100
            RENDER_STATE['last_render_time'] = elapsed
            RENDER_STATE['message'] = f'Successfully rendered in {elapsed}s!'
    except Exception as e:
        RENDER_STATE['error'] = str(e)
        RENDER_STATE['message'] = f'Error: {e}'
    finally:
        RENDER_STATE['rendering'] = False

class StudioHandler(BaseHTTPRequestHandler):
    def end_headers_with_cors(self, content_type='application/json'):
        self.send_header('Content-Type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers_with_cors()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == '/' or path == '/index.html':
            html_path = os.path.join(SCRIPT_DIR, 'index.html')
            if os.path.exists(html_path):
                with open(html_path, 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.end_headers_with_cors('text/html; charset=utf-8')
                self.wfile.write(content)
            else:
                self.send_error(404, "index.html not found")

        elif path == '/api/config':
            if os.path.exists(CONFIG_PATH):
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.send_response(200)
                self.end_headers_with_cors('application/json')
                self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))
            else:
                self.send_error(404, "Config not found")

        elif path == '/api/status':
            self.send_response(200)
            self.end_headers_with_cors('application/json')
            payload = {
                **RENDER_STATE,
                'video_ready': os.path.exists(OUTPUT_VIDEO),
                'video_size_mb': round(os.path.getsize(OUTPUT_VIDEO) / (1024*1024), 2) if os.path.exists(OUTPUT_VIDEO) else 0
            }
            self.wfile.write(json.dumps(payload).encode('utf-8'))

        elif path == '/api/preview':
            scene = query.get('scene', ['3'])[0]
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                jpeg_bytes = render_single_scene_frame(scene, config)
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(jpeg_bytes)
            except Exception as e:
                self.send_error(500, f"Preview failed: {e}")

        elif path.startswith('/video/'):
            video_file = os.path.join(SCRIPT_DIR, path.replace('/video/', ''))
            self.serve_video_file(video_file)

        else:
            self.send_error(404, "Not Found")

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)

        if path == '/api/save':
            try:
                data = json.loads(body.decode('utf-8'))
                with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                # Update shloka image if changed
                shloka_text = data.get('scene_4_invitation', {}).get('shloka', '')
                render_bin = os.path.join(SCRIPT_DIR, 'bin', 'render_text')
                if os.path.exists(render_bin) and shloka_text:
                    os.makedirs(os.path.join(SCRIPT_DIR, 'tmp_render'), exist_ok=True)
                    subprocess.run([
                        render_bin, shloka_text, 'Rozha One', '42', '214,123,39',
                        os.path.join(SCRIPT_DIR, 'tmp_render', 'shloka.png')
                    ], check=True)

                self.send_response(200)
                self.end_headers_with_cors('application/json')
                self.wfile.write(json.dumps({'status': 'saved'}).encode('utf-8'))
            except Exception as e:
                self.send_error(500, f"Save failed: {e}")

        elif path == '/api/preview_custom':
            try:
                data = json.loads(body.decode('utf-8'))
                scene = data.get('scene', '3')
                cfg = data.get('config', {})
                shloka_text = cfg.get('scene_4_invitation', {}).get('shloka', '')
                render_bin = os.path.join(SCRIPT_DIR, 'bin', 'render_text')
                if os.path.exists(render_bin) and shloka_text:
                    os.makedirs(os.path.join(SCRIPT_DIR, 'tmp_render'), exist_ok=True)
                    subprocess.run([
                        render_bin, shloka_text, 'Rozha One', '42', '214,123,39',
                        os.path.join(SCRIPT_DIR, 'tmp_render', 'shloka.png')
                    ], check=True)

                jpeg_bytes = render_single_scene_frame(scene, cfg)
                self.send_response(200)
                self.send_header('Content-Type', 'image/jpeg')
                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(jpeg_bytes)
            except Exception as e:
                self.send_error(500, f"Preview custom failed: {e}")

        elif path == '/api/render':
            if RENDER_STATE['rendering']:
                self.send_response(409)
                self.end_headers_with_cors('application/json')
                self.wfile.write(json.dumps({'status': 'busy', 'message': 'Render already in progress'}).encode('utf-8'))
                return

            try:
                data = json.loads(body.decode('utf-8')) if body else None
                if not data:
                    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                
                t = threading.Thread(target=background_render_worker, args=(data,))
                t.daemon = True
                t.start()

                self.send_response(202)
                self.end_headers_with_cors('application/json')
                self.wfile.write(json.dumps({'status': 'started'}).encode('utf-8'))
            except Exception as e:
                self.send_error(500, f"Render trigger failed: {e}")

        else:
            self.send_error(404, "Not Found")

    def serve_video_file(self, file_path):
        if not os.path.exists(file_path):
            self.send_error(404, "Video file not found")
            return

        file_size = os.path.getsize(file_path)
        range_header = self.headers.get('Range', None)

        if range_header:
            bytes_range = range_header.strip().split('=')[-1]
            parts = bytes_range.split('-')
            start = int(parts[0]) if parts[0] else 0
            end = int(parts[1]) if len(parts) > 1 and parts[1] else file_size - 1

            if start >= file_size:
                self.send_response(416, "Requested Range Not Satisfiable")
                self.send_header('Content-Range', f'bytes */{file_size}')
                self.end_headers()
                return

            length = (end - start) + 1
            self.send_response(206)
            self.send_header('Content-Type', 'video/mp4')
            self.send_header('Content-Range', f'bytes {start}-{end}/{file_size}')
            self.send_header('Content-Length', str(length))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            with open(file_path, 'rb') as f:
                f.seek(start)
                bytes_to_send = length
                chunk_size = 128 * 1024
                while bytes_to_send > 0:
                    current_chunk = min(bytes_to_send, chunk_size)
                    data = f.read(current_chunk)
                    if not data:
                        break
                    try:
                        self.wfile.write(data)
                    except (BrokenPipeError, ConnectionResetError):
                        break
                    bytes_to_send -= len(data)
        else:
            self.send_response(200)
            self.send_header('Content-Type', 'video/mp4')
            self.send_header('Content-Length', str(file_size))
            self.send_header('Accept-Ranges', 'bytes')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()

            with open(file_path, 'rb') as f:
                shutil.copyfileobj(f, self.wfile)

def run_server(port=8080):
    server = HTTPServer(('127.0.0.1', port), StudioHandler)
    print(f"=====================================================")
    print(f"  Wedding Invitation Web Studio running at:")
    print(f"  --> http://localhost:{port}")
    print(f"=====================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.server_close()

if __name__ == '__main__':
    port = 8080
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    run_server(port)
