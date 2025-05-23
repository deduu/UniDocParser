// test_json_viewer.js

document.addEventListener("DOMContentLoaded", () => {
  const container = document.getElementById("jsonEditorContainer");
  const loadSampleBtn = document.getElementById("loadSampleJson");
  const copyBtn = document.getElementById("copyJson");
  const expandBtn = document.getElementById("expandJson");
  const collapseBtn = document.getElementById("collapseJson");

  let jsonEditor = null; // Declare editor instance

  // Sample JSON data
  const sampleJson = {
    document: {
      title: "Sample PDF Document",
      file_name: "sample.pdf",
      size_bytes: 1234567,
      pages_extracted: 2,
      processing_time_s: 0.52,
    },
    extraction_result: {
      pages: [
        {
          page_number: 1,
          text_blocks: [
            {
              id: "t1",
              content: "This is the first text block on page 1.",
              bbox: [10, 20, 100, 30],
            },
            {
              id: "t2",
              content: "Another paragraph here, testing multi-line content.",
              bbox: [10, 40, 100, 60],
            },
          ],
          tables: [
            {
              id: "tab1",
              caption: "Sample Data Table",
              rows: [
                ["Header A", "Header B"],
                ["Value 1", "Value 2"],
                ["Value 3", "Value 4"],
              ],
            },
          ],
          images: [],
          markdown:
            "## Page 1\n\nThis is the first text block on page 1.\n\nAnother paragraph here, testing multi-line content.\n\n| Header A | Header B |\n|----------|----------|\n| Value 1  | Value 2  |\n| Value 3  | Value 4  |\n\n---",
        },
        {
          page_number: 2,
          text_blocks: [
            {
              id: "t3",
              content: "Content from page 2.",
              bbox: [10, 20, 100, 30],
            },
          ],
          tables: [],
          images: [
            { id: "img1", filename: "image1.png", bbox: [50, 50, 150, 150] },
          ],
          markdown:
            "## Page 2\n\nContent from page 2.\n\n![Image 1](image1.png)\n\n---",
        },
      ],
      text_blocks: 3,
      tables: 1,
      images: 1,
    },
    json_output: "/downloads/sample.json",
    markdown_output: "/downloads/sample.md",
  };

  // Function to initialize or update the JSON editor
  function initJsonEditor(data) {
    if (!jsonEditor) {
      // Ensure container is empty before creating editor
      container.innerHTML = "";
      jsonEditor = new JSONEditor(container, {
        mode: "view", // Set to 'view' for read-only
        modes: ["view", "code", "form", "tree", "text"], // Allow switching modes
        onError: function (err) {
          console.error("JSON Editor Error:", err);
          alert(
            "JSON Editor Error: " + err.message + ". Check console for details."
          );
        },
      });
    }
    // Set the data
    jsonEditor.set(data);
    jsonEditor.expandAll(); // Expand all nodes by default
  }

  // Event listener for loading sample JSON
  loadSampleBtn.addEventListener("click", () => {
    initJsonEditor(sampleJson);
    // Clear any initial text
    container.querySelector("p")?.remove();
  });

  // Event listeners for expand/collapse/copy buttons
  expandBtn.addEventListener("click", () => {
    if (jsonEditor) {
      jsonEditor.expandAll();
      console.log("JSON expanded!");
    }
  });

  collapseBtn.addEventListener("click", () => {
    if (jsonEditor) {
      jsonEditor.collapseAll();
      console.log("JSON collapsed!");
    }
  });

  copyBtn.addEventListener("click", () => {
    if (jsonEditor) {
      try {
        const jsonToCopy = JSON.stringify(jsonEditor.get(), null, 2);
        navigator.clipboard
          .writeText(jsonToCopy)
          .then(() => {
            console.log("JSON copied to clipboard!");
            alert("JSON copied to clipboard!"); // Simple notification for testing
          })
          .catch((err) => {
            console.error("Failed to copy JSON:", err);
            alert("Failed to copy JSON: " + err.message);
          });
      } catch (err) {
        console.error("Error getting JSON for copy:", err);
        alert("Error getting JSON for copy: " + err.message);
      }
    }
  });

  // Initial state: Display a message or load immediately
  // initJsonEditor({}); // Optionally load an empty object initially
});
