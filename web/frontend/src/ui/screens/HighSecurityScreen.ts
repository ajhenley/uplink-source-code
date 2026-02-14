import Phaser from 'phaser';
import { CONFIG } from '../../config';
import { wsClient } from '../../net/WebSocketClient';

/**
 * High Security authentication screen.
 *
 * Functionally identical to PasswordScreen but with a more alarming
 * visual treatment: red border, red title, amber warning text, and
 * the label "Enter Security Code:" instead of "Enter Password:".
 *
 * Input handling and submission logic are duplicated from PasswordScreen
 * to keep each screen self-contained.
 */
export class HighSecurityScreen {
  private scene: Phaser.Scene;
  private container: Phaser.GameObjects.Container;
  private typedCode: string = '';
  private codeDisplay!: Phaser.GameObjects.Text;
  private errorText!: Phaser.GameObjects.Text;
  private cursorVisible: boolean = true;
  private cursorTimer!: Phaser.Time.TimerEvent;
  private keydownHandler: ((event: KeyboardEvent) => void) | null = null;

  constructor(
    scene: Phaser.Scene,
    container: Phaser.GameObjects.Container,
    screenData: any
  ) {
    this.scene = scene;
    this.container = container;

    this.buildUI(screenData);
    this.setupKeyboard();
  }

  // ── UI Construction ──────────────────────────────────────────────

  private buildUI(screenData: any) {
    const contentWidth = CONFIG.SCREEN_WIDTH;
    const contentHeight =
      CONFIG.SCREEN_HEIGHT - CONFIG.HUD_HEIGHT - CONFIG.CONNECTION_BAR_HEIGHT - 30;

    // Centered box dimensions
    const boxW = 460;
    const boxH = 280;
    const boxX = (contentWidth - boxW) / 2;
    const boxY = (contentHeight - boxH) / 2;

    // ── Border (red instead of green) ──
    const gfx = this.scene.add.graphics();

    // Outer border -- red
    gfx.lineStyle(2, CONFIG.COLORS.RED, 1);
    gfx.strokeRect(boxX, boxY, boxW, boxH);

    // Double-line effect (inner border)
    gfx.lineStyle(1, CONFIG.COLORS.RED, 0.4);
    gfx.strokeRect(boxX + 4, boxY + 4, boxW - 8, boxH - 8);

    this.container.add(gfx);

    // ── Title: "HIGH SECURITY SYSTEM" in red ──
    const titleText = this.scene.add.text(
      contentWidth / 2,
      boxY + 30,
      'HIGH SECURITY SYSTEM',
      {
        fontFamily: 'Courier New',
        fontSize: '18px',
        color: CONFIG.COLOR_STR.RED,
      }
    ).setOrigin(0.5);
    this.container.add(titleText);

    // ── Divider line under title ──
    const divider = this.scene.add.graphics();
    divider.lineStyle(1, CONFIG.COLORS.RED, 0.5);
    divider.lineBetween(boxX + 20, boxY + 50, boxX + boxW - 20, boxY + 50);
    this.container.add(divider);

    // ── Warning text in amber ──
    const warningText = this.scene.add.text(
      contentWidth / 2,
      boxY + 72,
      'This system requires high-level authorization.',
      {
        fontFamily: 'Courier New',
        fontSize: '13px',
        color: CONFIG.COLOR_STR.AMBER,
      }
    ).setOrigin(0.5);
    this.container.add(warningText);

    // ── Prompt label ──
    const promptText = this.scene.add.text(
      boxX + 30,
      boxY + 105,
      'Enter Security Code:',
      {
        fontFamily: 'Courier New',
        fontSize: '14px',
        color: CONFIG.COLOR_STR.GREEN,
      }
    );
    this.container.add(promptText);

    // ── Code input field (background + text) ──
    const fieldX = boxX + 30;
    const fieldY = boxY + 130;
    const fieldW = boxW - 60;
    const fieldH = 28;

    const fieldGfx = this.scene.add.graphics();
    fieldGfx.fillStyle(0x000000, 1);
    fieldGfx.fillRect(fieldX, fieldY, fieldW, fieldH);
    fieldGfx.lineStyle(1, CONFIG.COLORS.GREEN, 0.8);
    fieldGfx.strokeRect(fieldX, fieldY, fieldW, fieldH);
    this.container.add(fieldGfx);

    this.codeDisplay = this.scene.add.text(
      fieldX + 8,
      fieldY + 7,
      '_',
      {
        fontFamily: 'Courier New',
        fontSize: '14px',
        color: CONFIG.COLOR_STR.GREEN,
      }
    );
    this.container.add(this.codeDisplay);

    // ── Buttons row ──
    const btnY = boxY + 185;
    this.createButton('SUBMIT', contentWidth / 2 - 80, btnY, 120, 30, () => {
      this.submit();
    });
    this.createButton('BYPASS', contentWidth / 2 + 60, btnY, 120, 30, () => {
      // Placeholder for bypass tool integration
      console.log('[HighSecurityScreen] BYPASS button pressed -- not yet implemented');
    }, true);

    // ── Error message area ──
    this.errorText = this.scene.add.text(
      contentWidth / 2,
      boxY + 235,
      '',
      {
        fontFamily: 'Courier New',
        fontSize: '12px',
        color: CONFIG.COLOR_STR.RED,
      }
    ).setOrigin(0.5);
    this.container.add(this.errorText);

    // Show existing error from server if present
    if (screenData.error) {
      this.errorText.setText(`Error: ${screenData.error}`);
    }

    // ── Blinking cursor timer ──
    this.cursorTimer = this.scene.time.addEvent({
      delay: 500,
      loop: true,
      callback: () => {
        this.cursorVisible = !this.cursorVisible;
        this.updateCodeDisplay();
      },
    });
  }

