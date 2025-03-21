// main.js - Main JavaScript for the DB Chat application

document.addEventListener('DOMContentLoaded', function() {
    // Initialize the application
    initDatabaseSelection();
});

// Database logos and information
const databases = {
    // Relational Databases
    'postgresql': { name: 'PostgreSQL', category: 'Relational' },
    'mysql': { name: 'MySQL', category: 'Relational' },
    'sqlserver': { name: 'SQL Server', category: 'Relational' },
    'oracle': { name: 'Oracle Database', category: 'Relational' },
    'sqlite': { name: 'SQLite', category: 'Relational' },
    'redshift': { name: 'Amazon Redshift', category: 'Relational' },
    'cloudsql': { name: 'Google Cloud SQL', category: 'Relational' },
    'mariadb': { name: 'MariaDB', category: 'Relational' },
    'db2': { name: 'IBM Db2', category: 'Relational' },
    
    // NoSQL Databases
    'mongodb': { name: 'MongoDB', category: 'NoSQL' },
    'cassandra': { name: 'Cassandra', category: 'NoSQL' },
    'redis': { name: 'Redis', category: 'NoSQL' },
    'elasticsearch': { name: 'Elasticsearch', category: 'NoSQL' },
    'dynamodb': { name: 'DynamoDB', category: 'NoSQL' },
    'couchbase': { name: 'Couchbase', category: 'NoSQL' },
    'neo4j': { name: 'Neo4j', category: 'NoSQL' },
    
    // Data Warehouses
    'snowflake': { name: 'Snowflake', category: 'Data Warehouse' },
    'bigquery': { name: 'Google BigQuery', category: 'Data Warehouse' },
    'synapse': { name: 'Azure Synapse Analytics', category: 'Data Warehouse' },
    
    // Cloud Databases
    'cosmosdb': { name: 'Azure Cosmos DB', category: 'Cloud' },
    'firestore': { name: 'Firestore', category: 'Cloud' },
    
    // Time Series Databases
    'influxdb': { name: 'InfluxDB', category: 'Time Series' }
};

// Initialize the database selection page
function initDatabaseSelection() {
    const dbSelectionContainer = document.getElementById('database-selection');
    
    if (!dbSelectionContainer) return;
    
    // Group databases by category
    const categories = {};
    
    for (const [dbType, dbInfo] of Object.entries(databases)) {
        if (!categories[dbInfo.category]) {
            categories[dbInfo.category] = [];
        }
        
        categories[dbInfo.category].push({
            type: dbType,
            name: dbInfo.name
        });
    }
    
    // Create category sections
    for (const [category, dbs] of Object.entries(categories)) {
        const categorySection = document.createElement('div');
        categorySection.className = 'db-category';
        
        const categoryTitle = document.createElement('h2');
        categoryTitle.textContent = category + ' Databases';
        categorySection.appendChild(categoryTitle);
        
        const dbGrid = document.createElement('div');
        dbGrid.className = 'db-grid';
        
        // Create database tiles
        dbs.forEach(db => {
            const dbTile = document.createElement('div');
            dbTile.className = 'db-tile';
            dbTile.setAttribute('data-db-type', db.type);
            
            // Create SVG logo using our database_logos.js utility
            const logoSvg = getDatabaseLogo(db.type);
            dbTile.innerHTML = logoSvg;
            
            const dbName = document.createElement('div');
            dbName.className = 'db-name';
            dbName.textContent = db.name;
            dbTile.appendChild(dbName);
            
            // Add click event
            dbTile.addEventListener('click', function() {
                selectDatabase(db.type);
            });
            
            dbGrid.appendChild(dbTile);
        });
        
        categorySection.appendChild(dbGrid);
        dbSelectionContainer.appendChild(categorySection);
    }
}

// Handle database selection
function selectDatabase(dbType) {
    // Get the required credentials for this database type
    fetch(`/get_required_credentials?db_type=${dbType}`)
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showCredentialForm(dbType, data.credentials);
            } else {
                showError(data.message);
            }
        })
        .catch(error => {
            console.error('Error fetching credential requirements:', error);
            showError('Failed to get credential requirements');
        });
}

