import Phaser from 'phaser';
import { CONFIG } from '../config';
import { restClient } from '../net/RestClient';
import { gameState } from '../net/StateSync';

export class LoginScene extends Phaser.Scene {
  private usernameText = '';
  private passwordText = '';
  private handleText = '';
  private activeField: 'username' | 'password' | 'handle' = 'username';
  private mode: 'login' | 'register' = 'login';
  private statusText!: Phaser.GameObjects.Text;
  private fieldTexts: Record<string, Phaser.GameObjects.Text> = {};
  private cursorBlink = true;

  constructor() {
    super({ key: 'LoginScene' });
  }

  create() {
    const cx = CONFIG.SCREEN_WIDTH / 2;
    const style = {
      fontFamily: 'Courier New',
      fontSize: '14px',
      color: CONFIG.COLOR_STR.GREEN,
    };
    const titleStyle = {
      fontFamily: 'Courier New',
      fontSize: '28px',
      color: CONFIG.COLOR_STR.GREEN,
    };
    const smallStyle = {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.CYAN,
    };

    // Title
    this.add.text(cx, 80, 'U P L I N K', titleStyle).setOrigin(0.5);
    this.add.text(cx, 115, 'Trust is a weakness', {
      ...style, fontSize: '12px', color: '#006622',
    }).setOrigin(0.5);

    // Border
    const gfx = this.add.graphics();
    gfx.lineStyle(1, CONFIG.COLORS.GREEN);
    gfx.strokeRect(cx - 200, 150, 400, this.mode === 'register' ? 320 : 260);

    // Header
    this.add.text(cx, 165, this.mode === 'register' ? 'NEW AGENT REGISTRATION' : 'AGENT LOGIN', {
      ...style, color: CONFIG.COLOR_STR.CYAN,
    }).setOrigin(0.5);

    // Fields
    let y = 200;
    this.add.text(cx - 180, y, 'USERNAME:', style);
    this.fieldTexts['username'] = this.add.text(cx - 60, y, '', style);
    y += 40;

    this.add.text(cx - 180, y, 'PASSWORD:', style);
    this.fieldTexts['password'] = this.add.text(cx - 60, y, '', style);
    y += 40;

    if (this.mode === 'register') {
      this.add.text(cx - 180, y, 'HANDLE:', style);
      this.fieldTexts['handle'] = this.add.text(cx - 60, y, '', style);
      y += 40;
    }

    // Buttons
    const btnY = y + 20;
    this.createButton(cx - 80, btnY, this.mode === 'register' ? 'REGISTER' : 'LOGIN', () => this.submit());
    this.createButton(cx + 80, btnY, this.mode === 'register' ? 'BACK' : 'REGISTER', () => this.toggleMode());

    // Status
    this.statusText = this.add.text(cx, btnY + 50, '', {
      ...style, color: CONFIG.COLOR_STR.AMBER,
    }).setOrigin(0.5);

    // Keyboard input
    this.input.keyboard!.on('keydown', (event: KeyboardEvent) => this.handleKey(event));

    // Cursor blink timer
    this.time.addEvent({
      delay: 500,
      loop: true,
      callback: () => {
        this.cursorBlink = !this.cursorBlink;
        this.updateFields();
      },
    });

    this.add.text(cx, CONFIG.SCREEN_HEIGHT - 40,
      'TAB to switch fields | ENTER to submit',
      smallStyle
    ).setOrigin(0.5);
  }

