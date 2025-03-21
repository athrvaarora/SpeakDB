// visualizations.js - Data visualization functionality for SpeakDB

/**
 * Detect if data is suitable for visualization
 * @param {Array} data - The data to check
 * @returns {Object} - Object containing visualization type and fields
 */
function detectVisualizableData(data) {
    // If not an array or empty, not visualizable
    if (!Array.isArray(data) || data.length === 0) {
        return { visualizable: false };
    }
    
    // Get keys from the first item
    const keys = Object.keys(data[0]);
    
    // Need at least 2 fields for most visualizations
    if (keys.length < 2) {
        return { visualizable: false };
    }
    
    // Check if we have numeric fields (for charts)
    const numericFields = [];
    const dateFields = [];
    const textFields = [];
    
    // Sample the first item for field types
    const sampleItem = data[0];
    
    keys.forEach(key => {
        const value = sampleItem[key];
        
        // Check if date field (common formats)
        if (
            (typeof value === 'string' && 
             (
                 /^\d{4}-\d{2}-\d{2}.*/.test(value) || // ISO date format
                 /^\d{2}\/\d{2}\/\d{4}.*/.test(value)   // MM/DD/YYYY format
             )
            ) || 
            value instanceof Date
        ) {
            dateFields.push(key);
        }
        // Check if numeric field
        else if (typeof value === 'number') {
            numericFields.push(key);
        }
        // Text fields
        else if (typeof value === 'string') {
            textFields.push(key);
        }
    });
    
    // Determine visualization types based on field types
    let visualizationTypes = [];
    
    // Line chart - needs date field and at least one numeric field
    if (dateFields.length > 0 && numericFields.length > 0) {
        visualizationTypes.push('line');
    }
    
    // Bar chart - needs categorical field and numeric field
    if ((textFields.length > 0 || dateFields.length > 0) && numericFields.length > 0) {
        visualizationTypes.push('bar');
    }
    
    // Pie chart - needs one categorical field and one numeric field
    if (textFields.length > 0 && numericFields.length > 0) {
        visualizationTypes.push('pie');
    }
    
    // Scatter plot - needs at least two numeric fields
    if (numericFields.length >= 2) {
        visualizationTypes.push('scatter');
    }
    
    return {
        visualizable: visualizationTypes.length > 0,
        types: visualizationTypes,
        numericFields: numericFields,
        dateFields: dateFields,
        textFields: textFields,
        allFields: keys
    };
}

/**
 * Create visualization buttons for the data
 * @param {Array} data - The data to visualize
 * @returns {HTMLElement} - Container with visualization buttons
 */
function createVisualizationButtons(data) {
    const vizInfo = detectVisualizableData(data);
    if (!vizInfo.visualizable) {
        return null;
    }
    
    const container = document.createElement('div');
    container.className = 'viz-buttons mt-2';
    
    // Add visualization type buttons
    const buttonGroup = document.createElement('div');
    buttonGroup.className = 'btn-group btn-group-sm me-2';
    buttonGroup.setAttribute('role', 'group');
    buttonGroup.setAttribute('aria-label', 'Visualization types');
    
    const label = document.createElement('div');
    label.className = 'viz-label me-2';
    label.innerHTML = '<i class="fas fa-chart-line me-1"></i> Visualize:';
    container.appendChild(label);
    
    // Add buttons for each visualization type
    vizInfo.types.forEach(type => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = 'btn btn-outline-primary btn-sm';
        button.dataset.vizType = type;
        
        let icon = '';
        switch (type) {
            case 'line':
                icon = '<i class="fas fa-chart-line"></i>';
                break;
            case 'bar':
                icon = '<i class="fas fa-chart-bar"></i>';
                break;
            case 'pie':
                icon = '<i class="fas fa-chart-pie"></i>';
                break;
            case 'scatter':
                icon = '<i class="fas fa-braille"></i>';
                break;
            default:
                icon = '<i class="fas fa-chart-simple"></i>';
        }
        
        button.innerHTML = `${icon} <span class="ms-1">${type.charAt(0).toUpperCase() + type.slice(1)}</span>`;
        
        // Store visualization info in the button
        button.dataset.vizInfo = JSON.stringify(vizInfo);
        button.dataset.jsonData = JSON.stringify(data);
        
        // Add click handler
        button.addEventListener('click', function() {
            const vizInfo = JSON.parse(this.dataset.vizInfo);
            const data = JSON.parse(this.dataset.jsonData);
            createVisualization(data, vizInfo, type, this.closest('.message'));
        });
        
        buttonGroup.appendChild(button);
    });
    
    container.appendChild(buttonGroup);
    return container;
}

/**
 * Create a visualization container
 * @param {Array} data - Data to visualize
 * @param {Object} vizInfo - Visualization information
 * @param {string} type - Type of visualization
 * @param {HTMLElement} messageElement - The message element to append to
 */
