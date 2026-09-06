// StudioMotion • Universal Video Template Studio App
let currentTemplateId = null;
let currentTemplateData = null;
let activeSceneId = null;
let currentFrameIdx = 0;
let previewDebounceTimer = null;
let selectedUploadFile = null;
let pollStatusInterval = null;

// DOM Elements
const templateSelect = document.getElementById("templateSelect");
const templateTitle = document.getElementById("templateTitle");
const templateSubtitle = document.getElementById("templateSubtitle");
const scenesTabs = document.getElementById("scenesTabs");
const fieldsContainer = document.getElementById("fieldsContainer");
const previewImage = document.getElementById("previewImage");
const previewLoader = document.getElementById("previewLoader");
const previewMeta = document.getElementById("previewMeta");
const frameView = document.getElementById("frameView");
const videoView = document.getElementById("videoView");
const videoPlayer = document.getElementById("videoPlayer");
const videoSource = document.getElementById("videoSource");
const timelineScrubber = document.getElementById("timelineScrubber");
const timeCurrent = document.getElementById("timeCurrent");
const timeTotal = document.getElementById("timeTotal");
const btnModePreview = document.getElementById("btnModePreview");
const btnModeVideo = document.getElementById("btnModeVideo");
const btnSave = document.getElementById("btnSave");
const btnRender = document.getElementById("btnRender");
const btnDownload = document.getElementById("btnDownload");
const toast = document.getElementById("toast");

// Modal Elements
const uploadModal = document.getElementById("uploadModal");
const btnUploadModal = document.getElementById("btnUploadModal");
const btnCloseUploadModal = document.getElementById("btnCloseUploadModal");
const btnCancelUpload = document.getElementById("btnCancelUpload");
const btnStartUpload = document.getElementById("btnStartUpload");
const dropzone = document.getElementById("dropzone");
const videoFileInput = document.getElementById("videoFileInput");
const pipelineProgress = document.getElementById("pipelineProgress");
const progressFill = document.getElementById("progressFill");
const progressStepText = document.getElementById("progressStepText");
const progressPercent = document.getElementById("progressPercent");

// -------------------------------------------------------------
// Initialization
// -------------------------------------------------------------
async function init() {
  bindEvents();
  await loadTemplatesList();
}

function bindEvents() {
  templateSelect.addEventListener("change", (e) => {
    if (e.target.value) {
      loadTemplate(e.target.value);
    }
  });

  btnModePreview.addEventListener("click", () => setPreviewMode("frame"));
  btnModeVideo.addEventListener("click", () => setPreviewMode("video"));

  timelineScrubber.addEventListener("input", (e) => {
    currentFrameIdx = parseInt(e.target.value, 10);
    updateTimelineLabel();
    triggerLivePreview(true);
  });

  btnSave.addEventListener("click", saveTemplateChanges);
  btnRender.addEventListener("click", triggerRender);

  // Modal events
  btnUploadModal.addEventListener("click", () => {
    resetUploadModal();
    uploadModal.classList.remove("hidden");
  });

  const closeModal = () => uploadModal.classList.add("hidden");
  btnCloseUploadModal.addEventListener("click", closeModal);
  btnCancelUpload.addEventListener("click", closeModal);

  // Drag & drop
  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  });
  dropzone.addEventListener("dragleave", () => dropzone.classList.remove("dragover"));
  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  videoFileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });

  btnStartUpload.addEventListener("click", startUploadAndProcessing);
}

// -------------------------------------------------------------
// Template Loading & Rendering
// -------------------------------------------------------------
async function loadTemplatesList() {
  try {
    const res = await fetch("/api/templates");
    const templates = await res.json();
    templateSelect.innerHTML = "";

    if (templates.length === 0) {
      templateSelect.innerHTML = "<option value=''>No templates found</option>";
      return;
    }

    templates.forEach((t) => {
      const opt = document.createElement("option");
      opt.value = t.id;
      opt.textContent = `${t.title} (${t.total_scenes} scenes)`;
      templateSelect.appendChild(opt);
    });

    // Default select wedding_invitation if available, else first
    const defaultTpl = templates.find((t) => t.id === "wedding_invitation") || templates[0];
    templateSelect.value = defaultTpl.id;
    await loadTemplate(defaultTpl.id);
  } catch (err) {
    showToast("Error loading templates: " + err.message);
  }
}

