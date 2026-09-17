import { ImageToHtmlConverter } from "./converter.js";

const GMAIL_LIMIT_KB = 100;

/** Wires the page's DOM to ImageToHtmlConverter: upload -> preview -> convert -> download. */
class ImageToHtmlApp {
  constructor(root) {
    this.dropzone = root.querySelector("#dropzone");
    this.fileInput = root.querySelector("#fileInput");
    this.sourcePreview = root.querySelector("#sourcePreview");
    this.controls = root.querySelector("#controls");
    this.rowsInput = root.querySelector("#rows");
    this.colsInput = root.querySelector("#cols");
    this.keepAspect = root.querySelector("#keepAspect");
    this.colorsInput = root.querySelector("#colors");
    this.cellSizeInput = root.querySelector("#cellSize");
    this.convertBtn = root.querySelector("#convertBtn");
    this.result = root.querySelector("#result");
    this.tablePreview = root.querySelector("#tablePreview");
    this.statsText = root.querySelector("#statsText");
    this.downloadReadableBtn = root.querySelector("#downloadReadable");
    this.downloadOptimalBtn = root.querySelector("#downloadOptimal");
    this.statusLine = root.querySelector("#statusLine");

    this.image = null;
    this.imageTitle = "image";
    this.lastConversion = null;

    this._bindEvents();
  }

  _bindEvents() {
    this.dropzone.addEventListener("click", () => this.fileInput.click());
    this.dropzone.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") this.fileInput.click();
    });
    this.fileInput.addEventListener("change", (e) => {
      const file = e.target.files[0];
      if (file) this._loadFile(file);
    });

    ["dragenter", "dragover"].forEach((type) =>
      this.dropzone.addEventListener(type, (e) => {
        e.preventDefault();
        this.dropzone.classList.add("is-dragover");
      })
    );
    ["dragleave", "drop"].forEach((type) =>
      this.dropzone.addEventListener(type, (e) => {
        e.preventDefault();
        this.dropzone.classList.remove("is-dragover");
      })
    );
    this.dropzone.addEventListener("drop", (e) => {
      const file = e.dataTransfer.files[0];
      if (file) this._loadFile(file);
    });

    this.keepAspect.addEventListener("change", () => this._syncAspect("rows"));
    this.rowsInput.addEventListener("input", () => this._syncAspect("rows"));
    this.colsInput.addEventListener("input", () => this._syncAspect("cols"));

    this.convertBtn.addEventListener("click", () => this._convert());
    this.downloadReadableBtn.addEventListener("click", () => this._download("readableHtml", "index.html"));
    this.downloadOptimalBtn.addEventListener("click", () => this._download("optimalHtml", "optimal.html"));
  }

  async _loadFile(file) {
    if (!file.type.startsWith("image/")) {
      this._setStatus("To nie jest plik obrazu.", true);
      return;
    }
    this.imageTitle = file.name.replace(/\.[^.]+$/, "") || "image";
    const url = URL.createObjectURL(file);
    const image = new Image();

    try {
      await new Promise((resolve, reject) => {
        image.onload = resolve;
        image.onerror = reject;
        image.src = url;
      });
    } catch {
      this._setStatus("Nie udało się wczytać obrazu.", true);
      return;
    }

    this.image = image;
    this.sourcePreview.src = url;
    this.sourcePreview.hidden = false;
    this.controls.hidden = false;
    this.result.hidden = true;
    this._setStatus(`Wczytano ${file.name} (${image.naturalWidth}×${image.naturalHeight}px).`);

    this.colsInput.value = 88;
    this._syncAspect("cols");
  }

  /** Keeps rows/cols in the image's aspect ratio when the checkbox is on. */
  _syncAspect(changedField) {
    if (!this.keepAspect.checked || !this.image) return;
    const ratio = this.image.naturalHeight / this.image.naturalWidth;
    if (changedField === "cols") {
      const cols = Math.max(1, parseInt(this.colsInput.value, 10) || 1);
      this.rowsInput.value = Math.max(1, Math.round(cols * ratio));
    } else {
      const rows = Math.max(1, parseInt(this.rowsInput.value, 10) || 1);
      this.colsInput.value = Math.max(1, Math.round(rows / ratio));
    }
  }

  _convert() {
    if (!this.image) return;

    const rows = Math.max(1, parseInt(this.rowsInput.value, 10) || 1);
    const cols = Math.max(1, parseInt(this.colsInput.value, 10) || 1);
    const colors = Math.max(0, parseInt(this.colorsInput.value, 10) || 0);
    const cellSize = Math.max(1, parseInt(this.cellSizeInput.value, 10) || 1);

    this._setStatus("Generuję…");
    this.convertBtn.disabled = true;

    // Let the "Generuję…" status paint before the (synchronous) conversion runs.
    setTimeout(() => {
      try {
        const converter = new ImageToHtmlConverter({ cellSize, colors });
        this.lastConversion = converter.convert(this.image, { rows, cols, title: this.imageTitle });
        this._renderResult();
        this._setStatus(`Gotowe: ${rows}×${cols} komórek.`);
      } catch (err) {
        this._setStatus(`Błąd generowania: ${err.message}`, true);
      } finally {
        this.convertBtn.disabled = false;
      }
    });
  }

  _renderResult() {
    const { readableHtml, optimalHtml, colorCount, rows, cols } = this.lastConversion;

    this.tablePreview.innerHTML = readableHtml.match(/<table>[\s\S]*<\/table>/)[0];
    // Scale the preview down so wide grids still fit the panel.
    const naturalWidth = cols * parseInt(this.cellSizeInput.value, 10);
    const scale = Math.min(1, 640 / naturalWidth);
    this.tablePreview.style.transform = scale < 1 ? `scale(${scale})` : "";
    this.tablePreview.style.transformOrigin = "top center";

    const optimalKb = new Blob([optimalHtml]).size / 1024;
    const gmailOk = optimalKb < GMAIL_LIMIT_KB;
    this.statsText.innerHTML =
      `${rows}×${cols} komórek, ${colorCount} kolorów · ` +
      `optimal.html: ${optimalKb.toFixed(1)} KB — ` +
      `<span class="${gmailOk ? "ok" : "warn"}">` +
      `${gmailOk ? "OK dla Gmaila" : "za duży dla Gmaila (limit ~100 KB)"}</span>`;

    this.result.hidden = false;
  }

  _download(key, filename) {
    if (!this.lastConversion) return;
    const blob = new Blob([this.lastConversion[key]], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${this.imageTitle}_${filename}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  _setStatus(message, isError = false) {
    this.statusLine.textContent = message;
    this.statusLine.style.color = isError ? "var(--warn)" : "var(--text-dim)";
  }
}

new ImageToHtmlApp(document);
