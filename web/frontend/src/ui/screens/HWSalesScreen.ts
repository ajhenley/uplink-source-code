import Phaser from 'phaser';
import { CONFIG } from '../../config';
import { restClient } from '../../net/RestClient';
import { gameState } from '../../net/StateSync';
import { wsClient } from '../../net/WebSocketClient';

/**
 * Hardware Sales screen -- displays all available hardware upgrades
 * for purchase. Unlike the software shop this screen shows all items
 * at once (no pagination) since the hardware catalog is small (~19 items).
 *
 * Purchasing sends a POST to `/api/shop/buy-hardware`.
 */
export class HWSalesScreen {
  private scene: Phaser.Scene;
  private container: Phaser.GameObjects.Container;
  private hardware: Array<{
    index: number;
    name: string;
    type: number;
    cost: number;
    size: number;
    data: number;
    description: string;
  }> = [];

  private balanceText!: Phaser.GameObjects.Text;

  // Layout constants
  private readonly contentWidth = CONFIG.SCREEN_WIDTH;
  private readonly contentHeight =
    CONFIG.SCREEN_HEIGHT - CONFIG.HUD_HEIGHT - CONFIG.CONNECTION_BAR_HEIGHT - 30;
  private readonly boxX = 40;
  private readonly boxY = 10;
  private readonly boxW = CONFIG.SCREEN_WIDTH - 80;
  private readonly boxH =
    CONFIG.SCREEN_HEIGHT - CONFIG.HUD_HEIGHT - CONFIG.CONNECTION_BAR_HEIGHT - 50;

  constructor(
    scene: Phaser.Scene,
    container: Phaser.GameObjects.Container,
    screenData: any
  ) {
    this.scene = scene;
    this.container = container;
    this.hardware = screenData.hardware || [];

    this.buildUI();
  }

  // ── UI Construction ──────────────────────────────────────────────

  private buildUI() {
    const { boxX, boxY, boxW, boxH } = this;

    // Outer border
    const gfx = this.scene.add.graphics();
    gfx.lineStyle(2, CONFIG.COLORS.GREEN, 1);
    gfx.strokeRect(boxX, boxY, boxW, boxH);
    gfx.lineStyle(1, CONFIG.COLORS.GREEN, 0.4);
    gfx.strokeRect(boxX + 4, boxY + 4, boxW - 8, boxH - 8);
    this.container.add(gfx);

    // Title
    const title = this.scene.add.text(
      this.contentWidth / 2,
      boxY + 30,
      'HARDWARE SALES',
      {
        fontFamily: 'Courier New',
        fontSize: '18px',
        color: CONFIG.COLOR_STR.CYAN,
      }
    ).setOrigin(0.5);
    this.container.add(title);

    // Divider under title
    const divider = this.scene.add.graphics();
    divider.lineStyle(1, CONFIG.COLORS.GREEN, 0.5);
    divider.lineBetween(boxX + 20, boxY + 50, boxX + boxW - 20, boxY + 50);
    this.container.add(divider);

    // Column headers
    const headerY = boxY + 65;
    const cols = this.getColumnPositions();

    const headers = [
      { text: 'ITEM', x: cols.name },
      { text: 'COST', x: cols.cost },
      { text: 'ACTION', x: cols.action },
    ];

    for (const h of headers) {
      const ht = this.scene.add.text(h.x, headerY, h.text, {
        fontFamily: 'Courier New',
        fontSize: '12px',
        color: CONFIG.COLOR_STR.GREEN,
      });
      ht.setAlpha(0.7);
      this.container.add(ht);
    }

    // Header underline
    const headerLine = this.scene.add.graphics();
    headerLine.lineStyle(1, CONFIG.COLORS.GREEN, 0.3);
    headerLine.lineBetween(boxX + 20, headerY + 18, boxX + boxW - 20, headerY + 18);
    this.container.add(headerLine);

    // Render all hardware items
    this.renderItems(cols);

    // Balance display (amber)
    this.balanceText = this.scene.add.text(
      boxX + 30,
      boxY + boxH - 55,
      this.getBalanceString(),
      {
        fontFamily: 'Courier New',
        fontSize: '13px',
        color: CONFIG.COLOR_STR.AMBER,
      }
    );
    this.container.add(this.balanceText);

    // BACK TO MENU button
    this.createActionButton(
      'BACK TO MENU',
      boxX + 30,
      boxY + boxH - 30,
      140,
      22,
      () => {
        wsClient.send('screen_action', { action: 'back' });
      }
    );
  }

  private getColumnPositions() {
    const baseX = this.boxX + 30;
    return {
      name: baseX,
      cost: baseX + 400,
      action: baseX + 520,
    };
  }

  // ── Item Rendering ────────────────────────────────────────────────

  private renderItems(cols: ReturnType<typeof this.getColumnPositions>) {
    const startY = this.boxY + 90;
    const rowHeight = 22;

    for (let i = 0; i < this.hardware.length; i++) {
      const item = this.hardware[i];
      const y = startY + i * rowHeight;

      // Name (includes description-style data inline)
      const nameText = this.scene.add.text(cols.name, y, item.name, {
        fontFamily: 'Courier New',
        fontSize: '12px',
        color: CONFIG.COLOR_STR.GREEN,
      });
      this.container.add(nameText);

      // Cost
      const costText = this.scene.add.text(cols.cost, y, `${item.cost}c`, {
        fontFamily: 'Courier New',
        fontSize: '12px',
        color: CONFIG.COLOR_STR.GREEN,
      });
      this.container.add(costText);

      // BUY button
      this.createBuyButton(cols.action, y, item);
    }
  }

  // ── Buy Button ────────────────────────────────────────────────────

