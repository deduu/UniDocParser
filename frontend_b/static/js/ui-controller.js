// static/js/ui-controller.js
import { showNotification, showError } from "./components/notification.js";

export class UIController {
  constructor(state, api) {
    this.state = state;
    this.api = api;

    this.jsonEditor = null;
    this.currentJsonData = null;

    this.pdfDoc = null;
    this.currentPdfPage = 0;
    this.pdfCanvas = null;
    this.pdfCtx = null;

    this.fileInput = null;
    this.fileNameDisplay = null;
    this.extractionOptions = null;
    this.uploadDropZone = null;

    this.progressBar = null;
    this.progressLabel = null;
    this.progressPercentage = null;
    // NEW: For status indicators and messages
    this.processingIndicator = null;
    this.completedIndicator = null;
    this.processingIcon = null; // NEW: Reference to the spinning icon
    this.progressSubMessage = null;

    this.extractButton = null;
    this.helpPanel = null;
    this.resultTabs = null;

    this.tabButtons = null;
    this.tabContents = null;

    this.pdfContainer = null;
    this.extractedContainer = null;
    this.prevPageButton = null;
    this.nextPageButton = null;
    this.pageInfoSpan = null;
    this.zoomLevelSelect = null;

    this.stepIndicators = [];
    this.helpToggle = null;

    this._scrollTimer = null;

    // NEW: File Info Card elements
    this.fileInfoCard = null;
    this.infoFileName = null;
    this.infoPageCount = null;
    this.infoFileSize = null;
    this.infoExtractionStatus = null;
    this.infoStatusText = null;
  }

  init() {
    this.initDOMElements();
    hljs.highlightAll();
    this.setupDragAndDrop();

    this.fileInput.addEventListener("change", () => {
      if (this.fileInput.files[0]) {
        this.handleFileSelection(this.fileInput.files[0]);
      }
    });
    this.extractButton.addEventListener("click", () => this.startExtraction());
    if (this.helpToggle) {
      this.helpToggle.addEventListener("click", () => {
        this.helpPanel.scrollIntoView({ behavior: "smooth" });
      });
    }

    this.initTabSwitching();
    this.initCopyButtons();
    this.initJsonExpandCollapse();
    this.initPageComparisonControls();
    this.setupScrollSync();

    this.updateStepIndicator(0);
  }

  initDOMElements() {
    this.fileInput = document.getElementById("pdf-file");
    this.fileNameDisplay = document.getElementById("file-name");
    this.extractionOptions = document.getElementById("extraction-options");
    this.uploadDropZone = document.getElementById("upload-drop-zone");

    this.progressBar = document.getElementById("upload-progress");
    this.progressLabel = document.getElementById("progress-label");
    this.progressPercentage = document.getElementById("progress-percentage");
    // NEW: Get references to new status elements
    this.processingIndicator = document.getElementById("processing-indicator");
    this.completedIndicator = document.getElementById("completed-indicator");
    this.processingIcon = document.getElementById("processing-icon"); // NEW
    this.progressSubMessage = document.getElementById("progress-sub-message");

    this.extractButton = document.getElementById("extract-button");
    this.helpPanel = document.getElementById("help-panel");
    this.resultTabs = document.getElementById("result-tabs");

    this.tabButtons = document.querySelectorAll(".tab-button");
    this.tabContents = document.querySelectorAll(".tab-content");

    this.pdfContainer = document.getElementById("pdf-container");
    this.extractedContainer = document.getElementById("extracted-container");
    this.pdfCanvas = document.getElementById("pdf-canvas");
    this.pdfCtx = this.pdfCanvas?.getContext("2d");
    this.prevPageButton = document.getElementById("prev-page");
    this.nextPageButton = document.getElementById("next-page");
    this.pageInfoSpan = document.getElementById("page-info");
    this.zoomLevelSelect = document.getElementById("zoom-level");

    this.stepIndicators = [
      document.getElementById("step-1"),
      document.getElementById("step-2"),
      document.getElementById("step-3"),
      document.getElementById("step-4"),
    ].filter(Boolean);

    this.helpToggle = document.getElementById("help-toggle");

    // NEW: Get references to File Info Card elements
    this.fileInfoCard = document.getElementById("file-info-card");
    this.infoFileName = document.getElementById("info-file-name");
    this.infoPageCount = document.getElementById("info-page-count");
    this.infoFileSize = document.getElementById("info-file-size");
    this.infoExtractionStatus = document.getElementById(
      "info-extraction-status"
    );
    this.infoStatusText = document.getElementById("info-status-text");
  }

  updateStepIndicator(step) {
    this.stepIndicators.forEach((element, index) => {
      if (element) {
        if (index <= step) {
          element.classList.add("step-active");
          element.classList.remove("bg-gray-300", "text-gray-600");
        } else {
          element.classList.remove("step-active");
          element.classList.add("bg-gray-300", "text-gray-600");
        }
      }
    });
  }

