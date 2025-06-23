export function initClipboard() {
    const copyJsonBtn = document.getElementById('copy-json');
    const copyMarkdownBtn = document.getElementById('copy-markdown');
  
    copyJsonBtn.addEventListener('click', () => {
      copyToClipboard(document.getElementById('json-code').textContent);
      showCopySuccess(copyJsonBtn);
    });
  
    copyMarkdownBtn.addEventListener('click', () => {
      copyToClipboard(document.getElementById('markdown-code').textContent);
      showCopySuccess(copyMarkdownBtn);
    });
  
    function copyToClipboard(text) {
      navigator.clipboard.writeText(text).catch(err => {
        console.error('Failed to copy text: ', err);
      });
    }
  
    function showCopySuccess(button) {
      const originalText = button.innerHTML;
      button.innerHTML = '<i class="fas fa-check mr-1"></i> Copied!';
      button.classList.add('bg-green-100', 'text-green-700');
      
      setTimeout(() => {
        button.innerHTML = originalText;
        button.classList.remove('bg-green-100', 'text-green-700');
      }, 2000);
    }
  }
  