async function loadTemplate(templateId) {
  try {
    showLoader(true);
    currentTemplateId = templateId;
    const res = await fetch(`/api/templates/${templateId}`);
    if (!res.ok) throw new Error("Could not load template");
    currentTemplateData = await res.json();

    templateTitle.textContent = currentTemplateData.title || templateId;
    const v = currentTemplateData.video_info || {};
    templateSubtitle.textContent = `${currentTemplateData.scenes.length} Scenes • ${v.duration_sec || 0}s • ${v.width || 1080}x${v.height || 1920}`;

    // Setup timeline scrubber
    timelineScrubber.max = v.total_frames ? v.total_frames - 1 : 1500;
    timelineScrubber.value = 0;
    currentFrameIdx = 0;
    timeTotal.textContent = formatTime(v.duration_sec || 0);
    updateTimelineLabel();

    // Setup download button
    btnDownload.href = `/api/templates/${templateId}/download`;

    // Render scenes tabs
    renderScenesTabs();

    // Pick first scene by default
    if (currentTemplateData.scenes && currentTemplateData.scenes.length > 0) {
      selectScene(currentTemplateData.scenes[0].scene_id);
    }

    // Update video source
    videoSource.src = `/api/templates/${templateId}/video?t=${Date.now()}`;
    videoPlayer.load();

    showLoader(false);
  } catch (err) {
    showLoader(false);
    showToast("Error: " + err.message);
  }
}

function renderScenesTabs() {
  scenesTabs.innerHTML = "";
  if (!currentTemplateData || !currentTemplateData.scenes) return;

  currentTemplateData.scenes.forEach((sc, idx) => {
    const tab = document.createElement("div");
    tab.className = `scene-tab ${sc.scene_id === activeSceneId ? "active" : ""}`;
    tab.dataset.sceneId = sc.scene_id;

    const count = sc.fields ? sc.fields.length : 0;
    tab.innerHTML = `
      <div class="tab-title">${sc.name || "Scene " + (idx + 1)}</div>
      <div class="tab-time">${count} text field${count === 1 ? "" : "s"}</div>
    `;

    tab.addEventListener("click", () => selectScene(sc.scene_id));
    scenesTabs.appendChild(tab);
  });
}

function selectScene(sceneId) {
  activeSceneId = sceneId;
  const scene = currentTemplateData.scenes.find((s) => s.scene_id === sceneId);
  if (!scene) return;

  // Update tabs active state
  document.querySelectorAll(".scene-tab").forEach((el) => {
    el.classList.toggle("active", el.dataset.sceneId === sceneId);
  });

  // Jump scrubber to scene preview frame
  currentFrameIdx = scene.preview_frame || scene.start_frame;
  timelineScrubber.value = currentFrameIdx;
  updateTimelineLabel();

  // Render form fields
  renderFields(scene);

  // Trigger live preview
  triggerLivePreview(true);
}

function renderFields(scene) {
  fieldsContainer.innerHTML = "";
  const fields = scene.fields || [];

  if (fields.length === 0) {
    fieldsContainer.innerHTML = `
      <div class="empty-state">
        <p>No text fields detected in this scene.</p>
      </div>
    `;
    return;
  }

  fields.forEach((f) => {
    const card = document.createElement("div");
    card.className = "field-card";

    const isMultiline = (f.value || "").length > 40;
    const inputHtml = isMultiline
      ? `<textarea class="field-input" rows="2">${escapeHtml(f.value || "")}</textarea>`
      : `<input type="text" class="field-input" value="${escapeHtml(f.value || "")}">`;

    card.innerHTML = `
      <div class="field-header">
        <span class="field-label">${f.label || f.id}</span>
        <span class="field-tag">${f.type || "text"}</span>
      </div>
      ${inputHtml}
      <div class="field-controls">
        <div class="color-picker-wrap">
          <input type="color" value="${f.color || "#ffffff"}">
          <span>${f.color || "#ffffff"}</span>
        </div>
        <div class="size-picker-wrap">
          <label>Size:</label>
          <input type="range" class="size-slider" min="18" max="180" value="${f.font_size || 36}">
          <span class="size-val">${f.font_size || 36}px</span>
        </div>
      </div>
    `;

    // Bind inputs
    const inputEl = card.querySelector(".field-input");
    const colorInput = card.querySelector("input[type='color']");
    const colorHex = card.querySelector(".color-picker-wrap span");
    const sizeSlider = card.querySelector(".size-slider");
    const sizeVal = card.querySelector(".size-val");

    inputEl.addEventListener("input", (e) => {
      f.value = e.target.value;
      debouncedPreview();
    });

    colorInput.addEventListener("input", (e) => {
      f.color = e.target.value;
      colorHex.textContent = e.target.value;
      debouncedPreview();
    });

    sizeSlider.addEventListener("input", (e) => {
      f.font_size = parseInt(e.target.value, 10);
      sizeVal.textContent = `${f.font_size}px`;
      debouncedPreview();
    });

    fieldsContainer.appendChild(card);
  });
}

