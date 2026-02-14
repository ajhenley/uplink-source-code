const ThemeManager = {
    themes: {
        green: {
            name: 'Classic Green',
            '--primary': '#00ff41',
            '--secondary': '#00cc33',
            '--dim': '#006622',
            '--highlight': '#00ffff',
        },
        amber: {
            name: 'Amber',
            '--primary': '#ffaa00',
            '--secondary': '#cc8800',
            '--dim': '#664400',
            '--highlight': '#ffdd44',
        },
        blue: {
            name: 'Ice Blue',
            '--primary': '#00aaff',
            '--secondary': '#0088cc',
            '--dim': '#004466',
            '--highlight': '#66ddff',
        },
        red: {
            name: 'Red Alert',
            '--primary': '#ff3333',
            '--secondary': '#cc2222',
            '--dim': '#661111',
            '--highlight': '#ff6666',
        },
        white: {
            name: 'Monochrome',
            '--primary': '#cccccc',
            '--secondary': '#999999',
            '--dim': '#444444',
            '--highlight': '#ffffff',
        }
    },

    _current: 'green',

    init() {
        const saved = localStorage.getItem('uplink-theme');
        if (saved && this.themes[saved]) {
            this._current = saved;
            this._apply(saved);
        }
    },

    toggle() {
        const keys = Object.keys(this.themes);
        const idx = keys.indexOf(this._current);
        const next = keys[(idx + 1) % keys.length];
        this.setTheme(next);
    },

    setTheme(name) {
        if (!this.themes[name]) return;
        this._current = name;
        localStorage.setItem('uplink-theme', name);
        this._apply(name);
        if (typeof App !== 'undefined' && App.showNotification) {
            App.showNotification('Theme: ' + this.themes[name].name, 'info');
        }
    },

    _apply(name) {
        const theme = this.themes[name];
        const root = document.documentElement;
        for (const [prop, val] of Object.entries(theme)) {
            if (prop.startsWith('--')) {
                root.style.setProperty(prop, val);
            }
        }
    },

    getCurrentName() {
        return this.themes[this._current] ? this.themes[this._current].name : 'Classic Green';
    }
};
