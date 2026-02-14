/* ============================================================
   UPLINK WEB - Screen: Cypher Puzzle
   Displays a cipher puzzle that the player must solve to
   bypass encryption. Used on high-security systems.
   ============================================================ */

const ScreenCypher = {

    render(container, data) {
        container.innerHTML = '';

        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Elliptic-Curve Encryption';
        container.appendChild(title);

        const block = document.createElement('div');
        block.style.padding = '12px 8px';

        // Cipher text
        if (data.cipher_text) {
            const cipherLabel = document.createElement('div');
            cipherLabel.className = 'text-dim';
            cipherLabel.style.cssText = 'font-size:11px;margin-bottom:4px;';
            cipherLabel.textContent = 'ENCRYPTED DATA:';
            block.appendChild(cipherLabel);

            const cipherBox = document.createElement('div');
            cipherBox.style.cssText = 'font-family:monospace;color:var(--warning);padding:8px;' +
                'border:1px solid var(--dim);margin-bottom:12px;word-break:break-all;font-size:11px;';
            cipherBox.textContent = data.cipher_text;
            block.appendChild(cipherBox);
        }

        // Status message
        if (data.status_message) {
            const msg = document.createElement('div');
            msg.style.cssText = 'color:var(--primary);margin-bottom:12px;';
            msg.textContent = data.status_message;
            block.appendChild(msg);
        }

        // If solvable manually, show input
        if (!data.solved) {
            const inputLabel = document.createElement('div');
            inputLabel.className = 'text-dim';
            inputLabel.style.cssText = 'font-size:11px;margin-bottom:4px;';
            inputLabel.textContent = 'Use Decypher tool to crack this encryption.';
            block.appendChild(inputLabel);
        } else {
            const solvedMsg = document.createElement('div');
            solvedMsg.style.cssText = 'color:#00ff41;font-weight:700;padding:8px 0;';
            solvedMsg.textContent = 'ENCRYPTION BYPASSED';
            block.appendChild(solvedMsg);
        }

        container.appendChild(block);
    }
};
