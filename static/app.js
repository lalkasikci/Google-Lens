const fileInput = document.querySelector("#fileInput");
const chooseButton = document.querySelector("#chooseButton");
const dropzone = document.querySelector("#dropzone");
const cameraButton = document.querySelector("#cameraButton");
const captureButton = document.querySelector("#captureButton");
const liveButton = document.querySelector("#liveButton");
const cameraActions = document.querySelector("#cameraActions");
const cameraStage = document.querySelector("#cameraStage");
const camera = document.querySelector("#camera");
const overlayCanvas = document.querySelector("#overlayCanvas");
const canvas = document.querySelector("#canvas");
const confidence = document.querySelector("#confidence");
const confidenceValue = document.querySelector("#confidenceValue");
const status = document.querySelector("#status");
const resultImage = document.querySelector("#resultImage");
const placeholder = document.querySelector("#previewPlaceholder");
const translations = document.querySelector("#translations");
const resultCount = document.querySelector("#resultCount");
let stream;
let liveScanning = false;
let processing = false;

document.querySelectorAll('input[name="detectionMode"]').forEach(input => {
  input.addEventListener("change", () => {
    const modeName = input.value === "objects" ? "Nesne algılama" : "Metin algılama";
    showStatus(`${modeName} modu seçildi.`);
  });
});

confidence.addEventListener("input", () => confidenceValue.value = confidence.value);
chooseButton.addEventListener("click", event => { event.stopPropagation(); fileInput.click(); });
dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("keydown", event => {
  if (event.key === "Enter" || event.key === " ") fileInput.click();
});
fileInput.addEventListener("change", () => fileInput.files[0] && processFile(fileInput.files[0]));

["dragenter", "dragover"].forEach(name => dropzone.addEventListener(name, event => {
  event.preventDefault();
  dropzone.classList.add("dragging");
}));
["dragleave", "drop"].forEach(name => dropzone.addEventListener(name, event => {
  event.preventDefault();
  dropzone.classList.remove("dragging");
}));
dropzone.addEventListener("drop", event => {
  const file = [...event.dataTransfer.files].find(item => item.type.startsWith("image/"));
  if (file) processFile(file);
});

cameraButton.addEventListener("click", async () => {
  if (stream) {
    stopCamera();
    return;
  }
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "environment",
        width: { ideal: 640 },
        height: { ideal: 480 },
        frameRate: { ideal: 30 }
      },
      audio: false
    });
    camera.srcObject = stream;
    await camera.play();
    cameraStage.style.aspectRatio = `${camera.videoWidth} / ${camera.videoHeight}`;
    // Kamera ilk anda sagdaki sonuc alaninda gosterilir.
    cameraStage.hidden = false;
    placeholder.hidden = true;
    resultImage.hidden = true;
    cameraActions.hidden = false;
    cameraButton.textContent = "Kamerayı kapat";
  } catch (_error) {
    showStatus("Kameraya erişilemedi. Tarayıcı iznini kontrol edin.", true);
  }
});

captureButton.addEventListener("click", () => {
  cameraFrame().then(file => file && processFile(file));
});

liveButton.addEventListener("click", () => {
  liveScanning = !liveScanning;
  liveButton.classList.toggle("active", liveScanning);
  liveButton.textContent = liveScanning ? "Canlı işlemeyi durdur" : "Canlı işlemeyi başlat";
  if (liveScanning) {
    cameraStage.hidden = false;
    resultImage.hidden = true;
    placeholder.hidden = true;
    processLiveFrame();
  }
});

