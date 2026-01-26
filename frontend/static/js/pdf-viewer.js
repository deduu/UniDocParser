// static/js/pdf-viewer.js
export class PDFViewer {
  constructor(canvasId, containerId) {
    this.canvas = document.getElementById(canvasId);
    this.container = document.getElementById(containerId);
    this.ctx = this.canvas.getContext("2d");

    this.pdf = null;
    this.page = 1;
    this.pages = 0;
    this.zoom = 1;
  }

  async load(fileOrArrayBuffer) {
    const buff =
      fileOrArrayBuffer instanceof ArrayBuffer
        ? fileOrArrayBuffer
        : await fileOrArrayBuffer.arrayBuffer();

    this.pdf = await window.pdfjsLib.getDocument(buff).promise;
    this.pages = this.pdf.numPages;
    this.page = 1;
  }

  async render(pageNo = this.page, zoom = this.zoom) {
    if (!this.pdf) return;
    this.page = pageNo;
    this.zoom = zoom;

    const page = await this.pdf.getPage(pageNo);
    const vp = page.getViewport({ scale: zoom });

    this.canvas.height = vp.height;
    this.canvas.width = vp.width;

    await page.render({ canvasContext: this.ctx, viewport: vp }).promise;
  }
}