function createVisualization(data, vizInfo, type, messageElement) {
    // Remove any existing visualization
    const existingViz = messageElement.querySelector('.visualization-container');
    if (existingViz) {
        existingViz.remove();
    }
    
    // Create container for the visualization
    const vizContainer = document.createElement('div');
    vizContainer.className = 'visualization-container mt-3 p-3 border rounded bg-white';
    
    // Add a header with controls
    const header = document.createElement('div');
    header.className = 'd-flex justify-content-between align-items-center mb-3';
    
    const title = document.createElement('h6');
    title.className = 'mb-0';
    title.innerHTML = `<i class="fas fa-chart-${type === 'scatter' ? 'line' : type}"></i> ${type.charAt(0).toUpperCase() + type.slice(1)} Chart`;
    header.appendChild(title);
    
    // Add configuration options
    const configContainer = document.createElement('div');
    configContainer.className = 'd-flex align-items-center';
    
    // Field selection for X axis
    if (type !== 'pie') {
        const xAxisLabel = document.createElement('span');
        xAxisLabel.className = 'me-1 small';
        xAxisLabel.textContent = 'X:';
        configContainer.appendChild(xAxisLabel);
        
        const xAxisSelect = document.createElement('select');
        xAxisSelect.className = 'form-select form-select-sm me-2';
        xAxisSelect.dataset.axis = 'x';
        xAxisSelect.style.width = 'auto';
        
        const xAxisFields = type === 'line' ? vizInfo.dateFields : 
                           type === 'bar' ? [...vizInfo.textFields, ...vizInfo.dateFields] : 
                           vizInfo.numericFields;
        
        xAxisFields.forEach(field => {
            const option = document.createElement('option');
            option.value = field;
            option.textContent = field;
            xAxisSelect.appendChild(option);
        });
        
        configContainer.appendChild(xAxisSelect);
    }
    
    // Field selection for Y axis
    const yAxisLabel = document.createElement('span');
    yAxisLabel.className = 'me-1 small';
    yAxisLabel.textContent = type === 'pie' ? 'Value:' : 'Y:';
    configContainer.appendChild(yAxisLabel);
    
    const yAxisSelect = document.createElement('select');
    yAxisSelect.className = 'form-select form-select-sm me-2';
    yAxisSelect.dataset.axis = 'y';
    yAxisSelect.style.width = 'auto';
    
    vizInfo.numericFields.forEach(field => {
        const option = document.createElement('option');
        option.value = field;
        option.textContent = field;
        yAxisSelect.appendChild(option);
    });
    
    configContainer.appendChild(yAxisSelect);
    
    // Only show category selection for pie charts
    if (type === 'pie') {
        const categoryLabel = document.createElement('span');
        categoryLabel.className = 'me-1 small';
        categoryLabel.textContent = 'Category:';
        configContainer.appendChild(categoryLabel);
        
        const categorySelect = document.createElement('select');
        categorySelect.className = 'form-select form-select-sm me-2';
        categorySelect.dataset.axis = 'category';
        categorySelect.style.width = 'auto';
        
        vizInfo.textFields.forEach(field => {
            const option = document.createElement('option');
            option.value = field;
            option.textContent = field;
            categorySelect.appendChild(option);
        });
        
        configContainer.appendChild(categorySelect);
    }
    
    // Add refresh button
    const refreshBtn = document.createElement('button');
    refreshBtn.className = 'btn btn-sm btn-outline-secondary';
    refreshBtn.innerHTML = '<i class="fas fa-sync-alt"></i>';
    refreshBtn.title = 'Refresh chart';
    configContainer.appendChild(refreshBtn);
    
    // Add close button
    const closeBtn = document.createElement('button');
    closeBtn.className = 'btn btn-sm btn-outline-secondary ms-2';
    closeBtn.innerHTML = '<i class="fas fa-times"></i>';
    closeBtn.title = 'Close chart';
    closeBtn.addEventListener('click', function() {
        vizContainer.remove();
    });
    configContainer.appendChild(closeBtn);
    
    header.appendChild(configContainer);
    vizContainer.appendChild(header);
    
    // Create canvas for the chart
    const canvas = document.createElement('canvas');
    canvas.id = 'chart-' + Math.random().toString(36).substring(2, 15);
    canvas.style.width = '100%';
    canvas.style.height = '300px';
    vizContainer.appendChild(canvas);
    
    // Add to the message element
    messageElement.appendChild(vizContainer);
    
    // Create initial chart
    const xField = type !== 'pie' ? xAxisSelect.value : null;
    const yField = yAxisSelect.value;
    const categoryField = type === 'pie' ? categorySelect.value : null;
    
    createChart(canvas, data, type, xField, yField, categoryField);
    
    // Add event listeners for controls
    const updateChart = () => {
        const xField = type !== 'pie' ? xAxisSelect.value : null;
        const yField = yAxisSelect.value;
        const categoryField = type === 'pie' ? categorySelect.value : null;
        createChart(canvas, data, type, xField, yField, categoryField);
    };
    
    refreshBtn.addEventListener('click', updateChart);
    
    if (xAxisSelect) {
        xAxisSelect.addEventListener('change', updateChart);
    }
    
    yAxisSelect.addEventListener('change', updateChart);
    
    if (type === 'pie' && categorySelect) {
        categorySelect.addEventListener('change', updateChart);
    }
}

