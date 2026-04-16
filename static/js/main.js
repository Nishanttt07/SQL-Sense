// main.js - Query Interface JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Initialize variables
    const queryForm = document.getElementById('queryForm');
    const generateBtn = document.getElementById('generateBtn');
    const executeBtn = document.getElementById('executeBtn');
    const editBtn = document.getElementById('editBtn');
    const copyBtn = document.getElementById('copyBtn');
    const examplesBtn = document.getElementById('examplesBtn');
    const userPrompt = document.getElementById('userPrompt');
    const generatedQuery = document.getElementById('generatedQuery');
    const resultsContainer = document.getElementById('resultsContainer');
    const emptyResults = document.getElementById('emptyResults');
    const resultsTable = document.getElementById('resultsTable');
    const resultsHeader = document.getElementById('resultsHeader');
    const resultsBody = document.getElementById('resultsBody');
    const resultsSummary = document.getElementById('resultsSummary');
    const errorAlert = document.getElementById('errorAlert');
    const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
    const examplesModal = new bootstrap.Modal(document.getElementById('examplesModal'));
    const toggleSchemaBtn = document.getElementById('toggleSchemaBtn');
    const schemaContainer = document.getElementById('schemaContainer');
    const refreshSchemaBtn = document.getElementById('refreshSchemaBtn');
    const copySchemaBtn = document.getElementById('copySchemaBtn');
    const schemaContent = document.getElementById('schemaContent');

    let queryHistory = [];
    let currentQuery = '';

    // Update UI based on database type
    function updateUIForDatabaseType() {
        const dbType = document.body.getAttribute('data-db-type') || 'mysql';
        
        if (dbType === 'firebase') {
            // Change labels and placeholders for Firebase
            if (userPrompt) {
                userPrompt.placeholder = 'e.g., Show me all active users, Get products with price over $100, Find orders from the last 7 days...';
            }
            if (generateBtn) {
                generateBtn.innerHTML = '<i class="fas fa-magic me-2"></i>Generate Python Code';
            }
            if (generatedQuery) {
                generatedQuery.placeholder = 'Your generated Python code for Firebase will appear here...';
            }
            if (executeBtn) {
                executeBtn.innerHTML = '<i class="fas fa-play me-1"></i>Run Code';
            }
        }
    }

    // Initialize UI
    updateUIForDatabaseType();

    // Auto-show schema on page load if there's content
    function checkAndShowSchema() {
        if (schemaContent) {
            const schemaText = schemaContent.textContent.trim();
            if (schemaText && schemaText !== 'No schema information available. Please refresh the schema.') {
                schemaContainer.style.display = 'block';
                toggleSchemaBtn.innerHTML = '<i class="fas fa-eye-slash me-1"></i>Hide Schema';
            }
        }
    }

    // Check schema on page load
    checkAndShowSchema();

    // Toggle schema visibility
    if (toggleSchemaBtn) {
        toggleSchemaBtn.addEventListener('click', function() {
            if (schemaContainer.style.display === 'none') {
                schemaContainer.style.display = 'block';
                toggleSchemaBtn.innerHTML = '<i class="fas fa-eye-slash me-1"></i>Hide Schema';
            } else {
                schemaContainer.style.display = 'none';
                toggleSchemaBtn.innerHTML = '<i class="fas fa-eye me-1"></i>Show Schema';
            }
        });
    }

    // Refresh schema
    if (refreshSchemaBtn) {
        refreshSchemaBtn.addEventListener('click', function() {
            refreshSchemaBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Refreshing...';
            refreshSchemaBtn.disabled = true;

            fetch('/api/get-schema')
                .then(response => response.json())
                .then(data => {
                    if (data.error) {
                        showAlert('Error refreshing schema: ' + data.error, 'danger');
                    } else {
                        schemaContent.textContent = data.schema;
                        showAlert('Schema refreshed successfully!', 'success');
                        checkAndShowSchema();
                    }
                })
                .catch(error => {
                    showAlert('Error refreshing schema: ' + error.message, 'danger');
                })
                .finally(() => {
                    refreshSchemaBtn.innerHTML = '<i class="fas fa-sync-alt me-1"></i>Refresh Schema';
                    refreshSchemaBtn.disabled = false;
                });
        });
    }

    // Copy schema to clipboard
    if (copySchemaBtn) {
        copySchemaBtn.addEventListener('click', function() {
            const schemaText = schemaContent.textContent;
            navigator.clipboard.writeText(schemaText).then(() => {
                const originalText = copySchemaBtn.innerHTML;
                copySchemaBtn.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
                setTimeout(() => {
                    copySchemaBtn.innerHTML = originalText;
                }, 2000);
            }).catch(err => {
                showAlert('Failed to copy schema: ' + err, 'danger');
            });
        });
    }

    // Make generated query textarea editable when edit button is clicked
    if (editBtn) {
        editBtn.addEventListener('click', function() {
            const isReadOnly = generatedQuery.readOnly;
            generatedQuery.readOnly = !isReadOnly;
            this.innerHTML = isReadOnly ? 
                '<i class="fas fa-check me-1"></i>Save' : 
                '<i class="fas fa-edit me-1"></i>Edit';
            
            if (!isReadOnly) {
                generatedQuery.focus();
            }
        });
    }

    // Copy query to clipboard
    if (copyBtn) {
        copyBtn.addEventListener('click', function() {
            const queryText = generatedQuery.value;
            if (!queryText) {
                showAlert('No query to copy', 'warning');
                return;
            }

            navigator.clipboard.writeText(queryText).then(() => {
                const originalText = copyBtn.innerHTML;
                copyBtn.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
                setTimeout(() => {
                    copyBtn.innerHTML = originalText;
                }, 2000);
            }).catch(err => {
                showAlert('Failed to copy query: ' + err, 'danger');
            });
        });
    }

    // Show examples modal
    if (examplesBtn) {
        examplesBtn.addEventListener('click', function() {
            examplesModal.show();
        });
    }

    // Example query click handler
    document.querySelectorAll('.example-query').forEach(item => {
        item.addEventListener('click', function() {
            userPrompt.value = this.textContent.trim();
            examplesModal.hide();
        });
    });

    // Generate query form submission
    if (queryForm) {
        queryForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const promptText = userPrompt.value.trim();
            if (!promptText) {
                showAlert('Please enter a query description', 'warning');
                return;
            }

            // Show loading modal
            const loadingMessage = document.getElementById('loadingMessage');
            const dbType = document.body.getAttribute('data-db-type') || 'mysql';
            loadingMessage.textContent = dbType === 'firebase' ? 
                'Generating Python code...' : 'Generating SQL query...';
            loadingModal.show();

            // Disable generate button
            generateBtn.disabled = true;
            generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';

            fetch('/api/generate-query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    prompt: promptText
                })
            })
            .then(response => response.json())
            .then(data => {
                loadingModal.hide();
                
                if (data.error) {
                    showAlert('Error generating query: ' + data.error, 'danger');
                } else {
                    generatedQuery.value = data.query;
                    currentQuery = data.query;
                    
                    // Enable execute and action buttons
                    executeBtn.disabled = false;
                    editBtn.disabled = false;
                    copyBtn.disabled = false;
                    
                    // Add to history
                    addToQueryHistory(promptText, data.query);
                    
                    showAlert('Query generated successfully!', 'success');
                }
            })
            .catch(error => {
                loadingModal.hide();
                showAlert('Error generating query: ' + error.message, 'danger');
            })
            .finally(() => {
                generateBtn.disabled = false;
                generateBtn.innerHTML = dbType === 'firebase' ? 
                    '<i class="fas fa-magic me-2"></i>Generate Python Code' : 
                    '<i class="fas fa-magic me-2"></i>Generate SQL Query';
            });
        });
    }

    // Execute query
    if (executeBtn) {
        executeBtn.addEventListener('click', function() {
            const query = generatedQuery.value.trim();
            if (!query) {
                showAlert('No query to execute', 'warning');
                return;
            }

            // Show loading
            executeBtn.disabled = true;
            executeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Running...';

            fetch('/api/execute-query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    query: query
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    showError(data.error);
                } else {
                    displayResults(data);
                    showAlert('Query executed successfully!', 'success');
                }
            })
            .catch(error => {
                showError('Error executing query: ' + error.message);
            })
            .finally(() => {
                executeBtn.disabled = false;
                const dbType = document.body.getAttribute('data-db-type') || 'mysql';
                executeBtn.innerHTML = dbType === 'firebase' ? 
                    '<i class="fas fa-play me-1"></i>Run Code' : 
                    '<i class="fas fa-play me-1"></i>Run Query';
            });
        });
    }

    // Display query results
    function displayResults(data) {
        // Hide empty results message and error alert
        emptyResults.style.display = 'none';
        errorAlert.style.display = 'none';
        
        // Show results table
        resultsTable.style.display = 'block';

        if (data.data && Array.isArray(data.data)) {
            // Regular tabular data
            const columns = data.columns || (data.data.length > 0 ? Object.keys(data.data[0]) : []);
            
            // Build header
            resultsHeader.innerHTML = '';
            const headerRow = document.createElement('tr');
            columns.forEach(col => {
                const th = document.createElement('th');
                th.textContent = col;
                th.scope = 'col';
                headerRow.appendChild(th);
            });
            resultsHeader.appendChild(headerRow);

            // Build body
            resultsBody.innerHTML = '';
            data.data.forEach(row => {
                const tr = document.createElement('tr');
                columns.forEach(col => {
                    const td = document.createElement('td');
                    let value = row[col];
                    
                    // Format the value for display
                    if (value === null || value === undefined) {
                        value = 'NULL';
                    } else if (typeof value === 'object') {
                        value = JSON.stringify(value);
                    } else if (typeof value === 'boolean') {
                        value = value ? 'true' : 'false';
                    }
                    
                    td.textContent = value;
                    tr.appendChild(td);
                });
                resultsBody.appendChild(tr);
            });

            // Update summary
            const execTime = data.execution_time ? ` in ${data.execution_time}s` : '';
            resultsSummary.textContent = `Returned ${data.row_count || data.data.length} row(s)${execTime}`;

        } else if (data.result !== undefined) {
            // Single result (for Firebase operations)
            resultsHeader.innerHTML = '';
            resultsBody.innerHTML = '';
            
            const headerRow = document.createElement('tr');
            const th = document.createElement('th');
            th.textContent = 'Result';
            th.scope = 'col';
            headerRow.appendChild(th);
            resultsHeader.appendChild(headerRow);

            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.textContent = typeof data.result === 'object' ? 
                JSON.stringify(data.result, null, 2) : 
                String(data.result);
            tr.appendChild(td);
            resultsBody.appendChild(tr);

            resultsSummary.textContent = data.message || 'Operation completed';

        } else if (data.affected_rows !== undefined) {
            // Non-SELECT operation
            resultsHeader.innerHTML = '';
            resultsBody.innerHTML = '';
            
            const headerRow = document.createElement('tr');
            const th = document.createElement('th');
            th.textContent = 'Message';
            th.scope = 'col';
            headerRow.appendChild(th);
            resultsHeader.appendChild(headerRow);

            const tr = document.createElement('tr');
            const td = document.createElement('td');
            td.textContent = data.message || `Affected ${data.affected_rows} row(s)`;
            tr.appendChild(td);
            resultsBody.appendChild(tr);

            resultsSummary.textContent = 'Operation completed successfully';
        }
    }

    // Show error message
    function showError(message) {
        emptyResults.style.display = 'none';
        resultsTable.style.display = 'none';
        
        errorAlert.style.display = 'block';
        errorAlert.textContent = message;
    }

    // Add query to history
    function addToQueryHistory(prompt, query) {
        const historyItem = {
            prompt: prompt,
            query: query,
            timestamp: new Date().toLocaleString()
        };
        
        queryHistory.unshift(historyItem);
        
        // Keep only last 10 items
        if (queryHistory.length > 10) {
            queryHistory = queryHistory.slice(0, 10);
        }
        
        updateQueryHistoryDisplay();
    }

    // Update query history display
    function updateQueryHistoryDisplay() {
        const historyContainer = document.getElementById('queryHistory');
        if (!historyContainer) return;
        
        historyContainer.innerHTML = '';
        
        if (queryHistory.length === 0) {
            historyContainer.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="fas fa-history fa-2x mb-2"></i>
                    <p>No query history yet</p>
                </div>
            `;
            return;
        }
        
        queryHistory.forEach((item, index) => {
            const historyElement = document.createElement('div');
            historyElement.className = 'list-group-item';
            historyElement.innerHTML = `
                <div class="d-flex w-100 justify-content-between">
                    <h6 class="mb-1">${item.prompt}</h6>
                    <small>${item.timestamp}</small>
                </div>
                <p class="mb-1 font-monospace small text-muted">${item.query.substring(0, 100)}${item.query.length > 100 ? '...' : ''}</p>
                <div class="mt-2">
                    <button class="btn btn-sm btn-outline-primary use-query" data-index="${index}">
                        <i class="fas fa-redo me-1"></i>Use Again
                    </button>
                </div>
            `;
            historyContainer.appendChild(historyElement);
        });
        
        // Add event listeners for "Use Again" buttons
        document.querySelectorAll('.use-query').forEach(button => {
            button.addEventListener('click', function() {
                const index = parseInt(this.getAttribute('data-index'));
                const historyItem = queryHistory[index];
                
                userPrompt.value = historyItem.prompt;
                generatedQuery.value = historyItem.query;
                currentQuery = historyItem.query;
                
                // Enable execute and action buttons
                executeBtn.disabled = false;
                editBtn.disabled = false;
                copyBtn.disabled = false;
                
                showAlert('Query loaded from history', 'info');
            });
        });
    }

    // Helper function to show alerts
    function showAlert(message, type) {
        // Remove any existing custom alerts
        const existingAlerts = document.querySelectorAll('.custom-alert');
        existingAlerts.forEach(alert => alert.remove());

        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} custom-alert alert-dismissible fade show mt-3`;
        alertDiv.innerHTML = `
            <i class="fas fa-${getAlertIcon(type)} me-2"></i>
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        // Insert after the connection alert or at the top of the container
        const connectionAlert = document.getElementById('connectionAlert');
        if (connectionAlert) {
            connectionAlert.parentNode.insertBefore(alertDiv, connectionAlert.nextSibling);
        } else {
            document.querySelector('.container-fluid').insertBefore(alertDiv, document.querySelector('.container-fluid').firstChild);
        }

        // Auto remove after 5 seconds if not danger
        if (type !== 'danger') {
            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 5000);
        }
    }

    // Get appropriate icon for alert type
    function getAlertIcon(type) {
        switch (type) {
            case 'success': return 'check-circle';
            case 'danger': return 'exclamation-triangle';
            case 'warning': return 'exclamation-circle';
            case 'info': return 'info-circle';
            default: return 'info-circle';
        }
    }

    // Initialize query history display
    updateQueryHistoryDisplay();

    // Debug: Log initialization
    console.log('Query interface initialized');
});