// ==UserScript==
// @name         YouTube zu Mixxx
// @namespace    local.youtube-to-mixxx
// @version      1.0.0
// @description  Speichert normale YouTube-Videos als MP3 für Mixxx.
// @match        https://www.youtube.com/watch*
// @match        https://www.youtube.com/results*
// @grant        GM_xmlhttpRequest
// @connect      127.0.0.1
// @run-at       document-idle
// ==/UserScript==

(() => {
  "use strict";

  const BUTTON_CLASS = "ytmixxx-tampermonkey-button";
  const API_URL = "http://127.0.0.1:8765/download";
  let scanQueued = false;

  function videoUrl(rawUrl) {
    try {
      const url = new URL(rawUrl, location.origin);
      if (url.origin !== "https://www.youtube.com" || url.pathname !== "/watch") return null;
      const id = url.searchParams.get("v");
      if (!id || !/^[A-Za-z0-9_-]{11}$/.test(id)) return null;
      return `https://www.youtube.com/watch?v=${id}`;
    } catch {
      return null;
    }
  }

  function setState(button, label, state) {
    button.textContent = label;
    button.dataset.state = state;
    button.disabled = state === "busy" || state === "success";
    button.style.cursor = button.disabled ? (state === "busy" ? "progress" : "default") : "pointer";
  }

  function requestDownload(url) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: "POST",
        url: API_URL,
        headers: {
          "Content-Type": "application/json",
          "X-YTMX-Bridge": "tampermonkey"
        },
        data: JSON.stringify({ url }),
        onload(response) {
          let result;
          try {
            result = JSON.parse(response.responseText);
          } catch {
            reject(new Error("Ungültige Antwort vom lokalen Downloader."));
            return;
          }
          if (response.status < 200 || response.status >= 300 || !result.ok) {
            reject(new Error(result.error || `Lokaler Downloader antwortete mit HTTP ${response.status}.`));
            return;
          }
          resolve(result);
        },
        onerror() {
          reject(new Error("Lokaler Downloader nicht erreichbar. Bitte den Tampermonkey-Dienst prüfen."));
        },
        ontimeout() {
          reject(new Error("Zeitüberschreitung beim lokalen Downloader."));
        }
      });
    });
  }

  function makeButton(url) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = BUTTON_CLASS;
    button.dataset.url = url;
    button.textContent = "Als MP3 für Mixxx speichern";
    button.title = "Audio herunterladen und als MP3 für Mixxx speichern";
    Object.assign(button.style, {
      display: "inline-flex",
      alignItems: "center",
      justifyContent: "center",
      minHeight: "36px",
      margin: "8px 8px 8px 0",
      padding: "0 16px",
      border: "0",
      borderRadius: "18px",
      background: "#2f7d32",
      color: "white",
      font: "500 14px/1.2 Roboto, Arial, sans-serif"
    });
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      setState(button, "Download läuft …", "busy");
      try {
        const result = await requestDownload(button.dataset.url);
        if (result.duplicate) {
          setState(button, "Bereits heruntergeladen", "success");
          button.title = "Dieses Video ist bereits im Download-Archiv enthalten.";
        } else {
          setState(button, "MP3 gespeichert · Mixxx-Bibliothek scannen", "success");
          button.title = `${result.path || "MP3 gespeichert"}\nIn Mixxx: Library → Rescan Library`;
        }
        button.style.background = "#245c27";
      } catch (error) {
        setState(button, `Fehler: ${error.message}`, "error");
        button.title = error.message;
        button.style.background = "#b3261e";
        button.style.maxWidth = "100%";
        button.style.whiteSpace = "normal";
      }
    });
    return button;
  }

  function addWatchButton() {
    if (location.pathname !== "/watch") return;
    const url = videoUrl(location.href);
    const metadata = document.querySelector("ytd-watch-metadata");
    if (!url || !metadata) return;
    let button = metadata.querySelector(`:scope > .${BUTTON_CLASS}`);
    if (button && button.dataset.url !== url) {
      button.remove();
      button = null;
    }
    if (!button) metadata.append(makeButton(url));
  }

  function addSearchButtons() {
    if (location.pathname !== "/results") return;
    const renderers = document.querySelectorAll(
      "ytd-video-renderer, ytd-rich-item-renderer, ytd-compact-video-renderer"
    );
    for (const renderer of renderers) {
      if (renderer.querySelector(`:scope > .${BUTTON_CLASS}`)) continue;
      const link = renderer.querySelector('a[href^="/watch?"]');
      const url = link && videoUrl(link.href);
      if (url) renderer.append(makeButton(url));
    }
  }

  function scan() {
    scanQueued = false;
    addWatchButton();
    addSearchButtons();
  }

  function scheduleScan() {
    if (scanQueued) return;
    scanQueued = true;
    requestAnimationFrame(scan);
  }

  new MutationObserver(scheduleScan).observe(document.documentElement, {
    childList: true,
    subtree: true
  });
  document.addEventListener("yt-navigate-finish", scheduleScan);
  window.addEventListener("popstate", scheduleScan);
  scheduleScan();
})();
