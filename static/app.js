// StudioMotion • Universal Video Template Studio (Production-Ready)
let allTemplates = [];
let currentTemplateId = null;
let currentTemplateData = null;
let activeSceneId = null;
let currentFrameIdx = 0;
let previewDebounceTimer = null;
let selectedFile = null;
let pipelinePollInterval = null;
let renderPollInterval = null;
let pendingDeleteId = null;

// ============================================================
// DOM ELEMENTS
// ============================================================
// Views
const dashboardView = document.getElementById("dashboardView");
const editorView = document.getElementById("editorView");

// Header
const brandHome = document.getElementById("brandHome");
const headerBreadcrumb = document.getElementById("headerBreadcrumb");
const headerProjectName = document.getElementById("headerProjectName");
const btnBackToDashboard = document.getElementById("btnBackToDashboard");
const dashboardActions = document.getElementById("dashboardActions");
const editorActions = document.getElementById("editorActions");
const btnHeaderNewProject = document.getElementById("btnHeaderNewProject");

// Dashboard Elements
const dashboardDropzone = document.getElementById("dashboardDropzone");
const dashboardFileInput = document.getElementById("dashboardFileInput");
const fileSelectedIndicator = document.getElementById("fileSelectedIndicator");
const selectedFileName = document.getElementById("selectedFileName");
const selectedFileSize = document.getElementById("selectedFileSize");
const btnStartProcessing = document.getElementById("btnStartProcessing");
const templatesGrid = document.getElementById("templatesGrid");
const templatesCount = document.getElementById("templatesCount");
const emptyLibrary = document.getElementById("emptyLibrary");
const projectSearch = document.getElementById("projectSearch");

// Editor Elements
const templateTitle = document.getElementById("templateTitle");
const templateSubtitle = document.getElementById("templateSubtitle");
const scenesTabs = document.getElementById("scenesTabs");
const activeSceneTitle = document.getElementById("activeSceneTitle");
const fieldsContainer = document.getElementById("fieldsContainer");
const btnAddField = document.getElementById("btnAddField");
const btnSave = document.getElementById("btnSave");
const btnRender = document.getElementById("btnRender");
const btnDownload = document.getElementById("btnDownload");

// Preview Elements
const btnModePreview = document.getElementById("btnModePreview");
const btnModeVideo = document.getElementById("btnModeVideo");
const frameView = document.getElementById("frameView");
const videoView = document.getElementById("videoView");
const previewImage = document.getElementById("previewImage");
const overlayLayer = document.getElementById("overlayLayer");
const previewLoader = document.getElementById("previewLoader");
const previewMeta = document.getElementById("previewMeta");
const videoPlayer = document.getElementById("videoPlayer");
const videoSource = document.getElementById("videoSource");
const timelineScrubber = document.getElementById("timelineScrubber");
const timeCurrent = document.getElementById("timeCurrent");
const timeTotal = document.getElementById("timeTotal");

// Modals
const pipelineModal = document.getElementById("pipelineModal");
const progressFill = document.getElementById("progressFill");
const progressStepText = document.getElementById("progressStepText");
const progressPercent = document.getElementById("progressPercent");

const renderModal = document.getElementById("renderModal");
const btnCloseRenderModal = document.getElementById("btnCloseRenderModal");
const renderProgressWrap = document.getElementById("renderProgressWrap");
const renderDoneWrap = document.getElementById("renderDoneWrap");
const renderStepText = document.getElementById("renderStepText");
const btnPreviewRendered = document.getElementById("btnPreviewRendered");
const btnDownloadRendered = document.getElementById("btnDownloadRendered");

const deleteModal = document.getElementById("deleteModal");
const deleteTemplateName = document.getElementById("deleteTemplateName");
const btnCloseDeleteModal = document.getElementById("btnCloseDeleteModal");
const btnCancelDelete = document.getElementById("btnCancelDelete");
const btnConfirmDelete = document.getElementById("btnConfirmDelete");

const toast = document.getElementById("toast");

// ============================================================
// INITIALIZATION (NO FORCED DEFAULT VIDEO)
// ============================================================
document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  showDashboard();
  loadTemplates();
});

