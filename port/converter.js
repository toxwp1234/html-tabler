/**
 * Image -> HTML table converter, ported from image_to_html/transform.py.
 * Pure logic, no DOM event handling — see app.js for the UI wiring.
 */

const ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";

/** Bijective base-52 index -> short CSS-safe class name (a, b, ..., z, A, ..., aa, ab, ...). */
function classNameFor(index) {
  const base = ALPHABET.length;
  let name = "";
  let i = index + 1;
  while (i > 0) {
    i -= 1;
    const rem = i % base;
    i = Math.floor(i / base);
    name = ALPHABET[rem] + name;
  }
  return name;
}

function toHex(value) {
  return value.toString(16).padStart(2, "0");
}

function escapeHtml(text) {
  return text.replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[ch]));
}

function channelRange(pixels, channel) {
  let min = 255;
  let max = 0;
  for (const p of pixels) {
    const v = p[channel];
    if (v < min) min = v;
    if (v > max) max = v;
  }
  return max - min;
}

/**
 * Median-cut color quantization — the JS analog of Pillow's
 * `quantize(colors, method=FASTOCTREE)` in transform.py.
 * Returns an array parallel to `pixels`, each entry replaced by its bucket's average color.
 */
function quantizeColors(pixels, maxColors) {
  if (!maxColors || maxColors <= 0 || pixels.length <= maxColors) {
    return pixels.map((p) => ({ r: p.r, g: p.g, b: p.b }));
  }

  const buckets = [pixels.slice()];
  while (buckets.length < maxColors) {
    let splitIndex = -1;
    let splitChannel = "r";
    let maxRange = -1;
    buckets.forEach((bucket, i) => {
      if (bucket.length < 2) return;
      for (const channel of ["r", "g", "b"]) {
        const range = channelRange(bucket, channel);
        if (range > maxRange) {
          maxRange = range;
          splitIndex = i;
          splitChannel = channel;
        }
      }
    });
    if (splitIndex === -1) break; // every bucket is a single color already

    const bucket = buckets[splitIndex];
    bucket.sort((a, b) => a[splitChannel] - b[splitChannel]);
    const mid = Math.floor(bucket.length / 2);
    buckets.splice(splitIndex, 1, bucket.slice(0, mid), bucket.slice(mid));
  }

  const result = new Array(pixels.length);
  for (const bucket of buckets) {
    let sr = 0, sg = 0, sb = 0;
    for (const p of bucket) { sr += p.r; sg += p.g; sb += p.b; }
    const n = bucket.length;
    const avg = { r: Math.round(sr / n), g: Math.round(sg / n), b: Math.round(sb / n) };
    for (const p of bucket) result[p.idx] = avg;
  }
  return result;
}

export class ImageToHtmlConverter {
  /**
   * @param {object} options
   * @param {number} options.cellSize   per-cell width/height in px
   * @param {number} options.borderPx   per-cell border in px
   * @param {number} options.colors     palette size (0 = keep every color)
   */
  constructor({ cellSize = 8, borderPx = 0, colors = 64 } = {}) {
    this.cellSize = cellSize;
    this.borderPx = borderPx;
    this.colors = colors;
  }

  /** Downscale `image` to cols x rows and return an [row][col] grid of '#rrggbb'. */
  gridFromImage(image, rows, cols) {
    const canvas = document.createElement("canvas");
    canvas.width = cols;
    canvas.height = rows;
    const ctx = canvas.getContext("2d");
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = "high";
    ctx.drawImage(image, 0, 0, cols, rows);

    const { data } = ctx.getImageData(0, 0, cols, rows);
    const pixels = [];
    for (let i = 0; i < rows * cols; i++) {
      pixels.push({ r: data[i * 4], g: data[i * 4 + 1], b: data[i * 4 + 2], idx: i });
    }
    const quantized = quantizeColors(pixels, this.colors);

    const grid = [];
    for (let row = 0; row < rows; row++) {
      const line = [];
      for (let col = 0; col < cols; col++) {
        const { r, g, b } = quantized[row * cols + col];
        line.push(`#${toHex(r)}${toHex(g)}${toHex(b)}`);
      }
      grid.push(line);
    }
    return grid;
  }

  /** Grid -> ({tableHtml, css, colorCount}), one CSS class per unique color. */
  buildTable(grid) {
    const colorToClass = new Map();
    const rows = ["<table>", "  <tbody>"];
    for (const gridRow of grid) {
      const cells = [];
      for (const color of gridRow) {
        if (!colorToClass.has(color)) {
          colorToClass.set(color, classNameFor(colorToClass.size));
        }
        cells.push(`<td class="${colorToClass.get(color)}"></td>`);
      }
      rows.push(`    <tr>${cells.join("")}</tr>`);
    }
    rows.push("  </tbody>", "</table>");

    const css = [
      "table { border-collapse: collapse; }",
      `td { width: ${this.cellSize}px; height: ${this.cellSize}px; padding: 0; border: ${this.borderPx}px solid #e5e7eb; }`,
    ];
    for (const [color, cls] of colorToClass) {
      css.push(`.${cls} { background: ${color}; }`);
    }

    return { tableHtml: rows.join("\n"), css: css.join("\n"), colorCount: colorToClass.size };
  }

  /** Grid + title -> full readable HTML document. */
  buildPage(grid, title) {
    const { tableHtml, css, colorCount } = this.buildTable(grid);
    const html = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>${escapeHtml(title)}</title>
<style>
${css}
</style>
</head>
<body>
${tableHtml}
</body>
</html>
`;
    return { html, colorCount };
  }

  /** Same shrink rules as `minify()` in transform.py — keeps </tr>, drops the rest. */
  static minify(html) {
    return html
      .replace(/\n\s*/g, "")
      .replace(/>\s+</g, "><")
      .replace(/class="([A-Za-z]+)"/g, "class=$1")
      .replace(/<\/td>/g, "");
  }

  /** Full pipeline: image -> {readableHtml, optimalHtml, colorCount, rows, cols}. */
  convert(image, { rows, cols, title }) {
    const grid = this.gridFromImage(image, rows, cols);
    const { html, colorCount } = this.buildPage(grid, title);
    const optimalHtml = ImageToHtmlConverter.minify(html);
    return { readableHtml: html, optimalHtml, colorCount, rows, cols };
  }
}
