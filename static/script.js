const messagesContainer = document.getElementById('messages-container');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const thinkingIndicator = document.getElementById('thinking-indicator');
const stateIntent = document.getElementById('state-intent');
const stateCaptured = document.getElementById('state-captured');
const successModal = document.getElementById('success-modal');
const leadDataContainer = document.getElementById('lead-data');

let isThinking = false;
const sessionId = "demo_" + Math.random().toString(36).substr(2, 9);

function addMessage(text, sender) {
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    div.innerHTML = `<div class="message-content">${text}</div>`;
    messagesContainer.appendChild(div);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message || isThinking) return;

    // Add user message to UI
    addMessage(message, 'user');
    userInput.value = '';
    
    // Show thinking indicator
    isThinking = true;
    thinkingIndicator.style.display = 'flex';
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, session_id: sessionId })
        });

        const data = await response.json();
        
        if (response.ok) {
            // Update the UI with assistant reply
            addMessage(data.reply, 'assistant');
            
            // Update sidebar state
            stateIntent.textContent = data.intent.toUpperCase();
            stateIntent.style.color = getIntentColor(data.intent);
            
            if (data.lead_captured) {
                stateCaptured.textContent = "True";
                stateCaptured.className = "value status-on";
                stateCaptured.style.color = "#10b981";
                showSuccessModal(data.lead_info);
            }
        } else {
            addMessage("Error: " + data.detail, 'assistant');
        }
    } catch (error) {
        addMessage("Connection error. Is the server running?", 'assistant');
    } finally {
        isThinking = false;
        thinkingIndicator.style.display = 'none';
    }
}

function getIntentColor(intent) {
    const colors = {
        'greeting': '#3b82f6',
        'product_inquiry': '#8b5cf6',
        'pricing_inquiry': '#f59e0b',
        'high_intent_lead': '#10b981',
        'other': '#94a3b8'
    };
    return colors[intent] || '#94a3b8';
}

function showSuccessModal(leadInfo) {
    leadDataContainer.innerHTML = `
        <strong>Name:</strong> ${leadInfo.name}<br>
        <strong>Email:</strong> ${leadInfo.email}<br>
        <strong>Platform:</strong> ${leadInfo.platform}<br>
        <hr style="margin: 10px 0; border: none; border-top: 1px solid var(--border-color)">
        <span style="font-size: 11px; color: var(--text-secondary)">Tool mock_lead_capture() executed successfully.</span>
    `;
    setTimeout(() => {
        successModal.style.display = 'flex';
    }, 1000);
}

function closeModal() {
    successModal.style.display = 'none';
}

async function resetChat() {
    await fetch('/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: "", session_id: sessionId })
    });
    window.location.reload();
}

// Event Listeners
sendBtn.addEventListener('click', sendMessage);
userInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendMessage();
});

// Focus input on load
window.onload = () => userInput.focus();
