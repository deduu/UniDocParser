// static/js/app.js
document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('pdf-upload-form');
    const fileInput = document.getElementById('pdf-file');
    const progressBar = document.getElementById('upload-progress');
    const extractionResults = document.getElementById('extraction-results');
    const resultContent = document.getElementById('result-content');

    // Drag and drop file upload
    const dropArea = form.querySelector('label');
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
        dropArea.classList.add('border-blue-500');
    }

    function unhighlight() {
        dropArea.classList.remove('border-blue-500');
    }

    // File selection and upload
    dropArea.addEventListener('drop', handleDrop, false);
    fileInput.addEventListener('change', handleFiles, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFileUpload(files[0]);
    }

    function handleFiles() {
        handleFileUpload(fileInput.files[0]);
    }

    function handleFileUpload(file) {
        if (!file || file.type !== 'application/pdf') {
            alert('Please upload a PDF file');
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        // Reset previous results
        progressBar.classList.remove('hidden');
        progressBar.querySelector('div').style.width = '0%';
        extractionResults.classList.add('hidden');
        resultContent.innerHTML = '';

        fetch('/api/v1/extract-pdf/', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            // Check if response is OK (status in 200-299 range)
            if (!response.ok) {
                // Try to parse error details
                return response.json().then(errorData => {
                    throw new Error(errorData.message || 'Upload failed');
                });
            }
            return response.json();
        })
        .then(data => {
            // Update progress bar
            progressBar.querySelector('div').style.width = '100%';
            
            // Show extraction results
            extractionResults.classList.remove('hidden');
            
            // Populate results
            const resultHTML = `
                <div class="space-y-2">
                    <p><strong>Source:</strong> ${data.extraction_result.source}</p>
                    <p><strong>Pages Extracted:</strong> ${data.extraction_result.pages.length}</p>
                    <div class="mt-4">
                        <a href="/api/v1/download/${encodeURIComponent(data.json_output.split('/').pop())}" 
                           class="bg-blue-500 text-white px-4 py-2 rounded mr-2 hover:bg-blue-600">
                            Download JSON
                        </a>
                        <a href="/api/v1/download/${encodeURIComponent(data.markdown_output.split('/').pop())}" 
                           class="bg-green-500 text-white px-4 py-2 rounded hover:bg-green-600">
                            Download Markdown
                        </a>
                    </div>
                </div>
            `;
            
            resultContent.innerHTML = resultHTML;
        })
        .catch(error => {
            console.error('Error:', error);
            
            // Show user-friendly error message
            progressBar.classList.add('hidden');
            extractionResults.classList.remove('hidden');
            resultContent.innerHTML = `
                <div class="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
                    <strong class="font-bold">Error!</strong>
                    <span class="block sm:inline">${error.message || 'PDF extraction failed'}</span>
                </div>
            `;
        });
    }
});