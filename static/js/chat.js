// chat.js - Chat interface functionality for DB Chat application

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the chat interface
    initChatInterface();
    loadChatHistory();
    loadPreviousChats();
});

// Global variables
let currentDbType = '';
let typingTimer;
let isProcessing = false;
let currentChatId = '';

// Initialize the chat interface elements and event listeners
function initChatInterface() {
    const chatForm = document.getElementById('chat-form');
    const newChatButton = document.getElementById('new-chat-btn');
    const exampleContainer = document.getElementById('example-queries');
    
    // Get database info from the page
    const dbInfoElement = document.getElementById('db-info');
    if (dbInfoElement) {
        currentDbType = dbInfoElement.getAttribute('data-db-type');
        
        // Load example queries for this database type
        loadExampleQueries(currentDbType);
    }
    
    // Set up form submission
    if (chatForm) {
        chatForm.addEventListener('submit', function(event) {
            event.preventDefault();
            
            const queryInput = document.getElementById('query-input');
            const query = queryInput.value.trim();
            
            if (query && !isProcessing) {
                sendQuery(query);
                queryInput.value = '';
            }
        });
    }
    
    // New chat button
    if (newChatButton) {
        newChatButton.addEventListener('click', function() {
            window.location.href = '/';
        });
    }
    
    // Set up autogrow for textarea
    const queryInput = document.getElementById('query-input');
    if (queryInput) {
        queryInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight) + 'px';
        });
    }
}

// Load example queries for the current database
function loadExampleQueries(dbType) {
    const exampleContainer = document.getElementById('example-queries');
    if (!exampleContainer) return;
    
    // Get example queries for this database type
    // This uses the function from database_connectors.js
    const examples = getExampleQueries(dbType, {});
    
    // Display the example queries
    examples.forEach(example => {
        const exampleElement = document.createElement('div');
        exampleElement.className = 'example-query';
        exampleElement.textContent = example;
        
        // Add click handler to use this example
        exampleElement.addEventListener('click', function() {
            const queryInput = document.getElementById('query-input');
            queryInput.value = example;
            queryInput.focus();
            
            // Trigger height adjustment
            queryInput.dispatchEvent(new Event('input'));
        });
        
        exampleContainer.appendChild(exampleElement);
    });
}

// Load chat history for the current chat
function loadChatHistory() {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;
    
    // Show loading state
    messagesContainer.innerHTML = '<div class="text-center my-4"><div class="spinner-border text-secondary" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    
    // Fetch chat history
    fetch('/get_chat_history')
        .then(response => response.json())
        .then(data => {
            messagesContainer.innerHTML = '';
            
            if (data.success) {
                if (data.history && data.history.length > 0) {
                    // Display the chat history
                    data.history.forEach(message => {
                        addMessageToChat(message.query, 'user', message.created_at);
                        
                        if (message.is_error) {
                            addErrorMessageToChat(message.error);
                        } else {
                            addQueryToChat(message.generated_query);
                            addMessageToChat(message.result, 'system');
                        }
                    });
                } else {
                    // Show welcome message for new chat
                    showWelcomeMessage();
                }
            } else {
                showError(data.message || 'Failed to load chat history');
            }
            
            // Scroll to bottom
            scrollToBottom();
        })
        .catch(error => {
            console.error('Error loading chat history:', error);
            messagesContainer.innerHTML = '';
            showError('Failed to load chat history. Please try again.');
            showWelcomeMessage();
        });
}

