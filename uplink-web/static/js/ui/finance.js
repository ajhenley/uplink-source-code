/**
 * Finance panel for bank account, stock market trading, and portfolio overview.
 */
const FinancePanel = {
    panelBody: null,
    stockData: null,
    activeTab: 'overview',

    /** Tracks which stock row has its trade controls expanded (company_name or null). */
    _expandedStock: null,

    /** Cached portfolio summary computed from stockData. */
    _portfolioCache: null,

    init() {
        this.panelBody = Panels.create('finance', 'FINANCIAL SERVICES', 520, 450);
        GameState.on('player_updated', () => {
            if (this.activeTab === 'overview' || this.activeTab === 'portfolio') this.render();
        });

        // Listen for real-time stock updates pushed from the server.
        GameState.on('stock_update', (data) => {
            if (data && data.stocks) {
                this.stockData = data;
                this._portfolioCache = null;
            }
            // Re-render if the stock or portfolio tab is active.
            if (this.activeTab === 'stocks' || this.activeTab === 'portfolio') {
                this.render();
            }
        });

        // Also wire up the socket event so GameState can relay it.
        if (GameSocket && GameSocket.socket) {
            GameSocket.socket.on('stock_update', (data) => {
                GameState.emit('stock_update', data);
            });
        }

        Panels.hide('finance');
    },

    toggle() {
        Panels.toggle('finance');
        if (Panels.panels['finance'] && Panels.panels['finance'].isVisible) {
            this.loadData();
        }
    },

    async loadData() {
        try {
            const resp = await fetch('/api/session/' + GAME_SESSION_ID + '/stocks');
            if (resp.ok) {
                this.stockData = await resp.json();
                this._portfolioCache = null;
            }
        } catch (e) { /* ignore */ }
        this.render();
    },

    render() {
        if (!this.panelBody) return;
        const p = GameState.player || {};

        let html = '<div class="finance-tabs">'
            + '<button class="tab-btn' + (this.activeTab === 'overview' ? ' active' : '') + '" onclick="FinancePanel.showTab(\'overview\')">Overview</button>'
            + '<button class="tab-btn' + (this.activeTab === 'stocks' ? ' active' : '') + '" onclick="FinancePanel.showTab(\'stocks\')">Stock Market</button>'
            + '<button class="tab-btn' + (this.activeTab === 'portfolio' ? ' active' : '') + '" onclick="FinancePanel.showTab(\'portfolio\')">Portfolio</button>'
            + '</div>';

        if (this.activeTab === 'overview') {
            html += this._renderOverview(p);
        } else if (this.activeTab === 'stocks') {
            html += this._renderStocks();
        } else if (this.activeTab === 'portfolio') {
            html += this._renderPortfolio(p);
        }

        this.panelBody.innerHTML = html;

        // Attach event listeners for trade inputs (cannot use inline oninput for
        // dynamic cost preview, so we bind after render).
        this._bindTradeInputs();
    },

    // ================================================================
    // Tab: Overview
    // ================================================================

    _renderOverview(p) {
        const portfolioValue = this._getPortfolioValue();
        const totalWealth = (p.balance || 0) + portfolioValue;

        let html = '<div style="padding:12px;">'
            + '<div style="margin-bottom:12px;">'
            + '<span style="color:var(--dim);">BALANCE:</span> '
            + '<span style="color:var(--highlight);font-size:18px;font-weight:bold;">'
            + (p.balance || 0).toLocaleString() + ' credits</span>'
            + '</div>'
            + '<div style="margin-bottom:12px;">'
            + '<span style="color:var(--dim);">CREDIT RATING:</span> '
            + '<span style="color:var(--primary);">' + this.esc(p.credit_rating || 'Unknown') + '</span>'
            + '</div>';

        if (portfolioValue > 0) {
            html += '<div style="margin-bottom:12px;">'
                + '<span style="color:var(--dim);">PORTFOLIO VALUE:</span> '
                + '<span style="color:var(--highlight);">' + portfolioValue.toLocaleString() + ' credits</span>'
                + '</div>'
                + '<div style="margin-bottom:12px;">'
                + '<span style="color:var(--dim);">TOTAL WEALTH:</span> '
                + '<span style="color:var(--primary);font-weight:bold;">' + totalWealth.toLocaleString() + ' credits</span>'
                + '</div>';
        }

        html += '<hr style="border-color:var(--dim);margin:12px 0;opacity:0.3;">'
            + '<div style="color:var(--dim);text-align:center;">'
            + 'Connect to a bank computer to manage accounts,<br>'
            + 'transfer funds, or take out loans.'
            + '</div>'
            + '</div>';

        return html;
    },

    // ================================================================
    // Tab: Stock Market
    // ================================================================

    _renderStocks() {
        if (!this.stockData || !this.stockData.stocks) {
            return '<div style="color:var(--dim);padding:20px;text-align:center;">Loading stock data...</div>';
        }

        const stocks = this.stockData.stocks;
        if (stocks.length === 0) {
            return '<div style="color:var(--dim);padding:20px;text-align:center;">No stocks available</div>';
        }

        let html = '<div style="padding:8px;max-height:340px;overflow-y:auto;">'
            + '<table style="width:100%;border-collapse:collapse;font-size:12px;">'
            + '<tr style="color:var(--dim);border-bottom:1px solid var(--dim);">'
            + '<th style="text-align:left;padding:4px 6px;">Company</th>'
            + '<th style="text-align:right;padding:4px 6px;">Price</th>'
            + '<th style="text-align:right;padding:4px 6px;">Chg</th>'
            + '<th style="text-align:right;padding:4px 6px;">Owned</th>'
            + '<th style="text-align:center;padding:4px 6px;">Trade</th>'
            + '</tr>';

        for (const s of stocks) {
            const changeColor = s.change > 0 ? 'var(--primary)' : s.change < 0 ? 'var(--danger)' : 'var(--dim)';
            const changePrefix = s.change > 0 ? '+' : '';
            const changePercent = s.current_price > 0
                ? ' (' + changePrefix + ((s.change / s.current_price) * 100).toFixed(1) + '%)'
                : '';
            const isExpanded = this._expandedStock === s.company_name;
            const shares = s.player_shares || 0;
            const escapedName = this.esc(s.company_name);
            const jsName = this._jsStr(s.company_name);

            // Main row
            html += '<tr style="border-bottom:1px solid rgba(0,255,65,0.05);' + (isExpanded ? 'background:rgba(0,255,65,0.04);' : '') + '">'
                + '<td style="padding:4px 6px;color:var(--primary);max-width:140px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="' + escapedName + '">' + escapedName + '</td>'
                + '<td style="padding:4px 6px;text-align:right;color:var(--highlight);">' + s.current_price + 'c</td>'
                + '<td style="padding:4px 6px;text-align:right;color:' + changeColor + ';white-space:nowrap;">'
                    + changePrefix + s.change + '<span style="font-size:10px;color:' + changeColor + ';">' + changePercent + '</span></td>'
                + '<td style="padding:4px 6px;text-align:right;color:var(--primary);">' + shares + '</td>'
                + '<td style="padding:4px 6px;text-align:center;">'
                    + '<button class="terminal-btn terminal-btn-small" style="padding:2px 8px;font-size:10px;letter-spacing:0;" '
                    + 'onclick="FinancePanel._toggleTrade(' + jsName + ')">'
                    + (isExpanded ? '[ CLOSE ]' : '[ TRADE ]')
                    + '</button>'
                + '</td>'
                + '</tr>';

            // Expanded trade row
            if (isExpanded) {
                html += this._renderTradeRow(s);
            }
        }

        html += '</table></div>';
        return html;
    },

    /**
     * Render the inline trade controls for a stock (appears as an extra table row).
     */
    _renderTradeRow(stock) {
        const name = stock.company_name;
        const price = stock.current_price || 0;
        const shares = stock.player_shares || 0;
        const balance = (GameState.player && GameState.player.balance) || 0;
        const maxBuy = price > 0 ? Math.floor(balance / price) : 0;
        const jsName = this._jsStr(name);

        let html = '<tr style="background:rgba(0,255,65,0.03);">'
            + '<td colspan="5" style="padding:8px 6px;">'
            + '<div style="display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap;">';

        // Buy section
        html += '<div style="flex:1;min-width:160px;">'
            + '<div style="color:var(--dim);font-size:10px;margin-bottom:4px;text-transform:uppercase;letter-spacing:1px;">Buy Shares</div>'
            + '<div style="display:flex;gap:4px;align-items:center;">'
            + '<input type="number" min="1" max="' + maxBuy + '" value="1" '
            + 'class="terminal-input" id="buy-qty-' + this._safeId(name) + '" '
            + 'style="width:70px;padding:3px 6px;font-size:11px;" '
            + 'data-action="buy" data-price="' + price + '" data-company="' + this.esc(name) + '">'
            + '<button class="terminal-btn terminal-btn-small" style="padding:2px 8px;font-size:10px;letter-spacing:0;white-space:nowrap;" '
            + 'onclick="FinancePanel._buyStock(' + jsName + ')">'
            + '[ BUY ]</button>'
            + '</div>'
            + '<div id="buy-cost-' + this._safeId(name) + '" style="color:var(--dim);font-size:10px;margin-top:2px;">'
            + 'Cost: ' + price.toLocaleString() + 'c'
            + ' | Max: ' + maxBuy
            + '</div>'
            + '</div>';

        // Sell section
        html += '<div style="flex:1;min-width:160px;">'
            + '<div style="color:var(--dim);font-size:10px;margin-bottom:4px;text-transform:uppercase;letter-spacing:1px;">Sell Shares</div>'
            + '<div style="display:flex;gap:4px;align-items:center;">'
            + '<input type="number" min="1" max="' + shares + '" value="1" '
            + 'class="terminal-input" id="sell-qty-' + this._safeId(name) + '" '
            + 'style="width:70px;padding:3px 6px;font-size:11px;" '
            + (shares === 0 ? 'disabled ' : '')
            + 'data-action="sell" data-price="' + price + '" data-company="' + this.esc(name) + '">'
            + '<button class="terminal-btn terminal-btn-small terminal-btn-danger" style="padding:2px 8px;font-size:10px;letter-spacing:0;white-space:nowrap;" '
            + (shares === 0 ? 'disabled ' : '')
            + 'onclick="FinancePanel._sellStock(' + jsName + ')">'
            + '[ SELL ]</button>'
            + '</div>'
            + '<div id="sell-value-' + this._safeId(name) + '" style="color:var(--dim);font-size:10px;margin-top:2px;">'
            + (shares > 0
                ? 'Value: ' + price.toLocaleString() + 'c | Owned: ' + shares
                : 'No shares owned')
            + '</div>'
            + '</div>';

        html += '</div>'
            + '</td></tr>';

        return html;
    },

    // ================================================================
    // Tab: Portfolio
    // ================================================================

    _renderPortfolio(p) {
        const portfolio = this._getPortfolioDetails();
        const balance = p.balance || 0;

        let html = '<div style="padding:12px;">';

        // Summary header
        html += '<div style="border:1px solid var(--dim);padding:10px;margin-bottom:12px;background:rgba(0,255,65,0.02);">'
            + '<div style="display:flex;justify-content:space-between;margin-bottom:8px;">'
            + '<span style="color:var(--dim);font-size:11px;text-transform:uppercase;letter-spacing:1px;">Portfolio Summary</span>'
            + '<button class="terminal-btn terminal-btn-small" style="padding:1px 8px;font-size:10px;letter-spacing:0;" '
            + 'onclick="FinancePanel.loadData()">[ REFRESH ]</button>'
            + '</div>';

        html += '<div style="display:flex;gap:20px;flex-wrap:wrap;">'
            + '<div>'
            + '<div style="color:var(--dim);font-size:10px;">CASH</div>'
            + '<div style="color:var(--highlight);font-size:14px;font-weight:bold;">' + balance.toLocaleString() + 'c</div>'
            + '</div>'
            + '<div>'
            + '<div style="color:var(--dim);font-size:10px;">STOCKS VALUE</div>'
            + '<div style="color:var(--highlight);font-size:14px;font-weight:bold;">' + portfolio.totalValue.toLocaleString() + 'c</div>'
            + '</div>'
            + '<div>'
            + '<div style="color:var(--dim);font-size:10px;">TOTAL WEALTH</div>'
            + '<div style="color:var(--primary);font-size:14px;font-weight:bold;">' + (balance + portfolio.totalValue).toLocaleString() + 'c</div>'
            + '</div>'
            + '<div>'
            + '<div style="color:var(--dim);font-size:10px;">TOTAL P/L</div>'
            + '<div style="font-size:14px;font-weight:bold;color:' + this._plColor(portfolio.totalPL) + ';">'
            + this._plPrefix(portfolio.totalPL) + Math.abs(portfolio.totalPL).toLocaleString() + 'c</div>'
            + '</div>'
            + '</div>'
            + '</div>';

        // Holdings table
        if (portfolio.holdings.length === 0) {
            html += '<div style="color:var(--dim);text-align:center;padding:30px;">'
                + 'No stock holdings.<br>'
                + '<span style="font-size:11px;">Visit the Stock Market tab to buy shares.</span>'
                + '</div>';
        } else {
            html += '<table style="width:100%;border-collapse:collapse;font-size:12px;">'
                + '<tr style="color:var(--dim);border-bottom:1px solid var(--dim);">'
                + '<th style="text-align:left;padding:4px 6px;">Company</th>'
                + '<th style="text-align:right;padding:4px 6px;">Shares</th>'
                + '<th style="text-align:right;padding:4px 6px;">Avg Cost</th>'
                + '<th style="text-align:right;padding:4px 6px;">Price</th>'
                + '<th style="text-align:right;padding:4px 6px;">Value</th>'
                + '<th style="text-align:right;padding:4px 6px;">P/L</th>'
                + '</tr>';

            for (const h of portfolio.holdings) {
                const plColor = this._plColor(h.profitLoss);
                html += '<tr style="border-bottom:1px solid rgba(0,255,65,0.05);">'
                    + '<td style="padding:4px 6px;color:var(--primary);">' + this.esc(h.company_name) + '</td>'
                    + '<td style="padding:4px 6px;text-align:right;color:var(--primary);">' + h.shares + '</td>'
                    + '<td style="padding:4px 6px;text-align:right;color:var(--dim);">'
                        + (h.avgCost !== null ? h.avgCost.toFixed(1) + 'c' : '-') + '</td>'
                    + '<td style="padding:4px 6px;text-align:right;color:var(--highlight);">' + h.currentPrice + 'c</td>'
                    + '<td style="padding:4px 6px;text-align:right;color:var(--highlight);">' + h.value.toLocaleString() + 'c</td>'
                    + '<td style="padding:4px 6px;text-align:right;color:' + plColor + ';font-weight:bold;">'
                        + this._plPrefix(h.profitLoss) + Math.abs(h.profitLoss).toLocaleString() + 'c'
                    + '</td>'
                    + '</tr>';
            }

            html += '</table>';
        }

        html += '</div>';
        return html;
    },

    // ================================================================
    // Trade actions
    // ================================================================

    _toggleTrade(companyName) {
        if (this._expandedStock === companyName) {
            this._expandedStock = null;
        } else {
            this._expandedStock = companyName;
        }
        this.render();
    },

    _buyStock(companyName) {
        const input = document.getElementById('buy-qty-' + this._safeId(companyName));
        if (!input) return;

        const count = parseInt(input.value, 10);
        if (!count || count < 1) {
            if (typeof App !== 'undefined' && App.showNotification) {
                App.showNotification('Enter a valid number of shares.', 'warning');
            }
            return;
        }

        // Validate against balance
        const stock = this._findStock(companyName);
        if (stock) {
            const cost = count * (stock.current_price || 0);
            const balance = (GameState.player && GameState.player.balance) || 0;
            if (cost > balance) {
                if (typeof App !== 'undefined' && App.showNotification) {
                    App.showNotification('Insufficient funds. Need ' + cost.toLocaleString() + 'c, have ' + balance.toLocaleString() + 'c.', 'error');
                }
                return;
            }
        }

        GameSocket.socket.emit('buy_stock', {
            session_id: GAME_SESSION_ID,
            company_name: companyName,
            shares: count
        });

        if (typeof App !== 'undefined' && App.showNotification) {
            App.showNotification('Buying ' + count + ' shares of ' + companyName + '...', 'info');
        }

        // Refresh after a short delay to allow the server to process.
        setTimeout(() => { this.loadData(); }, 500);
    },

    _sellStock(companyName) {
        const input = document.getElementById('sell-qty-' + this._safeId(companyName));
        if (!input) return;

        const count = parseInt(input.value, 10);
        if (!count || count < 1) {
            if (typeof App !== 'undefined' && App.showNotification) {
                App.showNotification('Enter a valid number of shares.', 'warning');
            }
            return;
        }

        // Validate against owned shares
        const stock = this._findStock(companyName);
        if (stock && count > (stock.player_shares || 0)) {
            if (typeof App !== 'undefined' && App.showNotification) {
                App.showNotification('You only own ' + (stock.player_shares || 0) + ' shares of ' + companyName + '.', 'error');
            }
            return;
        }

        GameSocket.socket.emit('sell_stock', {
            session_id: GAME_SESSION_ID,
            company_name: companyName,
            shares: count
        });

        if (typeof App !== 'undefined' && App.showNotification) {
            App.showNotification('Selling ' + count + ' shares of ' + companyName + '...', 'info');
        }

        // Refresh after a short delay to allow the server to process.
        setTimeout(() => { this.loadData(); }, 500);
    },

    // ================================================================
    // Bind dynamic trade input listeners (cost preview)
    // ================================================================

    _bindTradeInputs() {
        if (!this.panelBody) return;

        // Buy quantity inputs
        const buyInputs = this.panelBody.querySelectorAll('input[data-action="buy"]');
        buyInputs.forEach((input) => {
            input.addEventListener('input', () => {
                const price = parseFloat(input.dataset.price) || 0;
                const qty = parseInt(input.value, 10) || 0;
                const company = input.dataset.company;
                const costEl = document.getElementById('buy-cost-' + this._safeId(company));
                if (costEl) {
                    const balance = (GameState.player && GameState.player.balance) || 0;
                    const maxBuy = price > 0 ? Math.floor(balance / price) : 0;
                    const total = qty * price;
                    const costColor = total > balance ? 'var(--danger)' : 'var(--dim)';
                    costEl.innerHTML = '<span style="color:' + costColor + ';">Cost: ' + total.toLocaleString() + 'c</span>'
                        + ' | Max: ' + maxBuy;
                }
            });
        });

        // Sell quantity inputs
        const sellInputs = this.panelBody.querySelectorAll('input[data-action="sell"]');
        sellInputs.forEach((input) => {
            input.addEventListener('input', () => {
                const price = parseFloat(input.dataset.price) || 0;
                const qty = parseInt(input.value, 10) || 0;
                const company = input.dataset.company;
                const valEl = document.getElementById('sell-value-' + this._safeId(company));
                if (valEl) {
                    const stock = this._findStock(company);
                    const owned = stock ? (stock.player_shares || 0) : 0;
                    const total = qty * price;
                    const qtyColor = qty > owned ? 'var(--danger)' : 'var(--dim)';
                    valEl.innerHTML = '<span style="color:' + qtyColor + ';">Value: ' + total.toLocaleString() + 'c</span>'
                        + ' | Owned: ' + owned;
                }
            });
        });
    },

    // ================================================================
    // Portfolio helpers
    // ================================================================

    _getPortfolioValue() {
        if (!this.stockData || !this.stockData.stocks) return 0;
        let total = 0;
        for (const s of this.stockData.stocks) {
            if (s.player_shares && s.player_shares > 0) {
                total += s.player_shares * (s.current_price || 0);
            }
        }
        return total;
    },

    _getPortfolioDetails() {
        if (this._portfolioCache) return this._portfolioCache;

        const holdings = [];
        let totalValue = 0;
        let totalPL = 0;

        if (this.stockData && this.stockData.stocks) {
            for (const s of this.stockData.stocks) {
                if (s.player_shares && s.player_shares > 0) {
                    const value = s.player_shares * (s.current_price || 0);
                    // avg_purchase_price may be provided by the server; otherwise estimate
                    // profit/loss from the change field.
                    const avgCost = (typeof s.avg_purchase_price === 'number') ? s.avg_purchase_price : null;
                    let profitLoss = 0;
                    if (avgCost !== null) {
                        profitLoss = s.player_shares * ((s.current_price || 0) - avgCost);
                    } else {
                        // Fallback: use `change` as a session-relative indicator.
                        profitLoss = s.player_shares * (s.change || 0);
                    }

                    totalValue += value;
                    totalPL += profitLoss;
                    holdings.push({
                        company_name: s.company_name,
                        shares: s.player_shares,
                        avgCost: avgCost,
                        currentPrice: s.current_price || 0,
                        value: value,
                        profitLoss: Math.round(profitLoss)
                    });
                }
            }
        }

        this._portfolioCache = {
            holdings: holdings,
            totalValue: totalValue,
            totalPL: Math.round(totalPL)
        };
        return this._portfolioCache;
    },

    // ================================================================
    // Tab switching
    // ================================================================

    showTab(tab) {
        this.activeTab = tab;
        if ((tab === 'stocks' || tab === 'portfolio') && !this.stockData) {
            this.loadData();
        } else {
            this.render();
        }
    },

    // ================================================================
    // Utility helpers
    // ================================================================

    _findStock(companyName) {
        if (!this.stockData || !this.stockData.stocks) return null;
        return this.stockData.stocks.find(function(s) { return s.company_name === companyName; }) || null;
    },

    /**
     * Produce a safe DOM id fragment from a company name.
     * Strips non-alphanumeric characters and lowercases.
     */
    _safeId(str) {
        return (str || '').replace(/[^a-zA-Z0-9]/g, '_').toLowerCase();
    },

    /**
     * Produce a JS string literal safe for use inside onclick attributes.
     * Wraps in single quotes and escapes inner quotes/backslashes.
     */
    _jsStr(str) {
        return "'" + (str || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'") + "'";
    },

    /**
     * Return the theme color for a profit/loss value.
     */
    _plColor(value) {
        if (value > 0) return 'var(--primary)';
        if (value < 0) return 'var(--danger)';
        return 'var(--dim)';
    },

    /**
     * Return the prefix string (+/-/empty) for a profit/loss value.
     */
    _plPrefix(value) {
        if (value > 0) return '+';
        if (value < 0) return '-';
        return '';
    },

    /**
     * Escape HTML to prevent XSS.
     */
    esc(str) {
        const d = document.createElement('div');
        d.textContent = str || '';
        return d.innerHTML;
    }
};
