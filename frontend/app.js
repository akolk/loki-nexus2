const username = "researcher_01";
const historyDiv = document.getElementById("chat-history");
const statusDiv = document.getElementById("status");
let isMapMode = false;
let map = null;

function initMap() {
    if (map) return; // Prevent re-init

    // Amersfoort Center (EPSG:4326)
    map = L.map('map-container').setView([52.155, 5.387], 8);

    // PDOK BRT Achtergrondkaart via WMTS (EPSG:3857)
    // This uses standard Web Mercator which is compatible with Leaflet by default.
    const pdokUrl = 'https://service.pdok.nl/brt/achtergrondkaart/wmts/v2_0/standaard/EPSG:3857/{z}/{x}/{y}.png';

    L.tileLayer(pdokUrl, {
        attribution: 'Kaartgegevens &copy; <a href="https://www.pdok.nl">PDOK</a>',
        minZoom: 6,
        maxZoom: 19
    }).addTo(map);

    // Force map to redraw when container becomes visible
    setTimeout(() => { map.invalidateSize(); }, 200);
}

function toggleMode() {
    isMapMode = !isMapMode;
    const mapContainer = document.getElementById("map-container");
    const label = document.getElementById("mode-label");
    const body = document.body;

    if (isMapMode) {
        mapContainer.style.display = "block";
        label.textContent = "ON";
        label.style.color = "green";
        body.style.background = "#ddd";
        initMap();
        setTimeout(() => { if(map) map.invalidateSize(); }, 100);
    } else {
        mapContainer.style.display = "none";
        label.textContent = "OFF";
        label.style.color = "black";
        body.style.background = "white";
    }
}

let isChatOpen = false;
function toggleChat() {
    isChatOpen = !isChatOpen;
    const chatWindow = document.getElementById("chat-window");
    const chatBubble = document.getElementById("chat-bubble");

    if (isChatOpen) {
        chatWindow.style.display = "flex";
        chatBubble.style.display = "none";
        // Optionally scroll to bottom when opening
        setTimeout(scrollToBottom, 50);
    } else {
        chatWindow.style.display = "none";
        chatBubble.style.display = "flex";
    }
}

function toggleJobPanel() {
    const panel = document.getElementById("job-panel");
    panel.style.display = panel.style.display === "block" ? "none" : "block";
}

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
        scrollToBottom();
    } catch (e) {
        console.error("Failed to load history", e);
    }
}

function appendMessage(role, content) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${role}`;
    msgDiv.innerHTML = `<strong>${role}:</strong> ${content}`;
    historyDiv.appendChild(msgDiv);
    scrollToBottom();
}

function scrollToBottom() {
    if(historyDiv) historyDiv.scrollTop = historyDiv.scrollHeight;
}

async function sendMessage() {
    const input = document.getElementById("message-input");
    const message = input.value.trim();
    if (!message) return;

    appendMessage("user", message);
    input.value = "";

    // Get Bounding Box if in Map Mode
    let bbox = null;
    if (isMapMode && map) {
        const bounds = map.getBounds();
        bbox = {
            north: bounds.getNorth(),
            south: bounds.getSouth(),
            east: bounds.getEast(),
            west: bounds.getWest()
        };
        console.log("Sending BBox:", bbox);
    }

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "x-forwarded-user": username
            },
            body: JSON.stringify({ message, bbox }) // Send bbox
        });

        const data = await response.json();
        appendMessage("model", data.response);
    } catch (e) {
        appendMessage("model", "Error communicating with agent.");
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
        if (statusDiv) statusDiv.textContent = `Job Scheduled: ${data.status}`;
    } catch (e) {
        if (statusDiv) statusDiv.textContent = "Error scheduling job.";
    }
}

// Startup
loadHistory();
// Default to closed bubble
// toggleChat() would open it, so we leave it closed (default HTML state)