function bindEvents() {
  // Navigation
  brandHome.addEventListener("click", showDashboard);
  btnBackToDashboard.addEventListener("click", showDashboard);
  btnHeaderNewProject.addEventListener("click", () => {
    showDashboard();
    dashboardDropzone.scrollIntoView({ behavior: "smooth" });
  });

  // Search filter
  projectSearch.addEventListener("input", (e) => {
    filterTemplatesGrid(e.target.value);
  });

  // File Dropzone
  dashboardDropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dashboardDropzone.classList.add("dragover");
  });
  dashboardDropzone.addEventListener("dragleave", () => dashboardDropzone.classList.remove("dragover"));
  dashboardDropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dashboardDropzone.classList.remove("dragover");
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });
  dashboardFileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  });
  btnStartProcessing.addEventListener("click", startUploadAndPipeline);

  // Editor Actions
  btnSave.addEventListener("click", saveTemplate);
  btnRender.addEventListener("click", triggerRender);
  btnAddField.addEventListener("click", addNewCustomField);

  // Editable Title
  templateTitle.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      templateTitle.blur();
    }
  });
  templateTitle.addEventListener("blur", handleTitleRename);

  // View Mode
  btnModePreview.addEventListener("click", () => setPreviewMode("frame"));
  btnModeVideo.addEventListener("click", () => setPreviewMode("video"));

  // Timeline
  timelineScrubber.addEventListener("input", (e) => {
    currentFrameIdx = parseInt(e.target.value, 10);
    updateTimelineLabel();
    triggerLivePreviewDebounced();
  });

  // Render Modal
  btnCloseRenderModal.addEventListener("click", () => renderModal.classList.add("hidden"));
  btnPreviewRendered.addEventListener("click", () => {
    renderModal.classList.add("hidden");
    setPreviewMode("video");
    videoPlayer.play();
  });

  // Delete Modal
  const closeDel = () => deleteModal.classList.add("hidden");
  btnCloseDeleteModal.addEventListener("click", closeDel);
  btnCancelDelete.addEventListener("click", closeDel);
  btnConfirmDelete.addEventListener("click", confirmDeleteTemplate);
}

// ============================================================
// VIEW SWITCHING
// ============================================================
function showDashboard() {
  currentTemplateId = null;
  currentTemplateData = null;
  dashboardView.classList.remove("hidden");
  editorView.classList.add("hidden");
  headerBreadcrumb.classList.add("hidden");
  dashboardActions.classList.remove("hidden");
  editorActions.classList.add("hidden");
  loadTemplates();
}

function openEditor(templateId) {
  currentTemplateId = templateId;
  dashboardView.classList.add("hidden");
  editorView.classList.remove("hidden");
  headerBreadcrumb.classList.remove("hidden");
  dashboardActions.classList.add("hidden");
  editorActions.classList.remove("hidden");
  loadTemplateData(templateId);
}

// ============================================================
// TEMPLATES DASHBOARD
// ============================================================
async function loadTemplates() {
  try {
    const res = await fetch("/api/templates");
    if (!res.ok) throw new Error("Failed to load templates");
    allTemplates = await res.json();
    renderTemplatesGrid(allTemplates);
  } catch (err) {
    showToast("Error loading templates: " + err.message);
  }
}