// -------------------------------------------------------------
// Live Preview & Timeline
// -------------------------------------------------------------
function debouncedPreview() {
  if (previewDebounceTimer) clearTimeout(previewDebounceTimer);
  previewDebounceTimer = setTimeout(() => {
    triggerLivePreview(false);
  }, 250);
}

function triggerLivePreview(immediate = false) {
  if (!currentTemplateId) return;

  previewLoader.classList.add("active");
  const timestamp = Date.now();
  const url = `/api/templates/${currentTemplateId}/preview?frame=${currentFrameIdx}&scene_id=${activeSceneId}&_cb=${timestamp}`;

  const img = new Image();
  img.onload = () => {
    previewImage.src = url;
    previewLoader.classList.remove("active");
    previewMeta.textContent = `Frame ${currentFrameIdx} • ${formatTime(currentFrameIdx / 30.0)}`;
  };
  img.onerror = () => {
    previewLoader.classList.remove("active");
  };
  img.src = url;
}

function setPreviewMode(mode) {
  if (mode === "frame") {
    btnModePreview.classList.add("active");
    btnModeVideo.classList.remove("active");
    frameView.classList.remove("hidden");
    videoView.classList.add("hidden");
    videoPlayer.pause();
  } else {
    btnModeVideo.classList.add("active");
    btnModePreview.classList.remove("active");
    frameView.classList.add("hidden");
    videoView.classList.remove("hidden");
    videoPlayer.play();
  }
}

function updateTimelineLabel() {
  const fps = currentTemplateData?.video_info?.fps || 30.0;
  timeCurrent.textContent = formatTime(currentFrameIdx / fps);
}

