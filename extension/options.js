const form = document.querySelector("#settings-form");
const pathInput = document.querySelector("#download-path");
const status = document.querySelector("#status");

browser.runtime.sendMessage({ action: "get-settings" })
  .then((reply) => { pathInput.value = reply.settings.downloadPath; })
  .catch((error) => { status.textContent = `Begleitprogramm nicht erreichbar: ${error.message}`; });

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  status.textContent = "Speichere …";
  try {
    const reply = await browser.runtime.sendMessage({
      action: "set-settings",
      downloadPath: pathInput.value.trim()
    });
    pathInput.value = reply.settings.downloadPath;
    status.textContent = "Einstellungen gespeichert.";
  } catch (error) {
    status.textContent = `Fehler: ${error.message}`;
  }
});