function renderTemplatesGrid(templates) {
  templatesGrid.innerHTML = "";
  templatesCount.textContent = `${templates.length} project${templates.length === 1 ? "" : "s"}`;

  if (templates.length === 0) {
    emptyLibrary.classList.remove("hidden");
    return;
  }
  emptyLibrary.classList.add("hidden");

  templates.forEach((t) => {
    const card = document.createElement("div");
    card.className = "project-card";

    const thumbUrl = t.thumbnail ? `${t.thumbnail}?t=${t.updated_at || Date.now()}` : "";
    const durFormatted = formatTime(t.duration_sec || 0);

    card.innerHTML = `
      <div class="project-card-thumb-wrap">
        <img class="project-card-thumb" src="${thumbUrl}" alt="${escapeHtml(t.title)}" onerror="this.src='/static/placeholder.jpg'; this.onerror=null;">
        <div class="project-card-badges">
          <span class="meta-badge">${t.total_scenes} Scenes</span>
          <span class="meta-badge">${durFormatted}</span>
        </div>
      </div>
      <div class="project-card-body">
        <h3 class="project-card-title">${escapeHtml(t.title)}</h3>
        <div class="project-card-meta">
          <span>${t.total_fields} text fields</span>
          <span>•</span>
          <span>${t.resolution || "1080x1920"}</span>
        </div>
        <div class="project-card-actions">
          <button class="btn btn-primary btn-sm btn-open-project" data-id="${t.id}">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="5 3 19 12 5 21 5 3"/></svg>
            Open Studio
          </button>
          <button class="btn-card-delete" data-id="${t.id}" data-name="${escapeHtml(t.title)}" title="Delete project">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
          </button>
        </div>
      </div>
    `;

    card.querySelector(".btn-open-project").addEventListener("click", () => openEditor(t.id));
    card.querySelector(".btn-card-delete").addEventListener("click", (e) => {
      e.stopPropagation();
      openDeleteModal(t.id, t.title);
    });

    templatesGrid.appendChild(card);
  });
}

function filterTemplatesGrid(query) {
  const q = query.toLowerCase().trim();
  const filtered = allTemplates.filter((t) => (t.title || "").toLowerCase().includes(q));
  renderTemplatesGrid(filtered);
}

// ============================================================
// UPLOAD & INGESTION
// ============================================================
function handleFileSelected(file) {
  if (!file) return;
  selectedFile = file;
  selectedFileName.textContent = file.name;
  const sizeMb = (file.size / (1024 * 1024)).toFixed(1);
  selectedFileSize.textContent = `${sizeMb} MB`;
  fileSelectedIndicator.classList.remove("hidden");
}

async function startUploadAndPipeline() {
  if (!selectedFile) return;

  const formData = new FormData();
  formData.append("video", selectedFile);

  // Show pipeline modal
  pipelineModal.classList.remove("hidden");
  updatePipelineProgress(10, "Uploading video to studio...");
  updateStepChecklist(1);

  try {
    const res = await fetch("/api/templates/upload", {
      method: "POST",
      body: formData,
    });
    if (!res.ok) throw new Error("Upload failed");
    const data = await res.json();
    const templateId = data.template_id;

    pollPipelineStatus(templateId);
  } catch (err) {
    pipelineModal.classList.add("hidden");
    showToast("Upload error: " + err.message);
  }
}

function pollPipelineStatus(templateId) {
  clearInterval(pipelinePollInterval);
  pipelinePollInterval = setInterval(async () => {
    try {
      const res = await fetch(`/api/templates/${templateId}/status`);
      if (!res.ok) return;
      const statusData = await res.json();
      const p = statusData.pipeline || {};

      if (p.status === "processing") {
        updatePipelineProgress(p.progress || 35, p.step || "Analyzing video...");
        if (p.progress < 25) updateStepChecklist(1);
        else if (p.progress < 55) updateStepChecklist(2);
        else if (p.progress < 85) updateStepChecklist(3);
        else updateStepChecklist(4);
      } else if (p.status === "ready") {
        clearInterval(pipelinePollInterval);
        updatePipelineProgress(100, "Template ready!");
        updateStepChecklist(4, true);
        setTimeout(() => {
          pipelineModal.classList.add("hidden");
          // Automatically open the new template!
          openEditor(templateId);
        }, 800);
      } else if (p.status === "error") {
        clearInterval(pipelinePollInterval);
        pipelineModal.classList.add("hidden");
        showToast("Processing error: " + (p.error || "Failed to process video"));
      }
    } catch (e) {
      console.warn("Poll error:", e);
    }
  }, 1200);
}

function updatePipelineProgress(percent, stepText) {
  progressFill.style.width = `${percent}%`;
  progressPercent.textContent = `${percent}%`;
  progressStepText.textContent = stepText;
}

function updateStepChecklist(currentStepNum, allDone = false) {
  for (let i = 1; i <= 4; i++) {
    const item = document.getElementById(`step${i}`);
    if (!item) continue;
    if (allDone || i < currentStepNum) {
      item.className = "step-item done";
    } else if (i === currentStepNum) {
      item.className = "step-item active";
    } else {
      item.className = "step-item";
    }
  }
}

