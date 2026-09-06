import os
import sys
import json
import time
import shutil
import threading
import subprocess
import cv2
import numpy as np
from flask import Flask, request, jsonify, send_file, Response, send_from_directory
from werkzeug.utils import secure_filename

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from pipeline.scene_detector import detect_scenes
from pipeline.template_generator import generate_template
from pipeline.auto_inpaint import generate_clean_video
from pipeline.universal_renderer import render_frame_with_template, render_template_video

app = Flask(__name__, static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB upload limit

TEMPLATES_DIR = os.path.join(SCRIPT_DIR, "templates")
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# In-memory job state tracking
JOBS = {}
JOBS_LOCK = threading.Lock()

def update_job(job_id, status, step="Ready", progress=0, error=None):
    with JOBS_LOCK:
        JOBS[job_id] = {
            "status": status,
            "step": step,
            "progress": progress,
            "error": error,
            "updated_at": time.time()
        }

def get_job(job_id):
    with JOBS_LOCK:
        return JOBS.get(job_id, {"status": "idle", "step": "Idle", "progress": 0})

def background_pipeline_worker(template_id, source_video_path, template_dir):
    try:
        update_job(template_id, "processing", "Detecting scenes & extracting keyframes...", 15)
        
        # 1. Generate template schema (scenes + OCR)
        template_data = generate_template(source_video_path, template_dir, template_name=f"Custom Template ({template_id})")
        template_json_path = os.path.join(template_dir, "template.json")
        
        update_job(template_id, "processing", "Erasing original text (Inpainting background plate)...", 50)
        
        # 2. Inpaint clean background video
        clean_base_path = os.path.join(template_dir, "clean_base.mp4")
        generate_clean_video(source_video_path, template_json_path, clean_base_path)
        
        update_job(template_id, "processing", "Finalizing template assets & preview...", 90)
        
        # Update template.json to point to clean_base.mp4
        template_data["clean_video"] = "clean_base.mp4"
        with open(template_json_path, "w", encoding="utf-8") as f:
            json.dump(template_data, f, indent=2, ensure_ascii=False)
            
        update_job(template_id, "ready", "Template ready for editing!", 100)
    except Exception as e:
        import traceback
        traceback.print_exc()
        update_job(template_id, "error", "Failed to process video", 0, error=str(e))

def background_render_worker(template_id, template_dir):
    try:
        update_job(f"render_{template_id}", "rendering", "Starting video rendering...", 10)
        clean_video_path = os.path.join(template_dir, "clean_base.mp4")
        template_json_path = os.path.join(template_dir, "template.json")
        output_video_path = os.path.join(template_dir, "output.mp4")
        
        update_job(f"render_{template_id}", "rendering", "Rendering frames across CPU cores...", 40)
        render_template_video(clean_video_path, template_json_path, output_video_path)
        
        update_job(f"render_{template_id}", "done", "Render completed successfully!", 100)
    except Exception as e:
        import traceback
        traceback.print_exc()
        update_job(f"render_{template_id}", "error", "Rendering failed", 0, error=str(e))

# -------------------------------------------------------------
# Frontend Routes
# -------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)

# -------------------------------------------------------------
# API Endpoints
# -------------------------------------------------------------
@app.route("/api/templates", methods=["GET"])
def list_templates():
    templates = []
    if os.path.exists(TEMPLATES_DIR):
        for entry in os.scandir(TEMPLATES_DIR):
            if entry.is_dir():
                t_json_path = os.path.join(entry.path, "template.json")
                clean_mp4 = os.path.join(entry.path, "clean_base.mp4")
                out_mp4 = os.path.join(entry.path, "output.mp4")
                
                if os.path.exists(t_json_path):
                    try:
                        with open(t_json_path, "r", encoding="utf-8") as f:
                            t_data = json.load(f)
                            
                        first_preview = None
                        if t_data.get("scenes"):
                            for sc in t_data["scenes"]:
                                if sc.get("preview_path") and os.path.exists(os.path.join(entry.path, sc["preview_path"])):
                                    first_preview = f"/api/templates/{entry.name}/thumbnail"
                                    break
                                    
                        templates.append({
                            "id": entry.name,
                            "title": t_data.get("title", entry.name),
                            "description": t_data.get("description", ""),
                            "total_scenes": len(t_data.get("scenes", [])),
                            "total_fields": t_data.get("total_fields", 0),
                            "has_clean_base": os.path.exists(clean_mp4),
                            "has_output": os.path.exists(out_mp4),
                            "thumbnail": first_preview
                        })
                    except Exception:
                        pass
    return jsonify(templates)

@app.route("/api/templates/upload", methods=["POST"])
def upload_video():
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400
        
    file = request.files["video"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400
        
    filename = secure_filename(file.filename)
    base_name = os.path.splitext(filename)[0]
    template_id = f"{base_name}_{int(time.time())}"
    template_dir = os.path.join(TEMPLATES_DIR, template_id)
    os.makedirs(template_dir, exist_ok=True)
    
    source_path = os.path.join(template_dir, "source.mp4")
    file.save(source_path)
    
    # Start pipeline in background
    update_job(template_id, "processing", "Initializing video analysis...", 5)
    t = threading.Thread(target=background_pipeline_worker, args=(template_id, source_path, template_dir))
    t.daemon = True
    t.start()
    
    return jsonify({
        "status": "started",
        "template_id": template_id,
        "message": "Video uploaded, automated template generation started"
    })

@app.route("/api/templates/<template_id>/status", methods=["GET"])
def get_template_status(template_id):
    job = get_job(template_id)
    # Check render status as well
    render_job = get_job(f"render_{template_id}")
    return jsonify({
        "pipeline": job,
        "render": render_job
    })

@app.route("/api/templates/<template_id>", methods=["GET"])
def get_template(template_id):
    t_path = os.path.join(TEMPLATES_DIR, template_id, "template.json")
    if not os.path.exists(t_path):
        return jsonify({"error": "Template not found"}), 404
        
    with open(t_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return jsonify(data)

@app.route("/api/templates/<template_id>/save", methods=["POST"])
def save_template(template_id):
    t_path = os.path.join(TEMPLATES_DIR, template_id, "template.json")
    if not os.path.exists(t_path):
        return jsonify({"error": "Template not found"}), 404
        
    new_data = request.json
    with open(t_path, "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)
        
    return jsonify({"status": "saved", "message": "Template changes saved"})

@app.route("/api/templates/<template_id>/preview", methods=["GET"])
def preview_frame(template_id):
    template_dir = os.path.join(TEMPLATES_DIR, template_id)
    t_path = os.path.join(template_dir, "template.json")
    if not os.path.exists(t_path):
        return jsonify({"error": "Template not found"}), 404
        
    with open(t_path, "r", encoding="utf-8") as f:
        template = json.load(f)
        
    clean_video_path = os.path.join(template_dir, "clean_base.mp4")
    if not os.path.exists(clean_video_path):
        clean_video_path = os.path.join(template_dir, "source.mp4")
        
    frame_idx = request.args.get("frame", type=int)
    scene_id = request.args.get("scene_id")
    
    if frame_idx is None:
        if scene_id:
            for sc in template.get("scenes", []):
                if sc["scene_id"] == scene_id:
                    frame_idx = sc.get("preview_frame", sc["start_frame"])
                    break
        if frame_idx is None:
            frame_idx = 0
            
    cap = cv2.VideoCapture(clean_video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()
    
    if not ret or frame is None:
        # Generate dummy placeholder
        frame = np.zeros((1920, 1080, 3), dtype=np.uint8)
        
    w = int(template.get("video_info", {}).get("width", 1080))
    h = int(template.get("video_info", {}).get("height", 1920))
    
    rendered = render_frame_with_template(frame, frame_idx, template.get("scenes", []), w, h)
    
    _, buffer = cv2.imencode(".jpg", rendered, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return Response(buffer.tobytes(), mimetype="image/jpeg", headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.route("/api/templates/<template_id>/thumbnail", methods=["GET"])
def get_thumbnail(template_id):
    template_dir = os.path.join(TEMPLATES_DIR, template_id)
    t_path = os.path.join(template_dir, "template.json")
    if os.path.exists(t_path):
        with open(t_path, "r", encoding="utf-8") as f:
            template = json.load(f)
        for sc in template.get("scenes", []):
            p_rel = sc.get("preview_path")
            if p_rel:
                abs_p = os.path.join(template_dir, p_rel) if not os.path.isabs(p_rel) else p_rel
                if os.path.exists(abs_p):
                    return send_file(abs_p, mimetype="image/jpeg")
    return Response(b"", status=404)

@app.route("/api/templates/<template_id>/render", methods=["POST"])
def trigger_render(template_id):
    template_dir = os.path.join(TEMPLATES_DIR, template_id)
    t_path = os.path.join(template_dir, "template.json")
    if not os.path.exists(t_path):
        return jsonify({"error": "Template not found"}), 404
        
    # If client passed updated json in request body, save it first
    if request.is_json and request.json:
        with open(t_path, "w", encoding="utf-8") as f:
            json.dump(request.json, f, indent=2, ensure_ascii=False)
            
    t = threading.Thread(target=background_render_worker, args=(template_id, template_dir))
    t.daemon = True
    t.start()
    
    return jsonify({
        "status": "rendering",
        "message": "Render job started in background across parallel cores"
    })

@app.route("/api/templates/<template_id>/video", methods=["GET"])
def stream_video(template_id):
    template_dir = os.path.join(TEMPLATES_DIR, template_id)
    out_video = os.path.join(template_dir, "output.mp4")
    if not os.path.exists(out_video):
        clean_video = os.path.join(template_dir, "clean_base.mp4")
        if os.path.exists(clean_video):
            return send_file(clean_video, mimetype="video/mp4")
        return jsonify({"error": "Video not rendered yet"}), 404
    return send_file(out_video, mimetype="video/mp4")

@app.route("/api/templates/<template_id>/download", methods=["GET"])
def download_video(template_id):
    template_dir = os.path.join(TEMPLATES_DIR, template_id)
    out_video = os.path.join(template_dir, "output.mp4")
    if not os.path.exists(out_video):
        return jsonify({"error": "Video not rendered yet"}), 404
    return send_file(out_video, as_attachment=True, download_name=f"{template_id}_customized.mp4")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"[*] Starting Universal Video Template Studio at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