// Load list of previous chats
function loadPreviousChats() {
    const chatList = document.getElementById('chat-list');
    if (!chatList) return;
    
    // Show loading state
    chatList.innerHTML = '<li class="text-center my-2"><div class="spinner-border spinner-border-sm text-secondary" role="status"><span class="visually-hidden">Loading...</span></div></li>';
    
    // Fetch previous chats
    fetch('/get_previous_chats')
        .then(response => response.json())
        .then(data => {
            chatList.innerHTML = '';
            
            if (data.success) {
                if (data.chats && data.chats.length > 0) {
                    // Display the previous chats
                    data.chats.forEach(chat => {
                        const chatItem = document.createElement('li');
                        chatItem.className = 'chat-list-item';
                        
                        // Highlight current chat
                        if (chat.id === currentChatId) {
                            chatItem.classList.add('active');
                        }
                        
                        // Create chat item content
                        const chatName = document.createElement('div');
                        chatName.className = 'small fw-medium';
                        
                        // Get the first message or use a default name
                        const chatTitle = chat.name || `Chat ${new Date(chat.created_at).toLocaleDateString()}`;
                        chatName.textContent = chatTitle;
                        chatItem.appendChild(chatName);
                        
                        // Add database badge
                        const dbBadge = document.createElement('span');
                        dbBadge.className = `db-badge db-badge-${chat.db_type} small me-2`;
                        dbBadge.textContent = databases[chat.db_type]?.name || chat.db_type;
                        
                        const chatInfo = document.createElement('div');
                        chatInfo.className = 'd-flex align-items-center mt-1';
                        chatInfo.appendChild(dbBadge);
                        
                        // Add timestamp
                        const timestamp = document.createElement('small');
                        timestamp.className = 'text-muted';
                        timestamp.textContent = formatDate(chat.created_at);
                        chatInfo.appendChild(timestamp);
                        
                        chatItem.appendChild(chatInfo);
                        
                        // Add click handler to load this chat
                        chatItem.addEventListener('click', function() {
                            loadChat(chat.id);
                        });
                        
                        chatList.appendChild(chatItem);
                    });
                } else {
                    chatList.innerHTML = '<li class="text-center text-muted my-3">No previous chats</li>';
                }
            } else {
                chatList.innerHTML = '<li class="text-center text-muted my-3">Error loading chats</li>';
            }
        })
        .catch(error => {
            console.error('Error loading previous chats:', error);
            chatList.innerHTML = '<li class="text-center text-muted my-3">Error loading chats</li>';
        });
}

// Send a query to the server
function sendQuery(query) {
    if (isProcessing) return;
    
    // Prevent multiple submissions
    isProcessing = true;
    
    // Add user message to chat
    addMessageToChat(query, 'user');
    
    // Show typing indicator
    addTypingIndicator();
    
    // Scroll to bottom
    scrollToBottom();
    
    // Send query to server
    fetch('/process_query', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            query: query
        })
    })
    .then(response => response.json())
    .then(data => {
        // Remove typing indicator
        removeTypingIndicator();
        
        if (data.success) {
            // Show the generated query
            addQueryToChat(data.query, data.explanation);
            
            // Show the response
            addMessageToChat(data.result, 'system');
        } else {
            // Show error message
            addErrorMessageToChat(data.message);
        }
        
        // Allow new queries
        isProcessing = false;
        
        // Scroll to bottom
        scrollToBottom();
    })
    .catch(error => {
        console.error('Error processing query:', error);
        
        // Remove typing indicator
        removeTypingIndicator();
        
        // Show error message
        addErrorMessageToChat('Error processing query. Please try again.');
        
        // Allow new queries
        isProcessing = false;
        
        // Scroll to bottom
        scrollToBottom();
    });
}

// Add a message to the chat
function addMessageToChat(content, sender, timestamp = null) {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;
    
    const messageElement = document.createElement('div');
    messageElement.className = `message message-${sender}`;
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    
    // For user messages, just add the text
    if (sender === 'user') {
        messageContent.textContent = content;
    } else {
        // For system messages, parse any markdown or HTML
        messageContent.innerHTML = content;
    }
    
    messageElement.appendChild(messageContent);
    
    // Add timestamp if provided
    if (timestamp) {
        const timestampElement = document.createElement('div');
        timestampElement.className = 'message-timestamp';
        timestampElement.textContent = formatDate(timestamp);
        messageElement.appendChild(timestampElement);
    }
    
    messagesContainer.appendChild(messageElement);
}