// ============================================================
// DELETE TEMPLATE
// ============================================================
function openDeleteModal(templateId, templateName) {
  pendingDeleteId = templateId;
  deleteTemplateName.textContent = `"${templateName}"`;
  deleteModal.classList.remove("hidden");
}

async function confirmDeleteTemplate() {
  if (!pendingDeleteId) return;
  try {
    const res = await fetch(`/api/templates/${pendingDeleteId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Delete failed");
    deleteModal.classList.add("hidden");
    showToast("Template deleted successfully");
    loadTemplates();
  } catch (err) {
    showToast("Error deleting: " + err.message);
  } finally {
    pendingDeleteId = null;
  }
}

// ============================================================
// STUDIO EDITOR WORKSPACE
// ============================================================
async function loadTemplateData(templateId) {
  try {
    showPreviewLoader(true);
    const res = await fetch(`/api/templates/${templateId}`);
    if (!res.ok) throw new Error("Could not load template schema");
    currentTemplateData = await res.json();

    headerProjectName.textContent = currentTemplateData.title || templateId;
    templateTitle.textContent = currentTemplateData.title || templateId;

    const v = currentTemplateData.video_info || {};
    templateSubtitle.textContent = `${currentTemplateData.scenes.length} Scenes • ${formatTime(v.duration_sec || 0)} • ${v.width || 1080}x${v.height || 1920}`;

    // Scrubber setup
    timelineScrubber.max = v.total_frames ? v.total_frames - 1 : 1500;
    timelineScrubber.value = 0;
    currentFrameIdx = 0;
    timeTotal.textContent = formatTime(v.duration_sec || 0);
    updateTimelineLabel();

    // Download button
    btnDownload.href = `/api/templates/${templateId}/download`;

    // Render scenes filmstrip
    renderScenesTabs();

    // Select first scene
    if (currentTemplateData.scenes && currentTemplateData.scenes.length > 0) {
      selectScene(currentTemplateData.scenes[0].scene_id);
    }

    // Video player source
    videoSource.src = `/api/templates/${templateId}/video?t=${Date.now()}`;
    videoPlayer.load();

    showPreviewLoader(false);
  } catch (err) {
    showToast("Error opening editor: " + err.message);
  }
}

async function handleTitleRename() {
  const newTitle = templateTitle.textContent.trim();
  if (!newTitle || !currentTemplateId) return;
  headerProjectName.textContent = newTitle;
  currentTemplateData.title = newTitle;

  try {
    await fetch(`/api/templates/${currentTemplateId}/rename`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: newTitle }),
    });
  } catch (e) {
    console.warn("Title rename error:", e);
  }
}

function renderScenesTabs() {
  scenesTabs.innerHTML = "";
  if (!currentTemplateData || !currentTemplateData.scenes) return;

  currentTemplateData.scenes.forEach((sc, idx) => {
    const tab = document.createElement("div");
    tab.className = `scene-tab ${sc.scene_id === activeSceneId ? "active" : ""}`;
    tab.innerHTML = `
      <span class="scene-tab-dot"></span>
      <span>Scene ${sc.scene_num}</span>
      <span class="text-secondary" style="font-size: 11px;">(${sc.fields ? sc.fields.length : 0})</span>
    `;
    tab.addEventListener("click", () => selectScene(sc.scene_id));
    scenesTabs.appendChild(tab);
  });
}

function selectScene(sceneId) {
  activeSceneId = sceneId;
  const sc = currentTemplateData.scenes.find((s) => s.scene_id === sceneId);
  if (!sc) return;

  currentFrameIdx = sc.preview_frame || sc.start_frame;
  timelineScrubber.value = currentFrameIdx;
  updateTimelineLabel();

  // Highlight tab
  document.querySelectorAll(".scene-tab").forEach((tab, i) => {
    const tabSc = currentTemplateData.scenes[i];
    tab.classList.toggle("active", tabSc && tabSc.scene_id === sceneId);
  });

  activeSceneTitle.textContent = `Scene ${sc.scene_num} Elements (${sc.fields ? sc.fields.length : 0})`;
  renderSceneFields(sc);
  triggerLivePreview(true);
}

function renderSceneFields(scene) {
  fieldsContainer.innerHTML = "";
  overlayLayer.innerHTML = "";

  if (!scene.fields || scene.fields.length === 0) {
    fieldsContainer.innerHTML = `
      <div style="text-align: center; padding: 40px 10px; color: var(--text-muted);">
        <p>No text elements in this scene.</p>
        <button class="btn btn-secondary btn-sm" style="margin-top: 10px;" onclick="addNewCustomField()">+ Add Text Element</button>
      </div>
    `;
    return;
  }

  scene.fields.forEach((field, fIdx) => {
    const card = document.createElement("div");
    card.className = "field-card";
    card.id = `card_${field.id}`;

    const roleClass = `role-${(field.type || "general").toLowerCase()}`;
    const roleName = (field.type || "text").replace("_", " ");

    card.innerHTML = `
      <div class="field-header">
        <span class="role-badge ${roleClass}">${roleName}</span>
        <button class="btn-field-delete" title="Delete text field" data-id="${field.id}">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
        </button>
      </div>

      <textarea class="field-input-text" rows="2" spellcheck="false">${escapeHtml(field.value || "")}</textarea>

      <div class="field-style-controls">
        <div class="control-group">
          <label class="control-label">Font Family</label>
          <select class="select-input font-select">
            <option value="RozhaOne-Regular.ttf" ${field.font === "RozhaOne-Regular.ttf" ? "selected" : ""}>Rozha One (Devanagari / Royal)</option>
            <option value="GreatVibes-Regular.ttf" ${field.font === "GreatVibes-Regular.ttf" ? "selected" : ""}>Great Vibes (Calligraphy)</option>
            <option value="Cinzel.ttf" ${field.font === "Cinzel.ttf" ? "selected" : ""}>Cinzel (Royal Serif)</option>
            <option value="Poppins" ${field.font === "Poppins" ? "selected" : ""}>Poppins (Clean Modern)</option>
            <option value="Georgia.ttf" ${field.font === "Georgia.ttf" ? "selected" : ""}>Georgia (Classic Serif)</option>
            <option value="NotoSansDevanagari" ${field.font === "NotoSansDevanagari" ? "selected" : ""}>Noto Sans Devanagari</option>
          </select>
        </div>

        <div class="control-group">
          <label class="control-label">Size: <span class="slider-val">${field.font_size || 36}px</span></label>
          <div class="slider-wrap">
            <input type="range" class="range-slider font-slider" min="14" max="110" value="${field.font_size || 36}">
          </div>
        </div>

        <div class="color-controls">
          <label class="control-label" style="margin-bottom:0;">Color</label>
          <div class="swatches-row">
            ${renderColorSwatches(field.color || "#ffffff")}
          </div>
          <input type="color" class="color-picker-input" value="${normalizeHex(field.color || "#ffffff")}">
        </div>
      </div>
    `;

    // Bind inputs
    const textarea = card.querySelector(".field-input-text");
    textarea.addEventListener("input", (e) => {
      field.value = e.target.value;
      triggerLivePreviewDebounced();
    });

    const fontSelect = card.querySelector(".font-select");
    fontSelect.addEventListener("change", (e) => {
      field.font = e.target.value;
      triggerLivePreview(true);
    });

    const fontSlider = card.querySelector(".font-slider");
    const sliderVal = card.querySelector(".slider-val");
    fontSlider.addEventListener("input", (e) => {
      field.font_size = parseInt(e.target.value, 10);
      sliderVal.textContent = `${field.font_size}px`;
      triggerLivePreviewDebounced();
    });

    const colorPicker = card.querySelector(".color-picker-input");
    colorPicker.addEventListener("input", (e) => {
      field.color = e.target.value;
      triggerLivePreviewDebounced();
    });

    // Swatches
    card.querySelectorAll(".swatch-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        field.color = btn.dataset.color;
        colorPicker.value = btn.dataset.color;
        card.querySelectorAll(".swatch-btn").forEach((b) => b.classList.toggle("active", b === btn));
        triggerLivePreview(true);
      });
    });

    // Delete field
    card.querySelector(".btn-field-delete").addEventListener("click", () => {
      deleteField(scene, field.id);
    });

    // Hover highlight correlation
    card.addEventListener("mouseenter", () => highlightBoxOnCanvas(field.id, true));
    card.addEventListener("mouseleave", () => highlightBoxOnCanvas(field.id, false));

    fieldsContainer.appendChild(card);

    // Create interactive box on canvas
    createBoxMarker(field, fIdx + 1);
  });
}

function renderColorSwatches(currentColor) {
  const presets = [
    { name: "Gold", hex: "#e6ca65" },
    { name: "Rose Gold", hex: "#e0a899" },
    { name: "White", hex: "#ffffff" },
    { name: "Ivory", hex: "#f7f3e9" },
    { name: "Royal Blue", hex: "#60a5fa" },
    { name: "Crimson", hex: "#ef4444" },
  ];
  return presets
    .map(
      (p) =>
        `<button class="swatch-btn ${p.hex.toLowerCase() === (currentColor || "").toLowerCase() ? "active" : ""}" 
          style="background: ${p.hex};" data-color="${p.hex}" title="${p.name}"></button>`
    )
    .join("");
}

function normalizeHex(hex) {
  if (!hex) return "#ffffff";
  if (hex.startsWith("#") && hex.length === 7) return hex;
  return "#ffffff";
}

function createBoxMarker(field, number) {
  const marker = document.createElement("div");
  marker.className = "box-marker";
  marker.id = `box_${field.id}`;

  const box = field.box;
  let top = "50%", left = "10%", width = "80%", height = "6%";

  if (box && box.length === 4) {
    left = `${(box[0] * 100).toFixed(1)}%`;
    top = `${(box[1] * 100).toFixed(1)}%`;
    width = `${(box[2] * 100).toFixed(1)}%`;
    height = `${(box[3] * 100).toFixed(1)}%`;
  } else if (field.y_percent !== undefined) {
    top = `${(field.y_percent - 3).toFixed(1)}%`;
    left = "10%";
    width = "80%";
    height = "6%";
  }

  marker.style.left = left;
  marker.style.top = top;
  marker.style.width = width;
  marker.style.height = height;

  marker.innerHTML = `<span class="box-marker-tag">${number}. ${escapeHtml(field.value.slice(0, 16))}</span>`;

  marker.addEventListener("click", () => {
    const card = document.getElementById(`card_${field.id}`);
    if (card) {
      card.scrollIntoView({ behavior: "smooth", block: "center" });
      card.classList.add("highlighted");
      setTimeout(() => card.classList.remove("highlighted"), 1500);
    }
  });

  overlayLayer.appendChild(marker);
}

function highlightBoxOnCanvas(fieldId, active) {
  const marker = document.getElementById(`box_${fieldId}`);
  if (marker) {
    marker.classList.toggle("active", active);
  }
}

function deleteField(scene, fieldId) {
  scene.fields = scene.fields.filter((f) => f.id !== fieldId);
  renderScenesTabs();
  renderSceneFields(scene);
  triggerLivePreview(true);
  showToast("Text element removed");
}

function addNewCustomField() {
  const sc = currentTemplateData.scenes.find((s) => s.scene_id === activeSceneId);
  if (!sc) return;

  if (!sc.fields) sc.fields = [];
  const fNum = sc.fields.length + 1;
  const newField = {
    id: `field_${sc.scene_num}_custom_${Date.now()}`,
    label: `Custom Text ${fNum}`,
    value: "Your Custom Text Here",
    default_value: "Your Custom Text Here",
    type: "general",
    box: [0.15, 0.5, 0.7, 0.05],
    x_percent: 50.0,
    y_percent: 50.0,
    font_size: 36,
    color: "#ffffff",
    align: "center",
  };
  sc.fields.push(newField);
  renderScenesTabs();
  renderSceneFields(sc);
  triggerLivePreview(true);
  showToast("New text element added");
}

// ============================================================
// LIVE PREVIEW & VIDEO PLAYER
// ============================================================
function triggerLivePreviewDebounced() {
  clearTimeout(previewDebounceTimer);
  previewDebounceTimer = setTimeout(() => {
    triggerLivePreview(false);
  }, 120);
}

async function triggerLivePreview(showLoading = false) {
  if (!currentTemplateId) return;
  if (showLoading) showPreviewLoader(true);

  // Auto-save active template state in memory
  const previewUrl = `/api/templates/${currentTemplateId}/preview?frame=${currentFrameIdx}&scene_id=${activeSceneId || ""}&t=${Date.now()}`;
  previewImage.src = previewUrl;

  previewImage.onload = () => {
    showPreviewLoader(false);
    previewMeta.textContent = `Frame ${currentFrameIdx} • ${formatTime(currentFrameIdx / 30)}`;
  };
  previewImage.onerror = () => {
    showPreviewLoader(false);
  };
}

function showPreviewLoader(visible) {
  previewLoader.classList.toggle("visible", visible);
}

function setPreviewMode(mode) {
  if (mode === "frame") {
    btnModePreview.classList.add("active");
    btnModeVideo.classList.remove("active");
    frameView.classList.remove("hidden");
    videoView.classList.add("hidden");
    videoPlayer.pause();
    triggerLivePreview(true);
  } else {
    btnModePreview.classList.remove("active");
    btnModeVideo.classList.add("active");
    frameView.classList.add("hidden");
    videoView.classList.remove("hidden");
    videoPlayer.currentTime = currentFrameIdx / 30.0;
  }
}

function updateTimelineLabel() {
  timeCurrent.textContent = formatTime(currentFrameIdx / 30.0);
}

function formatTime(seconds) {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

// ============================================================
// SAVE & EXPORT
// ============================================================
async function saveTemplate() {
  if (!currentTemplateId || !currentTemplateData) return;
  try {
    const res = await fetch(`/api/templates/${currentTemplateId}/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentTemplateData),
    });
    if (!res.ok) throw new Error("Save failed");
    showToast("Template changes saved successfully ✓");
  } catch (err) {
    showToast("Error saving template: " + err.message);
  }
}

