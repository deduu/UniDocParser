// static/js/ui-controller.js
import { showNotification, showError } from "./components/notification.js";

export class UIController {
  constructor(state, api) {
    this.state = state;
    this.api = api;

    // JSON Editor instance
    this.jsonEditor = null;
    this.currentJsonData = null; // Store the current JSON data separately

    // PDF.js related properties for Page Compare tab
    this.pdfDoc = null; // Stores the loaded PDF document
    this.currentPdfPage = 0; // Current page number being displayed in comparison
    this.pdfCanvas = null; // <canvas> element for PDF rendering
    this.pdfCtx = null; // 2D rendering context of the canvas

    // DOM elements (will be populated in initDOMElements)
    this.form = null;
    this.fileInput = null;
    this.fileNameDisplay = null;
    this.extractionOptions = null;

    this.progressBar = null;
    this.progressDiv = null;
    this.progressLabel = null;
    this.progressPercentage = null;

    this.extractButton = null;
    this.helpPanel = null;
    this.resultTabs = null;

    this.tabButtons = null;
    this.tabContents = null;

    // Page Comparison specific elements
    this.pdfContainer = null;
    this.extractedContainer = null;
    this.prevPageButton = null;
    this.nextPageButton = null;
    this.pageInfoSpan = null;
    this.zoomLevelSelect = null;

    // New: Step indicator elements
    this.stepIndicators = [];
    this.helpToggle = null; // For the floating help button

    // Timer for scroll syncing to prevent infinite loops
    this._scrollTimer = null;
  }

  init() {
    // 1) Grab DOM elements
    this.initDOMElements();

    // 2) Initialize highlight.js for code blocks
    // Assumes hljs is globally available via HTML script tag
    hljs.highlightAll();

    // 3) Setup drag & drop functionality for file input
    this.setupDragAndDrop();

    // 4) Attach event listeners
    this.fileInput.addEventListener("change", () => {
      if (this.fileInput.files[0]) {
        this.handleFileSelection(this.fileInput.files[0]);
      }
    });
    this.extractButton.addEventListener("click", () => this.startExtraction());
    // New: Event listener for help toggle
    this.helpToggle.addEventListener("click", () => {
      this.helpPanel.scrollIntoView({ behavior: "smooth" });
    });

    // 5) Setup tab switching logic
    this.initTabSwitching();

    // 6) Setup copy buttons for JSON/Markdown code
    this.initCopyButtons();

    // 7) Setup JSON expand/collapse functionality
    this.initJsonExpandCollapse();

    // 8) Setup page navigation and zoom listeners for Page Compare
    this.initPageComparisonControls();

    // 9) Setup scroll syncing for Page Compare
    this.setupScrollSync();

    // New: Initialize step indicator to the first step
    this.updateStepIndicator(0);
  }

  initDOMElements() {
    this.form = document.getElementById("pdf-upload-form");
    this.fileInput = document.getElementById("pdf-file");
    this.fileNameDisplay = document.getElementById("file-name");
    this.extractionOptions = document.getElementById("extraction-options");

    this.progressBar = document.getElementById("upload-progress");
    this.progressDiv = this.progressBar.querySelector(".bg-blue-600");
    this.progressLabel = document.getElementById("progress-label");
    this.progressPercentage = document.getElementById("progress-percentage");

    this.extractButton = document.getElementById("extract-button");
    this.helpPanel = document.getElementById("help-panel");
    this.resultTabs = document.getElementById("result-tabs");

    this.tabButtons = document.querySelectorAll(".tab-button");
    this.tabContents = document.querySelectorAll(".tab-content");

    // Page Comparison elements
    this.pdfContainer = document.getElementById("pdf-container");
    this.extractedContainer = document.getElementById("extracted-container");
    this.pdfCanvas = document.getElementById("pdf-canvas");
    this.pdfCtx = this.pdfCanvas?.getContext("2d"); // Safe access with optional chaining
    this.prevPageButton = document.getElementById("prev-page");
    this.nextPageButton = document.getElementById("next-page");
    this.pageInfoSpan = document.getElementById("page-info");
    this.zoomLevelSelect = document.getElementById("zoom-level");

    // New: Get step indicator elements
    this.stepIndicators = [
      document.getElementById("step-1"),
      document.getElementById("step-2"),
      document.getElementById("step-3"),
      document.getElementById("step-4"),
    ].filter(Boolean); // Filter out any nulls if elements aren't found

    // New: Get help toggle button
    this.helpToggle = document.getElementById("help-toggle");
  }

