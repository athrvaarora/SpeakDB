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
    const toggleSchemaExplorerBtn = document.getElementById('toggle-schema-explorer-btn');
    const closeSchemaExplorerBtn = document.getElementById('close-schema-explorer-btn');
    const refreshSchemaBtn = document.getElementById('refresh-schema-btn');
    
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
    
    // Schema Explorer Toggle Button
    if (toggleSchemaExplorerBtn) {
        toggleSchemaExplorerBtn.addEventListener('click', function() {
            toggleSchemaExplorer();
        });
    }
    
    // Close Schema Explorer Button
    if (closeSchemaExplorerBtn) {
        closeSchemaExplorerBtn.addEventListener('click', function() {
            closeSchemaExplorer();
        });
    }
    
    // Refresh Schema Button
    if (refreshSchemaBtn) {
        refreshSchemaBtn.addEventListener('click', function() {
            loadSchemaInfo(true);
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
    
    // Add schema analysis badge if explanation mentions schema analysis
    const hasSchemaAnalysis = explanation && (
        explanation.toLowerCase().includes('schema') || 
        explanation.toLowerCase().includes('table') || 
        explanation.toLowerCase().includes('column') || 
        explanation.toLowerCase().includes('relationship')
    );
    
    if (hasSchemaAnalysis) {
        const schemaAnalysisBadge = document.createElement('div');
        schemaAnalysisBadge.className = 'schema-analysis-badge mb-2';
        schemaAnalysisBadge.innerHTML = `
            <div class="d-flex align-items-center">
                <span class="badge bg-info me-2">
                    <i class="fas fa-brain me-1"></i> AI Schema Analysis
                </span>
                <span class="small text-muted">
                    This response uses AI analysis of your database structure to improve accuracy
                </span>
            </div>
        `;
        queryContent.appendChild(schemaAnalysisBadge);
    }
    
    // Create markdown content with explanation and SQL code block
    let markdownContent = '';
    
    // Add explanation if provided
    if (explanation) {
        markdownContent += `${explanation}\n\n`;
    }
    
    // Add query as SQL code block with syntax highlighting
    markdownContent += `\`\`\`sql\n${query}\n\`\`\``;
    
    // Create div for the markdown content
    const markdownDiv = document.createElement('div');
    
    // Parse markdown and sanitize HTML
    try {
        const parsedContent = marked.parse(markdownContent);
        markdownDiv.innerHTML = DOMPurify.sanitize(parsedContent);
        queryContent.appendChild(markdownDiv);
        
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
        welcomeElement.className = 'text-center welcome-container compact'; // Added 'compact' class
        
        // Get database name
        const dbName = document.querySelector('#db-info')?.getAttribute('data-db-name') || 'database';
        
        welcomeElement.innerHTML = `
            <div class="mb-2 animate__animated animate__fadeIn"> <!-- Reduced margin -->
                <img src="/static/images/speakdb-logo.svg" alt="SpeakDB Logo" class="mb-2" width="70" height="70"> <!-- Smaller logo, less margin -->
                <h4 class="fw-semibold mb-1">Welcome to SpeakDB</h4> <!-- Reduced margin -->
                <p class="text-muted mb-1">You are connected to <strong>${dbName}</strong>.</p> <!-- Reduced margin -->
                <p class="mb-2">Ask questions about your database using natural language.</p> <!-- Reduced margin -->
                <div class="schema-analysis-badge mt-2 mx-auto" style="max-width: 500px;"> <!-- Reduced margin -->
                    <div class="d-flex align-items-center">
                        <span class="badge bg-info me-2">
                            <i class="fas fa-brain me-1"></i> AI Schema Analysis
                        </span>
                        <span class="small text-muted">
                            Your database schema has been analyzed to improve query accuracy
                        </span>
                    </div>
                </div>
            </div>
            <div class="mb-1 animate__animated animate__fadeIn animate__delay-1s"> <!-- Reduced margin -->
                <p class="text-muted small mb-1">Try these examples:</p> <!-- Reduced margin -->
                <div id="welcome-examples" class="d-flex flex-column gap-1"> <!-- Reduced gap -->
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

// Schema Explorer Functions

// Toggle schema explorer visibility
function toggleSchemaExplorer() {
    const schemaPanel = document.getElementById('schema-explorer-panel');
    if (!schemaPanel) return;
    
    // If panel is already visible, hide it, otherwise show it
    if (schemaPanel.classList.contains('d-none')) {
        schemaPanel.classList.remove('d-none');
        loadSchemaInfo();
    } else {
        closeSchemaExplorer();
    }
}

// Close schema explorer
function closeSchemaExplorer() {
    const schemaPanel = document.getElementById('schema-explorer-panel');
    if (!schemaPanel) return;
    
    // Add closing animation
    schemaPanel.classList.add('closing');
    
    // Wait for animation to complete before hiding
    setTimeout(() => {
        schemaPanel.classList.add('d-none');
        schemaPanel.classList.remove('closing');
    }, 300);
}

// Load schema information from the server
function loadSchemaInfo(forceRefresh = false) {
    const schemaTree = document.getElementById('schema-tree');
    const loadingElement = document.querySelector('.schema-loading');
    
    if (!schemaTree || !loadingElement) return;
    
    // Show loading state
    schemaTree.innerHTML = '';
    loadingElement.classList.remove('d-none');
    
    // Load schema info from server
    fetch('/get_schema_info' + (forceRefresh ? '?refresh=true' : ''))
        .then(response => response.json())
        .then(data => {
            // Hide loading indicator
            loadingElement.classList.add('d-none');
            
            if (data.success) {
                renderSchemaTree(data.schema, data.db_type);
            } else {
                schemaTree.innerHTML = `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-triangle me-2"></i>
                        ${data.message || 'Failed to load schema information'}
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Error loading schema info:', error);
            loadingElement.classList.add('d-none');
            schemaTree.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    Error loading schema information. Please try again.
                </div>
            `;
        });
}

// Render schema tree based on database type
function renderSchemaTree(schema, dbType) {
    const schemaTree = document.getElementById('schema-tree');
    if (!schemaTree) return;
    
    // Check if schema is empty
    if (!schema || schema.length === 0) {
        schemaTree.innerHTML = `
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                No schema information available for this database.
            </div>
        `;
        return;
    }
    
    // Create schema tree based on database type
    if (['postgresql', 'mysql', 'sqlserver', 'oracle', 'sqlite', 'mariadb',
         'db2', 'redshift', 'timescaledb', 'heroku', 'neon', 'crunchybridge'].includes(dbType)) {
        // Relational databases - show tables and columns
        renderRelationalSchema(schema, schemaTree);
    } else if (['mongodb', 'cassandra', 'dynamodb', 'couchbase'].includes(dbType)) {
        // NoSQL databases - show collections/tables and fields
        renderNoSQLSchema(schema, schemaTree);
    } else if (['neo4j', 'tigergraph'].includes(dbType)) {
        // Graph databases - show nodes, relationships, and properties
        renderGraphSchema(schema, schemaTree);
    } else if (['influxdb', 'prometheus', 'kdb'].includes(dbType)) {
        // Time series databases - show measurements, fields, and tags
        renderTimeSeriesSchema(schema, schemaTree);
    } else {
        // Generic rendering for other database types
        renderGenericSchema(schema, schemaTree);
    }
}

// Render relational database schema
function renderRelationalSchema(schema, container) {
    container.innerHTML = '';
    
    schema.forEach(table => {
        const tableEl = document.createElement('div');
        tableEl.className = 'schema-table';
        
        // Create table header
        const tableHeader = document.createElement('div');
        tableHeader.className = 'schema-table-header';
        tableHeader.innerHTML = `
            <div class="schema-table-icon">
                <i class="fas fa-table"></i>
            </div>
            <div class="schema-table-name">${escapeHtml(table.name)}</div>
        `;
        
        // Add click handler to toggle columns
        tableHeader.addEventListener('click', function() {
            tableEl.classList.toggle('schema-table-expanded');
        });
        
        tableEl.appendChild(tableHeader);
        
        // Create columns container
        const columnsContainer = document.createElement('div');
        columnsContainer.className = 'schema-table-columns';
        
        // Add columns
        if (table.columns && table.columns.length > 0) {
            table.columns.forEach(column => {
                const columnEl = document.createElement('div');
                columnEl.className = 'schema-column';
                
                // Column name and type
                columnEl.innerHTML = `
                    <div class="schema-column-name">${escapeHtml(column.name)}</div>
                    <div class="schema-column-type">${escapeHtml(column.type)}</div>
                `;
                
                // Add primary key indicator
                if (column.primary_key) {
                    const pkBadge = document.createElement('div');
                    pkBadge.className = 'schema-column-pk';
                    pkBadge.innerHTML = '<i class="fas fa-key me-1"></i> PK';
                    columnEl.appendChild(pkBadge);
                }
                
                // Add foreign key indicator
                if (column.foreign_key) {
                    const fkBadge = document.createElement('div');
                    fkBadge.className = 'schema-column-fk';
                    fkBadge.innerHTML = '<i class="fas fa-link me-1"></i> FK';
                    if (column.reference) {
                        fkBadge.innerHTML += ` → ${escapeHtml(column.reference)}`;
                    }
                    columnEl.appendChild(fkBadge);
                }
                
                columnsContainer.appendChild(columnEl);
            });
        } else {
            columnsContainer.innerHTML = '<div class="text-muted small">No columns information available</div>';
        }
        
        tableEl.appendChild(columnsContainer);
        container.appendChild(tableEl);
    });
}

// Render NoSQL database schema
function renderNoSQLSchema(schema, container) {
    container.innerHTML = '';
    
    schema.forEach(collection => {
        const collectionEl = document.createElement('div');
        collectionEl.className = 'schema-table';
        
        // Create collection header
        const collectionHeader = document.createElement('div');
        collectionHeader.className = 'schema-table-header';
        collectionHeader.innerHTML = `
            <div class="schema-table-icon">
                <i class="fas fa-cubes"></i>
            </div>
            <div class="schema-table-name">${escapeHtml(collection.name)}</div>
        `;
        
        // Add click handler to toggle fields
        collectionHeader.addEventListener('click', function() {
            collectionEl.classList.toggle('schema-table-expanded');
        });
        
        collectionEl.appendChild(collectionHeader);
        
        // Create fields container
        const fieldsContainer = document.createElement('div');
        fieldsContainer.className = 'schema-table-columns';
        
        // Add fields
        if (collection.fields && collection.fields.length > 0) {
            collection.fields.forEach(field => {
                const fieldEl = document.createElement('div');
                fieldEl.className = 'schema-column';
                
                // Field name and type
                fieldEl.innerHTML = `
                    <div class="schema-column-name">${escapeHtml(field.name)}</div>
                    <div class="schema-column-type">${escapeHtml(field.type)}</div>
                `;
                
                fieldsContainer.appendChild(fieldEl);
            });
        } else {
            fieldsContainer.innerHTML = '<div class="text-muted small">No fields information available</div>';
        }
        
        collectionEl.appendChild(fieldsContainer);
        container.appendChild(collectionEl);
    });
}

// Render graph database schema
function renderGraphSchema(schema, container) {
    container.innerHTML = '';
    
    // Group schema elements by type (nodes and relationships)
    const nodes = schema.filter(item => item.type === 'node');
    const relationships = schema.filter(item => item.type === 'relationship');
    
    // Create sections
    if (nodes.length > 0) {
        const nodesSection = document.createElement('div');
        nodesSection.className = 'mb-3';
        
        const nodesSectionHeader = document.createElement('h6');
        nodesSectionHeader.className = 'schema-section-header';
        nodesSectionHeader.innerHTML = '<i class="fas fa-circle me-2"></i> Nodes';
        nodesSection.appendChild(nodesSectionHeader);
        
        // Add each node
        nodes.forEach(node => {
            const nodeEl = document.createElement('div');
            nodeEl.className = 'schema-table';
            
            // Create node header
            const nodeHeader = document.createElement('div');
            nodeHeader.className = 'schema-table-header';
            nodeHeader.innerHTML = `
                <div class="schema-table-icon">
                    <i class="fas fa-circle"></i>
                </div>
                <div class="schema-table-name">${escapeHtml(node.name)}</div>
            `;
            
            // Add click handler to toggle properties
            nodeHeader.addEventListener('click', function() {
                nodeEl.classList.toggle('schema-table-expanded');
            });
            
            nodeEl.appendChild(nodeHeader);
            
            // Create properties container
            const propsContainer = document.createElement('div');
            propsContainer.className = 'schema-table-columns';
            
            // Add properties
            if (node.properties && node.properties.length > 0) {
                node.properties.forEach(prop => {
                    const propEl = document.createElement('div');
                    propEl.className = 'schema-column';
                    
                    // Property name and type
                    propEl.innerHTML = `
                        <div class="schema-column-name">${escapeHtml(prop.name)}</div>
                        <div class="schema-column-type">${escapeHtml(prop.type)}</div>
                    `;
                    
                    propsContainer.appendChild(propEl);
                });
            } else {
                propsContainer.innerHTML = '<div class="text-muted small">No properties information available</div>';
            }
            
            nodeEl.appendChild(propsContainer);
            nodesSection.appendChild(nodeEl);
        });
        
        container.appendChild(nodesSection);
    }
    
    if (relationships.length > 0) {
        const relsSection = document.createElement('div');
        relsSection.className = 'mb-3';
        
        const relsSectionHeader = document.createElement('h6');
        relsSectionHeader.className = 'schema-section-header';
        relsSectionHeader.innerHTML = '<i class="fas fa-project-diagram me-2"></i> Relationships';
        relsSection.appendChild(relsSectionHeader);
        
        // Add each relationship
        relationships.forEach(rel => {
            const relEl = document.createElement('div');
            relEl.className = 'schema-table';
            
            // Create relationship header
            const relHeader = document.createElement('div');
            relHeader.className = 'schema-table-header';
            relHeader.innerHTML = `
                <div class="schema-table-icon">
                    <i class="fas fa-arrow-right"></i>
                </div>
                <div class="schema-table-name">${escapeHtml(rel.name)}</div>
            `;
            
            // Add click handler to toggle details
            relHeader.addEventListener('click', function() {
                relEl.classList.toggle('schema-table-expanded');
            });
            
            relEl.appendChild(relHeader);
            
            // Create details container
            const detailsContainer = document.createElement('div');
            detailsContainer.className = 'schema-table-columns';
            
            // Add connection info
            if (rel.start_node && rel.end_node) {
                const connectionEl = document.createElement('div');
                connectionEl.className = 'schema-relation-path mb-2';
                connectionEl.innerHTML = `
                    <div class="text-muted mb-1">Connection:</div>
                    <div class="d-flex align-items-center">
                        <span class="me-2">${escapeHtml(rel.start_node)}</span>
                        <i class="fas fa-long-arrow-alt-right text-primary mx-2"></i>
                        <span>${escapeHtml(rel.end_node)}</span>
                    </div>
                `;
                detailsContainer.appendChild(connectionEl);
            }
            
            // Add properties
            if (rel.properties && rel.properties.length > 0) {
                const propsTitle = document.createElement('div');
                propsTitle.className = 'text-muted mb-1 mt-2';
                propsTitle.textContent = 'Properties:';
                detailsContainer.appendChild(propsTitle);
                
                rel.properties.forEach(prop => {
                    const propEl = document.createElement('div');
                    propEl.className = 'schema-column';
                    
                    // Property name and type
                    propEl.innerHTML = `
                        <div class="schema-column-name">${escapeHtml(prop.name)}</div>
                        <div class="schema-column-type">${escapeHtml(prop.type)}</div>
                    `;
                    
                    detailsContainer.appendChild(propEl);
                });
            } else {
                detailsContainer.innerHTML += '<div class="text-muted small mt-2">No properties information available</div>';
            }
            
            relEl.appendChild(detailsContainer);
            relsSection.appendChild(relEl);
        });
        
        container.appendChild(relsSection);
    }
    
    if (nodes.length === 0 && relationships.length === 0) {
        container.innerHTML = '<div class="alert alert-info">No graph schema information available</div>';
    }
}

// Render time series database schema
function renderTimeSeriesSchema(schema, container) {
    container.innerHTML = '';
    
    schema.forEach(measurement => {
        const measurementEl = document.createElement('div');
        measurementEl.className = 'schema-table';
        
        // Create measurement header
        const measurementHeader = document.createElement('div');
        measurementHeader.className = 'schema-table-header';
        measurementHeader.innerHTML = `
            <div class="schema-table-icon">
                <i class="fas fa-chart-line"></i>
            </div>
            <div class="schema-table-name">${escapeHtml(measurement.name)}</div>
        `;
        
        // Add click handler to toggle details
        measurementHeader.addEventListener('click', function() {
            measurementEl.classList.toggle('schema-table-expanded');
        });
        
        measurementEl.appendChild(measurementHeader);
        
        // Create details container
        const detailsContainer = document.createElement('div');
        detailsContainer.className = 'schema-table-columns';
        
        // Add fields
        if (measurement.fields && measurement.fields.length > 0) {
            const fieldsTitle = document.createElement('div');
            fieldsTitle.className = 'text-muted mb-1';
            fieldsTitle.innerHTML = '<i class="fas fa-hashtag me-1"></i> Fields:';
            detailsContainer.appendChild(fieldsTitle);
            
            measurement.fields.forEach(field => {
                const fieldEl = document.createElement('div');
                fieldEl.className = 'schema-column';
                
                // Field name and type
                fieldEl.innerHTML = `
                    <div class="schema-column-name">${escapeHtml(field.name)}</div>
                    <div class="schema-column-type">${escapeHtml(field.type)}</div>
                `;
                
                detailsContainer.appendChild(fieldEl);
            });
        }
        
        // Add tags
        if (measurement.tags && measurement.tags.length > 0) {
            const tagsTitle = document.createElement('div');
            tagsTitle.className = 'text-muted mb-1 mt-3';
            tagsTitle.innerHTML = '<i class="fas fa-tag me-1"></i> Tags:';
            detailsContainer.appendChild(tagsTitle);
            
            measurement.tags.forEach(tag => {
                const tagEl = document.createElement('div');
                tagEl.className = 'schema-column';
                
                // Tag name
                tagEl.innerHTML = `
                    <div class="schema-column-name">${escapeHtml(tag.name)}</div>
                `;
                
                detailsContainer.appendChild(tagEl);
            });
        }
        
        if ((!measurement.fields || measurement.fields.length === 0) && 
            (!measurement.tags || measurement.tags.length === 0)) {
            detailsContainer.innerHTML = '<div class="text-muted small">No fields or tags information available</div>';
        }
        
        measurementEl.appendChild(detailsContainer);
        container.appendChild(measurementEl);
    });
}

// Render generic schema for other database types
function renderGenericSchema(schema, container) {
    container.innerHTML = '';
    
    schema.forEach(item => {
        const itemEl = document.createElement('div');
        itemEl.className = 'schema-table';
        
        // Create item header
        const itemHeader = document.createElement('div');
        itemHeader.className = 'schema-table-header';
        itemHeader.innerHTML = `
            <div class="schema-table-icon">
                <i class="fas fa-database"></i>
            </div>
            <div class="schema-table-name">${escapeHtml(item.name)}</div>
        `;
        
        // Add click handler to toggle fields
        itemHeader.addEventListener('click', function() {
            itemEl.classList.toggle('schema-table-expanded');
        });
        
        itemEl.appendChild(itemHeader);
        
        // Create fields container
        const fieldsContainer = document.createElement('div');
        fieldsContainer.className = 'schema-table-columns';
        
        // Add fields
        if (item.fields && item.fields.length > 0) {
            item.fields.forEach(field => {
                const fieldEl = document.createElement('div');
                fieldEl.className = 'schema-column';
                
                // Field name and type
                fieldEl.innerHTML = `
                    <div class="schema-column-name">${escapeHtml(field.name)}</div>
                    <div class="schema-column-type">${field.type ? escapeHtml(field.type) : ''}</div>
                `;
                
                fieldsContainer.appendChild(fieldEl);
            });
        } else {
            fieldsContainer.innerHTML = '<div class="text-muted small">No fields information available</div>';
        }
        
        itemEl.appendChild(fieldsContainer);
        container.appendChild(itemEl);
    });
}

// Helper function to escape HTML
function escapeHtml(unsafe) {
    if (unsafe === null || unsafe === undefined) return '';
    return String(unsafe)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
