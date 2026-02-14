/* ============================================================
   UPLINK WEB - Screen: Disconnected
   Shown when the player is disconnected from a remote system,
   either voluntarily or due to trace/security.
   ============================================================ */

const ScreenDisconnected = {

    render(container, data) {
        container.innerHTML = '';

        const block = document.createElement('div');
        block.style.cssText = 'text-align:center;padding:40px 20px;';

        const icon = document.createElement('div');
        icon.style.cssText = 'font-size:24px;color:var(--danger);margin-bottom:16px;';
        icon.textContent = '[ DISCONNECTED ]';
        block.appendChild(icon);

        const reason = document.createElement('div');
        reason.style.cssText = 'color:var(--text);margin-bottom:20px;line-height:1.6;';
        reason.textContent = data.reason || data.message || 'Connection to remote system has been terminated.';
        block.appendChild(reason);

        if (data.traced) {
            const warning = document.createElement('div');
            warning.style.cssText = 'color:var(--danger);font-weight:700;margin-bottom:12px;';
            warning.textContent = 'WARNING: Your connection was traced!';
            block.appendChild(warning);
        }

        container.appendChild(block);
    }
};