  private createBuyButton(
    x: number,
    y: number,
    item: { index: number; name: string }
  ) {
    const btnW = 50;
    const btnH = 18;
    const centerX = x + btnW / 2;
    const centerY = y + btnH / 2 - 1;

    const bg = this.scene.add.graphics();
    bg.lineStyle(1, CONFIG.COLORS.GREEN, 1);
    bg.strokeRect(x, y - 1, btnW, btnH);
    this.container.add(bg);

    const label = this.scene.add.text(centerX, centerY, 'BUY', {
      fontFamily: 'Courier New',
      fontSize: '11px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setOrigin(0.5);
    this.container.add(label);

    const hitArea = this.scene.add
      .rectangle(centerX, centerY, btnW, btnH)
      .setInteractive({ useHandCursor: true })
      .setAlpha(0.001);
    this.container.add(hitArea);

    hitArea.on('pointerover', () => {
      bg.clear();
      bg.fillStyle(CONFIG.COLORS.DARK_GREEN, 1);
      bg.fillRect(x, y - 1, btnW, btnH);
      bg.lineStyle(1, CONFIG.COLORS.CYAN, 1);
      bg.strokeRect(x, y - 1, btnW, btnH);
      label.setColor(CONFIG.COLOR_STR.CYAN);
    });

    hitArea.on('pointerout', () => {
      bg.clear();
      bg.lineStyle(1, CONFIG.COLORS.GREEN, 1);
      bg.strokeRect(x, y - 1, btnW, btnH);
      label.setColor(CONFIG.COLOR_STR.GREEN);
    });

    hitArea.on('pointerdown', () => {
      this.buyItem(item.index, label, bg, x, y, btnW, btnH);
    });
  }

  private async buyItem(
    itemIndex: number,
    label: Phaser.GameObjects.Text,
    bg: Phaser.GameObjects.Graphics,
    x: number,
    y: number,
    btnW: number,
    btnH: number
  ) {
    try {
      const result = await restClient.post<{ balance: number }>(
        '/api/shop/buy-hardware',
        {
          session_id: gameState.sessionId,
          item_index: itemIndex,
        }
      );

      // Update balance
      if (gameState.playerData) {
        gameState.playerData.balance = result.balance;
      }
      this.balanceText.setText(this.getBalanceString());

      // Flash "OK!" in amber
      label.setText('OK!');
      label.setColor(CONFIG.COLOR_STR.AMBER);
      bg.clear();
      bg.lineStyle(1, CONFIG.COLORS.AMBER, 1);
      bg.strokeRect(x, y - 1, btnW, btnH);

      this.scene.time.delayedCall(1200, () => {
        if (label.active) {
          label.setText('BUY');
          label.setColor(CONFIG.COLOR_STR.GREEN);
          bg.clear();
          bg.lineStyle(1, CONFIG.COLORS.GREEN, 1);
          bg.strokeRect(x, y - 1, btnW, btnH);
        }
      });
    } catch (err: any) {
      const msg = err?.message || 'Purchase failed';
      label.setText('ERR');
      label.setColor(CONFIG.COLOR_STR.RED);
      bg.clear();
      bg.lineStyle(1, CONFIG.COLORS.RED, 1);
      bg.strokeRect(x, y - 1, btnW, btnH);

      // Show error in balance area temporarily
      const prevBalance = this.balanceText.text;
      this.balanceText.setText(msg);
      this.balanceText.setColor(CONFIG.COLOR_STR.RED);

      this.scene.time.delayedCall(2000, () => {
        if (label.active) {
          label.setText('BUY');
          label.setColor(CONFIG.COLOR_STR.GREEN);
          bg.clear();
          bg.lineStyle(1, CONFIG.COLORS.GREEN, 1);
          bg.strokeRect(x, y - 1, btnW, btnH);
        }
        if (this.balanceText.active) {
          this.balanceText.setText(prevBalance);
          this.balanceText.setColor(CONFIG.COLOR_STR.AMBER);
        }
      });
    }
  }

  // ── Action Button ─────────────────────────────────────────────────

  private createActionButton(
    label: string,
    x: number,
    y: number,
    w: number,
    h: number,
    onClick: () => void
  ) {
    const bg = this.scene.add.graphics();
    bg.lineStyle(1, CONFIG.COLORS.GREEN, 1);
    bg.strokeRect(x, y, w, h);
    this.container.add(bg);

    const centerX = x + w / 2;
    const centerY = y + h / 2;

    const text = this.scene.add.text(centerX, centerY, label, {
      fontFamily: 'Courier New',
      fontSize: '11px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setOrigin(0.5);
    this.container.add(text);

    const hitArea = this.scene.add
      .rectangle(centerX, centerY, w, h)
      .setInteractive({ useHandCursor: true })
      .setAlpha(0.001);
    this.container.add(hitArea);

    hitArea.on('pointerover', () => {
      bg.clear();
      bg.fillStyle(CONFIG.COLORS.DARK_GREEN, 1);
      bg.fillRect(x, y, w, h);
      bg.lineStyle(1, CONFIG.COLORS.GREEN, 1);
      bg.strokeRect(x, y, w, h);
    });

    hitArea.on('pointerout', () => {
      bg.clear();
      bg.lineStyle(1, CONFIG.COLORS.GREEN, 1);
      bg.strokeRect(x, y, w, h);
    });

    hitArea.on('pointerdown', onClick);
  }

  // ── Helpers ───────────────────────────────────────────────────────

  private getBalanceString(): string {
    const balance = gameState.playerData?.balance ?? 0;
    return `Balance: ${balance}c`;
  }

  // ── Cleanup ───────────────────────────────────────────────────────

  destroy() {
    // All game objects are managed by the container; nothing extra to clean up
  }
}