  setupDragAndDrop() {
    const dropArea = this.uploadDropZone;

    if (!dropArea) {
      console.warn(
        "Drag and drop area not found (ID: upload-drop-zone). Drag and drop functionality will not be available."
      );
      return;
    }

    ["dragenter", "dragover", "dragleave", "drop"].forEach((evt) => {
      dropArea.addEventListener(evt, (e) => {
        e.preventDefault();
        e.stopPropagation();
      });
    });
    // Keeping these as they might still provide a subtle visual cue or override default browser styles
    ["dragenter", "dragover"].forEach((evt) =>
      dropArea.classList.add("border-blue-500", "bg-blue-50")
    );
    ["dragleave", "drop"].forEach((evt) =>
      dropArea.classList.remove("border-blue-500", "bg-blue-50")
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
    const fileNameSpan = this.fileNameDisplay.querySelector("span");
    if (fileNameSpan) {
      fileNameSpan.textContent = file.name;
    }
    this.fileNameDisplay.classList.remove("hidden");
    this.extractionOptions.classList.remove("hidden");

    this.updateStepIndicator(1);

    // NEW: Update File Info Card with file details
    if (this.fileInfoCard) this.fileInfoCard.classList.remove("hidden");
    if (this.infoFileName) this.infoFileName.textContent = file.name;
    if (this.infoFileSize)
      this.infoFileSize.textContent = this.formatFileSize(file.size);
    // Reset page count, it will be updated after extraction
    if (this.infoPageCount) this.infoPageCount.textContent = "N/A";

    // Set initial status for the file info card
    this.updateFileInfoStatus("pending");
  }

  formatFileSize(bytes) {
    if (bytes < 1024) return bytes + " bytes";
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
    return (bytes / 1024 / 1024).toFixed(1) + " MB";
  }

  // NEW METHOD: To update the file info card status
  updateFileInfoStatus(status, message = "") {
    if (!this.infoExtractionStatus || !this.infoStatusText) return;

    // Reset classes
    this.infoExtractionStatus.classList.remove(
      "bg-blue-100",
      "text-blue-700", // Pending/Uploading
      "bg-green-100",
      "text-green-700", // Complete
      "bg-red-100",
      "text-red-700" // Error
    );
    this.infoExtractionStatus.innerHTML = ""; // Clear current icon and text

    let iconClass = "";
    let statusText = message;

    switch (status) {
      case "pending":
        iconClass = "fas fa-circle-notch fa-spin text-blue-500";
        statusText = message || "Uploading...";
        this.infoExtractionStatus.classList.add("bg-blue-100", "text-blue-700");
        break;
      case "processing":
        iconClass = "fas fa-cog fa-spin text-purple-500"; // Different icon/color for processing
        statusText = message || "Processing...";
        this.infoExtractionStatus.classList.add("bg-blue-100", "text-blue-700"); // Keep blue for ongoing
        break;
      case "complete":
        iconClass = "fas fa-check-circle text-green-500";
        statusText = message || "Extraction Complete";
        this.infoExtractionStatus.classList.add(
          "bg-green-100",
          "text-green-700"
        );
        break;
      case "error":
        iconClass = "fas fa-times-circle text-red-500";
        statusText = message || "Extraction Failed";
        this.infoExtractionStatus.classList.add("bg-red-100", "text-red-700");
        break;
      default:
        iconClass = "fas fa-info-circle text-gray-500";
        statusText = message || "Unknown Status";
        break;
    }
    this.infoExtractionStatus.innerHTML = `<i class="${iconClass} mr-2"></i><span id="info-status-text">${statusText}</span>`;
  }

  async startExtraction() {
    if (!this.fileInput.files[0]) {
      return showError("Please select a PDF first");
    }

    this.helpPanel.classList.add("hidden");
    this.resultTabs.classList.remove("hidden");

    this.progressBar.classList.remove("hidden");
    this.progressLabel.textContent = "Uploading...";
    this.progressPercentage.textContent = "0%";
    this.setProgress(0);

    // Update File Info Card status to pending/uploading
    this.updateFileInfoStatus("pending", "Uploading...");

    // Show processing indicator, hide completed indicator
    if (this.processingIndicator)
      this.processingIndicator.classList.remove("hidden");
    if (this.completedIndicator)
      this.completedIndicator.classList.add("hidden");
    if (this.processingIcon) this.processingIcon.classList.add("fa-spin"); // NEW
    // Show sub-message
    if (this.progressSubMessage)
      this.progressSubMessage.classList.remove("hidden");

    this.updateStepIndicator(2);

    const formData = new FormData();
    formData.append("file", this.fileInput.files[0]);
    ["extract-text", "extract-tables", "extract-images"].forEach((id) => {
      const checkbox = document.getElementById(id);
      if (checkbox) {
        formData.append(id, checkbox.checked);
      }
    });
    const pageRange = document.getElementById("page-range").value;
    if (pageRange) formData.append("page_range", pageRange);

    try {
      const data = await this.api.extractPdf(formData, (pct) => {
        this.progressPercentage.textContent = pct + "%";
        this.setProgress(pct);

        if (pct < 100) {
          this.progressLabel.textContent = "Uploading...";
          // Keep processing indicator, hide completed
          if (this.processingIndicator)
            this.processingIndicator.classList.remove("hidden");
          if (this.completedIndicator)
            this.completedIndicator.classList.add("hidden");
          if (this.processingIcon) this.processingIcon.classList.add("fa-spin"); // Ensure spinning during upload
          if (this.progressSubMessage)
            this.progressSubMessage.textContent = "This may take a few moments";
          // Update file info card status for upload/processing
          this.updateFileInfoStatus("pending", `Uploading... ${pct}%`); // Use pending for upload
        } else {
          // When pct is 100 or more, processing is considered complete
          this.progressLabel.textContent = "Processing completed";
          // Hide processing indicator, show completed
          if (this.processingIndicator)
            this.processingIndicator.classList.add("hidden");
          if (this.completedIndicator)
            this.completedIndicator.classList.remove("hidden");
          if (this.processingIcon)
            this.processingIcon.classList.remove("fa-spin"); // NEW: Stop the spinning!
          if (this.progressSubMessage)
            this.progressSubMessage.textContent = "Results are ready!";
          // Update file info card status to complete
          this.updateFileInfoStatus("complete", "Extraction Complete"); // Set to complete status
        }
      });

      console.log("Full API response 'data':", data);
      console.log(
        "Full API response 'data_extraction_result':",
        data.extraction_result
      );

      const extractionResult =
        data && data.extraction_result ? data.extraction_result : {};

      this.currentJsonData = extractionResult;
      this.api.lastExtractionResult = data;

      this.displayResults(data);

      // NEW: Update file info card with actual page count after extraction
      if (this.infoPageCount && extractionResult.pages) {
        this.infoPageCount.textContent = extractionResult.pages.length;
      }
      // Ensure the status is 'complete' on the file info card, in case the last pct update didn't trigger it.
      this.updateFileInfoStatus("complete", "Extraction Complete");

      const file = this.fileInput.files[0];
      if (file && typeof pdfjsLib !== "undefined") {
        const fileReader = new FileReader();
        fileReader.onload = async () => {
          const pdfData = new Uint8Array(fileReader.result);
          try {
            this.pdfDoc = await pdfjsLib.getDocument({ data: pdfData }).promise;
            this.showPage(1);
          } catch (err) {
            showError("Error loading PDF for preview: " + err.message);
            this.pdfDoc = null;
            this.updatePageNavigation();
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

      if (!this.jsonEditor) {
        const container = document.getElementById("json-code");
        if (container) {
          container.innerHTML = "";
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
      this.updateStepIndicator(3); // Assuming step 3 is "Results ready"
    } catch (err) {
      showError(err.message);
      this.progressBar.classList.add("hidden");
      this.progressLabel.textContent = "Error";
      this.progressPercentage.textContent = "";
      this.pdfDoc = null;
      this.updatePageNavigation();
      this.updateStepIndicator(1);
      // Ensure all indicators are hidden and message is set on error
      if (this.processingIndicator)
        this.processingIndicator.classList.add("hidden");
      if (this.completedIndicator)
        this.completedIndicator.classList.add("hidden");
      if (this.processingIcon) this.processingIcon.classList.remove("fa-spin"); // Ensure it stops spinning on error
      if (this.progressSubMessage)
        this.progressSubMessage.textContent =
          "An error occurred. Please try again.";
      // NEW: Update file info card status on error
      this.updateFileInfoStatus("error", "Extraction Failed");
    }
  }

  setProgress(percent) {
    const circle = document.getElementById("progress-circle");
    if (circle) {
      const radius = circle.r.baseVal.value || 52;
      const circumference = 2 * Math.PI * radius;
      const offset = circumference - (percent / 100) * circumference;
      circle.style.strokeDasharray = `${circumference} ${circumference}`;
      circle.style.strokeDashoffset = offset;
      circle.style.transition = "stroke-dashoffset 0.3s ease-in-out";
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

    document.getElementById("download-json").href =
      DOWNLOAD_URL_BASE + data.json_output || "#";
    document.getElementById("download-markdown").href =
      DOWNLOAD_URL_BASE + data.markdown_output || "#";

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
          md += "```json\n" + JSON.stringify(p, null, 2) + "\n```\n\n---\n\n";
        }
      });
    } else {
      md += "No pages extracted or invalid page structure.\n\n";
    }
    return md;
  }

  renderMarkdownAdv(text) {
    const raw = marked.parse(text, { breaks: true });
    return DOMPurify.sanitize(raw);
  }

  initTabSwitching() {
    this.tabButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        const target = btn.id.replace("tab-", "content-");

        this.tabButtons.forEach((b) => {
          b.classList.remove("active", "text-blue-600");
          b.classList.add("text-gray-600");
          b.classList.replace("text-blue-600", "text-gray-500");
          b.classList.remove("border-b-2", "border-blue-600");
        });
        this.tabContents.forEach((c) => c.classList.add("hidden"));

        btn.classList.add("active", "text-blue-600");
        btn.classList.remove("text-gray-600");
        btn.classList.replace("text-gray-500", "text-blue-600");
        btn.classList.add("border-b-2", "border-blue-600");

        document.getElementById(target).classList.remove("hidden");

        if (
          target === "content-json" &&
          this.jsonEditor &&
          this.currentJsonData
        ) {
          try {
            if (typeof this.jsonEditor.set === "function") {
              this.jsonEditor.set(this.currentJsonData);
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
    if (this.prevPageButton) {
      this.prevPageButton.addEventListener("click", () =>
        this.showPage(this.currentPdfPage - 1)
      );
    }
    if (this.nextPageButton) {
      this.nextPageButton.addEventListener("click", () =>
        this.showPage(this.currentPdfPage + 1)
      );
    }
    if (this.zoomLevelSelect) {
      this.zoomLevelSelect.addEventListener("change", () =>
        this.renderPage(this.currentPdfPage)
      );
    }
    this.updatePageNavigation();
  }

  setupScrollSync() {
    let activeScroll = null;

    if (this.pdfContainer) {
      this.pdfContainer.addEventListener("scroll", () => {
        if (activeScroll === "pdf" || activeScroll === null) {
          activeScroll = "pdf";
          if (this.extractedContainer) {
            this.extractedContainer.scrollTop = this.pdfContainer.scrollTop;
          }
        }
        clearTimeout(this._scrollTimer);
        this._scrollTimer = setTimeout(() => (activeScroll = null), 100);
      });
    }

    if (this.extractedContainer) {
      this.extractedContainer.addEventListener("scroll", () => {
        if (activeScroll === "extracted" || activeScroll === null) {
          activeScroll = "extracted";
          if (this.pdfContainer) {
            this.pdfContainer.scrollTop = this.extractedContainer.scrollTop;
          }
        }
        clearTimeout(this._scrollTimer);
        this._scrollTimer = setTimeout(() => (activeScroll = null), 100);
      });
    }
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

    // Add a null check for extracted-content as well for robustness
    const extractedContentElement =
      document.getElementById("extracted-content");
    if (extractedContentElement) {
      extractedContentElement.innerHTML = pageContentHTML;
      hljs.highlightAll();
    } else {
      console.warn("Element with ID 'extracted-content' not found.");
    }
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
    // Add null checks for pageInfoSpan, prevPageButton, nextPageButton
    if (!this.pdfDoc) {
      if (this.pageInfoSpan) this.pageInfoSpan.textContent = "Page 0 of 0";
      if (this.prevPageButton) this.prevPageButton.disabled = true;
      if (this.nextPageButton) this.nextPageButton.disabled = true;
      return;
    }
    if (this.pageInfoSpan) {
      this.pageInfoSpan.textContent = `Page ${this.currentPdfPage} of ${this.pdfDoc.numPages}`;
    }
    if (this.prevPageButton) {
      this.prevPageButton.disabled = this.currentPdfPage <= 1;
    }
    if (this.nextPageButton) {
      this.nextPageButton.disabled =
        this.currentPdfPage >= this.pdfDoc.numPages;
    }
  }

  updatePageComparisonView(fullExtractionData) {
    this.updatePageNavigation();

    // Add null checks for elements accessed here
    const extractedContentElement =
      document.getElementById("extracted-content");

    if (this.pdfDoc && this.pdfDoc.numPages > 0) {
      this.showPage(1);
    } else if (
      this.fileInput.files[0] &&
      this.fileInput.files[0].type === "application/pdf"
    ) {
      if (extractedContentElement) {
        extractedContentElement.innerHTML = `<p class="text-gray-500 italic">PDF preview not available. Please check PDF.js setup or console for errors.</p>`;
      }
    } else {
      if (extractedContentElement) {
        extractedContentElement.innerHTML = `<p class="text-gray-500 italic">Upload a PDF to see the comparison view.</p>`;
      }
    }
  }
}