  /**
   * Creates a styled terminal button and adds it to the container.
   * If `dimmed` is true the button appears at lower opacity (placeholder state).
   */
  private createButton(
    label: string,
    x: number,
    y: number,
    w: number,
    h: number,
    onClick: () => void,
    dimmed: boolean = false
  ) {
    const bg = this.scene.add.graphics();
    bg.lineStyle(1, CONFIG.COLORS.GREEN, dimmed ? 0.4 : 1);
    bg.strokeRect(x - w / 2, y - h / 2, w, h);
    this.container.add(bg);

    const text = this.scene.add.text(x, y, label, {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setOrigin(0.5);
    if (dimmed) {
      text.setAlpha(0.4);
    }
    this.container.add(text);

    const hitArea = this.scene.add.rectangle(x, y, w, h)
      .setInteractive({ useHandCursor: true })
      .setAlpha(0.001);
    this.container.add(hitArea);

    hitArea.on('pointerover', () => {
      bg.clear();
      bg.fillStyle(CONFIG.COLORS.DARK_GREEN, 1);
      bg.fillRect(x - w / 2, y - h / 2, w, h);
      bg.lineStyle(1, CONFIG.COLORS.GREEN, 1);
      bg.strokeRect(x - w / 2, y - h / 2, w, h);
      text.setAlpha(1);
    });

    hitArea.on('pointerout', () => {
      bg.clear();
      bg.lineStyle(1, CONFIG.COLORS.GREEN, dimmed ? 0.4 : 1);
      bg.strokeRect(x - w / 2, y - h / 2, w, h);
      if (dimmed) {
        text.setAlpha(0.4);
      }
    });

    hitArea.on('pointerdown', onClick);
  }

  // ── Keyboard Input ───────────────────────────────────────────────

  private setupKeyboard() {
    this.keydownHandler = (event: KeyboardEvent) => {
      this.handleKey(event);
    };
    this.scene.input.keyboard!.on('keydown', this.keydownHandler);
  }

  private handleKey(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      this.submit();
      return;
    }

    if (event.key === 'Backspace') {
      this.typedCode = this.typedCode.slice(0, -1);
      this.updateCodeDisplay();
      return;
    }

    if (event.key === 'Escape') {
      this.typedCode = '';
      this.updateCodeDisplay();
      return;
    }

    // Accept printable characters
    if (event.key.length === 1 && !event.ctrlKey && !event.metaKey) {
      const maxLen = 32;
      if (this.typedCode.length < maxLen) {
        this.typedCode += event.key;
        this.updateCodeDisplay();
      }
    }
  }

  private updateCodeDisplay() {
    const masked = '*'.repeat(this.typedCode.length);
    const cursor = this.cursorVisible ? '_' : '';
    this.codeDisplay.setText(masked + cursor);
  }

  // ── Actions ──────────────────────────────────────────────────────

  private submit() {
    if (this.typedCode.length === 0) {
      this.errorText.setText('Error: Please enter a security code');
      return;
    }

    // Clear any previous error
    this.errorText.setText('');

    wsClient.send('screen_action', {
      action: 'password_submit',
      password: this.typedCode,
    });
  }

  // ── Cleanup ──────────────────────────────────────────────────────

  destroy() {
    // Remove the keyboard listener
    if (this.keydownHandler) {
      this.scene.input.keyboard!.off('keydown', this.keydownHandler);
      this.keydownHandler = null;
    }

    // Stop the cursor blink timer
    if (this.cursorTimer) {
      this.cursorTimer.destroy();
    }
  }
}
