/* ============================================================
   UPLINK WEB - Screen: Global Thermonuclear War (Easter Egg)
   WarGames-inspired screen — the only winning move is not
   to play.
   ============================================================ */

const ScreenNuclearWar = {

    render(container, data) {
        container.innerHTML = '';

        const block = document.createElement('div');
        block.style.cssText = 'padding:20px;text-align:center;';

        const title = document.createElement('div');
        title.style.cssText = 'color:var(--danger);font-size:18px;font-weight:700;margin-bottom:20px;' +
            'text-shadow:0 0 8px var(--danger);';
        title.textContent = 'GLOBAL THERMONUCLEAR WAR';
        block.appendChild(title);

        if (data.phase === 'conclusion' || data.learned) {
            const lesson = document.createElement('div');
            lesson.style.cssText = 'color:var(--primary);font-size:14px;margin:30px 0;line-height:1.8;';
            lesson.textContent = 'A STRANGE GAME. THE ONLY WINNING MOVE IS NOT TO PLAY.';
            block.appendChild(lesson);

            const howAbout = document.createElement('div');
            howAbout.style.cssText = 'color:var(--highlight);margin-top:20px;';
            howAbout.textContent = 'HOW ABOUT A NICE GAME OF CHESS?';
            block.appendChild(howAbout);
        } else {
            // Simulation display
            const simLabel = document.createElement('div');
            simLabel.style.cssText = 'color:var(--warning);margin-bottom:12px;';
            simLabel.textContent = 'RUNNING SIMULATION...';
            block.appendChild(simLabel);

            const targets = Array.isArray(data.targets) ? data.targets : [
                'LAS VEGAS', 'SEATTLE', 'NEW YORK', 'MOSCOW', 'LONDON'
            ];

            const targetList = document.createElement('div');
            targetList.style.cssText = 'font-size:11px;color:var(--danger);line-height:1.8;';
            targets.forEach(t => {
                const line = document.createElement('div');
                line.textContent = 'TARGET: ' + t + ' ... IMPACT';
                targetList.appendChild(line);
            });
            block.appendChild(targetList);

            const allOut = document.createElement('div');
            allOut.style.cssText = 'color:var(--danger);font-weight:700;margin-top:16px;font-size:14px;' +
                'text-shadow:0 0 6px var(--danger);';
            allOut.textContent = 'WINNER: NONE';
            block.appendChild(allOut);
        }

        container.appendChild(block);
    }
};
