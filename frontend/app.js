const username = "researcher_01";
const historyDiv = document.getElementById("chat-history");
const statusDiv = document.getElementById("status");

// Load history on startup
async function loadHistory() {
    try {
        const response = await fetch("/history", {
            headers: { "x-forwarded-user": username }
        });
        const history = await response.json();

        historyDiv.innerHTML = "";
        history.forEach(msg => {
            appendMessage(msg.role, msg.content);
        });
        historyDiv.scrollTop = historyDiv.scrollHeight;
    } catch (e) {
        console.error("Failed to load history", e);
    }
}

function appendMessage(role, content) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${role}`;
    msgDiv.innerHTML = `<strong>${role}:</strong> ${content}`;
    historyDiv.appendChild(msgDiv);
    historyDiv.scrollTop = historyDiv.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById("message-input");
    const message = input.value.trim();
    if (!message) return;

    appendMessage("user", message);
    input.value = "";

    statusDiv.textContent = "Agent thinking...";

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "x-forwarded-user": username
            },
            body: JSON.stringify({ message })
        });

        const data = await response.json();
        appendMessage("model", data.response);
        statusDiv.textContent = "";
    } catch (e) {
        statusDiv.textContent = "Error communicating with agent.";
        console.error(e);
    }
}

function handleKey(e) {
    if (e.key === "Enter") {
        sendMessage();
    }
}

async function scheduleJob() {
    const query = document.getElementById("job-query").value;
    const interval = document.getElementById("job-interval").value;

    if (!query) return;

    try {
        const response = await fetch("/jobs", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "x-forwarded-user": username
            },
            body: JSON.stringify({ query, interval_seconds: parseInt(interval) })
        });
        const data = await response.json();
        statusDiv.textContent = `Job Scheduled: ${data.status}`;
    } catch (e) {
        statusDiv.textContent = "Error scheduling job.";
    }
}

window.onload = loadHistory;
