// ==============================================================================
// FILE: athena_prime_module.js
// OPERATION: PHOENIX (DEFINITIVE MASTER VERSION)
// ==============================================================================

(function() {
    'use strict';

    window.PhoenixModule = {
        _selectors: {},
        _isInitialized: false,
        _correctionUIDone: false,

        init: function() {
            this._selectors = {
                athenaHeader: document.querySelector('#athena-expander .card-header h3'),
                missionPlannerPane: document.getElementById('mission-planner-pane'),
                foundationFormContainer: document.getElementById('foundation-form-wrapper'),
                correctionBayContainer: null
            };
            
            if (this._selectors.athenaHeader && this._selectors.foundationFormContainer) {
                this._isInitialized = true;
                console.log("✅ PHOENIX MODULE: Synchronized and Initialized. Ready for operations.");
            } else {
                console.error("PHOENIX FATAL: Initialization failed. Could not find critical UI elements.");
            }
        },

        receiveData: function(serverData) {
            if (!this._isInitialized) return;
            this.analyzeAndDecide(serverData);
        },

        analyzeAndDecide: function(data) {
            // นำระบบกลับสู่สถานะอัตโนมัติ
            const isCorrectionNeeded = data.profit_consistency_percent > 20;
            
            if (isCorrectionNeeded) {
                this.runCorrectionProtocol(data);
            } else {
                this.runFoundationProtocol(data);
            }
        },

        runCorrectionProtocol: function(data) {
            const metrics = this._calculateCorrectionMetrics(data);
            this.updateUserInterface({
                mode: 'Correction',
                title: 'MISSION: FIX CONSISTENCY',
                metrics: metrics
            });
        },

        _calculateCorrectionMetrics: function(data) {
            const totalProfit = data.history_total_profit || 0;
            let dailyProfits = {};
            if (data.trade_history && data.trade_history.length > 0) {
                data.trade_history.forEach(trade => {
                    const date = trade['Close Time'].split(' ')[0];
                    dailyProfits[date] = (dailyProfits[date] || 0) + trade['Net P/L'];
                });
            }
            const highestProfitDay = Object.values(dailyProfits).reduce((max, profit) => Math.max(max, profit), 0);
            const requiredTotalProfit = highestProfitDay > 0 ? (highestProfitDay / 0.20) : 0;
            const profitNeeded = Math.max(0, requiredTotalProfit - totalProfit);
            const maxSafeProfit = highestProfitDay * 0.9;
            return { highestProfitDay, totalProfit, profitNeeded, maxSafeProfit };
        },

        runFoundationProtocol: function(data) {
            // --- Step 1: Update Balance (already complete) ---
            const balanceInput = document.getElementById('mp-balance');
            if (balanceInput && data.opening_balance) {
                balanceInput.value = data.opening_balance.toFixed(2);
            }

            // --- [NEW] Step 2: Calculate and Update Win/Loss Counts ---
            let wins = 0;
            let losses = 0;
            if (data.trade_history && data.trade_history.length > 0) {
                data.trade_history.forEach(trade => {
                    if (trade['Net P/L'] > 0) {
                        wins++;
                    } else {
                        losses++;
                    }
                });
            }
            
            const winsInput = document.getElementById('mp-wins');
            const lossesInput = document.getElementById('mp-losses');
            if (winsInput) winsInput.value = wins;
            if (lossesInput) lossesInput.value = losses;
            // --- [END OF NEW LOGIC] ---

            this.updateUserInterface({
                mode: 'Foundation',
                title: 'MISSION: BUILD & ADVANCE'
            });
        },
        
        updateUserInterface: function(payload) {
            if (!this._selectors.athenaHeader || !this._selectors.foundationFormContainer) return;

            this._selectors.athenaHeader.textContent = payload.title;
            this._selectors.athenaHeader.style.color = (payload.mode === 'Correction') ? 'var(--color-warning)' : 'var(--color-text-primary)';

            if (payload.mode === 'Correction') {
                this._selectors.foundationFormContainer.style.display = 'none';

                if (!this._correctionUIDone) {
                    this._buildCorrectionUI();
                    this._selectors.correctionBayContainer = document.getElementById('phoenix-correction-bay');
                    this._correctionUIDone = true;
                }
                
                if (this._selectors.correctionBayContainer) {
                    this._selectors.correctionBayContainer.style.display = 'flex';
                    const format = (val) => `$${val.toFixed(2)}`;
                    document.getElementById('pcc-highest-profit').textContent = format(payload.metrics.highestProfitDay);
                    document.getElementById('pcc-current-profit').textContent = format(payload.metrics.totalProfit);
                    document.getElementById('pcc-profit-needed').textContent = format(payload.metrics.profitNeeded);
                    document.getElementById('pcc-safe-profit').textContent = format(payload.metrics.maxSafeProfit);
                }
            } else { // Foundation Mode
                this._selectors.foundationFormContainer.style.display = 'block';
                if (this._selectors.correctionBayContainer) {
                    this._selectors.correctionBayContainer.style.display = 'none';
                }
            }
        },

        _buildCorrectionUI: function() {
            const container = this._selectors.missionPlannerPane;
            if (!container) return;
            const correctionUI_HTML = `
                <div id="phoenix-correction-bay" class="mission-results" style="display: flex; flex-direction: column; gap: 12px; margin-top: 0; padding-top: 0; border-top: none;">
                    <div class="result-item"><span class="result-label">Highest Profit Day:</span><span class="result-value" id="pcc-highest-profit">$0.00</span></div>
                    <div class="result-item"><span class="result-label">Current Total Profit:</span><span class="result-value" id="pcc-current-profit">$0.00</span></div>
                    <hr style="border-color: var(--color-border); margin: 4px 0;">
                    <div class="result-item" style="padding: 4px; background-color: rgba(226, 179, 19, 0.1); border-radius: 4px;"><span class="result-label" style="font-weight: 700;">Profit Still Needed:</span><span class="result-value text-warning" id="pcc-profit-needed" style="font-size: 1.1rem;">$0.00</span></div>
                    <div class="result-item" style="margin-top: 8px;"><span class="result-label text-loss">Max Safe Daily Profit:</span><span class="result-value text-loss" id="pcc-safe-profit">$0.00</span></div>
                    <p style="font-size: 0.8rem; color: var(--color-text-secondary); margin-top: 12px; text-align: center;">Focus on small, consistent wins. Do not exceed the 'Max Safe' profit in a single day to avoid resetting your progress.</p>
                </div>
            `;
            if (!document.getElementById('phoenix-correction-bay')) {
                 container.insertAdjacentHTML('beforeend', correctionUI_HTML);
            }
        }
    };
})();