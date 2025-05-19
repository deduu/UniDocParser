// static/js/app.js

// == DOM Elements ==
let form, fileInput, fileNameDisplay, extractionOptions;
let progressBar, progressDiv, progressLabel, progressPercentage;
let extractButton, helpPanel, resultTabs, tabButtons, tabContents;

// == Initialization ==
document.addEventListener('DOMContentLoaded', () => {
  // Grab references to DOM elements
  initDOMElements();

  // Initialize highlight.js
  hljs.highlightAll();

  // Setup drag & drop for PDF
  setupDragAndDrop();

  // Setup file input event
  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      handleFileSelection(fileInput.files[0]);
    }
  });

  // Extract button
  extractButton.addEventListener('click', startExtraction);

  // Initialize tab switching
  initTabSwitching();

  // Copy to clipboard
  initCopyButtons();

  // JSON Expand/Collapse (Demo)
  initJsonExpandCollapse();
});

// == Step 1: DOM Element References ==
function initDOMElements() {
  form = document.getElementById('pdf-upload-form');
  fileInput = document.getElementById('pdf-file');
  fileNameDisplay = document.getElementById('file-name');
  extractionOptions = document.getElementById('extraction-options');

  progressBar = document.getElementById('upload-progress');
  // Fix: Select the inner progress bar element (with class 'bg-blue-600') instead of the first div
  progressDiv = progressBar.querySelector('.bg-blue-600');
  progressLabel = document.getElementById('progress-label');
  progressPercentage = document.getElementById('progress-percentage');

  extractButton = document.getElementById('extract-button');
  helpPanel = document.getElementById('help-panel');
  resultTabs = document.getElementById('result-tabs');

  tabButtons = document.querySelectorAll('.tab-button');
  tabContents = document.querySelectorAll('.tab-content');
}

// == Step 2: Drag-and-Drop Setup ==
function setupDragAndDrop() {
  const dropArea = form.querySelector('label');

  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, preventDefaults, false);
  });

  function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
  }

  ['dragenter', 'dragover'].forEach(eventName => {
    dropArea.addEventListener(eventName, () => highlight(dropArea), false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropArea.addEventListener(eventName, () => unhighlight(dropArea), false);
  });

  dropArea.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      handleFileSelection(files[0]);
    }
  });
}

function highlight(area) {
  area.classList.add('border-blue-500', 'bg-blue-50');
}

function unhighlight(area) {
  area.classList.remove('border-blue-500', 'bg-blue-50');
}

// == Step 3: File Selection Logic ==
function handleFileSelection(file) {
  if (!file || file.type !== 'application/pdf') {
    showError('Please upload a PDF file');
    return;
  }

  // Display file name
  fileNameDisplay.textContent = file.name;
  fileNameDisplay.classList.remove('hidden');

  // Show extraction options
  extractionOptions.classList.remove('hidden');

  // Update file display in summary tab
  document.getElementById('file-title').textContent = file.name;
  document.getElementById('file-details').textContent = `Size: ${formatFileSize(file.size)}`;
}

function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' bytes';
  else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  else return (bytes / 1048576).toFixed(1) + ' MB';
}

// == Step 4: Start Extraction ==
function startExtraction() {
    // Make sure a file is selected
    if (!fileInput.files[0]) {
      showError('Please select a PDF file first');
      return;
    }
  
    // Hide help panel and show result tabs
    helpPanel.classList.add('hidden');
    resultTabs.classList.remove('hidden');
  
    // Show the progress bar
    progressBar.classList.remove('hidden');
    progressLabel.textContent = 'Uploading...';
    progressDiv.style.width = '0%';
    progressPercentage.textContent = '0%';
  
    // Gather extraction options
    const extractText = document.getElementById('extract-text').checked;
    const extractTables = document.getElementById('extract-tables').checked;
    const extractImages = document.getElementById('extract-images').checked;
    const pageRange = document.getElementById('page-range').value;
  
    // Prepare form data
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('extract_text', extractText);
    formData.append('extract_tables', extractTables);
    formData.append('extract_images', extractImages);
    if (pageRange) {
      formData.append('page_range', pageRange);
    }
  
    // Create an XHR to track upload progress
    const xhr = new XMLHttpRequest();
    xhr.open('POST', '/api/v1/extract-pdf/');
  
    // Update progress bar on upload progress
    xhr.upload.onprogress = function(e) {
      if (e.lengthComputable) {
        const percent = Math.round((e.loaded / e.total) * 100);
        progressDiv.style.width = percent + '%';
        progressPercentage.textContent = percent + '%';
        
        // Once upload hits 100%, the server is processing
        // but we only see "Uploading" progress unless we get more updates from server
        if (percent >= 100) {
          progressLabel.textContent = 'Processing...';
        }
      }
    };
  
    // Handle final result
    xhr.onload = function() {
      // Clear the progress bar (or leave it at 100%)
      progressDiv.style.width = '100%';
      progressPercentage.textContent = '100%';
  
      // If the server responded OK
      if (xhr.status === 200) {
        try {
          const response = JSON.parse(xhr.responseText);
          displayResults(response);
        } catch (err) {
          showError('Failed to parse server response');
        }
      } else {
        showError('Upload failed. Server responded with status ' + xhr.status);
      }
    };
  
    // Handle network errors
    xhr.onerror = function() {
      showError('An error occurred during the upload');
    };
  
    // Send the request
    xhr.send(formData);
  }
  

