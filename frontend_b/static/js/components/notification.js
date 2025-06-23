export function showNotification(message, type = "success", duration = 3000) {
  createToast(message, type, duration);
}

export function showError(message, duration = 5000) {
  createToast(message, "danger", duration);
}

function createToast(message, type, duration) {
  const bgColor = type === "danger" ? "bg-red-100" : "bg-green-100";
  const border = type === "danger" ? "border-red-500" : "border-green-500";
  const text = type === "danger" ? "text-red-700" : "text-green-700";
  const icon = type === "danger" ? "exclamation-circle" : "check-circle";
  const title = type === "danger" ? "Error" : "Success";

  const toast = document.createElement("div");
  toast.className = `fixed top-4 right-4 ${bgColor} border-l-4 ${border} ${text} p-4 rounded shadow-md flex items-start max-w-sm z-50`;
  toast.innerHTML = `
    <div class="mr-3">
      <i class="fas fa-${icon}"></i>
    </div>
    <div>
      <div class="font-bold">${title}</div>
      <div>${message}</div>
    </div>
    <button class="ml-auto text-${
      type === "danger" ? "red" : "green"
    }-500 hover:text-${
    type === "danger" ? "red" : "green"
  }-700">&times;</button>
  `;

  document.body.appendChild(toast);
  toast.querySelector("button").addEventListener("click", () => toast.remove());
  setTimeout(() => {
    if (document.body.contains(toast)) toast.remove();
  }, duration);
}

// // == General Purpose Error Notification ==
// function showError(message) {
//   // Create an error toast notification
//   const toast = document.createElement("div");
//   toast.className =
//     "fixed top-4 right-4 bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded shadow-md flex items-start max-w-sm z-50";
//   toast.innerHTML = `
//     <div class="text-red-500 mr-3">
//         <i class="fas fa-exclamation-circle"></i>
//     </div>
//     <div>
//         <div class="font-bold">Error</div>
//         <div>${message}</div>
//     </div>
//     <button class="ml-auto text-red-500 hover:text-red-700">
//         <i class="fas fa-times"></i>
//     </button>
//   `;

//   document.body.appendChild(toast);

//   // Close button
//   toast.querySelector("button").addEventListener("click", () => {
//     toast.remove();
//   });

//   // Auto-remove after 5 seconds
//   setTimeout(() => {
//     if (document.body.contains(toast)) {
//       toast.remove();
//     }
//   }, 5000);
// }
