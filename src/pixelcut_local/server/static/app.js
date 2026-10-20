// PixelCut Local Mobile Client
document.addEventListener("DOMContentLoaded", () => {
  // Elements
  const fileInput = document.getElementById("file-input");
  const bgFileInput = document.getElementById("bg-file-input");
  const uploadSection = document.getElementById("upload-section");
  const progressSection = document.getElementById("progress-section");
  const editorSection = document.getElementById("editor-section");
  const previewImage = document.getElementById("preview-image");
  const originalImage = document.getElementById("original-image");
  const progressBar = document.getElementById("progress-bar");
  const progressStatusText = document.getElementById("progress-status-text");
  const applyBtn = document.getElementById("apply-btn");
  const downloadBtn = document.getElementById("download-btn");
  const newPhotoBtn = document.getElementById("new-photo-btn");
  const exportFormatSelect = document.getElementById("export-format-select");
  const canvasPresetSelect = document.getElementById("canvas-preset-select");
  const solidColorPicker = document.getElementById("solid-color-picker");
  const solidColorHex = document.getElementById("solid-color-hex");
  const shadowToggle = document.getElementById("shadow-toggle");
  const outlineToggle = document.getElementById("outline-toggle");

  // Auth Elements
  const authBtn = document.getElementById("auth-btn");
  const authModal = document.getElementById("auth-modal");
  const tokenInput = document.getElementById("token-input");
  const saveTokenBtn = document.getElementById("save-token-btn");
  const cancelTokenBtn = document.getElementById("cancel-token-btn");
  const toast = document.getElementById("toast");

  // State
  let selectedFile = null;
  let selectedBgFile = null;
  let currentJobId = null;
  let currentResultBlobUrl = null;
  let currentBgMode = "transparent";
  let activeGradient = [[99, 102, 241], [168, 85, 247]];

  function showToast(message, duration = 3000) {
    toast.textContent = message;
    toast.classList.remove("hidden");
    setTimeout(() => {
      toast.classList.add("hidden");
    }, duration);
  }

  function getHeaders() {
    const headers = {};
    const token = localStorage.getItem("pixelcut_token");
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
      headers["X-Pairing-Token"] = token;
    }
    return headers;
  }

  // Auth Modal
  authBtn.addEventListener("click", () => {
    tokenInput.value = localStorage.getItem("pixelcut_token") || "";
    authModal.classList.remove("hidden");
  });

  saveTokenBtn.addEventListener("click", () => {
    const token = tokenInput.value.trim();
    if (token) {
      localStorage.setItem("pixelcut_token", token);
      showToast("Pairing token saved.");
    } else {
      localStorage.removeItem("pixelcut_token");
      showToast("Token cleared.");
    }
    authModal.classList.add("hidden");
  });

  cancelTokenBtn.addEventListener("click", () => {
    authModal.classList.add("hidden");
  });

  // Tab switching (Preview Result vs Original)
  const tabResult = document.getElementById("tab-result");
  const tabOriginal = document.getElementById("tab-original");

  tabResult.addEventListener("click", () => {
    tabResult.classList.add("active");
    tabOriginal.classList.remove("active");
    previewImage.classList.remove("hidden");
    originalImage.classList.add("hidden");
  });

  tabOriginal.addEventListener("click", () => {
    tabOriginal.classList.add("active");
    tabResult.classList.remove("active");
    previewImage.classList.add("hidden");
    originalImage.classList.remove("hidden");
  });

  // Controls Tab Switching
  document.querySelectorAll(".ctrl-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".ctrl-tab").forEach((t) => t.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.add("hidden"));
      tab.classList.add("active");
      const targetId = tab.dataset.tab;
      document.getElementById(targetId).classList.remove("hidden");
    });
  });

  // Background Chip selection
  const solidControls = document.getElementById("solid-controls");
  const gradientControls = document.getElementById("gradient-controls");
  const bgImgControls = document.getElementById("bg-img-controls");

  document.querySelectorAll(".chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      document.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
      chip.classList.add("active");
      currentBgMode = chip.dataset.bg;

      solidControls.classList.add("hidden");
      gradientControls.classList.add("hidden");
      bgImgControls.classList.add("hidden");

      if (currentBgMode === "solid") solidControls.classList.remove("hidden");
      if (currentBgMode === "gradient") gradientControls.classList.remove("hidden");
      if (currentBgMode === "image") bgImgControls.classList.remove("hidden");
    });
  });

  // Color picker
  solidColorPicker.addEventListener("input", (e) => {
    solidColorHex.textContent = e.target.value.toUpperCase();
  });

  // Gradient Swatches
  document.querySelectorAll(".grad-swatch").forEach((swatch) => {
    swatch.addEventListener("click", () => {
      document.querySelectorAll(".grad-swatch").forEach((s) => s.classList.remove("active"));
      swatch.classList.add("active");
      const hexToRgb = (hex) => {
        const num = parseInt(hex.slice(1), 16);
        return [(num >> 16) & 255, (num >> 8) & 255, num & 255];
      };
      activeGradient = [hexToRgb(swatch.dataset.g1), hexToRgb(swatch.dataset.g2)];
    });
  });

  // File Upload Handling
  fileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      selectedFile = e.target.files[0];
      // Display local original image immediately
      const reader = new FileReader();
      reader.onload = (ev) => {
        originalImage.src = ev.target.result;
      };
      reader.readAsDataURL(selectedFile);

      startProcessingJob();
    }
  });

  bgFileInput.addEventListener("change", (e) => {
    if (e.target.files && e.target.files[0]) {
      selectedBgFile = e.target.files[0];
      showToast("Background image selected.");
    }
  });

  newPhotoBtn.addEventListener("click", () => {
    fileInput.value = "";
    selectedFile = null;
    selectedBgFile = null;
    currentJobId = null;
    uploadSection.classList.remove("hidden");
    progressSection.classList.add("hidden");
    editorSection.classList.add("hidden");
  });

  // Submit Job
  async function startProcessingJob() {
    if (!selectedFile) return;

    uploadSection.classList.add("hidden");
    editorSection.classList.add("hidden");
    progressSection.classList.remove("hidden");
    progressBar.style.width = "10%";
    progressStatusText.textContent = "Uploading image...";

    const formData = new FormData();
    formData.append("file", selectedFile);
    if (selectedBgFile && currentBgMode === "image") {
      formData.append("bg_file", selectedBgFile);
    }
    formData.append("bg_mode", currentBgMode);
    formData.append("solid_color", solidColorPicker.value);
    formData.append("gradient_colors", JSON.stringify(activeGradient));
    formData.append("canvas_preset", canvasPresetSelect.value);
    formData.append("export_format", exportFormatSelect.value);
    formData.append("enable_shadow", shadowToggle.checked);
    formData.append("enable_outline", outlineToggle.checked);
    if (outlineToggle.checked) {
      formData.append("outline_width", "6");
    }

    try {
      const resp = await fetch("/api/v1/jobs", {
        method: "POST",
        headers: getHeaders(),
        body: formData,
      });

      if (resp.status === 401) {
        authModal.classList.remove("hidden");
        throw new Error("Authentication required. Please enter pairing token.");
      }
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || "Server rejected image upload.");
      }

      const data = await resp.json();
      currentJobId = data.job_id;
      pollJobProgress(currentJobId);
    } catch (err) {
      alert("Error: " + err.message);
      uploadSection.classList.remove("hidden");
      progressSection.classList.add("hidden");
    }
  }

  // Poll Job Status
  async function pollJobProgress(jobId) {
    try {
      const resp = await fetch(`/api/v1/jobs/${jobId}`, {
        headers: getHeaders(),
      });
      if (!resp.ok) throw new Error("Could not check job status.");

      const job = await resp.json();
      progressBar.style.width = `${Math.max(15, job.progress)}%`;

      if (job.status === "processing") {
        progressStatusText.textContent = "Running AI background removal...";
      } else if (job.status === "compositing") {
        progressStatusText.textContent = "Compositing background layers...";
      }

      if (job.status === "completed") {
        loadCompletedResult(jobId);
      } else if (job.status === "failed") {
        alert("Processing Failed: " + (job.error_message || "Unknown error"));
        uploadSection.classList.remove("hidden");
        progressSection.classList.add("hidden");
      } else if (job.status === "cancelled") {
        showToast("Job was cancelled.");
        uploadSection.classList.remove("hidden");
        progressSection.classList.add("hidden");
      } else {
        setTimeout(() => pollJobProgress(jobId), 400);
      }
    } catch (err) {
      console.error(err);
      setTimeout(() => pollJobProgress(jobId), 1000);
    }
  }

  // Load Completed Result
  async function loadCompletedResult(jobId) {
    try {
      const resp = await fetch(`/api/v1/jobs/${jobId}/result`, {
        headers: getHeaders(),
      });
      if (!resp.ok) throw new Error("Failed to download processed result.");

      const blob = await resp.blob();
      if (currentResultBlobUrl) URL.revokeObjectURL(currentResultBlobUrl);
      currentResultBlobUrl = URL.createObjectURL(blob);

      previewImage.src = currentResultBlobUrl;

      progressSection.classList.add("hidden");
      editorSection.classList.remove("hidden");
      tabResult.click();
      showToast("Background removed successfully!");
    } catch (err) {
      alert("Error fetching result: " + err.message);
    }
  }

  // Update Composition
  applyBtn.addEventListener("click", () => {
    if (selectedFile) {
      startProcessingJob();
    }
  });

  // Download Action
  downloadBtn.addEventListener("click", () => {
    if (!currentResultBlobUrl) return;
    const a = document.createElement("a");
    a.href = currentResultBlobUrl;
    const fmt = exportFormatSelect.value.toLowerCase();
    const stem = selectedFile ? selectedFile.name.split(".")[0] : "cutout";
    a.download = `${stem}_cutout.${fmt === "jpeg" ? "jpg" : fmt}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    showToast("Downloaded to your device!");
  });
});
