/**
 * Data visualization utilities for query results
 */

/**
 * Check if data can be visualized as a chart
 * @param {Array} data - The data array to check
 * @returns {Object|null} - Visualization info or null if not visualizable
 */
function detectVisualizableData(data) {
    if (!Array.isArray(data) || data.length < 2) {
        return null;
    }

    const firstItem = data[0];
    const numericFieldCount = 0;
    const stringFieldCount = 0;
    const dateFieldCount = 0;
    const fields = Object.keys(firstItem);

    // Need at least two fields for most visualizations
    if (fields.length < 2) {
        return null;
    }

    // Analyze fields
    const fieldTypes = {};
    fields.forEach(field => {
        // Check first few items to determine likely field type
        const sample = data.slice(0, Math.min(5, data.length));
        let numericCount = 0;
        let dateCount = 0;
        let stringCount = 0;

        sample.forEach(item => {
            const val = item[field];
            if (val === null || val === undefined) {
                return;
            }

            if (typeof val === 'number') {
                numericCount++;
            } else if (!isNaN(Date.parse(val)) && /^\d{4}-\d{2}-\d{2}/.test(val)) {
                dateCount++;
            } else if (typeof val === 'string') {
                stringCount++;
            }
        });

        // Determine predominant type
        if (numericCount >= Math.max(dateCount, stringCount)) {
            fieldTypes[field] = 'numeric';
        } else if (dateCount >= Math.max(numericCount, stringCount)) {
            fieldTypes[field] = 'date';
        } else {
            fieldTypes[field] = 'string';
        }
    });

    // Count field types
    let numericFields = [];
    let stringFields = [];
    let dateFields = [];

    for (const [field, type] of Object.entries(fieldTypes)) {
        if (type === 'numeric') {
            numericFields.push(field);
        } else if (type === 'string') {
            stringFields.push(field);
        } else if (type === 'date') {
            dateFields.push(field);
        }
    }

    // Decide which visualizations are possible
    const visualizations = [];

    // Line chart needs date/string field + numeric field
    if ((dateFields.length > 0 || stringFields.length > 0) && numericFields.length > 0) {
        visualizations.push({
            type: 'line',
            name: 'Line Chart',
            icon: 'fa-chart-line',
            xFields: [...dateFields, ...stringFields],
            yFields: numericFields
        });
    }

    // Bar chart needs string field + numeric field
    if (stringFields.length > 0 && numericFields.length > 0) {
        visualizations.push({
            type: 'bar',
            name: 'Bar Chart',
            icon: 'fa-chart-bar',
            xFields: stringFields,
            yFields: numericFields
        });
    }

    // Pie chart needs string field + numeric field
    if (stringFields.length > 0 && numericFields.length > 0) {
        visualizations.push({
            type: 'pie',
            name: 'Pie Chart',
            icon: 'fa-chart-pie',
            categoryFields: stringFields,
            valueFields: numericFields
        });
    }

    // Scatter plot needs two numeric fields
    if (numericFields.length >= 2) {
        visualizations.push({
            type: 'scatter',
            name: 'Scatter Plot',
            icon: 'fa-braille',
            xFields: numericFields,
            yFields: numericFields
        });
    }

    if (visualizations.length === 0) {
        return null;
    }

    return {
        visualizations: visualizations,
        fieldTypes: fieldTypes
    };
}

/**
 * Create visualization buttons for the data
 * @param {Array} data - The data to visualize
 * @returns {HTMLElement} - Container with visualization buttons
 */
function createVisualizationButtons(data) {
    const vizInfo = detectVisualizableData(data);
    if (!vizInfo) {
        return null;
    }

    const buttonContainer = document.createElement('div');
    buttonContainer.className = 'btn-group btn-group-sm visualization-buttons';

    const vizDropdown = document.createElement('div');
    vizDropdown.className = 'dropdown';

    const toggleButton = document.createElement('button');
    toggleButton.className = 'btn btn-outline-primary dropdown-toggle';
    toggleButton.setAttribute('data-bs-toggle', 'dropdown');
    toggleButton.innerHTML = '<i class="fas fa-chart-bar me-1"></i> Visualize';

    const dropdownMenu = document.createElement('ul');
    dropdownMenu.className = 'dropdown-menu';

    vizInfo.visualizations.forEach(viz => {
        const menuItem = document.createElement('li');
        const link = document.createElement('a');
        link.className = 'dropdown-item';
        link.href = '#';
        link.innerHTML = `<i class="fas ${viz.icon} me-2"></i> ${viz.name}`;
        
        link.addEventListener('click', (event) => {
            event.preventDefault();
            
            // Find message element
            const messageElement = event.target.closest('.message');
            if (!messageElement) return;
            
            // Create visualization
            createVisualization(data, viz, viz.type, messageElement);
        });
        
        menuItem.appendChild(link);
        dropdownMenu.appendChild(menuItem);
    });

    vizDropdown.appendChild(toggleButton);
    vizDropdown.appendChild(dropdownMenu);
    buttonContainer.appendChild(vizDropdown);

    return buttonContainer;
}

