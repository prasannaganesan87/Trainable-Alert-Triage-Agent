let emails = [];
let selectedEmailId = null;
let currentAiPrediction = null;

const emailListEl = document.getElementById('email-list');
const refreshBtn = document.getElementById('refresh-btn');
const emptyStateEl = document.getElementById('empty-state');
const emailContentEl = document.getElementById('email-content');

// Elements inside Reading Pane
const subjectEl = document.getElementById('mail-subject');
const timeEl = document.getElementById('mail-time');
const bodyEl = document.getElementById('mail-body');
const aiBoxEl = document.getElementById('ai-suggestion-box');
const aiDecisionEl = document.getElementById('ai-decision');
const aiReasonEl = document.getElementById('ai-reason');
const commentEl = document.getElementById('triage-comment');
const statusMsgEl = document.getElementById('triage-status');

// Fetch emails
async function fetchEmails() {
    refreshBtn.classList.add('loading');
    try {
        const res = await fetch('/api/emails');
        emails = await res.json();
        renderEmailList();
    } catch (e) {
        console.error(e);
        statusMsgEl.innerText = "Error fetching emails.";
    } finally {
        refreshBtn.classList.remove('loading');
    }
}

// Render the sidebar
function renderEmailList() {
    emailListEl.innerHTML = '';
    
    if (emails.length === 0) {
        emailListEl.innerHTML = '<div style="padding: 20px; color: var(--text-muted); text-align: center;">No new alerts.</br>Take a break! ☕</div>';
        return;
    }

    emails.forEach(email => {
        const div = document.createElement('div');
        div.className = `email-item ${email.entry_id === selectedEmailId ? 'active' : ''}`;
        div.onclick = () => selectEmail(email.entry_id);
        
        // Format time
        const d = new Date(email.received_time);
        const timeStr = d.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});

        div.innerHTML = `
            <div style="display: flex; justify-content: space-between;">
                <div class="email-item-subject">${email.subject}</div>
                <div style="font-size: 0.75rem; color: var(--text-muted);">${timeStr}</div>
            </div>
            <div class="email-item-snippet">${email.body}</div>
        `;
        emailListEl.appendChild(div);
    });
}

// Select email and populate main stage
async function selectEmail(id) {
    selectedEmailId = id;
    renderEmailList(); // update active state
    
    const email = emails.find(e => e.entry_id === id);
    if (!email) return;

    emptyStateEl.classList.add('hidden');
    emailContentEl.classList.remove('hidden');
    
    subjectEl.innerText = email.subject;
    timeEl.innerText = new Date(email.received_time).toLocaleString();
    
    // Render body
    if (email.html_body) {
        // Simple sanitization or iframe is better, but since it's local Outlook we trust it ish
        bodyEl.innerHTML = email.html_body;
    } else {
        bodyEl.innerHTML = `<pre>${email.body}</pre>`;
    }

    // Reset Triage form
    commentEl.value = '';
    statusMsgEl.innerText = '';
    aiBoxEl.classList.add('hidden');
    currentAiPrediction = null;

    // Fetch AI suggestion
    fetchSuggestion(email.subject, email.body);
}

async function fetchSuggestion(subject, body) {
    aiBoxEl.classList.add('hidden');
    
    try {
        const res = await fetch('/api/classify', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({subject, body})
        });
        const data = await res.json();
        
        if (data.suggestion) {
            currentAiPrediction = data;
            const confPercent = Math.round(data.confidence * 100);
            aiDecisionEl.innerText = `${data.suggestion} (${confPercent}%)`;
            aiReasonEl.innerText = data.reason;
            aiBoxEl.classList.remove('hidden');
        }
    } catch (e) {
        console.error("AI fetch failed", e);
    }
}

// Handle action
async function performTriage(decision) {
    if (!selectedEmailId) return;
    
    const email = emails.find(e => e.entry_id === selectedEmailId);
    
    const payload = {
        entry_id: email.entry_id,
        subject: email.subject,
        body: email.body,
        decision: decision,
        comment: commentEl.value.trim(),
        model_suggestion: currentAiPrediction ? currentAiPrediction.suggestion : null,
        confidence: currentAiPrediction ? currentAiPrediction.confidence : null
    };

    try {
        await fetch('/api/triage', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        // Remove from list
        emails = emails.filter(e => e.entry_id !== selectedEmailId);
        selectedEmailId = null;
        
        // Hide reading pane
        emailContentEl.classList.add('hidden');
        emptyStateEl.classList.remove('hidden');
        
        renderEmailList();
    } catch (e) {
        console.error(e);
        statusMsgEl.innerText = "Error saving triage decision.";
    }
}

// Event Listeners
document.getElementById('btn-check').addEventListener('click', () => performTriage('Check'));
document.getElementById('btn-ignore').addEventListener('click', () => performTriage('Ignore'));
refreshBtn.addEventListener('click', fetchEmails);

// Initial load
fetchEmails();
