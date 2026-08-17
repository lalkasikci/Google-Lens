const fileInput = document.querySelector("#fileInput");
const chooseButton = document.querySelector("#chooseButton");
const dropzone = document.querySelector("#dropzone");
const cameraButton = document.querySelector("#cameraButton");
const captureButton = document.querySelector("#captureButton");
const camera = document.querySelector("#camera");
const canvas = document.querySelector("#canvas");
const confidence = document.querySelector("#confidence");
const confidenceValue = document.querySelector("#confidenceValue");
const status = document.querySelector("#status");
const resultImage = document.querySelector("#resultImage");
const placeholder = document.querySelector("#previewPlaceholder");
const translations = document.querySelector("#translations");
const resultCount = document.querySelector("#resultCount");
let stream;

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
  try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false });
    camera.srcObject = stream;
    camera.hidden = false;
    captureButton.hidden = false;
    cameraButton.textContent = "Kamera açık";
  } catch (_error) {
    showStatus("Kameraya erişilemedi. Tarayıcı iznini kontrol edin.", true);
  }
});

captureButton.addEventListener("click", () => {
  canvas.width = camera.videoWidth;
  canvas.height = camera.videoHeight;
  canvas.getContext("2d").drawImage(camera, 0, 0);
  canvas.toBlob(blob => blob && processFile(new File([blob], "kamera.jpg", { type: "image/jpeg" })), "image/jpeg", .92);
});

async function processFile(file) {
  const form = new FormData();
  form.append("image", file);
  form.append("ocr_language", document.querySelector("#ocrLanguage").value);
  form.append("target_language", document.querySelector("#targetLanguage").value);
  form.append("confidence", confidence.value);
  showStatus("Metin aranıyor ve çevriliyor…");
  resultCount.textContent = "İşleniyor";
  translations.replaceChildren();

  try {
    const response = await fetch("/api/process", { method: "POST", body: form });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "İşlem başarısız oldu.");

    resultImage.src = data.image;
    resultImage.hidden = false;
    placeholder.hidden = true;
    resultCount.textContent = `${data.count} satır`;
    showStatus(data.count ? "İşlem tamamlandı." : "Metin bulunamadı. Görseli yaklaştırmayı deneyin.");
    renderTranslations(data.lines);
  } catch (error) {
    resultCount.textContent = "Hata";
    showStatus(error.message, true);
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

function showStatus(message, isError = false) {
  status.textContent = message;
  status.classList.toggle("error", isError);
}