async function cameraFrame() {
  if (!camera.videoWidth || !camera.videoHeight) return null;
  const selectedMode = document.querySelector('input[name="detectionMode"]:checked').value;
  const maxWidth = selectedMode === "objects" ? 480 : 640;
  const scale = Math.min(1, maxWidth / camera.videoWidth);
  canvas.width = Math.round(camera.videoWidth * scale);
  canvas.height = Math.round(camera.videoHeight * scale);
  canvas.getContext("2d").drawImage(camera, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/jpeg", .80));
  return blob ? new File([blob], "kamera.jpg", { type: "image/jpeg" }) : null;
}

async function processLiveFrame() {
  if (!liveScanning || !stream) return;
  if (!processing) {
    const file = await cameraFrame();
    if (file) await processFile(file, true);
  }
  if (liveScanning) window.setTimeout(processLiveFrame, 100);
}

function stopCamera() {
  liveScanning = false;
  liveButton.classList.remove("active");
  liveButton.textContent = "Canlı işlemeyi başlat";
  stream.getTracks().forEach(track => track.stop());
  stream = null;
  camera.srcObject = null;
  cameraStage.hidden = true;
  clearOverlay();
  if (resultImage.hidden) placeholder.hidden = false;
  cameraActions.hidden = true;
  cameraButton.textContent = "Kamerayı aç";
}

async function processFile(file, isLive = false) {
  if (processing) return;
  processing = true;
  const form = new FormData();
  form.append("image", file);
  form.append("ocr_language", document.querySelector("#ocrLanguage").value);
  form.append("target_language", document.querySelector("#targetLanguage").value);
  form.append("confidence", confidence.value);
  const detectionMode = document.querySelector('input[name="detectionMode"]:checked').value;
  form.append("detect_objects", detectionMode === "objects");
  form.append("detect_text", detectionMode === "text");
  form.append("live", isLive);
  if (!isLive) {
    showStatus("Görüntü işleniyor…");
    setResultCount("İşleniyor");
  }
  translations.replaceChildren();

  try {
    const response = await fetch("/api/process", { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "İşlem başarısız oldu.");

    if (isLive) {
      cameraStage.hidden = false;
      resultImage.hidden = true;
      placeholder.hidden = true;
      drawOverlay(data);
    } else {
      resultImage.src = data.image;
      resultImage.hidden = false;
      cameraStage.hidden = true;
      placeholder.hidden = true;
      clearOverlay();
    }
    if (detectionMode === "objects") {
      const detectedObjects = (data.detections || []).map(detection =>
        `${detection.class_name} %${Math.round(detection.confidence * 100)}`
      );
      setResultCount(`${detectedObjects.length} nesne`);
      showStatus(
        detectedObjects.length
          ? `Algılanan: ${detectedObjects.join(", ")}`
          : "Nesne bulunamadı."
      );
    } else {
      setResultCount(`${data.count} satır`);
      showStatus(data.count ? "Metin algılama tamamlandı." : "Metin bulunamadı. Görseli yaklaştırmayı deneyin.");
    }
    renderTranslations(data.lines);
  } catch (error) {
    setResultCount("Hata");
    showStatus(error.message, true);
    if (isLive) {
      liveScanning = false;
      liveButton.classList.remove("active");
      liveButton.textContent = "Canlı işlemeyi başlat";
    }
  } finally {
    processing = false;
  }
}

function renderTranslations(lines) {
  lines.forEach(line => {
    const row = document.createElement("article");
    row.className = "translation";
    const original = document.createElement("p");
    original.className = "original";
    original.textContent = line.original;
    const arrow = document.createElement("span");
    arrow.className = "arrow";
    arrow.textContent = "→";
    const translated = document.createElement("p");
    const language = document.createElement("small");
    language.textContent = line.detected_language;
    translated.append(language, document.createTextNode(line.translated));
    row.append(original, arrow, translated);
    translations.append(row);
  });
}

function drawOverlay(data) {
  overlayCanvas.width = data.frame_width;
  overlayCanvas.height = data.frame_height;
  const context = overlayCanvas.getContext("2d");
  context.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
  context.lineWidth = 2;
  context.font = "bold 16px Arial";

  (data.detections || []).forEach(detection => {
    drawBox(context, detection.box, detection.label, "#32dc78");
  });

  (data.lines || []).forEach(line => {
    const label = `[${line.detected_language}] ${line.translated}`;
    drawBox(context, line.box, label, "#ff9f43");
  });
}

function drawBox(context, box, label, color) {
  const [x1, y1, x2, y2] = box;
  context.strokeStyle = color;
  context.strokeRect(x1, y1, x2 - x1, y2 - y1);

  const textWidth = context.measureText(label).width;
  const labelY = Math.max(0, y1 - 23);
  context.fillStyle = "rgba(18, 31, 25, .88)";
  context.fillRect(x1, labelY, textWidth + 12, 23);
  context.fillStyle = color;
  context.fillText(label, x1 + 6, labelY + 17);
}

function clearOverlay() {
  const context = overlayCanvas.getContext("2d");
  context.clearRect(0, 0, overlayCanvas.width, overlayCanvas.height);
}

function showStatus(message, isError = false) {
  status.textContent = message;
  status.classList.toggle("error", isError);
}

function setResultCount(text) {
  if (resultCount) resultCount.textContent = text;
}
