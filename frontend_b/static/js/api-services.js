// static/js/api-service.js
import { API_BASE_URL } from "./config.js";

export class APIService {
  constructor() {
    this.token = localStorage.getItem("token") ?? null;
    this.currentUser = null;
  }

  _headers(json = true) {
    const h = {};
    if (json) h["Content-Type"] = "application/json";
    if (this.token) h["Authorization"] = `Bearer ${this.token}`;
    return h;
  }

  async _safeFetch(url, opts = {}) {
    const resp = await fetch(url, opts);
    if (resp.ok) return resp;

    let msg = `HTTP ${resp.status}`;
    try {
      const data = await resp.json();
      if (typeof data.detail === "string") msg = data.detail;
      else if (Array.isArray(data.detail)) {
        msg = data.detail.map((d) => d.msg).join("; ");
      }
    } catch {
      /* ignore JSON parse errors */
    }

    if (resp.status === 401) {
      this.logout();
      window.dispatchEvent(new Event("unauthorized"));
    }
    throw new Error(msg);
  }

  async extractPdf(payload, onProgress) {
    // Branch #1: if FormData, do XHR with progress
    if (payload instanceof FormData) {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        xhr.open("POST", `${API_BASE_URL}/api/v1/extractpdf`);

        if (typeof onProgress === "function") onProgress(0);

        // real upload → 0–30%
        xhr.upload.onprogress = (e) => {
          if (!e.lengthComputable || typeof onProgress !== "function") return;
          const uploadPct = (e.loaded / e.total) * 100;
          onProgress(Math.floor(uploadPct * 0.3));
        };

        let fakePct = 30;
        let fakeInterval;
        xhr.upload.onloadend = () => {
          if (typeof onProgress !== "function") return;
          fakeInterval = setInterval(() => {
            if (fakePct < 90) {
              fakePct++;
              onProgress(fakePct);
            } else {
              clearInterval(fakeInterval);
            }
          }, 100);
        };

        xhr.onload = () => {
          clearInterval(fakeInterval);
          if (xhr.status >= 200 && xhr.status < 300) {
            if (typeof onProgress === "function") onProgress(100);
            try {
              resolve(JSON.parse(xhr.responseText));
            } catch {
              reject(new Error("Invalid JSON in server response"));
            }
          } else {
            reject(new Error(`Upload failed (status ${xhr.status})`));
          }
        };

        xhr.onerror = () => {
          clearInterval(fakeInterval);
          reject(new Error("Network error during upload"));
        };

        xhr.send(payload);
      });
    }

    // Branch #2: non‐FormData → simple fetch
    const resp = await this._safeFetch(`${API_BASE_URL}/cross-check`, {
      method: "POST",
      headers: this._headers(),
      body: JSON.stringify(payload),
    });
    return resp.json();
  }

  // …other methods like login(), logout(), etc…
}