  private createButton(x: number, y: number, label: string, onClick: () => void) {
    const bg = this.add.graphics();
    const w = 120;
    const h = 30;
    bg.lineStyle(1, CONFIG.COLORS.GREEN);
    bg.strokeRect(x - w / 2, y - h / 2, w, h);

    const text = this.add.text(x, y, label, {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setOrigin(0.5);

    const hitArea = this.add.rectangle(x, y, w, h).setInteractive({ useHandCursor: true });
    hitArea.setAlpha(0.001);

    hitArea.on('pointerover', () => {
      bg.clear();
      bg.fillStyle(CONFIG.COLORS.DARK_GREEN, 1);
      bg.fillRect(x - w / 2, y - h / 2, w, h);
      bg.lineStyle(1, CONFIG.COLORS.GREEN);
      bg.strokeRect(x - w / 2, y - h / 2, w, h);
    });

    hitArea.on('pointerout', () => {
      bg.clear();
      bg.lineStyle(1, CONFIG.COLORS.GREEN);
      bg.strokeRect(x - w / 2, y - h / 2, w, h);
    });

    hitArea.on('pointerdown', onClick);
  }

  private handleKey(event: KeyboardEvent) {
    if (event.key === 'Tab') {
      event.preventDefault();
      const fields: Array<'username' | 'password' | 'handle'> = this.mode === 'register'
        ? ['username', 'password', 'handle']
        : ['username', 'password'];
      const idx = fields.indexOf(this.activeField);
      this.activeField = fields[(idx + 1) % fields.length];
      return;
    }

    if (event.key === 'Enter') {
      this.submit();
      return;
    }

    if (event.key === 'Backspace') {
      if (this.activeField === 'username') this.usernameText = this.usernameText.slice(0, -1);
      else if (this.activeField === 'password') this.passwordText = this.passwordText.slice(0, -1);
      else if (this.activeField === 'handle') this.handleText = this.handleText.slice(0, -1);
      this.updateFields();
      return;
    }

    if (event.key.length === 1 && !event.ctrlKey && !event.metaKey) {
      const maxLen = 24;
      if (this.activeField === 'username' && this.usernameText.length < maxLen)
        this.usernameText += event.key;
      else if (this.activeField === 'password' && this.passwordText.length < maxLen)
        this.passwordText += event.key;
      else if (this.activeField === 'handle' && this.handleText.length < maxLen)
        this.handleText += event.key;
      this.updateFields();
    }
  }

  private updateFields() {
    const cursor = this.cursorBlink ? '_' : '';
    if (this.fieldTexts['username'])
      this.fieldTexts['username'].setText(
        this.usernameText + (this.activeField === 'username' ? cursor : '')
      );
    if (this.fieldTexts['password'])
      this.fieldTexts['password'].setText(
        '*'.repeat(this.passwordText.length) + (this.activeField === 'password' ? cursor : '')
      );
    if (this.fieldTexts['handle'])
      this.fieldTexts['handle'].setText(
        this.handleText + (this.activeField === 'handle' ? cursor : '')
      );
  }

  private showGameSelection(games: Array<{ id: string; name: string; updated_at?: string }>) {
    // Clear existing scene content and show game list
    this.children.removeAll(true);

    const cx = CONFIG.SCREEN_WIDTH / 2;
    const style = {
      fontFamily: 'Courier New',
      fontSize: '14px',
      color: CONFIG.COLOR_STR.GREEN,
    };
    const smallStyle = {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.CYAN,
    };

    this.add.text(cx, 80, 'SELECT GAME SESSION', {
      fontFamily: 'Courier New',
      fontSize: '24px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setOrigin(0.5);

    // Border
    const gfx = this.add.graphics();
    const listHeight = games.length * 40 + 80;
    gfx.lineStyle(1, CONFIG.COLORS.GREEN);
    gfx.strokeRect(cx - 250, 120, 500, listHeight);

    let y = 140;
    for (const game of games) {
      const label = game.name || game.id;
      const updated = game.updated_at ? ` (${game.updated_at})` : '';
      const entryText = this.add.text(cx - 220, y, `> ${label}${updated}`, style)
        .setInteractive({ useHandCursor: true });

      entryText.on('pointerover', () => entryText.setColor(CONFIG.COLOR_STR.CYAN));
      entryText.on('pointerout', () => entryText.setColor(CONFIG.COLOR_STR.GREEN));
      entryText.on('pointerdown', () => {
        gameState.sessionId = game.id;
        this.scene.start('MainGameScene');
      });

      y += 40;
    }

    // NEW GAME button at the bottom
    const newGameY = y + 20;
    this.createButton(cx, newGameY, 'NEW GAME', () => {
      this.mode = 'register';
      this.scene.restart();
    });

    this.add.text(cx, CONFIG.SCREEN_HEIGHT - 40,
      'Click a session to load or create a new game',
      smallStyle
    ).setOrigin(0.5);
  }

  private toggleMode() {
    this.mode = this.mode === 'login' ? 'register' : 'login';
    this.scene.restart();
  }

  private async submit() {
    if (!this.usernameText || !this.passwordText) {
      this.statusText.setText('Please fill in all fields');
      return;
    }

    if (this.mode === 'register' && !this.handleText) {
      this.statusText.setText('Please enter an agent handle');
      return;
    }

    this.statusText.setText('Connecting...');

    try {
      interface AuthResponse {
        access_token: string;
        user_id: number;
        username: string;
      }
      interface GameResponse {
        session: { id: string };
        player_id: number;
      }

      if (this.mode === 'register') {
        // Register + create new game
        const auth = await restClient.post<AuthResponse>('/api/auth/register', {
          username: this.usernameText,
          password: this.passwordText,
        });
        restClient.setToken(auth.access_token);
        gameState.token = auth.access_token;

        const game = await restClient.post<GameResponse>('/api/game/new', {
          player_name: this.usernameText,
          handle: this.handleText,
        });
        gameState.sessionId = game.session.id;

        this.scene.start('MainGameScene');
      } else {
        // Login + load existing or create new game
        const auth = await restClient.post<AuthResponse>('/api/auth/login', {
          username: this.usernameText,
          password: this.passwordText,
        });
        restClient.setToken(auth.access_token);
        gameState.token = auth.access_token;

        // Check for existing games
        interface GameListEntry {
          id: string;
          name: string;
          updated_at?: string;
        }
        const games = await restClient.get<GameListEntry[]>('/api/game/list');
        if (games.length === 1) {
          // Auto-load the only game
          gameState.sessionId = games[0].id;
          this.scene.start('MainGameScene');
        } else if (games.length > 1) {
          // Show game selection list
          this.showGameSelection(games);
        } else {
          // No games, switch to register mode for handle entry
          this.statusText.setText('No saved games. Please register as a new agent.');
          this.mode = 'register';
          this.scene.restart();
        }
      }
    } catch (err) {
      this.statusText.setText(`Error: ${(err as Error).message}`);
    }
  }
}
