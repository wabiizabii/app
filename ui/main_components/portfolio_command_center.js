// ==============================================================================
// FILE: portfolio_command_center.js (VERSION: FLEET_COMMAND_CRUD - COMPLETE)
// ==============================================================================

const PortfolioCommandCenter = {
    _socket: null,
    _selectors: {},
    _isConnected: false,
    _portfolios: [],
    _selectedPortfolio: null, // NEW: State to hold the portfolio being edited
    _stagedData: null,

    init: function() {
        console.log("Portfolio Command Center Initializing...");
        const template = document.getElementById('portfolio-command-center-template');
        if (!template) {
            console.error("PCC FATAL: Template not found.");
            return;
        }
        document.body.appendChild(template.content.cloneNode(true));

        this._selectors = {
            launchBtn: document.getElementById('launch-portfolio-command-btn'),
            modalOverlay: document.getElementById('pcc-modal-overlay'),
            closeBtn: document.getElementById('pcc-close-btn'),
            tabContainer: document.querySelector('.pcc-tabs'),
            paneContainer: document.querySelector('.pcc-content'),
            managePane: document.getElementById('pcc-manage-pane'),
            uploadPane: document.getElementById('pcc-upload-pane')
        };
        
        this._attachEventListeners();
        this._connectToServer();
    },

    _attachEventListeners: function() {
        this._selectors.launchBtn?.addEventListener('click', () => {
            this._selectors.modalOverlay?.classList.remove('hidden');
            // Data is requested on connection, so it should be ready
        });
        
        this._selectors.closeBtn?.addEventListener('click', () => {
            this._selectors.modalOverlay?.classList.add('hidden');
            this._selectedPortfolio = null;
        });
        
        this._selectors.modalOverlay?.addEventListener('click', (e) => {
            if (e.target === this._selectors.modalOverlay) {
                this._selectors.modalOverlay.classList.add('hidden');
                this._selectedPortfolio = null;
            }
        });

        this._selectors.tabContainer?.addEventListener('click', (e) => {
            if (!e.target.matches('.pcc-tab-btn')) return;
            const targetPaneId = e.target.dataset.target;
            this._selectors.tabContainer.querySelectorAll('.pcc-tab-btn').forEach(btn => btn.classList.remove('active'));
            e.target.classList.add('active');
            this._selectors.paneContainer.querySelectorAll('.pcc-content-pane').forEach(pane => {
                pane.classList.toggle('active', pane.id === targetPaneId);
            });
        });
        
        // --- Event Delegation for the entire Manage Pane ---
        this._selectors.managePane?.addEventListener('click', (e) => {
            const rosterItem = e.target.closest('.portfolio-list-item');
            const createNewBtn = e.target.closest('#pcc-create-new-btn');
            const deleteBtn = e.target.closest('#pcc-delete-btn');

            if (rosterItem) {
                const portfolioId = rosterItem.dataset.id;
                const portfolio = this._portfolios.find(p => p.PortfolioID === portfolioId);
                this._selectedPortfolio = portfolio;
                this._renderManagePane();
            } else if (createNewBtn) {
                this._selectedPortfolio = null;
                this._renderManagePane();
            } else if (deleteBtn) {
                this._handleDeletePortfolio();
            }
        });

        this._selectors.managePane?.addEventListener('submit', (e) => {
            e.preventDefault();
            this._handleFormSubmit(e.target);
        });

        // --- Upload Pane Listeners ---
        this._selectors.uploadPane?.addEventListener('click', (e) => {
            if (e.target.id === 'pcc-upload-confirm-btn') {
                this._handleSaveConfirmation();
            }
        });

        this._selectors.uploadPane?.addEventListener('change', (e) => {
            if (e.target.id === 'pcc-file-uploader') {
                const file = e.target.files[0];
                if (file) {
                    this._handleFileUpload(file);
                }
            }
        });
    },

    _handleDeletePortfolio: function() {
        if (!this._selectedPortfolio) return;
        if (confirm(`Are you sure you want to delete "${this._selectedPortfolio.PortfolioName}"? This cannot be undone.`)) {
            this._sendMessage("DELETE_PORTFOLIO", { portfolio_id: this._selectedPortfolio.PortfolioID });
        }
    },

    // --- [MAJOR UPGRADE] ---
    _handleFormSubmit: function(form) {
        const formData = {
            PortfolioName: form.querySelector(`[name="PortfolioName"]`)?.value,
            InitialBalance: parseFloat(form.querySelector(`[name="InitialBalance"]`)?.value) || 0,
            mt5_account_id: form.querySelector(`[name="mt5_account_id"]`)?.value || null,
            BrokerName: form.querySelector(`[name="BrokerName"]`)?.value || 'Unknown', // <--- [FIX] เพิ่ม BrokerName
            ProgramType: form.querySelector(`[name="ProgramType"]`)?.value,
            EvaluationStep: form.querySelector(`[name="EvaluationStep"]`)?.value,
            Status: form.querySelector(`[name="Status"]`)?.value,
            Leverage: parseInt(form.querySelector(`[name="Leverage"]`)?.value) || 100,
            ProfitTargetPercent: parseFloat(form.querySelector(`[name="ProfitTargetPercent"]`)?.value) || 0,
            DailyLossLimitPercent: parseFloat(form.querySelector(`[name="DailyLossLimitPercent"]`)?.value) || 0,
            TotalStopoutPercent: parseFloat(form.querySelector(`[name="TotalStopoutPercent"]`)?.value) || 0,
            ProfitConsistencyRulePercent: parseFloat(form.querySelector(`[name="ProfitConsistencyRulePercent"]`)?.value) || 0, // <--- [FIX] เพิ่มบรรทัดนี้
            Notes: form.querySelector(`[name="Notes"]`)?.value
        };

        if (this._selectedPortfolio) {
            this._sendMessage("UPDATE_PORTFOLIO", {
                portfolio_id: this._selectedPortfolio.PortfolioID,
                update_data: formData
            });
        } else {
            this._sendMessage("CREATE_PORTFOLIO", formData);
        }
    },
    
    _handleFileUpload: function(file) {
        const selectedPortfolioId = document.getElementById('pcc-upload-portfolio-select').value;
        if (!selectedPortfolioId) {
            const feedbackEl = document.getElementById('pcc-upload-feedback');
            if (feedbackEl) {
                feedbackEl.innerHTML = `<p style="color: var(--color-danger);">❌ Please select a target portfolio first.</p>`;
            }
            document.getElementById('pcc-file-uploader').value = '';
            return;
        }
        this._stagedData = null;
        this._renderUploadPane();
        const feedbackEl = document.getElementById('pcc-upload-feedback');
        if (feedbackEl) feedbackEl.innerHTML = `<p><i>Processing "${file.name}"... Please wait.</i></p>`;
        const reader = new FileReader();
        reader.onload = (event) => {
            const fileContent = event.target.result;
            this._sendMessage('UPLOAD_STATEMENT', {
                portfolio_id: selectedPortfolioId,
                file_name: file.name,
                file_content: fileContent
            });
        };
        reader.onerror = () => {
            if (feedbackEl) {
                feedbackEl.innerHTML = `<p style="color: var(--color-danger);">❌ Failed to read the selected file.</p>`;
            }
        };
        reader.readAsText(file, 'UTF-8');
    },

    _handleSaveConfirmation: function() {
        if (!this._stagedData) {
            alert("No processed data is staged for saving.");
            return;
        }
        const feedbackEl = document.getElementById('pcc-upload-feedback');
        if (feedbackEl) feedbackEl.innerHTML = `<p><i>Saving to database... Please wait.</i></p>`;
        this._sendMessage('SAVE_PROCESSED_DATA', this._stagedData);
    },

     _connectToServer: function() {
        console.log("PCC: Attempting connection to ws://localhost:5556...");
        this._socket = new WebSocket('ws://localhost:5556');
        
        this._socket.onopen = () => { 
            console.log("✅ PCC: Connection established!"); 
            this._isConnected = true; 
            this._requestAllPortfolios(); 
        };
        
        this._socket.onclose = (event) => { console.warn("PCC: Connection closed.", event); this._isConnected = false; };
        this._socket.onerror = (error) => { console.error("PCC WebSocket Error:", error); };
        
        this._socket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            console.log("PCC Received Event:", message.event);

            if (message.event === "PORTFOLIO_LIST_DATA") {
                this._portfolios = message.payload.portfolios || [];
                // If a portfolio was just updated or created, clear the selection
                if (this._selectedPortfolio) {
                    const updatedPortfolio = this._portfolios.find(p => p.PortfolioID === this._selectedPortfolio.PortfolioID);
                    this._selectedPortfolio = updatedPortfolio || null;
                }
                this._renderManagePane();
                this._renderUploadPane(); 
            } 
            else if (message.event === "OPERATION_STATUS") {
                alert(message.payload.message); // Simple feedback for now
                if(message.payload.success) {
                    if (message.request_event === 'DELETE_PORTFOLIO') {
                        this._selectedPortfolio = null;
                    }
                    this._requestAllPortfolios(); // Refresh the list on any successful CRUD operation
                }
            }
        };
     },

    _sendMessage: function(event, payload = {}) {
        if (this._isConnected) {
            this._socket.send(JSON.stringify({ event, payload }));
        } else {
            console.error("PCC: Cannot send message, not connected to server.");
        }
    },
    
    _requestAllPortfolios: function() {
        this._sendMessage("GET_ALL_PORTFOLIOS");
    },
    
    // VVVVVV REPLACE THIS ENTIRE FUNCTION VVVVVV
    _renderManagePane: function() {
        if (!this._selectors.managePane) return;

        const portfolioListHTML = this._portfolios.map(p => `
            <div class="portfolio-list-item ${this._selectedPortfolio?.PortfolioID === p.PortfolioID ? 'active' : ''}" data-id="${p.PortfolioID}">
                <span>${p.PortfolioName} (${p.mt5_account_id || 'N/A'})</span>
                <span class="portfolio-status-badge status-${p.Status?.toLowerCase() || 'unknown'}">${p.Status || 'Unknown'}</span>
            </div>`).join('');

        const p = this._selectedPortfolio || {};
        const isEditMode = !!this._selectedPortfolio;
        
        const formHTML = `
            <form class="pcc-form" id="pcc-portfolio-form">
                <div class="pcc-form-header">
                    <h4>${isEditMode ? `⚙️ Editing: ${p.PortfolioName}` : '➕ Create New Portfolio'}</h4>
                </div>
                <div class="pcc-form-grid full-spec">
                    <!-- Column 1: Core Details -->
                    <div class="form-column">
                        <div class="pcc-form-group"><label>Portfolio Name</label><input type="text" name="PortfolioName" value="${p.PortfolioName || ''}" required></div>
                        <div class="pcc-form-group"><label>MT5 Account ID</label><input type="text" name="mt5_account_id" value="${p.mt5_account_id || ''}"></div>
                        <div class="pcc-form-group"><label>Initial Balance ($)</label><input type="number" name="InitialBalance" value="${p.InitialBalance || '10000'}" step="100"></div>
                        <div class="pcc-form-group"><label>Leverage</label><input type="number" name="Leverage" value="${p.Leverage || '100'}" step="10"></div>
                    </div>
                    
                    <!-- Column 2: Program & Status -->
                    <div class="form-column">
                        <div class="pcc-form-group"><label>Program Type</label><select name="ProgramType" class="pcc-select"><option value="Personal" ${p.ProgramType === 'Personal' ? 'selected' : ''}>Personal</option><option value="Prop Firm - Evaluation" ${p.ProgramType === 'Prop Firm - Evaluation' ? 'selected' : ''}>Prop Firm - Evaluation</option><option value="Prop Firm - Funded" ${p.ProgramType === 'Prop Firm - Funded' ? 'selected' : ''}>Prop Firm - Funded</option></select></div>
                        <div class="pcc-form-group"><label>Evaluation Step</label><input type="text" name="EvaluationStep" value="${p.EvaluationStep || 'Phase 1'}"></div>
                        <div class="pcc-form-group"><label>Status</label><select name="Status" class="pcc-select"><option value="Active" ${p.Status === 'Active' ? 'selected' : ''}>Active</option><option value="Passed" ${p.Status === 'Passed' ? 'selected' : ''}>Passed</option><option value="Failed" ${p.Status === 'Failed' ? 'selected' : ''}>Failed</option><option value="Archived" ${p.Status === 'Archived' ? 'selected' : ''}>Archived</option></select></div>
                    </div>

                    <!-- Column 3: Risk Parameters -->
                    <div class="form-column">
                        <div class="pcc-form-group"><label>Profit Target (%)</label><input type="number" name="ProfitTargetPercent" value="${p.ProfitTargetPercent || '8'}"></div>
                        <div class="pcc-form-group"><label>Max Daily Loss (%)</label><input type="number" name="DailyLossLimitPercent" value="${p.DailyLossLimitPercent || '5'}"></div>
                        <div class="pcc-form-group"><label>Max Overall Loss (%)</label><input type="number" name="TotalStopoutPercent" value="${p.TotalStopoutPercent || '10'}"></div>
                        <div class="pcc-form-group"><label>Profit Consistency (%)</label><input type="number" name="ProfitConsistencyRulePercent" value="${p.ProfitConsistencyRulePercent || '30'}"></div>
                    </div>
                </div>

                <div class="pcc-form-group" style="margin-top: 16px;">
                    <label>Notes</label>
                    <textarea name="Notes" class="pcc-textarea" rows="3">${p.Notes || ''}</textarea>
                </div>

                <div class="pcc-form-actions">
                    <button type="submit" class="pcc-submit-btn">${isEditMode ? 'Save Changes' : 'Create Portfolio'}</button>
                    ${isEditMode ? '<button type="button" id="pcc-delete-btn" class="pcc-danger-btn">Delete Portfolio</button>' : ''}
                </div>
            </form>
        `;

        this._selectors.managePane.innerHTML = `
            <div class="pcc-manage-layout">
                <div class="pcc-list-panel">
                    <h4>Your Fleet</h4>
                    <div class="portfolio-list">
                        <button id="pcc-create-new-btn" class="pcc-create-new-btn">➕ Add New Portfolio</button>
                        ${portfolioListHTML}
                    </div>
                </div>
                <div class="pcc-edit-panel">${formHTML}</div>
            </div>
        `;
    },
    // ^^^^^^ REPLACE THIS ENTIRE FUNCTION ^^^^^^

    _renderUploadPane: function() {
        if (!this._selectors.uploadPane) return;
        const optionsHTML = this._portfolios.map(p => `<option value="${p.PortfolioID}">${p.PortfolioName} (${p.mt5_account_id || 'N/A'})</option>`).join('');
        this._selectors.uploadPane.innerHTML = `
            <h4>Data Ingestion Dock</h4>
            <div class="pcc-form-group">
                <label for="pcc-upload-portfolio-select">Target Portfolio</label>
                <select id="pcc-upload-portfolio-select" class="pcc-select"><option value="">-- Select a Portfolio --</option>${optionsHTML}</select>
            </div>
            <div class="pcc-form-group">
                <label for="pcc-file-uploader">MT5 Statement File (.htm)</label>
                <input type="file" id="pcc-file-uploader" class="pcc-file-input" accept=".htm,.html">
            </div>
            <div id="pcc-upload-feedback" class="pcc-upload-feedback">
                <p>Please select a portfolio and a statement file to begin.</p>
            </div>`;
    }
};