/* ============================================================
   UPLINK WEB - Screen: Voice Phone Analysis
   Similar to voice screen but for phone-based voice print
   verification systems.
   ============================================================ */

const ScreenVoicePhone = {

    render(container, data) {
        container.innerHTML = '';

        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Voice Phone Verification';
        container.appendChild(title);

        const block = document.createElement('div');
        block.style.padding = '12px 8px';

        // Phone status
        const phoneStatus = document.createElement('div');
        phoneStatus.style.cssText = 'text-align:center;padding:16px;border:1px solid var(--dim);margin-bottom:12px;';

        if (data.phone_number) {
            const numDisplay = document.createElement('div');
            numDisplay.style.cssText = 'color:var(--highlight);font-size:16px;letter-spacing:3px;margin-bottom:8px;';
            numDisplay.textContent = data.phone_number;
            phoneStatus.appendChild(numDisplay);
        }

        const statusText = document.createElement('div');
        if (data.status === 'verified' || data.solved) {
            statusText.style.cssText = 'color:#00ff41;font-weight:700;';
            statusText.textContent = 'VOICE VERIFIED - ACCESS GRANTED';
        } else if (data.status === 'dialing') {
            statusText.style.cssText = 'color:var(--warning);';
            statusText.textContent = 'DIALING...';
        } else {
            statusText.style.cssText = 'color:var(--text);';
            statusText.textContent = data.status_message || 'Awaiting voice verification. Use Voice Analyser.';
        }
        phoneStatus.appendChild(statusText);

        block.appendChild(phoneStatus);
        container.appendChild(block);
    }
};