// == Step 5: Simulate Progress (Demo Purposes) ==
function simulateProcessing() {
  return new Promise(resolve => {
    let progress = 0;
    const interval = setInterval(() => {
      progress += 5;
      progressDiv.style.width = `${progress}%`;
      progressPercentage.textContent = `${progress}%`;

      if (progress <= 30) {
        progressLabel.textContent = 'Uploading...';
      } else if (progress <= 60) {
        progressLabel.textContent = 'Extracting content...';
      } else if (progress <= 90) {
        progressLabel.textContent = 'Processing data...';
      } else {
        progressLabel.textContent = 'Finalizing...';
      }

      if (progress >= 100) {
        clearInterval(interval);
        setTimeout(resolve, 500);
      }
    }, 100);
  });
}

// == Step 6: Display Results After Extraction ==
function displayResults(data) {
    // Update summary fields using the API response
    document.getElementById('pages-count').textContent = data.extraction_result.pages.length;
    document.getElementById('text-blocks-count').textContent = data.extraction_result.text_blocks || 0;
    document.getElementById('tables-count').textContent = data.extraction_result.tables || 0;
    document.getElementById('extraction-time').textContent =
      `Extraction completed in ${data.extraction_result.processing_time.toFixed(1)} seconds`;
  
    // Set download links from the response
    document.getElementById('download-json').href = DOWNLOAD_URL_BASE + data.json_output;
    document.getElementById('download-markdown').href = DOWNLOAD_URL_BASE + data.markdown_output;

  
    // Display the actual extraction result JSON in the JSON tab
    document.getElementById('json-code').textContent = JSON.stringify(data.extraction_result, null, 2);
  
    // Generate Markdown content based on the actual extracted data
    let markdownContent = `# ${fileInput.files[0].name}\n\n`;
    markdownContent += `Extraction completed in ${data.extraction_result.processing_time.toFixed(1)} seconds\n\n`;
    
    // Loop through each page and add its text (if available) to the markdown
    data.extraction_result.pages.forEach((page, index) => {
      markdownContent += `## Page ${index + 1}\n\n`;
      if (page.markdown) {
        markdownContent += `${page.markdown}`;
        markdownContent += `\n\n---\n\n`;
      } 

      else {
        // Fallback: If no text field exists, output the entire page object as JSON
        markdownContent += `${JSON.stringify(page, null, 2)}\n\n`;
      }
    });
    
    // Update markdown code and preview tabs
    document.getElementById('markdown-code').textContent = markdownContent;
    document.getElementById('markdown-preview').innerHTML = renderMarkdown(markdownContent);
  
    // Re-highlight code blocks for proper formatting
    hljs.highlightAll();
  }
  

// == Step 7: Simple Markdown Rendering (Demo) ==
function renderMarkdown(markdown) {
  var showdown  = require('showdown');
  var converter = new showdown.Converter();
  converter.setOption('tables', true);
  let html      = converter.makeHtml(markdown);

  // // Very simplistic parser for demonstration
  // let html = markdown
  //   .replace(/^# (.*$)/gm, '<h1 class="text-2xl font-bold mt-4 mb-2">$1</h1>')
  //   .replace(/^## (.*$)/gm, '<h2 class="text-xl font-semibold mt-4 mb-2">$1</h2>')
  //   .replace(/^### (.*$)/gm, '<h3 class="text-lg font-medium mt-3 mb-2">$1</h3>')
  //   .replace(/^#### (.*$)/gm, '<h4 class="text-md font-medium mt-3 mb-2">$1</h4>')
  //   .replace(/^##### (.*$)/gm, '<h5 class="text-sm font-medium mt-3 mb-2">$1</h5>')
  //   .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  //   .replace(/\*(.*?)\*/g, '<em>$1</em>')
  //   .replace(/\n\n/g, '</p><p class="my-2">');

  // // Very basic table rendering
  // const tableRegex = /\n\|(.+)\|\n\|([-]+)\|\n((\|.+\|\n)+)/g;
  // html = html.replace(tableRegex, function(match) {
  //   const rows = match.split('\n').filter(row => row.trim().length > 0);
  //   let table = '<div class="my-4 overflow-x-auto"><table class="min-w-full border-collapse border border-gray-300">';

  //   // Header
  //   table += '<thead><tr>';
  //   rows[0].split('|').filter(cell => cell.trim().length > 0).forEach(cell => {
  //     table += `<th class="border border-gray-300 px-4 py-2 bg-gray-100">${cell.trim()}</th>`;
  //   });
  //   table += '</tr></thead>';

  //   // Body
  //   table += '<tbody>';
  //   for (let i = 2; i < rows.length; i++) {
  //     table += '<tr>';
  //     rows[i].split('|').filter(cell => cell.trim().length > 0).forEach(cell => {
  //       table += `<td class="border border-gray-300 px-4 py-2">${cell.trim()}</td>`;
  //     });
  //     table += '</tr>';
  //   }
  //   table += '</tbody></table></div>';
  //   return table;
  // });

  return `<p class="my-2">${html}</p>`;
}