/**
 * Create a visualization container
 * @param {Array} data - Data to visualize
 * @param {Object} vizInfo - Visualization information
 * @param {string} type - Type of visualization
 * @param {HTMLElement} messageElement - The message element to append to
 */
function createVisualization(data, vizInfo, type, messageElement) {
    // Remove any existing visualizations
    const existingViz = messageElement.querySelector('.visualization-container');
    if (existingViz) {
        existingViz.remove();
    }
    
    // Create container
    const vizContainer = document.createElement('div');
    vizContainer.className = 'visualization-container card mt-3';
    
    // Create header with options
    const header = document.createElement('div');
    header.className = 'card-header d-flex justify-content-between align-items-center';
    
    const title = document.createElement('h6');
    title.className = 'mb-0';
    title.innerHTML = `<i class="fas ${vizInfo.icon} me-2"></i> ${vizInfo.name}`;
    
    const closeBtn = document.createElement('button');
    closeBtn.className = 'btn btn-sm btn-outline-secondary';
    closeBtn.innerHTML = '<i class="fas fa-times"></i>';
    closeBtn.addEventListener('click', () => vizContainer.remove());
    
    header.appendChild(title);
    header.appendChild(closeBtn);
    vizContainer.appendChild(header);
    
    // Create body for visualization
    const body = document.createElement('div');
    body.className = 'card-body';
    
    // Create canvas for chart
    const canvas = document.createElement('canvas');
    canvas.height = 300;
    body.appendChild(canvas);
    vizContainer.appendChild(body);
    
    // Add to message
    messageElement.querySelector('.message-content').appendChild(vizContainer);
    
    // Create configuration UI based on chart type
    const configUI = createConfigUI(type, vizInfo, data);
    if (configUI) {
        vizContainer.appendChild(configUI);
    }
    
    // Determine initial fields to use
    let xField, yField, categoryField;
    
    if (type === 'pie') {
        categoryField = vizInfo.categoryFields[0];
        yField = vizInfo.valueFields[0];
    } else {
        xField = type === 'scatter' ? vizInfo.xFields[0] : 
                (vizInfo.xFields.includes('date') ? 'date' : vizInfo.xFields[0]);
        yField = vizInfo.yFields[0];
    }
    
    // Initialize chart
    createChart(canvas, data, type, xField, yField, categoryField);
}

/**
 * Create configuration UI for the chart
 * @param {string} type - Chart type
 * @param {Object} vizInfo - Visualization information
 * @param {Array} data - The data to visualize
 * @returns {HTMLElement} - Configuration UI element
 */