// Show credential form for the selected database
function showCredentialForm(dbType, credentialInfo) {
    const dbSelectionContainer = document.getElementById('database-selection');
    const credentialFormContainer = document.getElementById('credential-form-container');
    
    // Hide database selection and show credential form
    dbSelectionContainer.style.display = 'none';
    credentialFormContainer.style.display = 'block';
    
    // Set the database name in the form
    const dbNameElement = document.getElementById('credential-db-name');
    dbNameElement.textContent = databases[dbType].name;
    
    // Clear any existing form fields
    const credentialForm = document.getElementById('credential-form');
    credentialForm.innerHTML = '';
    
    // Check if the credential info is in the new format (object) or old format (array)
    const useIndividualFields = Array.isArray(credentialInfo) || (credentialInfo && credentialInfo.fields);
    const requiredFields = Array.isArray(credentialInfo) ? credentialInfo : (credentialInfo ? credentialInfo.fields : []);
    const supportsConnectionString = credentialInfo && credentialInfo.url_option;
    
    // If connection string is supported, create a toggle switch
    if (supportsConnectionString) {
        const connectionStringToggleGroup = document.createElement('div');
        connectionStringToggleGroup.className = 'form-group mb-4';
        
        const toggleLabel = document.createElement('label');
        toggleLabel.className = 'form-label d-block mb-3';
        toggleLabel.textContent = 'Connection Method:';
        connectionStringToggleGroup.appendChild(toggleLabel);
        
        const buttonGroup = document.createElement('div');
        buttonGroup.className = 'btn-group w-100 mb-3';
        buttonGroup.role = 'group';
        
        const individualButton = document.createElement('button');
        individualButton.type = 'button';
        individualButton.className = 'btn btn-outline-primary active';
        individualButton.id = 'toggle-individual';
        individualButton.textContent = 'Individual Fields';
        
        const urlButton = document.createElement('button');
        urlButton.type = 'button';
        urlButton.className = 'btn btn-outline-primary';
        urlButton.id = 'toggle-url';
        urlButton.textContent = 'Connection String';
        
        buttonGroup.appendChild(individualButton);
        buttonGroup.appendChild(urlButton);
        connectionStringToggleGroup.appendChild(buttonGroup);
        
        // Create container divs for each mode
        const individualFieldsContainer = document.createElement('div');
        individualFieldsContainer.id = 'individual-fields-container';
        individualFieldsContainer.style.display = 'block';
        
        const urlFieldContainer = document.createElement('div');
        urlFieldContainer.id = 'url-field-container';
        urlFieldContainer.style.display = 'none';
        
        // Create connection string field
        const urlFormGroup = document.createElement('div');
        urlFormGroup.className = 'form-group mb-3';
        
        const urlLabel = document.createElement('label');
        urlLabel.setAttribute('for', `credential-${credentialInfo.url_field}`);
        urlLabel.textContent = formatCredentialLabel(credentialInfo.url_field);
        urlFormGroup.appendChild(urlLabel);
        
        const urlInput = document.createElement('input');
        urlInput.type = 'text';
        urlInput.className = 'form-control';
        urlInput.id = `credential-${credentialInfo.url_field}`;
        urlInput.name = credentialInfo.url_field;
        if (credentialInfo.url_example) {
            urlInput.placeholder = credentialInfo.url_example;
        }
        urlFormGroup.appendChild(urlInput);
        
        // Add example if provided
        if (credentialInfo.url_example) {
            const exampleText = document.createElement('small');
            exampleText.className = 'form-text text-muted';
            exampleText.textContent = `Example: ${credentialInfo.url_example}`;
            urlFormGroup.appendChild(exampleText);
        }
        
        urlFieldContainer.appendChild(urlFormGroup);
        
        // Add event listeners for toggle buttons
        individualButton.addEventListener('click', function() {
            individualButton.classList.add('active');
            urlButton.classList.remove('active');
            individualFieldsContainer.style.display = 'block';
            urlFieldContainer.style.display = 'none';
            
            // Make individual fields required and URL field not required
            const individualInputs = individualFieldsContainer.querySelectorAll('input');
            const urlInputs = urlFieldContainer.querySelectorAll('input');
            
            individualInputs.forEach(input => input.required = true);
            urlInputs.forEach(input => input.required = false);
        });
        
        urlButton.addEventListener('click', function() {
            urlButton.classList.add('active');
            individualButton.classList.remove('active');
            urlFieldContainer.style.display = 'block';
            individualFieldsContainer.style.display = 'none';
            
            // Make URL field required and individual fields not required
            const individualInputs = individualFieldsContainer.querySelectorAll('input');
            const urlInputs = urlFieldContainer.querySelectorAll('input');
            
            individualInputs.forEach(input => input.required = false);
            urlInputs.forEach(input => input.required = true);
        });
        
        credentialForm.appendChild(connectionStringToggleGroup);
        credentialForm.appendChild(individualFieldsContainer);
        credentialForm.appendChild(urlFieldContainer);
        
        // Create form fields for each required credential
        requiredFields.forEach(credential => {
            const formGroup = document.createElement('div');
            formGroup.className = 'form-group mb-3';
            
            const label = document.createElement('label');
            label.setAttribute('for', `credential-${credential}`);
            label.textContent = formatCredentialLabel(credential);
            formGroup.appendChild(label);
            
            const input = document.createElement('input');
            input.type = credential.includes('password') ? 'password' : 'text';
            input.className = 'form-control';
            input.id = `credential-${credential}`;
            input.name = credential;
            input.required = true;
            
            // Set default values or placeholders based on credential type
            if (credential === 'port') {
                switch (dbType) {
                    case 'postgresql':
                        input.placeholder = '5432';
                        break;
                    case 'mysql':
                    case 'mariadb':
                        input.placeholder = '3306';
                        break;
                    case 'mongodb':
                        input.placeholder = '27017';
                        break;
                    case 'redis':
                        input.placeholder = '6379';
                        break;
                    case 'elasticsearch':
                        input.placeholder = '9200';
                        break;
                    case 'cassandra':
                        input.placeholder = '9042';
                        break;
                    case 'influxdb':
                        input.placeholder = '8086';
                        break;
                    default:
                        input.placeholder = 'Enter port...';
                }
            } else if (credential === 'host') {
                input.placeholder = 'localhost';
            }
            
            formGroup.appendChild(input);
            individualFieldsContainer.appendChild(formGroup);
        });
    } else {
        // Standard form without connection string option
        // Create form fields for each required credential
        requiredFields.forEach(credential => {
            const formGroup = document.createElement('div');
            formGroup.className = 'form-group mb-3';
            
            const label = document.createElement('label');
            label.setAttribute('for', `credential-${credential}`);
            label.textContent = formatCredentialLabel(credential);
            formGroup.appendChild(label);
            
            const input = document.createElement('input');
            input.type = credential.includes('password') ? 'password' : 'text';
            input.className = 'form-control';
            input.id = `credential-${credential}`;
            input.name = credential;
            input.required = true;
            
            // Set default values or placeholders based on credential type
            if (credential === 'port') {
                switch (dbType) {
                    case 'postgresql':
                        input.placeholder = '5432';
                        break;
                    case 'mysql':
                    case 'mariadb':
                        input.placeholder = '3306';
                        break;
                    case 'mongodb':
                        input.placeholder = '27017';
                        break;
                    case 'redis':
                        input.placeholder = '6379';
                        break;
                    case 'elasticsearch':
                        input.placeholder = '9200';
                        break;
                    case 'cassandra':
                        input.placeholder = '9042';
                        break;
                    case 'influxdb':
                        input.placeholder = '8086';
                        break;
                    default:
                        input.placeholder = 'Enter port...';
                }
            } else if (credential === 'host') {
                input.placeholder = 'localhost';
            }
            
            formGroup.appendChild(input);
            credentialForm.appendChild(formGroup);
        });
    }
    
    // Add hidden input for database type
    const dbTypeInput = document.createElement('input');
    dbTypeInput.type = 'hidden';
    dbTypeInput.name = 'db_type';
    dbTypeInput.value = dbType;
    credentialForm.appendChild(dbTypeInput);
    
    // Add submit and cancel buttons
    const buttonGroup = document.createElement('div');
    buttonGroup.className = 'd-flex justify-content-between mt-4';
    
    const cancelButton = document.createElement('button');
    cancelButton.type = 'button';
    cancelButton.className = 'btn btn-secondary';
    cancelButton.textContent = 'Back';
    cancelButton.addEventListener('click', function() {
        credentialFormContainer.style.display = 'none';
        dbSelectionContainer.style.display = 'block';
    });
    buttonGroup.appendChild(cancelButton);
    
    const submitButton = document.createElement('button');
    submitButton.type = 'submit';
    submitButton.className = 'btn btn-primary';
    submitButton.textContent = 'Test Connection';
    buttonGroup.appendChild(submitButton);
    
    credentialForm.appendChild(buttonGroup);
    
    // Add submit event listener to the form
    credentialForm.addEventListener('submit', function(event) {
        event.preventDefault();
        testConnection(credentialForm);
    });
}

