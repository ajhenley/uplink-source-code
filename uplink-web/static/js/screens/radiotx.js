/* ============================================================
   UPLINK WEB - Screen: Radio Transmitter
   Displays a radio transmitter interface with frequency
   and signal information.
   ============================================================ */

const ScreenRadioTX = {

    render(container, data) {
        container.innerHTML = '';

        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Radio Transmitter';
        container.appendChild(title);

        const block = document.createElement('div');
        block.style.padding = '12px 8px';

        // Frequency display
        const freqLabel = document.createElement('div');
        freqLabel.className = 'text-dim';
        freqLabel.style.cssText = 'font-size:11px;margin-bottom:4px;';
        freqLabel.textContent = 'FREQUENCY:';
        block.appendChild(freqLabel);

        const freqValue = document.createElement('div');
        freqValue.style.cssText = 'color:var(--highlight);font-size:18px;letter-spacing:2px;' +
            'margin-bottom:16px;font-weight:700;';
        freqValue.textContent = data.frequency || '---.- MHz';
        block.appendChild(freqValue);

        // Signal strength
        if (data.signal_strength != null) {
            const sigLabel = document.createElement('div');
            sigLabel.className = 'text-dim';
            sigLabel.style.cssText = 'font-size:11px;margin-bottom:4px;';
            sigLabel.textContent = 'SIGNAL STRENGTH:';
            block.appendChild(sigLabel);

            const sigBar = document.createElement('div');
            sigBar.style.cssText = 'height:12px;border:1px solid var(--primary);background:var(--bg);margin-bottom:12px;';
            const sigFill = document.createElement('div');
            sigFill.style.cssText = 'height:100%;background:var(--primary);width:' +
                Math.min(100, data.signal_strength) + '%;';
            sigBar.appendChild(sigFill);
            block.appendChild(sigBar);
        }

        // Status
        if (data.status_message) {
            const msg = document.createElement('div');
            msg.style.cssText = 'color:var(--primary);margin-top:8px;';
            msg.textContent = data.status_message;
            block.appendChild(msg);
        }

        // Transmit button
        if (data.can_transmit) {
            const txBtn = document.createElement('button');
            txBtn.className = 'terminal-btn';
            txBtn.style.cssText = 'margin-top:12px;padding:8px 20px;';
            txBtn.textContent = 'TRANSMIT';
            txBtn.addEventListener('click', () => {
                txBtn.disabled = true;
                txBtn.textContent = 'TRANSMITTING...';
                GameSocket.screenAction('transmit', {});
            });
            block.appendChild(txBtn);
        }

        container.appendChild(block);
    }
};
