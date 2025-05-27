// static/js/app.js

import { StateManager } from "./state-manager.js";
import { api } from "./singleton.js";
import { UIController } from "./ui-controller.js";
import { showError } from "./components/notification.js";

document.addEventListener("DOMContentLoaded", () => {
  // 1️⃣ Create your UI state manager
  const state = new StateManager();

  // 3️⃣ Create your UI controller, passing both state & api
  const ui = new UIController(state, api);

  // 4️⃣ Kick off all the DOM wiring
  ui.init();
});
