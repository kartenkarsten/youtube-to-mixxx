(() => {
  const BUTTON_CLASS = "ytmixxx-button";
  const activeButtons = new Map();
  let scanScheduled = false;

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

  function setButtonState(button, label, state) {
    button.textContent = label;
    button.dataset.state = state;
    button.disabled = state === "busy";
  }

  function makeButton(url) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = BUTTON_CLASS;
    button.textContent = "Als MP3 für Mixxx speichern";
    button.title = "Audio herunterladen und als MP3 für Mixxx speichern";
    button.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      const downloadId = crypto.randomUUID();
      activeButtons.set(downloadId, button);
      setButtonState(button, "Download wird gestartet …", "busy");
      try {
        const result = await browser.runtime.sendMessage({
          action: "download",
          downloadId,
          url
        });
        if (result.duplicate) {
          setButtonState(button, "Bereits heruntergeladen", "success");
        } else {
          setButtonState(button, "MP3 gespeichert · Mixxx-Bibliothek scannen", "success");
        }
        button.title = result.path || "In Mixxx: Library → Rescan Library";
      } catch (error) {
        setButtonState(button, `Fehler: ${error.message}`, "error");
        button.title = error.message;
      } finally {
        activeButtons.delete(downloadId);
      }
    });
    return button;
  }

  function addAction(container, url) {
    if (!container || container.querySelector(`:scope > .${BUTTON_CLASS}`)) return;
    container.append(makeButton(url));
  }

  function addWatchButton() {
    if (location.pathname !== "/watch") return;
    const url = videoUrl(location.href);
    if (!url) return;
    const metadata = document.querySelector("ytd-watch-metadata");
    if (metadata) addAction(metadata, url);
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
      if (!url) continue;
      addAction(renderer, url);
    }
  }

  function scan() {
    scanScheduled = false;
    addWatchButton();
    addSearchButtons();
  }

  function scheduleScan() {
    if (scanScheduled) return;
    scanScheduled = true;
    requestAnimationFrame(scan);
  }

  browser.runtime.onMessage.addListener((message) => {
    if (message.action !== "download-progress") return;
    const button = activeButtons.get(message.downloadId);
    if (!button) return;
    const event = message.event;
    const label = Number.isFinite(event.percent)
      ? `MP3 wird erstellt · ${event.percent}%`
      : event.message || "Download läuft …";
    setButtonState(button, label, "busy");
  });

  new MutationObserver(scheduleScan).observe(document.documentElement, {
    childList: true,
    subtree: true
  });
  document.addEventListener("yt-navigate-finish", scheduleScan);
  window.addEventListener("popstate", scheduleScan);
  scheduleScan();
})();
