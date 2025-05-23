// static/js/state-manager.js

/**
 * StateManager handles persisting UI state (e.g. active tab) in localStorage.
 */
export class StateManager {
  constructor() {
    // Restore activeTab or default to 'tab-summary'
    this.activeTab = localStorage.getItem("activeTab") || "tab-summary";
  }

  getActiveTab() {
    return this.activeTab;
  }

  setActiveTab(tabId) {
    this.activeTab = tabId;
    localStorage.setItem("activeTab", tabId);
  }

  clear() {
    this.activeTab = null;
    localStorage.removeItem("activeTab");
  }
}
