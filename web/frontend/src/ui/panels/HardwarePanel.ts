import Phaser from 'phaser';
import { CONFIG } from '../../config';
import { restClient } from '../../net/RestClient';
import { gameState } from '../../net/StateSync';
import type { GatewayData } from '../../net/MessageTypes';

interface HardwareCatalogItem {
  index: number;
  name: string;
  type: 'cpu' | 'modem' | 'memory' | 'special';
  cost: number;
  value: number;
}

const HARDWARE_CATALOG: HardwareCatalogItem[] = [
  { index: 0, name: 'CPU 20 GHz', type: 'cpu', cost: 250, value: 20 },
  { index: 1, name: 'CPU 60 GHz', type: 'cpu', cost: 1000, value: 60 },
  { index: 2, name: 'CPU 80 GHz', type: 'cpu', cost: 1300, value: 80 },
  { index: 3, name: 'CPU 100 GHz', type: 'cpu', cost: 3000, value: 100 },
  { index: 4, name: 'CPU 120 GHz', type: 'cpu', cost: 5000, value: 120 },
  { index: 5, name: 'CPU 150 GHz', type: 'cpu', cost: 8000, value: 150 },
  { index: 6, name: 'CPU Turbo 200 GHz', type: 'cpu', cost: 12000, value: 200 },
  { index: 7, name: 'Modem 1 Gq/s', type: 'modem', cost: 1000, value: 1 },
  { index: 8, name: 'Modem 2 Gq/s', type: 'modem', cost: 2000, value: 2 },
  { index: 9, name: 'Modem 4 Gq/s', type: 'modem', cost: 4000, value: 4 },
  { index: 10, name: 'Modem 6 Gq/s', type: 'modem', cost: 6000, value: 6 },
  { index: 11, name: 'Modem 8 Gq/s', type: 'modem', cost: 8000, value: 8 },
  { index: 12, name: 'Modem 10 Gq/s', type: 'modem', cost: 10000, value: 10 },
  { index: 13, name: 'Memory 8 Gq', type: 'memory', cost: 3000, value: 8 },
  { index: 14, name: 'Memory 16 Gq', type: 'memory', cost: 5500, value: 16 },
  { index: 15, name: 'Memory 24 Gq', type: 'memory', cost: 8000, value: 24 },
  { index: 16, name: 'Memory 32 Gq', type: 'memory', cost: 11000, value: 32 },
  { index: 17, name: 'Self Destruct', type: 'special', cost: 20000, value: 0 },
  { index: 18, name: 'Motion Sensor', type: 'special', cost: 10000, value: 0 },
];

/**
 * HardwarePanel: a popup overlay showing the hardware upgrade catalog.
 *
 * Lists available CPU, modem, memory, and special hardware upgrades
 * with prices and [BUY] buttons. Items the player already owns or that
 * are inferior to current hardware are greyed out.
 */
export class HardwarePanel {
  private scene: Phaser.Scene;
  private container: Phaser.GameObjects.Container;
  private visible: boolean = false;

  // Current gateway data (set externally before opening)
  private gatewayData: GatewayData | null = null;

  // Callback to refresh gateway panel after purchase
  private onPurchase: (() => void) | null = null;

  // Panel layout constants
  private readonly PANEL_W = 550;
  private readonly PANEL_H = 500;
  private readonly panelX: number;
  private readonly panelY: number;

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
    this.panelX = (CONFIG.SCREEN_WIDTH - this.PANEL_W) / 2;
    this.panelY = (CONFIG.SCREEN_HEIGHT - this.PANEL_H) / 2;

