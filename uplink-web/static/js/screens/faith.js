/* ============================================================
   UPLINK WEB - Screen: Faith Counter-Virus
   Plot-related screen for the Faith counter-virus deployment
   interface used in the Arunmor storyline.
   ============================================================ */

const ScreenFaith = {

    render(container, data) {
        container.innerHTML = '';

        const title = document.createElement('div');
        title.className = 'screen-section-title';
        title.textContent = data.title || 'Faith Counter-Virus System';
        container.appendChild(title);

        // Status display
        const statusBlock = document.createElement('div');
        statusBlock.style.padding = '12px 8px';

        if (data.status_message) {
            const msg = document.createElement('div');
            msg.style.cssText = 'color:var(--primary);line-height:1.6;margin-bottom:12px;';
            msg.textContent = data.status_message;
            statusBlock.appendChild(msg);
        }

        // Progress indicator
        if (data.progress != null) {
            const progLabel = document.createElement('div');
            progLabel.className = 'text-dim';
            progLabel.style.cssText = 'font-size:11px;margin-bottom:4px;';
            progLabel.textContent = 'DEPLOYMENT PROGRESS:';
            statusBlock.appendChild(progLabel);

            const progBar = document.createElement('div');
            progBar.style.cssText = 'height:12px;border:1px solid var(--primary);background:var(--bg);';
            const progFill = document.createElement('div');
            progFill.style.cssText = 'height:100%;background:var(--primary);transition:width 0.3s;' +
                'width:' + Math.min(100, data.progress) + '%;';
            progBar.appendChild(progFill);
            statusBlock.appendChild(progBar);

            const progPct = document.createElement('div');
            progPct.style.cssText = 'text-align:right;font-size:11px;color:var(--primary);margin-top:2px;';
            progPct.textContent = Math.round(data.progress) + '%';
            statusBlock.appendChild(progPct);
        }

        container.appendChild(statusBlock);

        // Deploy button
        if (data.can_deploy) {
            const deployBtn = document.createElement('button');
            deployBtn.className = 'terminal-btn';
            deployBtn.style.cssText = 'margin:8px;padding:8px 20px;font-size:14px;';
            deployBtn.textContent = 'DEPLOY FAITH';
            deployBtn.addEventListener('click', () => {
                deployBtn.disabled = true;
                deployBtn.textContent = 'DEPLOYING...';
                GameSocket.screenAction('deploy_faith', {});
            });
            container.appendChild(deployBtn);
        }

        // Infection map
        if (Array.isArray(data.infected_systems) && data.infected_systems.length > 0) {
            const infTitle = document.createElement('div');
            infTitle.className = 'screen-section-title';
            infTitle.textContent = 'Infected Systems';
            container.appendChild(infTitle);

            const list = document.createElement('div');
            list.style.cssText = 'max-height:150px;overflow-y:auto;padding:4px 8px;';
            data.infected_systems.forEach(sys => {
                const item = document.createElement('div');
                item.style.cssText = 'padding:2px 0;color:var(--danger);font-size:11px;';
                item.textContent = sys;
                list.appendChild(item);
            });
            container.appendChild(list);
        }
    }
};
