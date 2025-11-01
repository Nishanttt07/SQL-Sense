// SQL-Sense Main JavaScript
class SQLSenseApp {
    constructor() {
        this.currentQuery = '';
        this.queryHistory = [];
        this.isEditing = false;
        this.init();
    }

    init() {
        this.bindEvents();
        this.loadHistory();
        this.updateUI();
    }

    bindEvents() {
        // Query generation form
        const queryForm = document.getElementById('queryForm');
        if (queryForm) {
            queryForm.addEventListener('submit', (e) => this.handleQueryGeneration(e));
        }

        // Execute query button
        const executeBtn = document.getElementById('executeBtn');
        if (executeBtn) {
            executeBtn.addEventListener('click', () => this.executeQuery());
        }

        // Edit query button
        const editBtn = document.getElementById('editBtn');
        if (editBtn) {
            editBtn.addEventListener('click', () => this.toggleEditMode());
        }

        // Copy query button
        const copyBtn = document.getElementById('copyBtn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => this.copyQuery());
        }

        // Examples button
        const examplesBtn = document.getElementById('examplesBtn');
        if (examplesBtn) {
            examplesBtn.addEventListener('click', () => this.showExamples());
        }

        // Example query clicks
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('example-query')) {
                this.useExampleQuery(e.target.textContent.trim());
            }
        });

        // Generated query textarea changes
        const generatedQuery = document.getElementById('generatedQuery');
        if (generatedQuery) {
            generatedQuery.addEventListener('input', () => {
                this.currentQuery = generatedQuery.value;
                this.updateExecuteButton();
            });
        }
    }

    async handleQueryGeneration(e) {
        e.preventDefault();
        
        const prompt = document.getElementById('userPrompt').value.trim();
        if (!prompt) return;

        this.showLoading('Generating query...');

        try {
            const response = await fetch('/api/generate-query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ prompt })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Failed to generate query');
            }

            if (data.error) {
                throw new Error(data.error);
            }

            this.currentQuery = data.query;
            this.displayGeneratedQuery(data.query);
            this.addToHistory(prompt, data.query);
            
        } catch (error) {
            this.showError('Failed to generate query: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    async executeQuery() {
        if (!this.currentQuery.trim()) return;

        this.showLoading('Executing query...');

        try {
            const response = await fetch('/api/execute-query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query: this.currentQuery })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || `Server error: ${response.status}`);
            }

            if (data.error) {
                throw new Error(data.error);
            }

            this.displayResults(data);

        } catch (error) {
            console.error('Query execution error:', error);
            this.showError('Failed to execute query: ' + error.message);
        } finally {
            this.hideLoading();
        }
    }

    displayGeneratedQuery(query) {
        const textarea = document.getElementById('generatedQuery');
        textarea.value = query;
        textarea.readOnly = true;
        
        this.updateExecuteButton();
        this.updateEditButton();
        this.updateCopyButton();
        
        // Scroll to generated query
        textarea.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    displayResults(result) {
        const emptyResults = document.getElementById('emptyResults');
        const resultsTable = document.getElementById('resultsTable');
        const resultsHeader = document.getElementById('resultsHeader');
        const resultsBody = document.getElementById('resultsBody');
        const resultsSummary = document.getElementById('resultsSummary');
        const errorAlert = document.getElementById('errorAlert');

        // Hide error and empty state
        errorAlert.style.display = 'none';
        emptyResults.style.display = 'none';
        resultsTable.style.display = 'none';

        // Clear previous results
        resultsHeader.innerHTML = '';
        resultsBody.innerHTML = '';
        resultsSummary.textContent = '';

        // Check if result has error
        if (result && result.error) {
            this.showError(result.error);
            return;
        }

        // Check if we have data array
        if (result && result.data && Array.isArray(result.data)) {
            const dataArray = result.data;
            
            if (dataArray.length > 0) {
                // Get column names from first object
                const firstRow = dataArray[0];
                const headers = Object.keys(firstRow);
                
                // Create table header
                resultsHeader.innerHTML = '<tr>' + headers.map(header => 
                    `<th>${this.formatHeader(header)}</th>`
                ).join('') + '</tr>';

                // Create table body
                resultsBody.innerHTML = dataArray.map(row => 
                    '<tr>' + headers.map(header => 
                        `<td>${this.formatCellValue(row[header])}</td>`
                    ).join('') + '</tr>'
                ).join('');

                // Update summary
                resultsSummary.textContent = `Showing ${dataArray.length} row(s)`;

                // Show table
                resultsTable.style.display = 'block';
            } else {
                emptyResults.style.display = 'block';
                emptyResults.innerHTML = `
                    <i class="fas fa-info-circle fa-3x mb-3 text-muted"></i>
                    <p>Query executed successfully but returned no results.</p>
                `;
            }
        } else {
            // Handle unexpected response format
            console.warn('Unexpected response format:', result);
            this.showError('Unexpected response format from server');
        }
    }

    formatHeader(header) {
        return header.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    }

    formatCellValue(value) {
        if (value === null || value === undefined) return '<em>null</em>';
        if (typeof value === 'boolean') return value ? '✓' : '✗';
        if (typeof value === 'object') return JSON.stringify(value);
        return value.toString();
    }

    toggleEditMode() {
        const textarea = document.getElementById('generatedQuery');
        const editBtn = document.getElementById('editBtn');
        
        this.isEditing = !this.isEditing;
        textarea.readOnly = !this.isEditing;
        
        if (this.isEditing) {
            editBtn.innerHTML = '<i class="fas fa-check me-1"></i>Save';
            editBtn.classList.remove('btn-outline-secondary');
            editBtn.classList.add('btn-success');
            textarea.focus();
        } else {
            editBtn.innerHTML = '<i class="fas fa-edit me-1"></i>Edit Query';
            editBtn.classList.remove('btn-success');
            editBtn.classList.add('btn-outline-secondary');
            this.currentQuery = textarea.value;
        }
        
        this.updateExecuteButton();
    }

    copyQuery() {
        const textarea = document.getElementById('generatedQuery');
        textarea.select();
        document.execCommand('copy');
        
        // Show temporary feedback
        const originalText = document.getElementById('copyBtn').innerHTML;
        document.getElementById('copyBtn').innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
        setTimeout(() => {
            document.getElementById('copyBtn').innerHTML = originalText;
        }, 2000);
    }

    showExamples() {
        const modal = new bootstrap.Modal(document.getElementById('examplesModal'));
        modal.show();
    }

    useExampleQuery(example) {
        document.getElementById('userPrompt').value = example;
        const modal = bootstrap.Modal.getInstance(document.getElementById('examplesModal'));
        modal.hide();
    }

    addToHistory(prompt, query) {
        const historyItem = {
            prompt,
            query,
            timestamp: new Date().toLocaleString()
        };
        
        this.queryHistory.unshift(historyItem);
        if (this.queryHistory.length > 10) {
            this.queryHistory = this.queryHistory.slice(0, 10);
        }
        
        this.saveHistory();
        this.renderHistory();
    }

    renderHistory() {
        const historyContainer = document.getElementById('queryHistory');
        
        if (this.queryHistory.length === 0) {
            historyContainer.innerHTML = `
                <div class="text-center text-muted py-3">
                    <i class="fas fa-history fa-2x mb-2"></i>
                    <p>No query history yet</p>
                </div>
            `;
            return;
        }

        historyContainer.innerHTML = this.queryHistory.map((item, index) => `
            <div class="list-group-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div class="flex-grow-1">
                        <div class="query-prompt">${item.prompt}</div>
                        <div class="query-sql">${item.query}</div>
                        <small class="text-muted">${item.timestamp}</small>
                    </div>
                    <button class="btn btn-sm btn-outline-primary ms-2" onclick="app.useHistoryItem(${index})">
                        <i class="fas fa-redo"></i>
                    </button>
                </div>
            </div>
        `).join('');
    }

    useHistoryItem(index) {
        const item = this.queryHistory[index];
        document.getElementById('userPrompt').value = item.prompt;
        this.displayGeneratedQuery(item.query);
    }

    saveHistory() {
        localStorage.setItem('sqlSenseHistory', JSON.stringify(this.queryHistory));
    }

    loadHistory() {
        const saved = localStorage.getItem('sqlSenseHistory');
        if (saved) {
            this.queryHistory = JSON.parse(saved);
            this.renderHistory();
        }
    }

    updateExecuteButton() {
        const executeBtn = document.getElementById('executeBtn');
        executeBtn.disabled = !this.currentQuery.trim();
    }

    updateEditButton() {
        const editBtn = document.getElementById('editBtn');
        editBtn.disabled = !this.currentQuery.trim();
    }

    updateCopyButton() {
        const copyBtn = document.getElementById('copyBtn');
        copyBtn.disabled = !this.currentQuery.trim();
    }

    updateUI() {
        this.updateExecuteButton();
        this.updateEditButton();
        this.updateCopyButton();
    }

    showLoading(message = 'Loading...') {
        document.getElementById('loadingMessage').textContent = message;
        const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
        modal.show();
    }

    hideLoading() {
        const modal = bootstrap.Modal.getInstance(document.getElementById('loadingModal'));
        if (modal) {
            modal.hide();
        }
    }

    showError(message) {
        const errorAlert = document.getElementById('errorAlert');
        errorAlert.textContent = message;
        errorAlert.style.display = 'block';
        
        // Hide other result displays
        document.getElementById('emptyResults').style.display = 'none';
        document.getElementById('resultsTable').style.display = 'none';
        
        // Scroll to error
        errorAlert.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// Initialize the app when DOM is loaded
let app;
document.addEventListener('DOMContentLoaded', function() {
    app = new SQLSenseApp();
});