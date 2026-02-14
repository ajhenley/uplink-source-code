import Phaser from 'phaser';
import { CONFIG } from '../../config';
import { wsClient } from '../../net/WebSocketClient';

/**
 * System message / public announcement screen.
 *
 * Displays a simple text message from the remote computer (e.g. a
 * welcome banner or public notice). A CONTINUE button navigates
 * to the next screen if one is specified, otherwise sends go_back.
 *
 * All game objects are added to `container`.
 */
export class MessageScreen {
  private scene: Phaser.Scene;
  private container: Phaser.GameObjects.Container;

  constructor(
    scene: Phaser.Scene,
    container: Phaser.GameObjects.Container,
    screenData: any
  ) {
    this.scene = scene;
    this.container = container;

    this.buildUI(screenData);
  }

  // ── UI Construction ──────────────────────────────────────────────

  private buildUI(screenData: any) {
    const message: string = screenData.message || '';
    const nextScreenIndex: number | undefined = screenData.next_screen_index;

    const contentWidth = CONFIG.SCREEN_WIDTH;
    const contentHeight =
      CONFIG.SCREEN_HEIGHT - CONFIG.HUD_HEIGHT - CONFIG.CONNECTION_BAR_HEIGHT - 30;

    // Box dimensions
    const boxW = 560;
    const boxX = (contentWidth - boxW) / 2;

    // We need to estimate the message height to size the box.
    // Create a temporary text to measure, then destroy it.
    const tempText = this.scene.add.text(0, 0, message, {
      fontFamily: 'Courier New',
      fontSize: '13px',
      wordWrap: { width: boxW - 60 },
    });
    const messageHeight = Math.max(tempText.height, 20);
    tempText.destroy();

    const headerAreaH = 70;  // title + divider
    const footerAreaH = 50;  // continue button
    const paddingV = 40;     // vertical padding around message body
    const boxH = Math.min(
      Math.max(headerAreaH + messageHeight + paddingV + footerAreaH, 200),
      contentHeight - 40
    );
    const boxY = (contentHeight - boxH) / 2;

    // ── Border ──
    const gfx = this.scene.add.graphics();
    gfx.lineStyle(2, CONFIG.COLORS.GREEN, 1);
    gfx.strokeRect(boxX, boxY, boxW, boxH);
    gfx.lineStyle(1, CONFIG.COLORS.GREEN, 0.4);
    gfx.strokeRect(boxX + 4, boxY + 4, boxW - 8, boxH - 8);
    this.container.add(gfx);

    // ── Title ──
    const titleText = this.scene.add.text(
      contentWidth / 2,
      boxY + 28,
      'SYSTEM MESSAGE',
      {
        fontFamily: 'Courier New',
        fontSize: '18px',
        color: CONFIG.COLOR_STR.CYAN,
      }
    ).setOrigin(0.5);
    this.container.add(titleText);

    // ── Divider below title ──
    const divider = this.scene.add.graphics();
    divider.lineStyle(1, CONFIG.COLORS.GREEN, 0.5);
    divider.lineBetween(boxX + 20, boxY + 48, boxX + boxW - 20, boxY + 48);
    this.container.add(divider);

    // ── Message body ──
    const bodyText = this.scene.add.text(
      boxX + 30,
      boxY + 60,
      message,
      {
        fontFamily: 'Courier New',
        fontSize: '13px',
        color: CONFIG.COLOR_STR.GREEN,
        wordWrap: { width: boxW - 60 },
        lineSpacing: 4,
      }
    );
    this.container.add(bodyText);

    // ── Continue button ──
    this.createContinueButton(contentWidth / 2, boxY + boxH - 25, nextScreenIndex);
  }

  /**
   * Creates the "CONTINUE" button. If a next_screen_index is provided,
   * clicking navigates to that screen; otherwise sends go_back.
   */
  private createContinueButton(
    x: number,
    y: number,
    nextScreenIndex: number | undefined
  ) {
    const text = this.scene.add.text(x, y, '[ CONTINUE ]', {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setOrigin(0.5);
    this.container.add(text);

    text.setInteractive({ useHandCursor: true });

    text.on('pointerover', () => {
      text.setColor(CONFIG.COLOR_STR.CYAN);
    });

    text.on('pointerout', () => {
      text.setColor(CONFIG.COLOR_STR.GREEN);
    });

    text.on('pointerdown', () => {
      if (nextScreenIndex !== undefined) {
        wsClient.send('screen_action', {
          action: 'menu_select',
          screen_index: nextScreenIndex,
        });
      } else {
        wsClient.send('screen_action', { action: 'go_back' });
      }
    });
  }

  // ── Cleanup ──────────────────────────────────────────────────────

  destroy() {
    // No persistent listeners to clean up; all game objects are
    // managed by the container and destroyed with removeAll(true).
  }
}
