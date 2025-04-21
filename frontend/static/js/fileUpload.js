export function initFileUpload() {
    const form = document.getElementById('pdf-upload-form');
    const fileInput = document.getElementById('pdf-file');
    const fileNameDisplay = document.getElementById('file-name');
    const extractionOptions = document.getElementById('extraction-options');
    const dropArea = form.querySelector('label');
  
    // Prevent default behaviors for drag events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
      dropArea.addEventListener(eventName, preventDefaults, false);
    });
  
    function preventDefaults(e) {
      e.preventDefault();
      e.stopPropagation();
    }
  
    ['dragenter', 'dragover'].forEach(eventName => {
      dropArea.addEventListener(eventName, () => dropArea.classList.add('border-blue-500', 'bg-blue-50'), false);
    });
  
    ['dragleave', 'drop'].forEach(eventName => {
      dropArea.addEventListener(eventName, () => dropArea.classList.remove('border-blue-500', 'bg-blue-50'), false);
    });
  
    dropArea.addEventListener('drop', handleDrop, false);
    fileInput.addEventListener('change', handleFiles, false);
  
    function handleDrop(e) {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files.length > 0) {
        handleFileSelection(files[0]);
      }
    }
  
    function handleFiles() {
      if (fileInput.files.length > 0) {
        handleFileSelection(fileInput.files[0]);
      }
    }
  
    function handleFileSelection(file) {
      if (!file || file.type !== 'application/pdf') {
        showError('Please upload a PDF file');
        return;
      }
      
      fileNameDisplay.textContent = file.name;
      fileNameDisplay.classList.remove('hidden');
      extractionOptions.classList.remove('hidden');
  
      // Update summary tab details
      document.getElementById('file-title').textContent = file.name;
      document.getElementById('file-details').textContent = `Size: ${formatFileSize(file.size)}`;
    }
  
    function formatFileSize(bytes) {
      if (bytes < 1024) return bytes + ' bytes';
      else if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
      else return (bytes / 1048576).toFixed(1) + ' MB';
    }
  
    function showError(message) {
      // Basic error toast (you can enhance or centralize this later)
      const toast = document.createElement('div');
      toast.className = 'fixed top-4 right-4 bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded shadow-md flex items-start max-w-sm z-50';
      toast.innerHTML = `
        <div class="text-red-500 mr-3"><i class="fas fa-exclamation-circle"></i></div>
        <div>
          <div class="font-bold">Error</div>
          <div>${message}</div>
        </div>
        <button class="ml-auto text-red-500 hover:text-red-700"><i class="fas fa-times"></i></button>
      `;
      document.body.appendChild(toast);
      toast.querySelector('button').addEventListener('click', () => toast.remove());
      setTimeout(() => { if (document.body.contains(toast)) toast.remove(); }, 5000);
    }
  }
  