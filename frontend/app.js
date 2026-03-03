const username = "researcher_01";
const historyDiv = document.getElementById("chat-history");
const statusDiv = document.getElementById("status");
let isMapMode = false;
let map = null;
let currentGeoJsonLayer = null;
let currentTileServerLayers = [];

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

let isSettingsOpen = false;
function toggleSettings() {
    isSettingsOpen = !isSettingsOpen;
    const sidebar = document.getElementById("settings-sidebar");
    if (isSettingsOpen) {
        sidebar.style.display = "flex";
    } else {
        sidebar.style.display = "none";
    }
}

function openSettings() {
    isSettingsOpen = true;
    document.getElementById("settings-sidebar").style.display = "flex";
}

function closeSettings() {
    isSettingsOpen = false;
    document.getElementById("settings-sidebar").style.display = "none";
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

    // Recalculate maximized post-its if any
    document.querySelectorAll('.postit-note.maximized').forEach(recalcMaximizedPostit);
}

window.addEventListener('resize', () => {
    document.querySelectorAll('.postit-note.maximized').forEach(recalcMaximizedPostit);
});

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

// Helper to initialize drag-and-drop for post-its
function makeDraggable(element, handle = element) {
    let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;

    handle.onmousedown = dragMouseDown;

    function dragMouseDown(e) {
        // Prevent drag on buttons or inputs
        if(e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT') return;

        e.preventDefault();
        // get the mouse cursor position at startup:
        pos3 = e.clientX;
        pos4 = e.clientY;

        // Prevent drag if maximized
        if (element.classList.contains('maximized')) return;

        // bring to front
        document.querySelectorAll('.postit-note, .postit-group').forEach(el => {
            if(!el.classList.contains('pinned') && !el.classList.contains('maximized')) el.style.zIndex = "10";
        });
        if(!element.classList.contains('pinned') && !element.classList.contains('maximized')) element.style.zIndex = "100";

        document.onmouseup = closeDragElement;
        document.onmousemove = elementDrag;
    }

    function elementDrag(e) {
        e.preventDefault();
        // calculate the new cursor position:
        pos1 = pos3 - e.clientX;
        pos2 = pos4 - e.clientY;
        pos3 = e.clientX;
        pos4 = e.clientY;
        // set the element's new position:
        element.style.top = (element.offsetTop - pos2) + "px";
        element.style.left = (element.offsetLeft - pos1) + "px";
    }

    function closeDragElement() {
        // stop moving when mouse button is released:
        document.onmouseup = null;
        document.onmousemove = null;

        // Handle grouping logic
        if (element.classList.contains('postit-note')) {
            const groups = Array.from(document.querySelectorAll('.postit-group'));
            const otherNotes = Array.from(document.querySelectorAll('.postit-note')).filter(n => n !== element && !n.closest('.postit-group'));

            const elementRect = element.getBoundingClientRect();

            // Check if dropped on a group
            let droppedOnGroup = false;
            for (let group of groups) {
                const groupRect = group.getBoundingClientRect();
                if (isColliding(elementRect, groupRect)) {
                    group.querySelector('.postit-group-content').appendChild(element);
                    element.style.top = 'auto';
                    element.style.left = 'auto';
                    droppedOnGroup = true;
                    break;
                }
            }

            // Check if dropped on another note to create a new group
            if (!droppedOnGroup && !element.closest('.postit-group')) {
                for (let otherNote of otherNotes) {
                    const otherRect = otherNote.getBoundingClientRect();
                    if (isColliding(elementRect, otherRect)) {
                        createGroup([otherNote, element], otherRect.left, otherRect.top);
                        break;
                    }
                }
            }

            // If dragging out of a group
            if (!droppedOnGroup && element.closest('.postit-group')) {
                const group = element.closest('.postit-group');
                const groupRect = group.getBoundingClientRect();
                if (!isColliding(elementRect, groupRect)) {
                    document.getElementById('postit-container').appendChild(element);
                    element.style.left = elementRect.left + 'px';
                    element.style.top = elementRect.top + 'px';

                    // remove group if empty
                    const contentDiv = group.querySelector('.postit-group-content');
                    if(contentDiv.children.length <= 1) {
                        const remainingNotes = Array.from(contentDiv.children);
                        remainingNotes.forEach(n => {
                            document.getElementById('postit-container').appendChild(n);
                            n.style.left = groupRect.left + 'px';
                            n.style.top = groupRect.top + 'px';
                        });
                        group.remove();
                    }
                }
            }
        }
    }
}

function isColliding(r1, r2) {
    return !(r2.left > r1.right ||
             r2.right < r1.left ||
             r2.top > r1.bottom ||
             r2.bottom < r1.top);
}

function createGroup(notes, left, top) {
    const groupDiv = document.createElement("div");
    groupDiv.className = "postit-group";
    groupDiv.style.left = (left - 20) + "px";
    groupDiv.style.top = (top - 20) + "px";

    const header = document.createElement("div");
    header.className = "postit-group-header";
    header.innerHTML = `
        <input type="text" value="New Group">
        <button style="border:none;background:none;cursor:pointer;" onclick="this.closest('.postit-group').remove()">❌</button>
    `;

    const contentDiv = document.createElement("div");
    contentDiv.className = "postit-group-content";

    notes.forEach(note => {
        note.style.left = 'auto';
        note.style.top = 'auto';
        contentDiv.appendChild(note);
    });

    groupDiv.appendChild(header);
    groupDiv.appendChild(contentDiv);
    document.getElementById('postit-container').appendChild(groupDiv);

    makeDraggable(groupDiv, header);
}

function createPostit(execResult) {
    const postit = document.createElement("div");
    postit.className = "postit-note";

    // Random slight rotation
    const rotation = Math.random() * 6 - 3;
    postit.style.transform = `rotate(${rotation}deg)`;

    // Random position offset slightly from center
    const x = window.innerWidth / 2 + (Math.random() * 200 - 100);
    const y = window.innerHeight / 2 + (Math.random() * 200 - 100);
    postit.style.left = `${x}px`;
    postit.style.top = `${y}px`;

    const header = document.createElement("div");
    header.className = "postit-header";
    header.innerHTML = `
        <button title="Pin" onclick="this.closest('.postit-note').classList.toggle('pinned'); event.stopPropagation();">📌</button>
        <button title="Delete" onclick="this.closest('.postit-note').remove(); event.stopPropagation();">✖</button>
    `;

    const content = document.createElement("div");
    content.className = "postit-content";

    const resDiv = document.createElement("div");
    resDiv.className = "result-container";

    if (execResult.type === "dataframe") {
        resDiv.innerHTML = execResult.content;
    } else if (execResult.type === "picture") {
        const img = document.createElement("img");
        img.src = execResult.content.startsWith('http') ? execResult.content : `data:image/png;base64,${execResult.content}`;
        resDiv.appendChild(img);
    } else if (execResult.type === "html") {
        resDiv.innerHTML = execResult.content;
    } else if (execResult.type === "plotly") {
        try {
            const plotData = typeof execResult.content === 'string' ? JSON.parse(execResult.content) : execResult.content;
            const plotDivId = `plotly-${Math.random().toString(36).substr(2, 9)}`;
            resDiv.id = plotDivId;
            resDiv.style.width = '100%';
            resDiv.style.height = '100%';
            setTimeout(() => {
                Plotly.newPlot(plotDivId, plotData.data, plotData.layout).then(() => {
                    const ro = new ResizeObserver(() => {
                        Plotly.Plots.resize(plotDivId);
                    });
                    ro.observe(resDiv);
                });
            }, 100);
        } catch (e) {
            resDiv.innerHTML = `Error rendering Plotly chart: ${e}`;
        }
    } else if (execResult.type === "folium") {
        const iframe = document.createElement("iframe");
        iframe.srcdoc = execResult.content;
        resDiv.appendChild(iframe);
    } else {
        resDiv.innerHTML = `<pre>${JSON.stringify(execResult.content, null, 2)}</pre>`;
    }

    content.appendChild(resDiv);
    postit.appendChild(header);
    postit.appendChild(content);

    postit.ondblclick = (e) => {
        // Don't maximize if clicking on the header buttons
        if (e.target.tagName === 'BUTTON') return;
        toggleMaximize(postit);
    };

    document.getElementById('postit-container').appendChild(postit);

    makeDraggable(postit);
}

function toggleMaximize(postit) {
    if (postit.classList.contains('maximized')) {
        // Restore original size/position
        postit.classList.remove('maximized');
        postit.style.width = postit.dataset.origWidth || '';
        postit.style.height = postit.dataset.origHeight || '';
        postit.style.top = postit.dataset.origTop || '';
        postit.style.left = postit.dataset.origLeft || '';
        postit.style.transform = postit.dataset.origTransform || '';
        postit.style.zIndex = postit.dataset.origZIndex || '';
    } else {
        // Store original size/position
        postit.dataset.origWidth = postit.style.width || postit.offsetWidth + 'px';
        postit.dataset.origHeight = postit.style.height || postit.offsetHeight + 'px';
        postit.dataset.origTop = postit.style.top;
        postit.dataset.origLeft = postit.style.left;
        postit.dataset.origTransform = postit.style.transform;
        postit.dataset.origZIndex = postit.style.zIndex;

        postit.classList.add('maximized');
        recalcMaximizedPostit(postit);
    }
}

function recalcMaximizedPostit(postit) {
    if (!postit || !postit.classList.contains('maximized')) return;

    const chatWindow = document.getElementById("chat-window");
    const isChatVisible = chatWindow.style.display === "flex";

    if (isChatVisible) {
        const chatRect = chatWindow.getBoundingClientRect();
        postit.style.left = chatRect.right + 'px';
        postit.style.width = (window.innerWidth - chatRect.right) + 'px';
    } else {
        postit.style.left = '0px';
        postit.style.width = '100vw';
    }

    postit.style.top = '0px';
    postit.style.height = '100vh';
    postit.style.transform = 'none';
}


function appendMessage(role, content, execResult=null, related=[]) {
    const msgDiv = document.createElement("div");
    msgDiv.className = `message ${role}`;

    // Convert newlines to breaks for text content
    let formattedContent = content;
    if (typeof content === 'string') {
        formattedContent = content.replace(/\n/g, '<br>');
    }

    msgDiv.innerHTML = `<strong>${role}:</strong> <br>${formattedContent}`;

    if (execResult) {
        if (!isMapMode && execResult.type !== "geojson_map") {
            createPostit(execResult);
        } else {
            const resDiv = document.createElement("div");
            resDiv.className = "result-container";

            if (execResult.type === "dataframe") {
                // Assume content is HTML table string
                resDiv.innerHTML = execResult.content;
            } else if (execResult.type === "picture") {
                // Assume content is base64 string or URL
                const img = document.createElement("img");
                img.src = execResult.content.startsWith('http') ? execResult.content : `data:image/png;base64,${execResult.content}`;
                resDiv.appendChild(img);
            } else if (execResult.type === "html") {
                resDiv.innerHTML = execResult.content;
            } else if (execResult.type === "plotly") {
                // Assume content is JSON string for plotly layout/data
                try {
                    const plotData = typeof execResult.content === 'string' ? JSON.parse(execResult.content) : execResult.content;
                    const plotDivId = `plotly-${Math.random().toString(36).substr(2, 9)}`;
                    resDiv.id = plotDivId;
                    resDiv.style.width = '100%';
                    resDiv.style.height = '100%';
                    setTimeout(() => {
                        Plotly.newPlot(plotDivId, plotData.data, plotData.layout).then(() => {
                            const ro = new ResizeObserver(() => {
                                Plotly.Plots.resize(plotDivId);
                            });
                            ro.observe(resDiv);
                        });
                    }, 100);
                } catch (e) {
                    resDiv.innerHTML = `Error rendering Plotly chart: ${e}`;
                }
            } else if (execResult.type === "folium") {
                // Assume content is HTML for an iframe
                const iframe = document.createElement("iframe");
                iframe.srcdoc = execResult.content;
                resDiv.appendChild(iframe);
            } else if (execResult.type === "geojson_map") {
                let featuresCount = 0;
                let tileServersCount = 0;

                if (isMapMode && map) {
                    // Clear existing layers
                    if (currentGeoJsonLayer) {
                        map.removeLayer(currentGeoJsonLayer);
                        currentGeoJsonLayer = null;
                    }
                    currentTileServerLayers.forEach(layer => map.removeLayer(layer));
                    currentTileServerLayers = [];

                    if (execResult.content.features && execResult.content.features.length > 0) {
                        currentGeoJsonLayer = L.geoJSON(execResult.content.features).addTo(map);
                        // Fit bounds to the newly added layer
                        if (currentGeoJsonLayer.getBounds().isValid()) {
                            map.fitBounds(currentGeoJsonLayer.getBounds());
                        }
                        featuresCount = execResult.content.features.length;
                    }

                    if (execResult.content.tile_servers && execResult.content.tile_servers.length > 0) {
                        execResult.content.tile_servers.forEach(ts => {
                            const newLayer = L.tileLayer(ts.url, {
                                attribution: ts.attribution || '',
                                minZoom: ts.minZoom || 0,
                                maxZoom: ts.maxZoom || 19
                            }).addTo(map);
                            currentTileServerLayers.push(newLayer);
                        });
                        tileServersCount = execResult.content.tile_servers.length;
                    }
                }

                // Output summary
                const summary = document.createElement("p");
                summary.innerHTML = `<em>Map updated with ${featuresCount} features and ${tileServersCount} tile servers.</em>`;
                resDiv.appendChild(summary);

                // Add the model's textual answer if present
                if (execResult.content.answer) {
                    const answerText = document.createElement("div");
                    let formattedAnswer = execResult.content.answer;
                    if (typeof execResult.content.answer === 'string') {
                        formattedAnswer = execResult.content.answer.replace(/\n/g, '<br>');
                    }
                    answerText.innerHTML = `<br>${formattedAnswer}`;
                    resDiv.appendChild(answerText);
                }

            } else {
                // Fallback
                resDiv.innerHTML = `<pre>${JSON.stringify(execResult.content, null, 2)}</pre>`;
            }

            msgDiv.appendChild(resDiv);
        }
    }

    if (role === 'model' && related && related.length > 0) {
        const relatedContainer = document.createElement("div");
        relatedContainer.className = "related-bubbles-container";

        related.slice(0, 3).forEach(question => {
            const bubble = document.createElement("div");
            bubble.className = "related-bubble";
            bubble.textContent = question;
            bubble.onclick = () => {
                const input = document.getElementById("message-input");
                input.value = question;
                sendMessage();
            };
            relatedContainer.appendChild(bubble);
        });

        msgDiv.appendChild(relatedContainer);
    }

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

    const mcpType = document.getElementById("mcp-type").value;
    const mcpUrl = document.getElementById("mcp-url").value;
    const skillFile = document.getElementById("skill-file").files[0];

    const formData = new FormData();
    formData.append("message", message);
    if (bbox) formData.append("bbox", JSON.stringify(bbox));
    if (mcpType && mcpUrl) {
        formData.append("mcp_type", mcpType);
        formData.append("mcp_url", mcpUrl);
    }
    if (skillFile) {
        formData.append("skill_file", skillFile);
    }

    try {
        const response = await fetch("/chat", {
            method: "POST",
            headers: {
                "x-forwarded-user": username
            },
            body: formData // Send FormData
        });

        const data = await response.json();
        if (data.exec_result) {
            appendMessage("model", data.response, data.exec_result, data.related);
        } else {
            appendMessage("model", data.response, null, data.related);
        }

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

async function startDeepResearch() {
    const query = document.getElementById("research-query").value;
    const format = document.getElementById("research-format").value;
    const researchStatusDiv = document.getElementById("research-status");

    if (!query || !format) return;

    if (researchStatusDiv) researchStatusDiv.textContent = "Running research...";

    try {
        const response = await fetch("/deep_research", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "x-forwarded-user": username
            },
            body: JSON.stringify({ query, format })
        });

        const data = await response.json();

        if (researchStatusDiv) researchStatusDiv.textContent = "Research completed!";

        if (data.exec_result) {
            appendMessage("model", data.response, data.exec_result);
        } else {
            appendMessage("model", data.response);
        }
    } catch (e) {
        if (researchStatusDiv) researchStatusDiv.textContent = "Error running research.";
    }
}

// Startup
loadHistory();
// Default to closed bubble
// toggleChat() would open it, so we leave it closed (default HTML state)
