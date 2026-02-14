/* ============================================================
   UPLINK WEB - Screen Type 8: High Security Screen
   Handles voice print, elliptic curve, and cipher security
   challenges. Shows bypass status or challenge UI.
   ============================================================ */

const ScreenHighSecurity = {

    /**
     * Render a high security screen into the given container.
     * @param {HTMLElement} container - The panel body element to render into
     * @param {Object} data - Screen data from server
     * @param {string} data.title - Screen title
     * @param {string} data.security_type - 'voice' | 'elliptic' | 'cipher'
     * @param {Object} data.challenge_data - Type-specific challenge data
     * @param {boolean} data.bypassed - Whether the security has been bypassed
     */
    render(container, data) {
        container.innerHTML = '';

        // Title
        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'High Security';
        container.appendChild(title);

        // Security status indicator
        const statusBar = document.createElement('div');
        statusBar.style.padding = '8px';
        statusBar.style.textAlign = 'center';
        statusBar.style.fontSize = '11px';
        statusBar.style.letterSpacing = '1px';

        if (data.bypassed) {
            statusBar.style.color = 'var(--primary)';
            statusBar.style.background = 'rgba(0, 255, 65, 0.08)';
            statusBar.textContent = 'SECURITY BYPASSED - ACCESS GRANTED';
            container.appendChild(statusBar);

            // Proceed button
            const btnWrap = document.createElement('div');
            btnWrap.style.textAlign = 'center';
            btnWrap.style.padding = '20px';

            const proceedBtn = document.createElement('button');
            proceedBtn.className = 'terminal-btn';
            proceedBtn.textContent = 'PROCEED';
            proceedBtn.addEventListener('click', () => {
                GameSocket.screenAction('navigate', { next_page: 0 });
            });

            btnWrap.appendChild(proceedBtn);
            container.appendChild(btnWrap);
            return;
        }

        // Security is active
        statusBar.style.color = 'var(--danger)';
        statusBar.style.background = 'rgba(255, 51, 51, 0.08)';
        statusBar.textContent = 'SECURITY ACTIVE - ACCESS DENIED';
        container.appendChild(statusBar);

        // Render the specific challenge type
        const challengeArea = document.createElement('div');
        challengeArea.style.padding = '12px 8px';

        switch (data.security_type) {
            case 'voice':
                this._renderVoiceChallenge(challengeArea, data);
                break;
            case 'elliptic':
                this._renderEllipticChallenge(challengeArea, data);
                break;
            case 'cipher':
                this._renderCipherChallenge(challengeArea, data);
                break;
            default:
                const unknown = document.createElement('div');
                unknown.className = 'text-warning';
                unknown.textContent = 'Unknown security type: ' + escapeHtml(data.security_type || '?');
                challengeArea.appendChild(unknown);
        }

        container.appendChild(challengeArea);
    },

    /**
     * Render voice print authentication challenge.
     * @param {HTMLElement} area
     * @param {Object} data
     */
    _renderVoiceChallenge(area, data) {
        const header = document.createElement('div');
        header.style.color = 'var(--danger)';
        header.style.fontWeight = '700';
        header.style.marginBottom = '12px';
        header.textContent = 'VOICE PRINT AUTHENTICATION REQUIRED';
        area.appendChild(header);

        // Visual waveform placeholder
        const waveform = document.createElement('div');
        waveform.style.cssText = 'height:60px;background:var(--bg);border:1px solid var(--danger);' +
            'margin-bottom:12px;display:flex;align-items:center;justify-content:center;overflow:hidden;';

        // Animated bars to represent voice analysis
        const barsContainer = document.createElement('div');
        barsContainer.style.cssText = 'display:flex;gap:2px;align-items:end;height:40px;';

        for (let i = 0; i < 32; i++) {
            const bar = document.createElement('div');
            const h = Math.floor(Math.random() * 30) + 5;
            bar.style.cssText = 'width:3px;background:var(--danger);opacity:0.4;height:' + h + 'px;';
            barsContainer.appendChild(bar);
        }
        waveform.appendChild(barsContainer);
        area.appendChild(waveform);

        const desc = document.createElement('div');
        desc.className = 'text-dim';
        desc.style.marginBottom = '16px';
        desc.style.fontSize = '11px';
        desc.textContent = 'This system requires voice print verification. ' +
            'Use a Voice Analyser to bypass this security measure.';
        area.appendChild(desc);

        const btnWrap = document.createElement('div');
        btnWrap.style.textAlign = 'center';

        const bypassBtn = document.createElement('button');
        bypassBtn.className = 'terminal-btn danger';
        bypassBtn.textContent = 'RUN VOICE ANALYSER';
        bypassBtn.addEventListener('click', () => {
            GameSocket.runTool('Voice_Analyser', 1, GameState.connection.targetIp, {
                security_type: 'voice'
            });
            bypassBtn.disabled = true;
            bypassBtn.textContent = 'ANALYSING...';
        });

        btnWrap.appendChild(bypassBtn);
        area.appendChild(btnWrap);
    },

    /**
     * Render elliptic curve security challenge.
     * @param {HTMLElement} area
     * @param {Object} data
     */
    _renderEllipticChallenge(area, data) {
        const header = document.createElement('div');
        header.style.color = 'var(--danger)';
        header.style.fontWeight = '700';
        header.style.marginBottom = '12px';
        header.textContent = 'ELLIPTIC CURVE VERIFICATION REQUIRED';
        area.appendChild(header);

        // Visual puzzle placeholder - grid of dots representing curve
        const grid = document.createElement('div');
        grid.style.cssText = 'width:200px;height:200px;margin:0 auto 12px;position:relative;' +
            'border:1px solid var(--danger);background:var(--bg);';

        const challenge = data.challenge_data || {};
        const points = Array.isArray(challenge.points) ? challenge.points : [];

        // Draw some placeholder points on the "curve"
        if (points.length > 0) {
            points.forEach(pt => {
                const dot = document.createElement('div');
                const px = (pt.x / 100) * 200;
                const py = (pt.y / 100) * 200;
                dot.style.cssText = 'position:absolute;width:4px;height:4px;border-radius:50%;' +
                    'background:var(--warning);left:' + px + 'px;top:' + py + 'px;';
                grid.appendChild(dot);
            });
        } else {
            // Default visual
            for (let i = 0; i < 16; i++) {
                const dot = document.createElement('div');
                const angle = (i / 16) * Math.PI * 2;
                const px = 100 + Math.cos(angle) * 70;
                const py = 100 + Math.sin(angle) * 50;
                dot.style.cssText = 'position:absolute;width:3px;height:3px;border-radius:50%;' +
                    'background:var(--danger);opacity:0.6;left:' + px + 'px;top:' + py + 'px;';
                grid.appendChild(dot);
            }
        }

        area.appendChild(grid);

        const desc = document.createElement('div');
        desc.className = 'text-dim';
        desc.style.marginBottom = '16px';
        desc.style.fontSize = '11px';
        desc.style.textAlign = 'center';
        desc.textContent = 'Elliptic-curve signature verification in progress. ' +
            'Use a compatible bypass tool to proceed.';
        area.appendChild(desc);

        const btnWrap = document.createElement('div');
        btnWrap.style.textAlign = 'center';

        const bypassBtn = document.createElement('button');
        bypassBtn.className = 'terminal-btn danger';
        bypassBtn.textContent = 'RUN BYPASS';
        bypassBtn.addEventListener('click', () => {
            GameSocket.screenAction('bypass', { security_type: 'elliptic' });
            bypassBtn.disabled = true;
            bypassBtn.textContent = 'BYPASSING...';
        });

        btnWrap.appendChild(bypassBtn);
        area.appendChild(btnWrap);
    },

    /**
     * Render cipher text decryption challenge.
     * @param {HTMLElement} area
     * @param {Object} data
     */
    _renderCipherChallenge(area, data) {
        const header = document.createElement('div');
        header.style.color = 'var(--danger)';
        header.style.fontWeight = '700';
        header.style.marginBottom = '12px';
        header.textContent = 'CIPHER ENCRYPTION ACTIVE';
        area.appendChild(header);

        const challenge = data.challenge_data || {};

        // Display cipher text
        const cipherBlock = document.createElement('pre');
        cipherBlock.style.cssText = 'background:var(--bg);border:1px solid var(--danger);padding:12px;' +
            'margin-bottom:12px;color:var(--warning);font-family:inherit;font-size:11px;' +
            'white-space:pre-wrap;word-wrap:break-word;max-height:120px;overflow-y:auto;';
        cipherBlock.textContent = challenge.cipher_text || 'ENCRYPTED DATA BLOCK - UNABLE TO DISPLAY';
        area.appendChild(cipherBlock);

        const desc = document.createElement('div');
        desc.className = 'text-dim';
        desc.style.marginBottom = '16px';
        desc.style.fontSize = '11px';
        desc.textContent = 'Data is protected by cipher encryption. ' +
            'Use a Decypher tool to decode the security layer.';
        area.appendChild(desc);

        const btnWrap = document.createElement('div');
        btnWrap.style.textAlign = 'center';

        const decryptBtn = document.createElement('button');
        decryptBtn.className = 'terminal-btn danger';
        decryptBtn.textContent = 'RUN DECYPHER';
        decryptBtn.addEventListener('click', () => {
            GameSocket.runTool('Decypher', 1, GameState.connection.targetIp, {
                security_type: 'cipher'
            });
            decryptBtn.disabled = true;
            decryptBtn.textContent = 'DECRYPTING...';
        });

        btnWrap.appendChild(decryptBtn);
        area.appendChild(btnWrap);
    }
};
