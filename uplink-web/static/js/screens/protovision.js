/* ============================================================
   UPLINK WEB - Screen: ProtOVision (Easter Egg)
   A WarGames reference — the WOPR/Joshua system.
   Displays a game selection menu.
   ============================================================ */

const ScreenProtoVision = {

    render(container, data) {
        container.innerHTML = '';

        const block = document.createElement('div');
        block.style.cssText = 'padding:20px;text-align:center;';

        const greeting = document.createElement('div');
        greeting.style.cssText = 'color:var(--primary);font-size:16px;margin-bottom:20px;';
        greeting.textContent = 'GREETINGS PROFESSOR FALKEN.';
        block.appendChild(greeting);

        const subtitle = document.createElement('div');
        subtitle.style.cssText = 'color:var(--text);margin-bottom:20px;';
        subtitle.textContent = data.message || 'SHALL WE PLAY A GAME?';
        block.appendChild(subtitle);

        const games = Array.isArray(data.games) ? data.games : [
            'CHESS', 'CHECKERS', 'BACKGAMMON', 'POKER',
            'FIGHTER COMBAT', 'GUERILLA ENGAGEMENT',
            'DESERT WARFARE', 'AIR-TO-GROUND ACTIONS',
            'THEATERWIDE TACTICAL WARFARE',
            'THEATERWIDE BIOTOXIC AND CHEMICAL WARFARE',
            'GLOBAL THERMONUCLEAR WAR'
        ];

        const list = document.createElement('div');
        list.style.cssText = 'text-align:left;display:inline-block;';

        games.forEach(game => {
            const item = document.createElement('div');
            item.style.cssText = 'padding:3px 16px;color:var(--highlight);cursor:pointer;' +
                'transition:color 0.15s;';
            item.textContent = game;
            item.addEventListener('mouseenter', () => { item.style.color = 'var(--primary)'; });
            item.addEventListener('mouseleave', () => { item.style.color = 'var(--highlight)'; });
            item.addEventListener('click', () => {
                GameSocket.screenAction('select_game', { game: game });
            });
            list.appendChild(item);
        });

        block.appendChild(list);
        container.appendChild(block);
    }
};
