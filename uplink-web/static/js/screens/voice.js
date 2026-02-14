/* ============================================================
   UPLINK WEB - Screen: Voice Print Analysis
   Displays a voice print authentication challenge. Player
   must use Voice_Analyser tool to bypass.
   ============================================================ */

const ScreenVoice = {

    render(container, data) {
        container.innerHTML = '';

        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Voice Print Authentication';
        container.appendChild(title);

        const block = document.createElement('div');
        block.style.padding = '12px 8px';

        // Waveform visualization (ASCII art style)
        const waveBox = document.createElement('div');
        waveBox.style.cssText = 'font-family:monospace;color:var(--highlight);padding:12px;' +
            'border:1px solid var(--dim);margin-bottom:12px;text-align:center;font-size:10px;line-height:1.2;';
        waveBox.textContent = data.waveform || '~~~\\/\\/\\/\\/\\/\\/\\/~~~  VOICE PRINT REQUIRED  ~~~\\/\\/\\/\\/\\/\\/\\/~~~';
        block.appendChild(waveBox);

        // Status
        if (data.status === 'matched' || data.solved) {
            const matched = document.createElement('div');
            matched.style.cssText = 'color:#00ff41;font-weight:700;text-align:center;padding:8px;';
            matched.textContent = 'VOICE PRINT MATCHED - ACCESS GRANTED';
            block.appendChild(matched);
        } else {
            const prompt = document.createElement('div');
            prompt.style.cssText = 'color:var(--warning);text-align:center;padding:8px;';
            prompt.textContent = data.status_message || 'Use Voice Analyser tool to bypass authentication.';
            block.appendChild(prompt);
        }

        container.appendChild(block);
    }
};
