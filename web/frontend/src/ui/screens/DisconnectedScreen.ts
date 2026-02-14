import Phaser from 'phaser';
import { CONFIG } from '../../config';

/**
 * Shown when the remote computer has terminated the connection or
 * is no longer reachable.
 *
 * Displays a simple "CONNECTION TERMINATED" message in the center
 * of the remote screen overlay.
 *
 * All game objects are added to `container`.
 */
export class DisconnectedScreen {
  private scene: Phaser.Scene;
  private container: Phaser.GameObjects.Container;

  constructor(
    scene: Phaser.Scene,
    container: Phaser.GameObjects.Container,
    _screenData: any
  ) {
    this.scene = scene;
    this.container = container;

    this.buildUI();
  }

  // ── UI Construction ──────────────────────────────────────────────

  private buildUI() {
    const contentWidth = CONFIG.SCREEN_WIDTH;
    const contentHeight =
      CONFIG.SCREEN_HEIGHT - CONFIG.HUD_HEIGHT - CONFIG.CONNECTION_BAR_HEIGHT - 30;

    // Centered box
    const boxW = 460;
    const boxH = 160;
    const boxX = (contentWidth - boxW) / 2;
    const boxY = (contentHeight - boxH) / 2;

    // ── Border ──
    const gfx = this.scene.add.graphics();

    gfx.lineStyle(2, CONFIG.COLORS.RED, 0.8);
    gfx.strokeRect(boxX, boxY, boxW, boxH);

    // Inner double-line effect
    gfx.lineStyle(1, CONFIG.COLORS.RED, 0.3);
    gfx.strokeRect(boxX + 4, boxY + 4, boxW - 8, boxH - 8);

    this.container.add(gfx);

    // ── Title ──
    const titleText = this.scene.add.text(
      contentWidth / 2,
      boxY + 40,
      'CONNECTION TERMINATED',
      {
        fontFamily: 'Courier New',
        fontSize: '20px',
        color: CONFIG.COLOR_STR.RED,
      }
    ).setOrigin(0.5);

    this.container.add(titleText);

    // ── Divider ──
    const divider = this.scene.add.graphics();
    divider.lineStyle(1, CONFIG.COLORS.RED, 0.4);
    divider.lineBetween(boxX + 20, boxY + 65, boxX + boxW - 20, boxY + 65);
    this.container.add(divider);

    // ── Description ──
    const descText = this.scene.add.text(
      contentWidth / 2,
      boxY + 90,
      'The remote system has closed the connection.',
      {
        fontFamily: 'Courier New',
        fontSize: '13px',
        color: CONFIG.COLOR_STR.GREEN,
      }
    ).setOrigin(0.5);

    this.container.add(descText);

    // ── Hint ──
    const hintText = this.scene.add.text(
      contentWidth / 2,
      boxY + 120,
      'Click DISCONNECT in the header to return to the map.',
      {
        fontFamily: 'Courier New',
        fontSize: '11px',
        color: CONFIG.COLOR_STR.GREEN,
      }
    ).setOrigin(0.5);
    hintText.setAlpha(0.5);

    this.container.add(hintText);
  }

  // ── Cleanup ──────────────────────────────────────────────────────

  destroy() {
    // No persistent listeners to clean up.
  }
}