function formatTime(sec) {
  const m = Math.floor(sec / 60);
  const s = Math.floor(sec % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function showLoader(show) {
  previewLoader.classList.toggle("active", show);
}

function showToast(msg) {
  toast.textContent = msg;
  toast.classList.remove("hidden");
  setTimeout(() => toast.classList.add("hidden"), 3500);
}

// -------------------------------------------------------------
// Save & Render Operations
// -------------------------------------------------------------
async function saveTemplateChanges() {
  if (!currentTemplateId || !currentTemplateData) return;
  try {
    btnSave.disabled = true;
    btnSave.textContent = "Saving...";

    const res = await fetch(`/api/templates/${currentTemplateId}/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentTemplateData)
    });

    const data = await res.json();
    btnSave.disabled = false;
    btnSave.innerHTML = `
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
      Save
    `;
    showToast("Template changes saved successfully!");
  } catch (err) {
    btnSave.disabled = false;
    btnSave.textContent = "Save";
    showToast("Save failed: " + err.message);
  }
}

async function triggerRender() {
  if (!currentTemplateId || !currentTemplateData) return;
  try {
    btnRender.disabled = true;
    btnRender.textContent = "Rendering Video...";
    showToast("Video render job launched across parallel cores!");

    await fetch(`/api/templates/${currentTemplateId}/render`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentTemplateData)
    });

    // Poll for completion
    const pollInterval = setInterval(async () => {
      try {
        const res = await fetch(`/api/templates/${currentTemplateId}/status`);
        const data = await res.json();
        const renderJob = data.render;

        if (renderJob.status === "done") {
          clearInterval(pollInterval);
          btnRender.disabled = false;
          btnRender.innerHTML = `
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            Export Final Video
          `;
          showToast("Video rendered successfully!");
          // Switch to video view and reload video source
          setPreviewMode("video");
          videoSource.src = `/api/templates/${currentTemplateId}/video?t=${Date.now()}`;
          videoPlayer.load();
          videoPlayer.play();
        } else if (renderJob.status === "error") {
          clearInterval(pollInterval);
          btnRender.disabled = false;
          btnRender.textContent = "Export Final Video";
          showToast("Render error: " + renderJob.error);
        }
      } catch (e) {
        // ignore network glitches during poll
      }
    }, 1500);
  } catch (err) {
    btnRender.disabled = false;
    btnRender.textContent = "Export Final Video";
    showToast("Error starting render: " + err.message);
  }
}

// -------------------------------------------------------------
// Modal: Video Upload & Pipeline Tracking
// -------------------------------------------------------------
function resetUploadModal() {
  selectedUploadFile = null;
  videoFileInput.value = "";
  btnStartUpload.disabled = true;
  pipelineProgress.classList.add("hidden");
  dropzone.classList.remove("hidden");
  progressFill.style.width = "0%";
  progressPercent.textContent = "0%";
  progressStepText.textContent = "Initializing video analyzer...";
  resetStepChecklist();
}

function handleFileSelected(file) {
  selectedUploadFile = file;
  btnStartUpload.disabled = false;
  dropzone.querySelector("h4").textContent = `Selected: ${file.name} (${(file.size / (1024 * 1024)).toFixed(1)} MB)`;
}

function resetStepChecklist() {
  ["step1", "step2", "step3", "step4"].forEach((id) => {
    const el = document.getElementById(id);
    el.className = "step-item";
  });
}

function updateStepStatus(progress) {
  const s1 = document.getElementById("step1");
  const s2 = document.getElementById("step2");
  const s3 = document.getElementById("step3");
  const s4 = document.getElementById("step4");

  if (progress >= 15) {
    s1.className = "step-item done";
    s2.className = "step-item active";
  }
  if (progress >= 45) {
    s2.className = "step-item done";
    s3.className = "step-item active";
  }
  if (progress >= 85) {
    s3.className = "step-item done";
    s4.className = "step-item active";
  }
  if (progress >= 100) {
    s4.className = "step-item done";
  }
}

async function startUploadAndProcessing() {
  if (!selectedUploadFile) return;

  try {
    btnStartUpload.disabled = true;
    dropzone.classList.add("hidden");
    pipelineProgress.classList.remove("hidden");

    const formData = new FormData();
    formData.append("video", selectedUploadFile);

    progressStepText.textContent = "Uploading video...";
    progressFill.style.width = "10%";
    progressPercent.textContent = "10%";

    const res = await fetch("/api/templates/upload", {
      method: "POST",
      body: formData
    });

    if (!res.ok) throw new Error("Upload failed");
    const data = await res.json();
    const newTemplateId = data.template_id;

    // Start polling pipeline status
    pollStatusInterval = setInterval(async () => {
      try {
        const sRes = await fetch(`/api/templates/${newTemplateId}/status`);
        const sData = await sRes.json();
        const pJob = sData.pipeline;

        if (pJob) {
          const pct = pJob.progress || 0;
          progressFill.style.width = `${pct}%`;
          progressPercent.textContent = `${pct}%`;
          progressStepText.textContent = pJob.step || "Processing...";
          updateStepStatus(pct);

          if (pJob.status === "ready") {
            clearInterval(pollStatusInterval);
            showToast("Template generated successfully!");
            setTimeout(async () => {
              uploadModal.classList.add("hidden");
              await loadTemplatesList();
              templateSelect.value = newTemplateId;
              await loadTemplate(newTemplateId);
            }, 1000);
          } else if (pJob.status === "error") {
            clearInterval(pollStatusInterval);
            progressStepText.textContent = "Error: " + (pJob.error || "Processing failed");
            progressFill.style.backgroundColor = "var(--crimson)";
            showToast("Template generation error: " + pJob.error);
          }
        }
      } catch (e) {
        // ignore poll errors
      }
    }, 1500);
  } catch (err) {
    progressStepText.textContent = "Upload failed: " + err.message;
    showToast("Upload failed: " + err.message);
  }
}

// Start app
window.addEventListener("DOMContentLoaded", init);
