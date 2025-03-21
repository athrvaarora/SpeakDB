// database_connectors.js - Functions for database connection handling

// Get example queries for each database type
function getExampleQueries(dbType, schema) {
    let examples = [];
    
    // Generic examples for all database types
    examples.push("Show me all tables in the database");
    examples.push("How many records are in the [table] table?");
    
    // Database-specific examples
    switch (dbType) {
        case 'postgresql':
        case 'mysql':
        case 'sqlserver':
        case 'oracle':
        case 'sqlite':
        case 'redshift':
        case 'cloudsql':
        case 'mariadb':
        case 'db2':
        case 'snowflake':
        case 'synapse':
            // SQL databases
            examples.push("Select the first 10 records from [table]");
            examples.push("Show me the schema of [table]");
            examples.push("Count the number of records in [table] grouped by [column]");
            examples.push("Find all records in [table] where [column] equals [value]");
            examples.push("Join [table1] and [table2] on [common_column]");
            break;
            
        case 'mongodb':
            examples.push("Find documents in [collection] where [field] equals [value]");
            examples.push("Count documents in [collection]");
            examples.push("Aggregate documents in [collection] by [field]");
            break;
            
        case 'redis':
            examples.push("Get the value of [key]");
            examples.push("List all keys matching [pattern]");
            examples.push("Get all fields in hash [key]");
            break;
            
        case 'elasticsearch':
            examples.push("Search for [term] in [index]");
            examples.push("Count documents in [index]");
            examples.push("Get mapping for [index]");
            break;
            
        case 'cassandra':
            examples.push("Select all records from [table]");
            examples.push("Count records in [table]");
            examples.push("Select records from [table] where [column] equals [value]");
            break;
            
        case 'dynamodb':
            examples.push("Scan [table] for all items");
            examples.push("Get item from [table] with key [key_value]");
            examples.push("Query [table] where [key] equals [value]");
            break;
            
        case 'neo4j':
            examples.push("Match all nodes with label [Label]");
            examples.push("Find relationships between nodes");
            examples.push("Count nodes with label [Label]");
            break;
            
        case 'influxdb':
            examples.push("Get the last 10 measurements from [bucket]");
            examples.push("Calculate mean of [field] from [bucket] grouped by [tag]");
            examples.push("Count measurements in [bucket] over the last hour");
            break;
            
        default:
            // Add more generic examples
            examples.push("Get all data from [table/collection]");
            examples.push("Find records matching [criteria]");
    }
    
    // If we have schema information, use it to make more specific examples
    if (schema && schema.tables) {
        const tables = schema.tables;
        if (tables.length > 0) {
            const sampleTable = tables[0].name;
            
            // Replace [table] with actual table name in some examples
            examples = examples.map(example => {
                return example.replace('[table]', sampleTable);
            });
            
            // Add more specific examples based on columns
            if (tables[0].columns && tables[0].columns.length > 0) {
                const sampleColumn = tables[0].columns[0].name;
                
                examples.push(`Select ${sampleColumn} from ${sampleTable}`);
                examples.push(`Sort ${sampleTable} by ${sampleColumn}`);
            }
        }
    }
    
    return examples;
}

// Helper function to generate a "Connecting..." message with the appropriate database name
function getConnectingMessage(dbType) {
    const dbName = databases[dbType]?.name || dbType;
    return `Connecting to ${dbName}...`;
}

// Format a database query result for display
function formatQueryResult(result) {
    if (!result || result.length === 0) {
        return '<div class="alert alert-info">No results returned</div>';
    }
    
    // Handle different result types
    if (Array.isArray(result)) {
        // Format array of objects as a table
        return formatResultTable(result);
    } else if (typeof result === 'object') {
        // Format single object as a properties list
        return formatResultObject(result);
    } else {
        // Format other types as plain text
        return `<pre>${JSON.stringify(result, null, 2)}</pre>`;
    }
}

// Format an array of objects as an HTML table
function formatResultTable(resultArray) {
    if (resultArray.length === 0) {
        return '<div class="alert alert-info">Empty result set</div>';
    }
    
    // Get column headers from the first object
    const columns = Object.keys(resultArray[0]);
    
    let tableHtml = '<div class="table-responsive"><table class="table table-striped table-hover">';
    
    // Table header
    tableHtml += '<thead><tr>';
    columns.forEach(column => {
        tableHtml += `<th>${escapeHtml(column)}</th>`;
    });
    tableHtml += '</tr></thead>';
    
    // Table body
    tableHtml += '<tbody>';
    resultArray.forEach(row => {
        tableHtml += '<tr>';
        columns.forEach(column => {
            let cellValue = row[column];
            
            // Format cell value based on type
            if (cellValue === null || cellValue === undefined) {
                cellValue = '<em class="text-muted">null</em>';
            } else if (typeof cellValue === 'object') {
                cellValue = `<pre class="mb-0">${JSON.stringify(cellValue, null, 2)}</pre>`;
            } else {
                cellValue = escapeHtml(String(cellValue));
            }
            
            tableHtml += `<td>${cellValue}</td>`;
        });
        tableHtml += '</tr>';
    });
    tableHtml += '</tbody>';
    
    tableHtml += '</table></div>';
    return tableHtml;
}

// Format a single object as an HTML properties list
function formatResultObject(resultObj) {
    if (Object.keys(resultObj).length === 0) {
        return '<div class="alert alert-info">Empty result object</div>';
    }
    
    let html = '<div class="card"><div class="card-body"><dl class="row">';
    
    for (const [key, value] of Object.entries(resultObj)) {
        html += `<dt class="col-sm-3">${escapeHtml(key)}</dt>`;
        
        // Format value based on type
        let formattedValue;
        if (value === null || value === undefined) {
            formattedValue = '<em class="text-muted">null</em>';
        } else if (typeof value === 'object') {
            formattedValue = `<pre class="mb-0">${JSON.stringify(value, null, 2)}</pre>`;
        } else {
            formattedValue = escapeHtml(String(value));
        }
        
        html += `<dd class="col-sm-9">${formattedValue}</dd>`;
    }
    
    html += '</dl></div></div>';
    return html;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