// Test connection with provided credentials
function testConnection(form) {
    const formData = new FormData(form);
    const credentials = {};
    const dbType = formData.get('db_type');
    
    // Build credentials object
    for (const [key, value] of formData.entries()) {
        if (key !== 'db_type') {
            credentials[key] = value;
        }
    }
    
    // Show loading state
    const submitButton = form.querySelector('button[type="submit"]');
    const originalText = submitButton.textContent;
    submitButton.disabled = true;
    submitButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Testing...';
    
    // Send request to test connection
    fetch('/test_connection', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            db_type: dbType,
            credentials: credentials
        })
    })
    .then(response => response.json())
    .then(data => {
        // Reset button state
        submitButton.disabled = false;
        submitButton.textContent = originalText;
        
        if (data.success) {
            // Show success message and redirect to chat
            showSuccess('Connection successful! Redirecting to chat...');
            
            // Redirect to chat page after a short delay
            setTimeout(() => {
                window.location.href = '/chat';
            }, 1500);
            
        } else {
            showError(data.message);
        }
    })
    .catch(error => {
        // Reset button state
        submitButton.disabled = false;
        submitButton.textContent = originalText;
        
        console.error('Error testing connection:', error);
        showError('An error occurred while testing the connection');
    });
}

// Helper function to format credential labels
function formatCredentialLabel(credential) {
    // Convert snake_case to Title Case with spaces
    return credential
        .split('_')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
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

// Show success message
function showSuccess(message) {
    const alertContainer = document.getElementById('alert-container');
    
    const alert = document.createElement('div');
    alert.className = 'alert alert-success alert-dismissible fade show';
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