    this.container = scene.add.container(0, 0);
    this.container.setVisible(false);
    this.container.setDepth(210);
  }

  /**
   * Open the panel with gateway data. Optionally provide a callback
   * that fires after a successful purchase (e.g. to refresh the gateway panel).
   */
  open(gateway: GatewayData, onPurchase?: () => void) {
    this.gatewayData = gateway;
    this.onPurchase = onPurchase ?? null;
    this.visible = true;
    this.container.setVisible(true);
    this.render();
  }

  toggle() {
    if (this.visible) {
      this.visible = false;
      this.container.setVisible(false);
    } else {
      // If toggled without data, try to open with last known data
      if (this.gatewayData) {
        this.visible = true;
        this.container.setVisible(true);
        this.render();
      }
    }
  }

  isVisible(): boolean {
    return this.visible;
  }

  private render() {
    this.container.removeAll(true);

    const { panelX: x, panelY: y, PANEL_W: w, PANEL_H: h } = this;

    // Background
    const bg = this.scene.add.graphics();
    bg.fillStyle(0x001100, 0.95);
    bg.fillRect(x, y, w, h);
    bg.lineStyle(2, CONFIG.COLORS.GREEN, 1);
    bg.strokeRect(x, y, w, h);
    bg.lineStyle(1, CONFIG.COLORS.GREEN, 0.4);
    bg.strokeRect(x + 3, y + 3, w - 6, h - 6);
    this.container.add(bg);

    // Title
    const title = this.scene.add.text(x + w / 2, y + 20, 'HARDWARE UPGRADES', {
      fontFamily: 'Courier New',
      fontSize: '16px',
      color: CONFIG.COLOR_STR.CYAN,
    }).setOrigin(0.5);
    this.container.add(title);

    // Divider
    const divider = this.scene.add.graphics();
    divider.lineStyle(1, CONFIG.COLORS.GREEN, 0.5);
    divider.lineBetween(x + 15, y + 38, x + w - 15, y + 38);
    this.container.add(divider);

    // Close button
    this.createCloseButton(x + w - 20, y + 12);

    if (!this.gatewayData) {
      const noData = this.scene.add.text(x + w / 2, y + h / 2, 'No gateway data.', {
        fontFamily: 'Courier New',
        fontSize: '13px',
        color: CONFIG.COLOR_STR.GREEN,
      }).setOrigin(0.5).setAlpha(0.6);
      this.container.add(noData);
      return;
    }

    const gw = this.gatewayData;
    let curY = y + 50;
    const rowH = 22;

    // Render each category
    curY = this.renderCategory('CPU', HARDWARE_CATALOG.filter(i => i.type === 'cpu'), gw.cpu_speed, x, curY, w, rowH);
    curY += 8;
    curY = this.renderCategory('MODEM', HARDWARE_CATALOG.filter(i => i.type === 'modem'), gw.modem_speed, x, curY, w, rowH);
    curY += 8;
    curY = this.renderCategory('MEMORY', HARDWARE_CATALOG.filter(i => i.type === 'memory'), gw.memory_size, x, curY, w, rowH);
    curY += 8;
    this.renderSpecialCategory(gw, x, curY, w, rowH);
  }

  private renderCategory(
    label: string,
    items: HardwareCatalogItem[],
    currentValue: number,
    x: number,
    startY: number,
    w: number,
    rowH: number
  ): number {
    // Category header
    const header = this.scene.add.text(x + 20, startY, label, {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.CYAN,
    });
    this.container.add(header);

    let curY = startY + rowH;

    for (const item of items) {
      const isOwned = item.value <= currentValue;
      this.renderItem(item, isOwned, x, curY, w);
      curY += rowH;
    }

    return curY;
  }

  private renderSpecialCategory(
    gw: GatewayData,
    x: number,
    startY: number,
    w: number,
    rowH: number
  ) {
    const header = this.scene.add.text(x + 20, startY, 'SPECIAL', {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.CYAN,
    });
    this.container.add(header);

    let curY = startY + rowH;
    const specials = HARDWARE_CATALOG.filter(i => i.type === 'special');

    for (const item of specials) {
      const isOwned = (item.name === 'Self Destruct' && gw.has_self_destruct)
        || (item.name === 'Motion Sensor' && gw.has_motion_sensor);
      this.renderItem(item, isOwned, x, curY, w);
      curY += rowH;
    }
  }

  private renderItem(item: HardwareCatalogItem, isOwned: boolean, x: number, curY: number, w: number) {
    const nameColor = isOwned ? '#446644' : CONFIG.COLOR_STR.GREEN;
    const costColor = isOwned ? '#446644' : CONFIG.COLOR_STR.AMBER;

    // Item name
    const nameText = this.scene.add.text(x + 40, curY, item.name, {
      fontFamily: 'Courier New',
      fontSize: '11px',
      color: nameColor,
    });
    this.container.add(nameText);

    // Cost
    const costStr = `${item.cost.toLocaleString()}c`;
    const costText = this.scene.add.text(x + w - 160, curY, costStr, {
      fontFamily: 'Courier New',
      fontSize: '11px',
      color: costColor,
    });
    this.container.add(costText);

    if (isOwned) {
      // Show INSTALLED label
      const installedText = this.scene.add.text(x + w - 60, curY, 'INSTALLED', {
        fontFamily: 'Courier New',
        fontSize: '11px',
        color: '#446644',
      });
      this.container.add(installedText);
    } else {
      // BUY button
      const buyBtn = this.scene.add.text(x + w - 55, curY, '[ BUY ]', {
        fontFamily: 'Courier New',
        fontSize: '11px',
        color: CONFIG.COLOR_STR.GREEN,
      }).setInteractive({ useHandCursor: true });
      this.container.add(buyBtn);

      buyBtn.on('pointerover', () => buyBtn.setColor(CONFIG.COLOR_STR.CYAN));
      buyBtn.on('pointerout', () => buyBtn.setColor(CONFIG.COLOR_STR.GREEN));
      buyBtn.on('pointerdown', () => {
        this.purchaseItem(item, buyBtn);
      });
    }
  }

  private async purchaseItem(item: HardwareCatalogItem, btn: Phaser.GameObjects.Text) {
    btn.disableInteractive();
    btn.setColor(CONFIG.COLOR_STR.AMBER);
    btn.setText('...');

    try {
      const result = await restClient.post<{ balance: number }>(
        '/api/shop/buy-hardware',
        { session_id: gameState.sessionId, item_index: item.index }
      );

      // Update local balance
      if (gameState.playerData) {
        gameState.playerData.balance = result.balance;
      }

      // Re-fetch gateway data and re-render
      if (this.onPurchase) {
        this.onPurchase();
      }

      // Re-fetch gateway data for this panel
      await this.refreshGatewayData();
    } catch (err) {
      console.error('[HardwarePanel] Purchase failed:', err);
      btn.setText('FAIL');
      btn.setColor(CONFIG.COLOR_STR.RED);
    }
  }

  private async refreshGatewayData() {
    try {
      const response = await restClient.get<{ gateway: GatewayData }>(
        `/api/player/${gameState.sessionId}/gateway`
      );
      this.gatewayData = response.gateway;
      this.render();
    } catch (err) {
      console.error('[HardwarePanel] Failed to refresh gateway data:', err);
    }
  }

  private createCloseButton(x: number, y: number) {
    const closeBtn = this.scene.add.text(x, y, 'X', {
      fontFamily: 'Courier New',
      fontSize: '14px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setOrigin(0.5).setInteractive({ useHandCursor: true });
    this.container.add(closeBtn);

    closeBtn.on('pointerover', () => closeBtn.setColor(CONFIG.COLOR_STR.RED));
    closeBtn.on('pointerout', () => closeBtn.setColor(CONFIG.COLOR_STR.GREEN));
    closeBtn.on('pointerdown', () => {
      this.visible = false;
      this.container.setVisible(false);
    });
  }

  destroy() {
    this.container.destroy(true);
  }
}
