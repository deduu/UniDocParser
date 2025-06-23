export function initProgress() {
    const extractButton = document.getElementById('extract-button');
    const progressBar = document.getElementById('upload-progress');
    const progressDiv = progressBar.querySelector('div');
    const progressLabel = document.getElementById('progress-label');
    const progressPercentage = document.getElementById('progress-percentage');
    const helpPanel = document.getElementById('help-panel');
    const resultTabs = document.getElementById('result-tabs');
    const fileInput = document.getElementById('pdf-file');
  
    extractButton.addEventListener('click', () => {
      if (!fileInput.files[0]) {
        showError('Please select a PDF file first');
        return;
      }
  
      helpPanel.classList.add('hidden');
      resultTabs.classList.remove('hidden');
      progressBar.classList.remove('hidden');
  
      // Simulate processing and then display results (for demo purposes)
      simulateProcessing().then(() => {
        displayResults({
          extraction_result: {
            source: fileInput.files[0].name,
            pages: Array(5).fill().map((_, i) => ({ page_num: i + 1 })),
            text_blocks: 42,
            tables: 3,
            processing_time: 2.4
          },
          json_output: "/outputs/result.json",
          markdown_output: "/outputs/result.md"
        });
      });
    });
  
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
  
    function showError(message) {
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
  
    // Expose displayResults globally so other modules can call it
    window.displayResults = displayResults;
  
    function displayResults(data) {
      document.getElementById('pages-count').textContent = data.extraction_result.pages.length;
      document.getElementById('text-blocks-count').textContent = data.extraction_result.text_blocks || 0;
      document.getElementById('tables-count').textContent = data.extraction_result.tables || 0;
      document.getElementById('extraction-time').textContent =
        `Extraction completed in ${data.extraction_result.processing_time.toFixed(1)} seconds`;
  
      document.getElementById('download-json').href = data.json_output;
      document.getElementById('download-markdown').href = data.markdown_output;
  
      // Sample JSON and markdown for demo
      const sampleJson = {
        metadata: {
          title: fileInput.files[0].name,
          pages: data.extraction_result.pages.length,
          extraction_date: new Date().toISOString()
        },
        pages: data.extraction_result.pages.map((page, i) => ({
          page_num: i + 1,
          content: [{
            type: "text",
            text: "Sample extracted text from page " + (i + 1),
            bbox: [72, 72, 540, 100]
          }]
        }))
      };
  
      const sampleMarkdown = `# ${fileInput.files[0].name}\n\n` +
        `*Extracted on ${new Date().toLocaleDateString()}*\n\n` +
        data.extraction_result.pages.map((page, i) => (
          `## Page ${i + 1}\n\n` +
          `Sample extracted text from page ${i + 1}\n\n` +
          (i < 2 ? `### Table Example\n\n| Header 1 | Header 2 | Header 3 |\n|----------|----------|----------|\n| Data 1 | Data 2 | Data 3 |\n| More 1 | More 2 | More 3 |\n\n` : '')
        )).join('\n');
  
      document.getElementById('json-code').textContent = JSON.stringify(sampleJson, null, 2);
      document.getElementById('markdown-code').textContent = sampleMarkdown;
      document.getElementById('markdown-preview').innerHTML = renderMarkdown(sampleMarkdown);
      hljs.highlightAll();
    }
  
    function renderMarkdown(markdown) {
      let html = markdown
        .replace(/^# (.*$)/gm, '<h1 class="text-2xl font-bold mt-4 mb-2">$1</h1>')
        .replace(/^## (.*$)/gm, '<h2 class="text-xl font-semibold mt-4 mb-2">$1</h2>')
        .replace(/^### (.*$)/gm, '<h3 class="text-lg font-medium mt-3 mb-2">$1</h3>')
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n\n/g, '</p><p class="my-2">');
      
      const tableRegex = /\n\|(.+)\|\n\|([-]+)\|\n((\|.+\|\n)+)/g;
      html = html.replace(tableRegex, function(match) {
        const rows = match.split('\n').filter(row => row.trim().length > 0);
        let table = '<div class="my-4 overflow-x-auto"><table class="min-w-full border-collapse border border-gray-300">';
        
        table += '<thead><tr>';
        rows[0].split('|').filter(cell => cell.trim().length > 0).forEach(cell => {
          table += `<th class="border border-gray-300 px-4 py-2 bg-gray-100">${cell.trim()}</th>`;
        });
        table += '</tr></thead>';
        
        table += '<tbody>';
        for (let i = 2; i < rows.length; i++) {
          table += '<tr>';
          rows[i].split('|').filter(cell => cell.trim().length > 0).forEach(cell => {
            table += `<td class="border border-gray-300 px-4 py-2">${cell.trim()}</td>`;
          });
          table += '</tr>';
        }
        table += '</tbody></table></div>';
        return table;
      });
      
      return `<p class="my-2">${html}</p>`;
    }
  }
  