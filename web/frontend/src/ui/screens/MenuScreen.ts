import Phaser from 'phaser';
import { CONFIG } from '../../config';
import { wsClient } from '../../net/WebSocketClient';

interface MenuOption {
  label: string;
  screen_index: number;
}

/**
 * Post-login navigation menu screen.
 *
 * Displays the list of services available on the connected computer
 * (File Server, Log Server, BBS, etc.). Each option is a clickable
 * line that highlights on hover and sends a `menu_select` action
 * on click.
 *
 * All game objects are added to `container`.
 */
export class MenuScreen {
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
    const options: MenuOption[] = screenData.menu_options || [];

    const contentWidth = CONFIG.SCREEN_WIDTH;
    const contentHeight =
      CONFIG.SCREEN_HEIGHT - CONFIG.HUD_HEIGHT - CONFIG.CONNECTION_BAR_HEIGHT - 30;

    // Dynamic box height based on number of options
    const lineHeight = 32;
    const paddingTop = 70;   // space for title + divider
    const paddingBottom = 30;
    const boxH = paddingTop + options.length * lineHeight + paddingBottom;
    const minBoxH = 180;
    const finalBoxH = Math.max(boxH, minBoxH);

    const boxW = 460;
    const boxX = (contentWidth - boxW) / 2;
    const boxY = (contentHeight - finalBoxH) / 2;

    // ── Border ──
    const gfx = this.scene.add.graphics();

    gfx.lineStyle(2, CONFIG.COLORS.GREEN, 1);
    gfx.strokeRect(boxX, boxY, boxW, finalBoxH);

    // Inner double-line effect
    gfx.lineStyle(1, CONFIG.COLORS.GREEN, 0.4);
    gfx.strokeRect(boxX + 4, boxY + 4, boxW - 8, finalBoxH - 8);

    this.container.add(gfx);

    // ── Title: "SYSTEM MENU" ──
    const titleText = this.scene.add.text(
      contentWidth / 2,
      boxY + 30,
      'SYSTEM MENU',
      {
        fontFamily: 'Courier New',
        fontSize: '18px',
        color: CONFIG.COLOR_STR.CYAN,
      }
    ).setOrigin(0.5);

    this.container.add(titleText);

    // ── Divider ──
    const divider = this.scene.add.graphics();
    divider.lineStyle(1, CONFIG.COLORS.GREEN, 0.5);
    divider.lineBetween(boxX + 20, boxY + 50, boxX + boxW - 20, boxY + 50);
    this.container.add(divider);

    // ── Menu options ──
    if (options.length === 0) {
      const emptyText = this.scene.add.text(
        contentWidth / 2,
        boxY + paddingTop + 10,
        'No services available.',
        {
          fontFamily: 'Courier New',
          fontSize: '13px',
          color: CONFIG.COLOR_STR.GREEN,
        }
      ).setOrigin(0.5);
      emptyText.setAlpha(0.6);
      this.container.add(emptyText);
      return;
    }

    const optionStartY = boxY + paddingTop;

    for (let i = 0; i < options.length; i++) {
      const option = options[i];
      const itemY = optionStartY + i * lineHeight;

      this.createMenuOption(option, boxX + 30, itemY, boxW - 60);
    }
  }

  /**
   * Creates a single clickable menu option row.
   */
  private createMenuOption(
    option: MenuOption,
    x: number,
    y: number,
    rowWidth: number
  ) {
    // Row highlight background (hidden by default)
    const rowBg = this.scene.add.graphics();
    this.container.add(rowBg);

    // Option text with ">" prefix
    const text = this.scene.add.text(x + 8, y + 5, `> ${option.label}`, {
      fontFamily: 'Courier New',
      fontSize: '14px',
      color: CONFIG.COLOR_STR.GREEN,
    });
    this.container.add(text);

    // Invisible hit area covering the full row width
    const hitArea = this.scene.add.rectangle(
      x + rowWidth / 2,
      y + lineHeightHalf(),
      rowWidth,
      28
    )
      .setInteractive({ useHandCursor: true })
      .setAlpha(0.001);
    this.container.add(hitArea);

    hitArea.on('pointerover', () => {
      text.setColor(CONFIG.COLOR_STR.CYAN);
      rowBg.clear();
      rowBg.fillStyle(CONFIG.COLORS.DARK_GREEN, 0.6);
      rowBg.fillRect(x, y + 1, rowWidth, 26);
    });

    hitArea.on('pointerout', () => {
      text.setColor(CONFIG.COLOR_STR.GREEN);
      rowBg.clear();
    });

    hitArea.on('pointerdown', () => {
      wsClient.send('screen_action', {
        action: 'menu_select',
        screen_index: option.screen_index,
      });
    });
  }

  // ── Cleanup ──────────────────────────────────────────────────────

  destroy() {
    // No persistent listeners to clean up; all game objects are
    // managed by the container and destroyed with removeAll(true).
  }
}

// ── Helpers ──────────────────────────────────────────────────────────

/** Half the visual row height for centering the hit area. */
function lineHeightHalf(): number {
  return 14;
}
