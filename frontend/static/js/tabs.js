export function initTabs() {
    const tabButtons = document.querySelectorAll('.tab-button');
    const tabContents = document.querySelectorAll('.tab-content');
  
    tabButtons.forEach(button => {
      button.addEventListener('click', () => {
        const target = button.id.replace('tab-', 'content-');
  
        // Update active tab
        tabButtons.forEach(btn => {
          btn.classList.remove('text-blue-600', 'border-b-2', 'border-blue-600');
          btn.classList.add('text-gray-500', 'hover:text-gray-700');
        });
        button.classList.remove('text-gray-500', 'hover:text-gray-700');
        button.classList.add('text-blue-600', 'border-b-2', 'border-blue-600');
  
        // Show the corresponding tab content
        tabContents.forEach(content => content.classList.add('hidden'));
        document.getElementById(target).classList.remove('hidden');
      });
    });
  }
  