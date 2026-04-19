const chatContainer = document.getElementById('chat-container');
const messagesWrapper = document.getElementById('messages-wrapper');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');

// Auto-resize textarea
userInput.addEventListener('input', () => {
    userInput.style.height = 'auto';
    userInput.style.height = userInput.scrollHeight + 'px';
});

// Handle enter key
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

sendBtn.addEventListener('click', sendMessage);

async function sendMessage() {
    const text = userInput.value.trim();
    if (!text) return;

    // Add user message to UI
    appendMessage('user', text);
    userInput.value = '';
    userInput.style.height = 'auto';
    
    // Disable input
    userInput.disabled = true;
    sendBtn.disabled = true;

    // Add temporary AI message (typing...)
    const aiMessageId = 'ai-' + Date.now();
    appendMessage('ai', '...', aiMessageId);

    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message: text })
        });

        const data = await response.json();
        
        if (data.error) {
            updateMessage(aiMessageId, 'Error: ' + data.error);
        } else {
            // Render markdown content
            const content = data.content;
            updateMessage(aiMessageId, content);
            
            if (data.file) {
                appendMessage('system', `File created: ${data.file}`);
            }
        }
    } catch (error) {
        updateMessage(aiMessageId, 'Network error. Please try again.');
    } finally {
        userInput.disabled = false;
        sendBtn.disabled = false;
        userInput.focus();
    }
}

function appendMessage(role, content, id = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;
    if (id) messageDiv.id = id;

    const avatar = document.createElement('div');
    avatar.className = 'avatar';
    avatar.textContent = role === 'user' ? 'U' : (role === 'system' ? 'S' : '');

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (role === 'ai') {
        contentDiv.innerHTML = marked.parse(content);
    } else {
        contentDiv.textContent = content;
    }

    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentDiv);
    messagesWrapper.appendChild(messageDiv);
    
    // Scroll to bottom
    chatContainer.scrollTo({
        top: chatContainer.scrollHeight,
        behavior: 'smooth'
    });
}

function updateMessage(id, content) {
    const messageDiv = document.getElementById(id);
    if (messageDiv) {
        const contentDiv = messageDiv.querySelector('.message-content');
        contentDiv.innerHTML = marked.parse(content);
        
        chatContainer.scrollTo({
            top: chatContainer.scrollHeight,
            behavior: 'smooth'
        });
    }
}