  setupDragAndDrop() {
    const dropArea = this.form.querySelector("label");
    ["dragenter", "dragover", "dragleave", "drop"].forEach((evt) => {
      dropArea.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
      });
    });
    ["dragenter", "dragover"].forEach((evt) =>
      dropArea.addEventListener(evt, () =>
        dropArea.classList.add("border-blue-500", "bg-blue-50")
      )
    );
    ["dragleave", "drop"].forEach((evt) =>
      dropArea.addEventListener(evt, () =>
        dropArea.classList.remove("border-blue-500", "bg-blue-50")
      )
    );
    dropArea.addEventListener("drop", (e) => {
      const file = e.dataTransfer.files[0];
      if (file) this.handleFileSelection(file);
    });
  }

  handleFileSelection(file) {
    if (file.type !== "application/pdf") {
      return showError("Please upload a PDF file");
    }
    this.fileNameDisplay.textContent = file.name;
    this.fileNameDisplay.classList.remove("hidden");
    this.extractionOptions.classList.remove("hidden");

    document.getElementById("file-title").textContent = file.name;
    document.getElementById(
      "file-details"
    ).textContent = `Size: ${this.formatFileSize(file.size)}`;

    // New: Update step indicator when a file is selected
    this.updateStepIndicator(1);
  }

  formatFileSize(bytes) {
    if (bytes < 1024) return bytes + " bytes";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1024 / 1024).toFixed(1) + " MB";
  }

  async startExtraction() {
    if (!this.fileInput.files[0]) {
      return showError("Please select a PDF first");
    }

    this.helpPanel.classList.add("hidden");
    this.resultTabs.classList.remove("hidden");

    this.progressBar.classList.remove("hidden");
    this.progressLabel.textContent = "Uploading...";
    this.progressDiv.style.width = "0%";
    this.progressPercentage.textContent = "0%";

    // New: Update step indicator when extraction starts
    this.updateStepIndicator(2);

    const formData = new FormData();
    formData.append("file", this.fileInput.files[0]);
    ["extract-text", "extract-tables", "extract-images"].forEach((id) => {
      formData.append(id, document.getElementById(id).checked);
    });
    const pageRange = document.getElementById("page-range").value;
    if (pageRange) formData.append("page_range", pageRange);

    try {
      const data = await this.api.extractPdf(formData, (pct) => {
        this.progressDiv.style.width = pct + "%";
        this.progressPercentage.textContent = pct + "%";
        this.progressLabel.textContent =
          pct < 100 ? "Uploading..." : "Processing completed";
      });

      console.log("Full API response 'data':", data); // <-- ADD THIS LOG
      console.log(
        "Full API response 'data_extraction_result':",
        data.extraction_result
      ); // <-- ADD THIS LOG

      // Ensure data.extraction_result is a valid object
      const extractionResult =
        data && data.extraction_result ? data.extraction_result : {};

      // Store the current JSON data
      this.currentJsonData = extractionResult;

      // Store the ENTIRE data object received from the API response for page comparison
      this.api.lastExtractionResult = data;

      this.displayResults(data); // Call displayResults with the full data object

      // Load PDF for comparison view after successful extraction
      const file = this.fileInput.files[0];
      if (file && typeof pdfjsLib !== "undefined") {
        const fileReader = new FileReader();
        fileReader.onload = async () => {
          const pdfData = new Uint8Array(fileReader.result);
          try {
            this.pdfDoc = await pdfjsLib.getDocument({ data: pdfData }).promise;
            this.showPage(1); // Show the first page of the PDF
          } catch (err) {
            showError("Error loading PDF for preview: " + err.message);
            this.pdfDoc = null;
            this.updatePageNavigation(); // Disable navigation buttons if PDF fails to load
          }
        };
        fileReader.readAsArrayBuffer(file);
      } else if (!file) {
        showError("No file selected to load PDF preview.");
        this.pdfDoc = null;
        this.updatePageNavigation();
      } else {
        showError(
          "PDF.js library not loaded or undefined. Cannot render PDF preview."
        );
        this.pdfDoc = null;
        this.updatePageNavigation();
      }

      // Initialize JSON editor if it hasn't been yet
      if (!this.jsonEditor) {
        const container = document.getElementById("json-code");
        if (container) {
          container.innerHTML = ""; // Clear any existing text content
          try {
            this.jsonEditor = new JSONEditor(container, {
              mode: "view",
              modes: ["view", "tree"],
              onError: function (err) {
                showError("JSON Viewer Error: " + err.message);
              },
            });
          } catch (err) {
            showError("Failed to initialize JSON Editor: " + err.message);
            // Fallback to plain text display
            container.innerHTML = `<pre><code class="language-json">${JSON.stringify(
              extractionResult,
              null,
              2
            )}</code></pre>`;
            hljs.highlightAll();
            return;
          }
        }
      }

      // Set the JSON data safely
      if (this.jsonEditor && typeof this.jsonEditor.set === "function") {
        try {
          this.jsonEditor.set(extractionResult);
          if (typeof this.jsonEditor.expandAll === "function") {
            this.jsonEditor.expandAll();
          }
        } catch (err) {
          showError("Error setting JSON data: " + err.message);
        }
      }
      // New: Update step indicator when extraction is complete
      this.updateStepIndicator(3);
    } catch (err) {
      showError(err.message);
      this.progressBar.classList.add("hidden");
      this.progressLabel.textContent = "Error";
      this.progressPercentage.textContent = "";
      this.pdfDoc = null;
      this.updatePageNavigation();
      // New: Reset or indicate error step
      this.updateStepIndicator(1); // Or a specific error step if you have one
    }
  }

  displayResults(data) {
    const res = data && data.extraction_result ? data.extraction_result : {};
    document.getElementById("pages-count").textContent = res.pages
      ? res.pages.length
      : 0;
    document.getElementById("text-blocks-count").textContent =
      res.text_blocks || 0;
    document.getElementById("tables-count").textContent = res.tables || 0;

    document.getElementById(
      "extraction-time"
    ).textContent = `Extraction completed in ${
      res.processing_time ? res.processing_time.toFixed(1) : "N/A"
    }s`;

    document.getElementById("download-json").href = data.json_output || "#";
    document.getElementById("download-markdown").href =
      data.markdown_output || "#";

    // Update JSON editor if it exists
    if (this.jsonEditor && typeof this.jsonEditor.set === "function") {
      try {
        this.jsonEditor.set(res);
        if (typeof this.jsonEditor.expandAll === "function") {
          this.jsonEditor.expandAll();
        }
      } catch (err) {
        showError("Error updating JSON editor: " + err.message);
      }
    }

    const generatedMarkdown = this.generateMarkdownContent(
      res,
      this.fileInput.files[0]
    );
    document.getElementById("markdown-code").textContent = generatedMarkdown;
    document.getElementById("markdown-preview").innerHTML =
      this.renderMarkdownAdv(generatedMarkdown);

    hljs.highlightAll();

    this.updatePageComparisonView(data);
  }

  // In generateMarkdownContent method:
  generateMarkdownContent(res, file) {
    const fileName = file ? file.name : "Document";
    const processingTime = res.processing_time
      ? res.processing_time.toFixed(1)
      : "N/A";

    let md = `# ${fileName}\n\nExtraction in ${processingTime}s\n\n`;
    if (res.pages && Array.isArray(res.pages)) {
      res.pages.forEach((p, i) => {
        md += `## Page ${i + 1}\n\n`;
        if (p.markdown) {
          md += p.markdown + "\n\n---\n\n";
        } else {
          // If no markdown, display the page's JSON structure.
          // Wrap it in a specific code block for JSON, and escape the JSON string.
          // Using `&lt;` and `&gt;` for the code block delimiters might prevent Highlight.js warnings if it's sensitive.
          // However, JSON.stringify itself outputs plain text, so `<pre><code>` is sufficient normally.
          // The warning might be because of certain markdown characters (`<`, `>`, `*`, `_`, etc.)
          // which Highlight.js parses as part of HTML entities when it shouldn't for code blocks.
          // Let's ensure the JSON is correctly wrapped for highlight.js
          md += "```json\n" + JSON.stringify(p, null, 2) + "\n```\n\n---\n\n";
        }
      });
    } else {
      md += "No pages extracted or invalid page structure.\n\n";
    }
    return md;
  }
  // generateMarkdownContent(res, file) {
  //   const fileName = file ? file.name : "Document";
  //   const processingTime = res.processing_time
  //     ? res.processing_time.toFixed(1)
  //     : "N/A";

  //   let md = `# ${fileName}\n\nExtraction in ${processingTime}s\n\n`;
  //   if (res.pages && Array.isArray(res.pages)) {
  //     res.pages.forEach((p, i) => {
  //       md += `## Page ${i + 1}\n\n`;
  //       md += p.markdown
  //         ? p.markdown + "\n\n---\n\n"
  //         : JSON.stringify(p, null, 2) + "\n\n";
  //     });
  //   } else {
  //     md += "No pages extracted or invalid page structure.\n\n";
  //   }
  //   return md;
  // }

  renderMarkdownAdv(text) {
    const raw = marked.parse(text, { breaks: true });
    return DOMPurify.sanitize(raw);
  }

  initTabSwitching() {
    this.tabButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = btn.id.replace("tab-", "content-");

        this.tabButtons.forEach((b) => {
          // Remove active class from all buttons
          b.classList.remove("active", "text-blue-600");
          b.classList.add("text-gray-600");
          // Original removal:
          b.classList.replace("text-blue-600", "text-gray-500");
          b.classList.remove("border-b-2", "border-blue-600");
        });
        this.tabContents.forEach((c) => c.classList.add("hidden"));

        // Add active class to clicked button
        btn.classList.add("active", "text-blue-600");
        btn.classList.remove("text-gray-600");
        // Original addition:
        btn.classList.replace("text-gray-500", "text-blue-600");
        btn.classList.add("border-b-2", "border-blue-600");

        document.getElementById(target).classList.remove("hidden");
        // Fixed: Use stored JSON data instead of calling .get()
        if (
          target === "content-json" &&
          this.jsonEditor &&
          this.currentJsonData
        ) {
          try {
            if (typeof this.jsonEditor.set === "function") {
              this.jsonEditor.set(this.currentJsonData); // Force refresh using stored data
            }
          } catch (err) {
            console.warn("Error refreshing JSON editor:", err);
          }
        }
        if (target === "content-comparison" && this.pdfDoc) {
          this.showPage(this.currentPdfPage);
        }
      });
    });

    document.getElementById("tab-summary").click();
  }

  initCopyButtons() {
    document.getElementById("copy-json").addEventListener("click", () => {
      let jsonContent = "";

      // Try to get content from JSON editor first, then fall back to stored data
      if (this.jsonEditor && typeof this.jsonEditor.get === "function") {
        try {
          jsonContent = JSON.stringify(this.jsonEditor.get(), null, 2);
        } catch (err) {
          console.warn("Error getting JSON from editor:", err);
          jsonContent = this.currentJsonData
            ? JSON.stringify(this.currentJsonData, null, 2)
            : "";
        }
      } else if (this.currentJsonData) {
        jsonContent = JSON.stringify(this.currentJsonData, null, 2);
      } else {
        jsonContent = document.getElementById("json-code").textContent || "";
      }

      if (jsonContent) {
        navigator.clipboard.writeText(jsonContent);
        showNotification("JSON copied!");
      } else {
        showError("No JSON content to copy");
      }
    });

    document.getElementById("copy-markdown").addEventListener("click", () => {
      const markdownContent =
        document.getElementById("markdown-code").textContent;
      if (markdownContent) {
        navigator.clipboard.writeText(markdownContent);
        showNotification("Markdown copied!");
      } else {
        showError("No Markdown content to copy");
      }
    });
  }

  initJsonExpandCollapse() {
    document.getElementById("expand-json").addEventListener("click", () => {
      if (this.jsonEditor && typeof this.jsonEditor.expandAll === "function") {
        try {
          this.jsonEditor.expandAll();
          showNotification("JSON expanded!");
        } catch (err) {
          showError("Error expanding JSON: " + err.message);
        }
      } else {
        showNotification("JSON editor not available");
      }
    });

    document.getElementById("collapse-json").addEventListener("click", () => {
      if (
        this.jsonEditor &&
        typeof this.jsonEditor.collapseAll === "function"
      ) {
        try {
          this.jsonEditor.collapseAll();
          showNotification("JSON collapsed!");
        } catch (err) {
          showError("Error collapsing JSON: " + err.message);
        }
      } else {
        showNotification("JSON editor not available");
      }
    });
  }

  // --- Page Comparison View Methods ---

  initPageComparisonControls() {
    this.prevPageButton.addEventListener("click", () =>
      this.showPage(this.currentPdfPage - 1)
    );
    this.nextPageButton.addEventListener("click", () =>
      this.showPage(this.currentPdfPage + 1)
    );
    this.zoomLevelSelect.addEventListener("change", () =>
      this.renderPage(this.currentPdfPage)
    );
    this.updatePageNavigation();
  }

  setupScrollSync() {
    let activeScroll = null;

    this.pdfContainer.addEventListener("scroll", () => {
      if (activeScroll === "pdf" || activeScroll === null) {
        activeScroll = "pdf";
        this.extractedContainer.scrollTop = this.pdfContainer.scrollTop;
      }
      clearTimeout(this._scrollTimer);
      this._scrollTimer = setTimeout(() => (activeScroll = null), 100);
    });

    this.extractedContainer.addEventListener("scroll", () => {
      if (activeScroll === "extracted" || activeScroll === null) {
        activeScroll = "extracted";
        this.pdfContainer.scrollTop = this.extractedContainer.scrollTop;
      }
      clearTimeout(this._scrollTimer);
      this._scrollTimer = setTimeout(() => (activeScroll = null), 100);
    });
  }

  async showPage(pageNum) {
    if (!this.pdfDoc) return;

    if (pageNum < 1 || pageNum > this.pdfDoc.numPages) return;

    this.currentPdfPage = pageNum;
    this.updatePageNavigation();
    await this.renderPage(pageNum);

    const fullExtractionData = this.api.lastExtractionResult;

    let pageContentHTML = `<p class="text-gray-500 italic">No extracted content for this page.</p>`;

    if (
      fullExtractionData &&
      fullExtractionData.extraction_result &&
      fullExtractionData.extraction_result.pages &&
      fullExtractionData.extraction_result.pages[pageNum - 1]
    ) {
      const pageData = fullExtractionData.extraction_result.pages[pageNum - 1];

      if (pageData.markdown) {
        pageContentHTML = this.renderMarkdownAdv(pageData.markdown);
      } else {
        pageContentHTML = `<pre><code class="language-json">${JSON.stringify(
          pageData,
          null,
          2
        )}</code></pre>`;
      }
    }

    document.getElementById("extracted-content").innerHTML = pageContentHTML;
    hljs.highlightAll();
  }

  async renderPage(pageNum) {
    if (!this.pdfDoc || !this.pdfCanvas || !this.pdfCtx) return;

    try {
      const page = await this.pdfDoc.getPage(pageNum);
      const zoom = parseFloat(this.zoomLevelSelect.value);
      const viewport = page.getViewport({ scale: zoom });

      this.pdfCanvas.height = viewport.height;
      this.pdfCanvas.width = viewport.width;

      const renderContext = {
        canvasContext: this.pdfCtx,
        viewport: viewport,
      };
      await page.render(renderContext).promise;
    } catch (err) {
      showError("Error rendering PDF page: " + err.message);
    }
  }

  updatePageNavigation() {
    if (!this.pdfDoc) {
      this.pageInfoSpan.textContent = "Page 0 of 0";
      this.prevPageButton.disabled = true;
      this.nextPageButton.disabled = true;
      return;
    }
    this.pageInfoSpan.textContent = `Page ${this.currentPdfPage} of ${this.pdfDoc.numPages}`;
    this.prevPageButton.disabled = this.currentPdfPage <= 1;
    this.nextPageButton.disabled = this.currentPdfPage >= this.pdfDoc.numPages;
  }

  updatePageComparisonView(fullExtractionData) {
    // This method is primarily called after successful extraction to set up the initial view.
    // The `this.api.lastExtractionResult` is already populated in `startExtraction`.
    this.updatePageNavigation();

    if (this.pdfDoc && this.pdfDoc.numPages > 0) {
      // If a PDF is already loaded, render the first page
      this.showPage(1);
    } else if (
      this.fileInput.files[0] &&
      this.fileInput.files[0].type === "application/pdf"
    ) {
      // If a PDF file was selected but pdfDoc isn't loaded (e.g., failed earlier)
      // The logic in startExtraction should handle loading pdfDoc.
      // This else-if is mainly for user feedback if PDF.js failed to load.
      document.getElementById(
        "extracted-content"
      ).innerHTML = `<p class="text-gray-500 italic">PDF preview not available. Please check PDF.js setup or console for errors.</p>`;
    } else {
      document.getElementById(
        "extracted-content"
      ).innerHTML = `<p class="text-gray-500 italic">Upload a PDF to see the comparison view.</p>`;
    }
  }
}