async function triggerRender() {
  if (!currentTemplateId || !currentTemplateData) return;

  // Open render modal
  renderModal.classList.remove("hidden");
  renderProgressWrap.classList.remove("hidden");
  renderDoneWrap.classList.add("hidden");
  renderStepText.textContent = "Starting parallel multi-core video renderer...";

  try {
    // Save latest changes first
    await fetch(`/api/templates/${currentTemplateId}/save`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentTemplateData),
    });

    const res = await fetch(`/api/templates/${currentTemplateId}/render`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(currentTemplateData),
    });
    if (!res.ok) throw new Error("Render trigger failed");

    pollRenderStatus(currentTemplateId);
  } catch (err) {
    renderModal.classList.add("hidden");
    showToast("Render error: " + err.message);
  }
}

function pollRenderStatus(templateId) {
  clearInterval(renderPollInterval);
  renderPollInterval = setInterval(async () => {
    try {
      const res = await fetch(`/api/templates/${templateId}/status`);
      if (!res.ok) return;
      const statusData = await res.json();
      const r = statusData.render || {};

      if (r.status === "rendering") {
        renderStepText.textContent = r.step || "Rendering frames across CPU cores...";
      } else if (r.status === "done") {
        clearInterval(renderPollInterval);
        renderProgressWrap.classList.add("hidden");
        renderDoneWrap.classList.remove("hidden");
        btnDownloadRendered.href = `/api/templates/${templateId}/download?t=${Date.now()}`;
        btnDownload.href = `/api/templates/${templateId}/download?t=${Date.now()}`;
        videoSource.src = `/api/templates/${templateId}/video?t=${Date.now()}`;
        videoPlayer.load();
        showToast("Render complete! Video ready to download.");
      } else if (r.status === "error") {
        clearInterval(renderPollInterval);
        renderModal.classList.add("hidden");
        showToast("Rendering error: " + (r.error || "Render job failed"));
      }
    } catch (e) {
      console.warn("Poll error:", e);
    }
  }, 1000);
}

// ============================================================
// UTILITIES
// ============================================================
function showToast(message) {
  toast.textContent = message;
  toast.classList.remove("hidden");
  setTimeout(() => {
    toast.classList.add("hidden");
  }, 3200);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