/**
 * Create a chart with Chart.js
 * @param {HTMLCanvasElement} canvas - The canvas element
 * @param {Array} data - The data to visualize
 * @param {string} type - The type of chart
 * @param {string} xField - Field to use for X axis
 * @param {string} yField - Field to use for Y axis
 * @param {string} categoryField - Field to use for categories (pie chart)
 */
function createChart(canvas, data, type, xField, yField, categoryField) {
    // Check if we already have a chart instance
    if (canvas.chart) {
        canvas.chart.destroy();
    }
    
    let chartData;
    let options;
    
    if (type === 'pie') {
        // Group data by category
        const groupedData = {};
        data.forEach(item => {
            const category = String(item[categoryField]);
            if (!groupedData[category]) {
                groupedData[category] = 0;
            }
            groupedData[category] += Number(item[yField]) || 0;
        });
        
        // Prepare data for pie chart
        const labels = Object.keys(groupedData);
        const values = Object.values(groupedData);
        
        // Generate colors
        const colors = generateColors(labels.length);
        
        chartData = {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors
            }]
        };
        
        options = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw;
                            const total = context.chart.data.datasets[0].data.reduce((a, b) => a + b, 0);
                            const percentage = Math.round((value / total) * 100);
                            return `${label}: ${value} (${percentage}%)`;
                        }
                    }
                }
            }
        };
    } else {
        // For line, bar, and scatter charts
        let labels = [];
        let chartValues = [];
        
        if (type === 'line') {
            // Sort data by date field first
            data = [...data].sort((a, b) => {
                const dateA = new Date(a[xField]);
                const dateB = new Date(b[xField]);
                return dateA - dateB;
            });
        }
        
        // Extract data
        data.forEach(item => {
            const xValue = type === 'line' ? new Date(item[xField]) : item[xField];
            labels.push(xValue);
            chartValues.push(Number(item[yField]) || 0);
        });
        
        chartData = {
            labels: labels,
            datasets: [{
                label: yField,
                data: chartValues,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.5)',
                tension: type === 'line' ? 0.1 : 0,
                pointRadius: type === 'scatter' ? 5 : 3
            }]
        };
        
        options = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'top',
                },
                tooltip: {
                    callbacks: {
                        title: function(context) {
                            const value = context[0].label;
                            // Format dates for better readability
                            if (type === 'line') {
                                try {
                                    const date = new Date(value);
                                    return date.toLocaleDateString();
                                } catch(e) {
                                    return value;
                                }
                            }
                            return value;
                        }
                    }
                }
            },
            scales: {
                x: {
                    title: {
                        display: true,
                        text: xField
                    },
                    type: type === 'line' ? 'time' : 'category',
                    time: type === 'line' ? {
                        unit: 'day',
                        displayFormats: {
                            day: 'MMM d'
                        }
                    } : undefined
                },
                y: {
                    title: {
                        display: true,
                        text: yField
                    },
                    beginAtZero: true
                }
            }
        };
    }
    
    // Create chart
    canvas.chart = new Chart(canvas, {
        type: type,
        data: chartData,
        options: options
    });
}

/**
 * Generate colors for visualization
 * @param {number} count - Number of colors needed
 * @returns {Array} - Array of color strings
 */
function generateColors(count) {
    const colors = [
        'rgba(75, 192, 192, 0.7)',   // Teal
        'rgba(54, 162, 235, 0.7)',   // Blue
        'rgba(255, 99, 132, 0.7)',   // Pink
        'rgba(255, 159, 64, 0.7)',   // Orange
        'rgba(153, 102, 255, 0.7)',  // Purple
        'rgba(255, 205, 86, 0.7)',   // Yellow
        'rgba(201, 203, 207, 0.7)',  // Grey
        'rgba(100, 255, 100, 0.7)',  // Green
        'rgba(255, 100, 255, 0.7)',  // Magenta
        'rgba(100, 255, 255, 0.7)'   // Cyan
    ];
    
    // If we need more colors than available, generate them
    if (count > colors.length) {
        for (let i = colors.length; i < count; i++) {
            const r = Math.floor(Math.random() * 255);
            const g = Math.floor(Math.random() * 255);
            const b = Math.floor(Math.random() * 255);
            colors.push(`rgba(${r}, ${g}, ${b}, 0.7)`);
        }
    }
    
    return colors.slice(0, count);
}