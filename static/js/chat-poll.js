(function () {
  const container = document.getElementById("chatThread");
  const form = document.getElementById("chatForm");
  if (!container || !form) return;

  const updatesUrl = container.dataset.updatesUrl;
  let lastId = parseInt(container.dataset.lastId, 10) || 0;
  const POLL_INTERVAL_MS = 5000;

  function scrollToBottom() {
    container.scrollTop = container.scrollHeight;
  }

  function appendMessage(message) {
    const emptyState = document.getElementById("chatEmptyState");
    if (emptyState) emptyState.remove();

    const bubble = document.createElement("div");
    bubble.className = "chat-bubble " + (message.mine ? "chat-bubble-mine" : "chat-bubble-theirs");
    bubble.dataset.messageId = message.id;

    const body = document.createElement("div");
    body.textContent = message.body;
    bubble.appendChild(body);

    const time = document.createElement("small");
    time.className = "text-muted";
    time.textContent = message.created_at;
    bubble.appendChild(time);

    container.appendChild(bubble);
  }

  async function poll() {
    try {
      const response = await fetch(`${updatesUrl}?after=${lastId}`, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
      });
      if (!response.ok) return;
      const data = await response.json();
      if (data.messages && data.messages.length) {
        const wasNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 60;
        data.messages.forEach((message) => {
          // The message we just sent via the normal form POST+redirect
          // is already rendered server-side -- skip re-appending it.
          if (!container.querySelector(`[data-message-id="${message.id}"]`)) {
            appendMessage(message);
          }
          lastId = Math.max(lastId, message.id);
        });
        if (wasNearBottom) scrollToBottom();
      }
    } catch (err) {
      // Silent -- a failed poll just tries again next interval.
    }
  }

  scrollToBottom();
  setInterval(poll, POLL_INTERVAL_MS);
})();
