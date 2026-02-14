import Phaser from 'phaser';
import { CONFIG } from '../../config';
import { restClient } from '../../net/RestClient';
import { gameState } from '../../net/StateSync';
import { wsClient } from '../../net/WebSocketClient';

/**
 * Software Sales screen -- displays a paginated catalog of software
 * items available for purchase.
 *
 * Data comes from the server as `screenData.software`, an array of
 * software entries. Items are shown 15 per page with navigation
 * buttons. Purchasing sends a POST to `/api/shop/buy-software`.
 */
export class SWSalesScreen {
  private scene: Phaser.Scene;
  private container: Phaser.GameObjects.Container;
  private software: Array<{
    index: number;
    name: string;
    type: number;
    cost: number;
    size: number;
    version: number;
    description: string;
  }> = [];

  private currentPage: number = 0;
  private itemsPerPage: number = 15;
  private totalPages: number = 1;

  // Redrawn each page
  private pageObjects: Phaser.GameObjects.GameObject[] = [];

  // Persistent UI elements
  private balanceText!: Phaser.GameObjects.Text;
  private pageText!: Phaser.GameObjects.Text;

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
    this.software = screenData.software || [];
    this.totalPages = Math.max(1, Math.ceil(this.software.length / this.itemsPerPage));

    this.buildFrame();
    this.renderPage();
  }

  // ── Frame (drawn once) ───────────────────────────────────────────

  private buildFrame() {
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
      'SOFTWARE SALES',
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
      { text: 'VER', x: cols.version },
      { text: 'SIZE', x: cols.size },
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

    // Page indicator
    this.pageText = this.scene.add.text(
      boxX + boxW - 200,
      boxY + boxH - 55,
      this.getPageString(),
      {
        fontFamily: 'Courier New',
        fontSize: '13px',
        color: CONFIG.COLOR_STR.GREEN,
      }
    );
    this.container.add(this.pageText);

    // Prev / Next buttons (beside page indicator)
    this.createNavButton('[<]', boxX + boxW - 90, boxY + boxH - 48, () => {
      if (this.currentPage > 0) {
        this.currentPage--;
        this.renderPage();
      }
    });

    this.createNavButton('[>]', boxX + boxW - 50, boxY + boxH - 48, () => {
      if (this.currentPage < this.totalPages - 1) {
        this.currentPage++;
        this.renderPage();
      }
    });

    // BACK TO MENU button
    this.createActionButton(
      'BACK TO MENU',
      boxX + 30,
      boxY + boxH - 30,
      140,
      22,
      () => {
        // Navigate back via WebSocket (standard pattern for remote screens)
        wsClient.send('screen_action', { action: 'back' });
      }
    );
  }

  private getColumnPositions() {
    const baseX = this.boxX + 30;
    return {
      name: baseX,
      version: baseX + 300,
      size: baseX + 370,
      cost: baseX + 440,
      action: baseX + 530,
    };
  }

  // ── Page Rendering ────────────────────────────────────────────────

  private renderPage() {
    // Clear previous page objects
    for (const obj of this.pageObjects) {
      obj.destroy();
    }
    this.pageObjects = [];

    const startIdx = this.currentPage * this.itemsPerPage;
    const endIdx = Math.min(startIdx + this.itemsPerPage, this.software.length);
    const cols = this.getColumnPositions();
    const startY = this.boxY + 90;
    const rowHeight = 22;

    for (let i = startIdx; i < endIdx; i++) {
      const item = this.software[i];
      const y = startY + (i - startIdx) * rowHeight;

      // Name
      const nameText = this.scene.add.text(cols.name, y, item.name, {
        fontFamily: 'Courier New',
        fontSize: '12px',
        color: CONFIG.COLOR_STR.GREEN,
      });
      this.container.add(nameText);
      this.pageObjects.push(nameText);

      // Version
      const verText = this.scene.add.text(cols.version, y, `v${item.version}`, {
        fontFamily: 'Courier New',
        fontSize: '12px',
        color: CONFIG.COLOR_STR.GREEN,
      });
      this.container.add(verText);
      this.pageObjects.push(verText);

      // Size
      const sizeText = this.scene.add.text(cols.size, y, `${item.size}k`, {
        fontFamily: 'Courier New',
        fontSize: '12px',
        color: CONFIG.COLOR_STR.GREEN,
      });
      this.container.add(sizeText);
      this.pageObjects.push(sizeText);

      // Cost
      const costText = this.scene.add.text(cols.cost, y, `${item.cost}c`, {
        fontFamily: 'Courier New',
        fontSize: '12px',
        color: CONFIG.COLOR_STR.GREEN,
      });
      this.container.add(costText);
      this.pageObjects.push(costText);

      // BUY button
      this.createBuyButton(cols.action, y, item);
    }

    // Update page indicator
    if (this.pageText) {
      this.pageText.setText(this.getPageString());
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
    this.pageObjects.push(bg);

    const label = this.scene.add.text(centerX, centerY, 'BUY', {
      fontFamily: 'Courier New',
      fontSize: '11px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setOrigin(0.5);
    this.container.add(label);
    this.pageObjects.push(label);

    const hitArea = this.scene.add
      .rectangle(centerX, centerY, btnW, btnH)
      .setInteractive({ useHandCursor: true })
      .setAlpha(0.001);
    this.container.add(hitArea);
    this.pageObjects.push(hitArea);

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
        '/api/shop/buy-software',
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

  // ── Navigation / Action Buttons ───────────────────────────────────

  private createNavButton(
    text: string,
    x: number,
    y: number,
    onClick: () => void
  ) {
    const btn = this.scene.add.text(x, y, text, {
      fontFamily: 'Courier New',
      fontSize: '13px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setInteractive({ useHandCursor: true });

    btn.on('pointerover', () => btn.setColor(CONFIG.COLOR_STR.CYAN));
    btn.on('pointerout', () => btn.setColor(CONFIG.COLOR_STR.GREEN));
    btn.on('pointerdown', onClick);

    this.container.add(btn);
  }

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

  private getPageString(): string {
    return `Page ${this.currentPage + 1}/${this.totalPages}`;
  }

  // ── Cleanup ───────────────────────────────────────────────────────

  destroy() {
    for (const obj of this.pageObjects) {
      obj.destroy();
    }
    this.pageObjects = [];
  }
}