function createConfigUI(type, vizInfo, data) {
    const container = document.createElement('div');
    container.className = 'card-footer bg-light';
    
    const form = document.createElement('form');
    form.className = 'row g-2';
    
    if (type === 'pie') {
        // Category field selector
        const categoryGroup = document.createElement('div');
        categoryGroup.className = 'col-md-6';
        
        const categoryLabel = document.createElement('label');
        categoryLabel.className = 'form-label small';
        categoryLabel.textContent = 'Category Field';
        
        const categorySelect = document.createElement('select');
        categorySelect.className = 'form-select form-select-sm';
        categorySelect.id = 'chart-category-field';
        
        vizInfo.categoryFields.forEach(field => {
            const option = document.createElement('option');
            option.value = field;
            option.textContent = field;
            categorySelect.appendChild(option);
        });
        
        categoryGroup.appendChild(categoryLabel);
        categoryGroup.appendChild(categorySelect);
        form.appendChild(categoryGroup);
        
        // Value field selector
        const valueGroup = document.createElement('div');
        valueGroup.className = 'col-md-6';
        
        const valueLabel = document.createElement('label');
        valueLabel.className = 'form-label small';
        valueLabel.textContent = 'Value Field';
        
        const valueSelect = document.createElement('select');
        valueSelect.className = 'form-select form-select-sm';
        valueSelect.id = 'chart-value-field';
        
        vizInfo.valueFields.forEach(field => {
            const option = document.createElement('option');
            option.value = field;
            option.textContent = field;
            valueSelect.appendChild(option);
        });
        
        valueGroup.appendChild(valueLabel);
        valueGroup.appendChild(valueSelect);
        form.appendChild(valueGroup);
        
        // Update chart when selections change
        categorySelect.addEventListener('change', () => {
            const canvas = categorySelect.closest('.visualization-container').querySelector('canvas');
            createChart(canvas, data, type, null, valueSelect.value, categorySelect.value);
        });
        
        valueSelect.addEventListener('change', () => {
            const canvas = valueSelect.closest('.visualization-container').querySelector('canvas');
            createChart(canvas, data, type, null, valueSelect.value, categorySelect.value);
        });
    } else {
        // X-axis field selector
        const xGroup = document.createElement('div');
        xGroup.className = 'col-md-6';
        
        const xLabel = document.createElement('label');
        xLabel.className = 'form-label small';
        xLabel.textContent = 'X-Axis Field';
        
        const xSelect = document.createElement('select');
        xSelect.className = 'form-select form-select-sm';
        xSelect.id = 'chart-x-field';
        
        vizInfo.xFields.forEach(field => {
            const option = document.createElement('option');
            option.value = field;
            option.textContent = field;
            xSelect.appendChild(option);
        });
        
        xGroup.appendChild(xLabel);
        xGroup.appendChild(xSelect);
        form.appendChild(xGroup);
        
        // Y-axis field selector
        const yGroup = document.createElement('div');
        yGroup.className = 'col-md-6';
        
        const yLabel = document.createElement('label');
        yLabel.className = 'form-label small';
        yLabel.textContent = 'Y-Axis Field';
        
        const ySelect = document.createElement('select');
        ySelect.className = 'form-select form-select-sm';
        ySelect.id = 'chart-y-field';
        
        vizInfo.yFields.forEach(field => {
            const option = document.createElement('option');
            option.value = field;
            option.textContent = field;
            ySelect.appendChild(option);
        });
        
        yGroup.appendChild(yLabel);
        yGroup.appendChild(ySelect);
        form.appendChild(yGroup);
        
        // Update chart when selections change
        xSelect.addEventListener('change', () => {
            const canvas = xSelect.closest('.visualization-container').querySelector('canvas');
            createChart(canvas, data, type, xSelect.value, ySelect.value);
        });
        
        ySelect.addEventListener('change', () => {
            const canvas = ySelect.closest('.visualization-container').querySelector('canvas');
            createChart(canvas, data, type, xSelect.value, ySelect.value);
        });
    }
    
    container.appendChild(form);
    return container;
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
    // Destroy existing chart if any
    if (canvas.chart) {
        canvas.chart.destroy();
    }
    
    let chartData;
    let options;
    const colors = generateColors(data.length);
    
    if (type === 'pie') {
        // Prepare data for pie chart
        const categories = data.map(item => item[categoryField]);
        const values = data.map(item => item[yField]);
        
        chartData = {
            labels: categories,
            datasets: [{
                data: values,
                backgroundColor: colors,
                hoverOffset: 4
            }]
        };
        
        options = {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right'
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.raw || 0;
                            return `${label}: ${value}`;
                        }
                    }
                }
            }
        };
    } else if (type === 'scatter') {
        // Prepare data for scatter plot
        chartData = {
            datasets: [{
                label: `${xField} vs ${yField}`,
                data: data.map(item => ({
                    x: item[xField],
                    y: item[yField]
                })),
                backgroundColor: colors[0],
                pointRadius: 5,
                pointHoverRadius: 7
            }]
        };
        
        options = {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: xField
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: yField
                    }
                }
            }
        };
    } else {
        // Prepare data for line/bar charts
        const labels = data.map(item => item[xField]);
        
        chartData = {
            labels: labels,
            datasets: [{
                label: yField,
                data: data.map(item => item[yField]),
                backgroundColor: type === 'bar' ? colors : colors[0],
                borderColor: type === 'line' ? colors[0] : undefined,
                tension: 0.1,
                fill: false
            }]
        };
        
        options = {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: xField
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: yField
                    }
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
        'rgba(0, 123, 255, 0.7)',    // Blue
        'rgba(220, 53, 69, 0.7)',    // Red
        'rgba(40, 167, 69, 0.7)',    // Green
        'rgba(255, 193, 7, 0.7)',    // Yellow
        'rgba(111, 66, 193, 0.7)',   // Purple
        'rgba(23, 162, 184, 0.7)',   // Cyan
        'rgba(255, 127, 80, 0.7)',   // Coral
        'rgba(0, 191, 165, 0.7)',    // Teal
        'rgba(255, 159, 64, 0.7)',   // Orange
        'rgba(153, 102, 255, 0.7)'   // Indigo
    ];
    
    // If we need more colors than available, generate them randomly
    if (count > colors.length) {
        for (let i = colors.length; i < count; i++) {
            const r = Math.floor(Math.random() * 200);
            const g = Math.floor(Math.random() * 200);
            const b = Math.floor(Math.random() * 200);
            colors.push(`rgba(${r}, ${g}, ${b}, 0.7)`);
        }
    }
    
    return colors.slice(0, count);
}