const HOST_NAME = "org.mixxx.youtube_downloader";
let downloadQueue = Promise.resolve();

function callHost(message, onEvent = () => {}) {
  return new Promise((resolve, reject) => {
    let finished = false;
    const port = browser.runtime.connectNative(HOST_NAME);

    port.onMessage.addListener((reply) => {
      if (reply.event === "progress") {
        onEvent(reply);
      } else if (reply.event === "done") {
        finished = true;
        resolve(reply);
        port.disconnect();
      } else if (reply.event === "error") {
        finished = true;
        reject(new Error(reply.error || "Der Download ist fehlgeschlagen."));
        port.disconnect();
      } else if (reply.ok) {
        finished = true;
        resolve(reply);
        port.disconnect();
      } else {
        finished = true;
        reject(new Error(reply.error || "Der Native-Messaging-Host hat einen Fehler gemeldet."));
        port.disconnect();
      }
    });

    port.onDisconnect.addListener(() => {
      if (!finished) {
        reject(new Error(browser.runtime.lastError?.message || "Verbindung zum lokalen Begleitprogramm fehlgeschlagen."));
      }
    });

    port.postMessage(message);
  });
}

browser.runtime.onMessage.addListener((message, sender) => {
  if (message.action === "get-settings") {
    return callHost({ action: "get_settings" });
  }

  if (message.action === "set-settings") {
    return callHost({ action: "set_settings", downloadPath: message.downloadPath });
  }

  if (message.action === "download") {
    const tabId = sender.tab?.id;
    const job = downloadQueue.then(() => callHost(
      { action: "download", url: message.url },
      (event) => {
        if (tabId !== undefined) {
          browser.tabs.sendMessage(tabId, {
            action: "download-progress",
            downloadId: message.downloadId,
            event
          }).catch(() => {});
        }
      }
    ));
    downloadQueue = job.catch(() => {});
    return job;
  }

  return undefined;
});