// Add the generated query to the chat
function addQueryToChat(query, explanation = null) {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;
    
    const queryElement = document.createElement('div');
    queryElement.className = 'message message-system';
    
    const queryContent = document.createElement('div');
    queryContent.className = 'message-content';
    
    // Add explanation if provided
    if (explanation) {
        const explanationElement = document.createElement('div');
        explanationElement.className = 'mb-2';
        explanationElement.textContent = explanation;
        queryContent.appendChild(explanationElement);
    }
    
    // Add query with syntax highlighting
    const queryCode = document.createElement('div');
    queryCode.className = 'message-query';
    queryCode.textContent = query;
    queryContent.appendChild(queryCode);
    
    queryElement.appendChild(queryContent);
    messagesContainer.appendChild(queryElement);
}

// Add an error message to the chat
function addErrorMessageToChat(errorMessage) {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;
    
    const errorElement = document.createElement('div');
    errorElement.className = 'message message-system';
    
    const errorContent = document.createElement('div');
    errorContent.className = 'message-content';
    
    const alertElement = document.createElement('div');
    alertElement.className = 'alert alert-danger mb-0';
    alertElement.textContent = errorMessage;
    
    errorContent.appendChild(alertElement);
    errorElement.appendChild(errorContent);
    messagesContainer.appendChild(errorElement);
}

// Add typing indicator
function addTypingIndicator() {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;
    
    // Create typing indicator
    const typingElement = document.createElement('div');
    typingElement.className = 'message message-system';
    typingElement.id = 'typing-indicator';
    
    const typingContent = document.createElement('div');
    typingContent.className = 'message-content';
    
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'typing-indicator';
    typingIndicator.innerHTML = '<span></span><span></span><span></span>';
    
    typingContent.appendChild(typingIndicator);
    typingElement.appendChild(typingContent);
    messagesContainer.appendChild(typingElement);
}

// Remove typing indicator
function removeTypingIndicator() {
    const typingIndicator = document.getElementById('typing-indicator');
    if (typingIndicator) {
        typingIndicator.remove();
    }
}

// Show welcome message
function showWelcomeMessage() {
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;
    
    // Only show if the messages container is empty
    if (messagesContainer.children.length === 0) {
        const welcomeElement = document.createElement('div');
        welcomeElement.className = 'text-center my-4';
        
        // Get database name
        const dbName = document.querySelector('#db-info')?.getAttribute('data-db-name') || 'database';
        
        welcomeElement.innerHTML = `
            <div class="mb-3">
                <i class="fas fa-database fa-3x text-secondary mb-3"></i>
                <h4>Welcome to DB Chat</h4>
                <p class="text-muted">You are connected to <strong>${dbName}</strong>.</p>
                <p>Ask questions about your database in natural language.</p>
            </div>
            <div class="mb-3">
                <p class="text-muted small">Examples:</p>
                <div id="welcome-examples" class="d-flex flex-column gap-2">
                    <div class="example-query" onclick="useExample(this)">Show me all tables in this database</div>
                    <div class="example-query" onclick="useExample(this)">How many records are in each table?</div>
                    <div class="example-query" onclick="useExample(this)">Show me the schema of a specific table</div>
                </div>
            </div>
        `;
        
        messagesContainer.appendChild(welcomeElement);
    }
}

// Use an example query
function useExample(element) {
    const queryInput = document.getElementById('query-input');
    queryInput.value = element.textContent;
    queryInput.focus();
    
    // Trigger height adjustment
    queryInput.dispatchEvent(new Event('input'));
}

// Scroll the chat to the bottom
function scrollToBottom() {
    const messagesContainer = document.getElementById('chat-messages');
    if (messagesContainer) {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
}

// Format a date string
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleString();
}

// Show error message
function showError(message) {
    const alertContainer = document.getElementById('alert-container');
    
    const alert = document.createElement('div');
    alert.className = 'alert alert-danger alert-dismissible fade show';
    alert.role = 'alert';
    
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    alertContainer.innerHTML = '';
    alertContainer.appendChild(alert);
    
    // Auto dismiss after 5 seconds
    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
    }, 5000);
}
