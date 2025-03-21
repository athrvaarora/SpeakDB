// chat.js - Chat interface functionality for SpeakDB application

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the chat interface
    initChatInterface();
    
    // Get chat ID from the URL if present
    const urlParams = new URLSearchParams(window.location.search);
    const chatId = urlParams.get('id');
    
    if (chatId) {
        // Load specific chat if ID is in URL
        loadChat(chatId);
    } else {
        // Otherwise load the current chat history
        loadChatHistory();
    }
    
    // Load the list of previous chats
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
    const chatMessages = document.getElementById('chat-messages');
    
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
    
    // Add event delegation for export buttons
    if (chatMessages) {
        chatMessages.addEventListener('click', function(e) {
            // Handle CSV export button clicks
            if (e.target.classList.contains('export-csv-btn') || e.target.closest('.export-csv-btn')) {
                const container = e.target.closest('.query-result-container');
                if (container) {
                    const hiddenData = container.querySelector('.hidden-data');
                    if (hiddenData && hiddenData.dataset.result) {
                        exportToCSV(hiddenData.dataset.result);
                    }
                }
            }
            
            // Handle JSON export button clicks
            if (e.target.classList.contains('export-json-btn') || e.target.closest('.export-json-btn')) {
                const container = e.target.closest('.query-result-container');
                if (container) {
                    const hiddenData = container.querySelector('.hidden-data');
                    if (hiddenData && hiddenData.dataset.result) {
                        exportToJSON(hiddenData.dataset.result);
                    }
                }
            }
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
                        chatItem.dataset.chatId = chat.id;
                        
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
                        dbBadge.textContent = chat.db_type;
                        
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
    messageElement.className = `message message-${sender} animate__animated`;
    
    // Add different animation based on sender
    if (sender === 'user') {
        messageElement.classList.add('animate__fadeInRight');
    } else {
        messageElement.classList.add('animate__fadeInLeft');
    }
    
    const messageContent = document.createElement('div');
    messageContent.className = 'message-content';
    
    // For user messages, just add the text
    if (sender === 'user') {
        messageContent.textContent = content;
    } else {
        // For system messages, parse markdown with marked.js
        // Add markdown-body class for GitHub-styled markdown
        messageContent.className += ' markdown-body';
        
        // Configure marked.js options
        marked.setOptions({
            highlight: function(code, lang) {
                if (lang && hljs.getLanguage(lang)) {
                    return hljs.highlight(code, { language: lang }).value;
                }
                return hljs.highlightAuto(code).value;
            },
            breaks: true,
            gfm: true
        });
        
        // Check if content contains table - could be query result
        const isQueryResult = content.includes('|') && content.includes('---') && (content.includes('SELECT') || content.includes('select'));
        
        // Parse markdown and sanitize HTML
        try {
            const parsedContent = marked.parse(content);
            messageContent.innerHTML = DOMPurify.sanitize(parsedContent);
            
            // Initialize highlight.js on code blocks after content is added
            setTimeout(() => {
                messageContent.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightElement(block);
                });
                
                // Format JSON in code blocks with class="language-json"
                messageContent.querySelectorAll('code.language-json').forEach((block) => {
                    try {
                        // Check if the content is JSON
                        const jsonObj = JSON.parse(block.textContent);
                        block.textContent = JSON.stringify(jsonObj, null, 2);
                        hljs.highlightElement(block);
                    } catch (e) {
                        // Not valid JSON, leave as is
                        console.log('Invalid JSON in code block', e);
                    }
                });
            }, 0);
            
            // If this appears to be a query result, add export buttons
            if (isQueryResult) {
                // Try to extract JSON data from the message content
                let jsonData = null;
                try {
                    // Look for JSON structure in the content - common pattern in our system responses
                    const jsonMatch = content.match(/```json\n([\s\S]*?)\n```/);
                    if (jsonMatch && jsonMatch[1]) {
                        jsonData = jsonMatch[1];
                    }
                } catch (e) {
                    console.log('No valid JSON data found for export', e);
                }
                
                if (jsonData) {
                    // Create export container
                    const exportContainer = document.createElement('div');
                    exportContainer.className = 'query-result-container mt-2';
                    
                    // Add export buttons
                    const exportButtons = document.createElement('div');
                    exportButtons.className = 'btn-group btn-group-sm';
                    
                    const csvButton = document.createElement('button');
                    csvButton.className = 'btn btn-outline-secondary export-csv-btn';
                    csvButton.innerHTML = '<i class="fas fa-file-csv me-1"></i> Export CSV';
                    
                    const jsonButton = document.createElement('button');
                    jsonButton.className = 'btn btn-outline-secondary export-json-btn';
                    jsonButton.innerHTML = '<i class="fas fa-file-code me-1"></i> Export JSON';
                    
                    exportButtons.appendChild(csvButton);
                    exportButtons.appendChild(jsonButton);
                    exportContainer.appendChild(exportButtons);
                    
                    // Hidden data element to store the raw JSON
                    const hiddenData = document.createElement('div');
                    hiddenData.className = 'hidden-data d-none';
                    hiddenData.dataset.result = jsonData;
                    exportContainer.appendChild(hiddenData);
                    
                    messageContent.appendChild(exportContainer);
                }
            }
        } catch (e) {
            console.error('Error parsing markdown:', e);
            messageContent.innerHTML = DOMPurify.sanitize(content);
        }
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
    queryContent.className = 'message-content markdown-body';
    
    // Create markdown content with explanation and SQL code block
    let markdownContent = '';
    
    // Add explanation if provided
    if (explanation) {
        markdownContent += `${explanation}\n\n`;
    }
    
    // Add query as SQL code block with syntax highlighting
    markdownContent += `\`\`\`sql\n${query}\n\`\`\``;
    
    // Parse markdown and sanitize HTML
    try {
        const parsedContent = marked.parse(markdownContent);
        queryContent.innerHTML = DOMPurify.sanitize(parsedContent);
        
        // Initialize highlight.js on code blocks
        setTimeout(() => {
            queryContent.querySelectorAll('pre code').forEach((block) => {
                hljs.highlightElement(block);
            });
        }, 0);
    } catch (e) {
        console.error('Error parsing markdown:', e);
        // Fallback to basic formatting if markdown parsing fails
        if (explanation) {
            const explanationElement = document.createElement('div');
            explanationElement.className = 'mb-2';
            explanationElement.textContent = explanation;
            queryContent.appendChild(explanationElement);
        }
        
        const queryCode = document.createElement('div');
        queryCode.className = 'message-query';
        queryCode.textContent = query;
        queryContent.appendChild(queryCode);
    }
    
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
            <div class="mb-4 animate__animated animate__fadeIn">
                <img src="/static/images/speakdb-logo.svg" alt="SpeakDB Logo" class="mb-3" width="80" height="80">
                <h4 class="fw-semibold">Welcome to SpeakDB</h4>
                <p class="text-muted">You are connected to <strong>${dbName}</strong>.</p>
                <p>Ask questions about your database using natural language.</p>
            </div>
            <div class="mb-3 animate__animated animate__fadeIn animate__delay-1s">
                <p class="text-muted small">Try these examples:</p>
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

// Load a specific chat by ID
function loadChat(chatId) {
    if (!chatId) return;
    
    // Store the chat ID
    currentChatId = chatId;
    
    // Update the URL without reloading the page
    history.pushState({}, '', `/chat?id=${chatId}`);
    
    const messagesContainer = document.getElementById('chat-messages');
    if (!messagesContainer) return;
    
    // Show loading state
    messagesContainer.innerHTML = '<div class="text-center my-4"><div class="spinner-border text-secondary" role="status"><span class="visually-hidden">Loading...</span></div><p class="mt-3 text-muted">Loading chat...</p></div>';
    
    // Fetch the chat
    fetch(`/load_chat/${chatId}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Update the database info
                const dbInfoElement = document.getElementById('db-info');
                if (dbInfoElement && data.chat.db_type) {
                    dbInfoElement.setAttribute('data-db-type', data.chat.db_type);
                    dbInfoElement.setAttribute('data-db-name', data.chat.db_name || data.chat.db_type);
                    
                    // Update UI elements
                    const dbBadge = document.querySelector('.db-badge');
                    if (dbBadge) {
                        dbBadge.className = `db-badge db-badge-${data.chat.db_type} me-2`;
                        dbBadge.textContent = data.chat.db_name || data.chat.db_type;
                    }
                    
                    // Reload example queries for this database type
                    currentDbType = data.chat.db_type;
                    const exampleContainer = document.getElementById('example-queries');
                    if (exampleContainer) {
                        exampleContainer.innerHTML = '';
                        loadExampleQueries(currentDbType);
                    }
                }
                
                // Show warning if there is one
                if (data.warning) {
                    showError(data.warning);
                }
                
                // Load chat history
                loadChatHistory();
                
                // Update chat list to highlight current chat
                const chatItems = document.querySelectorAll('.chat-list-item');
                chatItems.forEach(item => {
                    if (item.dataset.chatId === chatId) {
                        item.classList.add('active');
                    } else {
                        item.classList.remove('active');
                    }
                });
            } else {
                messagesContainer.innerHTML = '';
                showError(data.message || 'Failed to load chat');
                showWelcomeMessage();
            }
        })
        .catch(error => {
            console.error('Error loading chat:', error);
            messagesContainer.innerHTML = '';
            showError('Error loading chat. Please try again.');
            showWelcomeMessage();
        });
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

// Export data to CSV format
function exportToCSV(jsonDataStr) {
    try {
        // Parse the JSON data
        const jsonData = JSON.parse(jsonDataStr);
        
        if (!Array.isArray(jsonData) || jsonData.length === 0) {
            console.error('Invalid data for CSV export');
            return;
        }
        
        // Get the column headers from the first object
        const headers = Object.keys(jsonData[0]);
        
        // Create CSV header row
        let csvContent = headers.join(',') + '\n';
        
        // Add data rows
        jsonData.forEach(item => {
            const row = headers.map(header => {
                const value = item[header];
                
                // Format based on data type
                if (value === null || value === undefined) {
                    return '';
                } else if (typeof value === 'object') {
                    // Convert objects/arrays to JSON strings, ensure quotes are escaped
                    return '"' + JSON.stringify(value).replace(/"/g, '""') + '"';
                } else if (typeof value === 'string') {
                    // Escape quotes in strings
                    return '"' + value.replace(/"/g, '""') + '"';
                } else {
                    return value;
                }
            }).join(',');
            
            csvContent += row + '\n';
        });
        
        // Create and download the CSV file
        downloadFile(csvContent, 'query_result.csv', 'text/csv');
    } catch (e) {
        console.error('Error exporting to CSV:', e);
        showError('Failed to export data to CSV');
    }
}

// Export data to JSON format
function exportToJSON(jsonDataStr) {
    try {
        // Parse and re-stringify with proper formatting
        const jsonData = JSON.parse(jsonDataStr);
        const formattedJson = JSON.stringify(jsonData, null, 2);
        
        // Create and download the JSON file
        downloadFile(formattedJson, 'query_result.json', 'application/json');
    } catch (e) {
        console.error('Error exporting to JSON:', e);
        showError('Failed to export data to JSON');
    }
}

// Helper function to create and trigger download
function downloadFile(content, fileName, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    
    const a = document.createElement('a');
    a.href = url;
    a.download = fileName;
    document.body.appendChild(a);
    a.click();
    
    // Clean up
    setTimeout(() => {
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }, 100);
}
