const year = document.getElementById("year");
year.textContent = new Date().getFullYear();

const typingText = document.getElementById("typingText");
const text = "Refining the checkout experience...";
let index = 0;

function typeText() {
  if (index <= text.length) {
    typingText.textContent = text.slice(0, index);
    index += 1;
    setTimeout(typeText, 55);
  } else {
    setTimeout(() => {
      index = 0;
      typeText();

      const chatInput = document.getElementById("chatInput");
      const chatSend = document.getElementById("chatSend");
      const chatMessages = document.getElementById("chatMessages");
      const sessionId = `browser-${Date.now()}-${Math.random().toString(16).slice(2)}`;

      function appendChatMessage(speaker, text) {
        const row = document.createElement("div");
        row.className = `message ${speaker === "You" ? "user" : "bot"}`;

        const avatar = document.createElement("div");
        avatar.className = `avatar${speaker === "Bona" ? " bot-avatar" : ""}`;
        avatar.textContent = speaker === "Bona" ? ">_" : "Y";

        const body = document.createElement("div");
        const label = document.createElement("span");
        label.textContent = speaker;
        const message = document.createElement("p");
        message.textContent = text;
        body.append(label, message);
        row.append(avatar, body);
        chatMessages.append(row);
        chatMessages.scrollTop = chatMessages.scrollHeight;
      }

      async function sendChat() {
        const prompt = chatInput.value.trim();
        if (!prompt || chatSend.disabled) return;

        chatInput.value = "";
        appendChatMessage("You", prompt);
        chatSend.disabled = true;

        try {
          const response = await fetch("/api/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ prompt, session_id: sessionId }),
          });
          const data = await response.json();
          if (!response.ok) throw new Error(data.error || "Bona could not answer.");
          appendChatMessage("Bona", data.answer);
        } catch (error) {
          appendChatMessage("Bona", error.message);
        } finally {
          chatSend.disabled = false;
          chatInput.focus();
        }
      }

      chatSend.addEventListener("click", sendChat);
      chatInput.addEventListener("keydown", (event) => {
        if (event.key === "Enter") sendChat();
      });
    }, 1800);
  }
}
typeText();