function renderMarkdown_adv(markdownText) {
  // Convert markdown → HTML with Marked…
  const rawHtml = marked.parse(markdownText, { breaks: true });
  // …then sanitize it so we don’t inject anything nasty
  return DOMPurify.sanitize(rawHtml);
}

// == Step 8: Tab Switching ==
function initTabSwitching() {
  tabButtons.forEach(button => {
    button.addEventListener('click', () => {
      const target = button.id.replace('tab-', 'content-');
      
      // Update active tab button
      tabButtons.forEach(btn => {
        btn.classList.remove('text-blue-600', 'border-b-2', 'border-blue-600');
        btn.classList.add('text-gray-500', 'hover:text-gray-700');
      });
      button.classList.remove('text-gray-500', 'hover:text-gray-700');
      button.classList.add('text-blue-600', 'border-b-2', 'border-blue-600');

      // Show selected tab content
      tabContents.forEach(content => content.classList.add('hidden'));
      document.getElementById(target).classList.remove('hidden');
    });
  });
}

// == Step 9: Copy Buttons (JSON & Markdown) ==
function initCopyButtons() {
  document.getElementById('copy-json').addEventListener('click', () => {
    copyToClipboard(document.getElementById('json-code').textContent);
    showCopySuccess('copy-json');
  });
  document.getElementById('copy-markdown').addEventListener('click', () => {
    copyToClipboard(document.getElementById('markdown-code').textContent);
    showCopySuccess('copy-markdown');
  });
}

function copyToClipboard(text) {
  navigator.clipboard.writeText(text).catch(err => {
    console.error('Failed to copy text: ', err);
  });
}

function showCopySuccess(buttonId) {
  const button = document.getElementById(buttonId);
  const originalText = button.innerHTML;
  button.innerHTML = '<i class="fas fa-check mr-1"></i> Copied!';
  button.classList.add('bg-green-100', 'text-green-700');

  setTimeout(() => {
    button.innerHTML = originalText;
    button.classList.remove('bg-green-100', 'text-green-700');
  }, 2000);
}

// == Step 10: Expand/Collapse JSON (Demo) ==
function initJsonExpandCollapse() {
  document.getElementById('expand-json').addEventListener('click', () => {
    // For demonstration, highlight button
    const button = document.getElementById('expand-json');
    button.classList.add('bg-blue-100', 'text-blue-700');
    setTimeout(() => button.classList.remove('bg-blue-100', 'text-blue-700'), 500);
  });

  document.getElementById('collapse-json').addEventListener('click', () => {
    // For demonstration, highlight button
    const button = document.getElementById('collapse-json');
    button.classList.add('bg-blue-100', 'text-blue-700');
    setTimeout(() => button.classList.remove('bg-blue-100', 'text-blue-700'), 500);
  });
}

// == General Purpose Error Notification ==
function showError(message) {
  // Create an error toast notification
  const toast = document.createElement('div');
  toast.className = 'fixed top-4 right-4 bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded shadow-md flex items-start max-w-sm z-50';
  toast.innerHTML = `
    <div class="text-red-500 mr-3">
        <i class="fas fa-exclamation-circle"></i>
    </div>
    <div>
        <div class="font-bold">Error</div>
        <div>${message}</div>
    </div>
    <button class="ml-auto text-red-500 hover:text-red-700">
        <i class="fas fa-times"></i>
    </button>
  `;

  document.body.appendChild(toast);
  
  // Close button
  toast.querySelector('button').addEventListener('click', () => {
    toast.remove();
  });
  
  // Auto-remove after 5 seconds
  setTimeout(() => {
    if (document.body.contains(toast)) {
      toast.remove();
    }
  }, 5000);
}
