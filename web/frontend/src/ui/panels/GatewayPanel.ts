import Phaser from 'phaser';
import { CONFIG } from '../../config';
import { restClient } from '../../net/RestClient';
import { gameState } from '../../net/StateSync';
import type { GatewayResponse, GatewayData, GatewayFileData } from '../../net/MessageTypes';
import { HardwarePanel } from './HardwarePanel';

/**
 * GatewayPanel: a popup overlay showing the player's gateway hardware,
 * memory usage, and file list.
 *
 * Opened via the HUD "Hardware" toolbar button. Fetches gateway data
 * from the REST API and displays hardware specs, a memory bar, and
 * a list of files with delete buttons.
 */
export class GatewayPanel {
  private scene: Phaser.Scene;
  private container: Phaser.GameObjects.Container;
  private visible: boolean = false;

  // Cached response data
  private gatewayResponse: GatewayResponse | null = null;

  // Reference to the hardware upgrade panel
  private hardwarePanel: HardwarePanel;

  // Callback to update balance display in HUD
  private onBalanceChange: ((amount: number) => void) | null = null;

  // Panel layout constants
  private readonly PANEL_W = 600;
  private readonly PANEL_H = 500;
  private readonly panelX: number;
  private readonly panelY: number;

  constructor(scene: Phaser.Scene, hardwarePanel: HardwarePanel, onBalanceChange?: (amount: number) => void) {
    this.scene = scene;
    this.hardwarePanel = hardwarePanel;
    this.onBalanceChange = onBalanceChange ?? null;
    this.panelX = (CONFIG.SCREEN_WIDTH - this.PANEL_W) / 2;
    this.panelY = (CONFIG.SCREEN_HEIGHT - this.PANEL_H) / 2;

    this.container = scene.add.container(0, 0);
    this.container.setVisible(false);
    this.container.setDepth(200);
  }

  toggle() {
    this.visible = !this.visible;
    this.container.setVisible(this.visible);
    if (this.visible) {
      this.fetchAndRender();
    }
  }

  isVisible(): boolean {
    return this.visible;
  }

  async refresh() {
    await this.fetchAndRender();
  }

  private async fetchAndRender() {
    try {
      const response = await restClient.get<GatewayResponse>(
        `/api/player/${gameState.sessionId}/gateway`
      );
      this.gatewayResponse = response;
    } catch (err) {
      console.error('[GatewayPanel] Failed to fetch gateway data:', err);
    }
    this.render();
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
    const title = this.scene.add.text(x + w / 2, y + 20, 'GATEWAY', {
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

    if (!this.gatewayResponse) {
      const loading = this.scene.add.text(x + w / 2, y + h / 2, 'Loading...', {
        fontFamily: 'Courier New',
        fontSize: '13px',
        color: CONFIG.COLOR_STR.GREEN,
      }).setOrigin(0.5).setAlpha(0.6);
      this.container.add(loading);
      return;
    }

    const gw = this.gatewayResponse.gateway;
    const files = this.gatewayResponse.files;
    const memUsed = this.gatewayResponse.memory_used;
    const memTotal = this.gatewayResponse.memory_total;

    // Subtitle: gateway name
    const subtitle = this.scene.add.text(x + w / 2, y + 52, `Gateway ${gw.name}`, {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setOrigin(0.5).setAlpha(0.8);
    this.container.add(subtitle);

    // Hardware specs section
    const labelStyle = {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.GREEN,
    };
    const valueStyle = {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.AMBER,
    };

    const specStartY = y + 78;
    const specLabelX = x + 30;
    const specValueX = x + 180;

    // CPU
    this.container.add(
      this.scene.add.text(specLabelX, specStartY, 'CPU:', labelStyle)
    );
    this.container.add(
      this.scene.add.text(specValueX, specStartY, `${gw.cpu_speed} GHz`, valueStyle)
    );

    // Modem
    this.container.add(
      this.scene.add.text(specLabelX, specStartY + 20, 'Modem:', labelStyle)
    );
    this.container.add(
      this.scene.add.text(specValueX, specStartY + 20, `${gw.modem_speed} Gq/s`, valueStyle)
    );

    // Memory with bar
    this.container.add(
      this.scene.add.text(specLabelX, specStartY + 40, 'Memory:', labelStyle)
    );

    const memBar = this.buildMemoryBar(memUsed, memTotal);
    this.container.add(
      this.scene.add.text(specValueX, specStartY + 40, `${memUsed} / ${memTotal} Gq  ${memBar}`, valueStyle)
    );

    // UPGRADES button
    const upgradeBtn = this.scene.add.text(x + w - 40, specStartY + 10, '[ UPGRADES ]', {
      fontFamily: 'Courier New',
      fontSize: '11px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setOrigin(1, 0).setInteractive({ useHandCursor: true });
    this.container.add(upgradeBtn);

    upgradeBtn.on('pointerover', () => upgradeBtn.setColor(CONFIG.COLOR_STR.CYAN));
    upgradeBtn.on('pointerout', () => upgradeBtn.setColor(CONFIG.COLOR_STR.GREEN));
    upgradeBtn.on('pointerdown', () => {
      this.hardwarePanel.open(gw, () => {
        // After purchase, refresh this panel and update HUD balance
        this.fetchAndRender();
        if (this.onBalanceChange && gameState.playerData) {
          this.onBalanceChange(gameState.playerData.balance);
        }
      });
    });

    // File list section divider
    const fileDivY = specStartY + 70;
    const fileDivGfx = this.scene.add.graphics();
    fileDivGfx.lineStyle(1, CONFIG.COLORS.GREEN, 0.5);
    fileDivGfx.lineBetween(x + 15, fileDivY, x + w - 15, fileDivY);
    this.container.add(fileDivGfx);

    const fileHeaderY = fileDivY + 8;
    this.container.add(
      this.scene.add.text(x + 30, fileHeaderY, 'FILES', {
        fontFamily: 'Courier New',
        fontSize: '12px',
        color: CONFIG.COLOR_STR.CYAN,
      })
    );

    // File list
    const fileStartY = fileHeaderY + 22;
    const fileRowH = 24;
    const maxVisibleFiles = Math.floor((y + h - fileStartY - 50) / fileRowH);

    if (files.length === 0) {
      const empty = this.scene.add.text(x + w / 2, fileStartY + 20, 'No files on gateway.', {
        fontFamily: 'Courier New',
        fontSize: '11px',
        color: CONFIG.COLOR_STR.GREEN,
      }).setOrigin(0.5).setAlpha(0.6);
      this.container.add(empty);
    } else {
      const visibleFiles = files.slice(0, maxVisibleFiles);
      for (let i = 0; i < visibleFiles.length; i++) {
        const file = visibleFiles[i];
        const rowY = fileStartY + i * fileRowH;
        this.renderFileRow(file, x + 30, rowY, w - 60);
      }

      if (files.length > maxVisibleFiles) {
        const moreText = this.scene.add.text(
          x + w / 2,
          fileStartY + maxVisibleFiles * fileRowH + 4,
          `... and ${files.length - maxVisibleFiles} more files`,
          {
            fontFamily: 'Courier New',
            fontSize: '10px',
            color: CONFIG.COLOR_STR.GREEN,
          }
        ).setOrigin(0.5).setAlpha(0.5);
        this.container.add(moreText);
      }
    }

    // Special features at the bottom
    this.renderSpecialFeatures(gw, x, y + h - 40, w);
  }

  private renderFileRow(file: GatewayFileData, x: number, y: number, w: number) {
    // File name
    const nameText = this.scene.add.text(x, y, file.filename, {
      fontFamily: 'Courier New',
      fontSize: '11px',
      color: CONFIG.COLOR_STR.GREEN,
    });
    this.container.add(nameText);

    // File size
    const sizeText = this.scene.add.text(x + w - 100, y, `[${file.size} Gq]`, {
      fontFamily: 'Courier New',
      fontSize: '11px',
      color: CONFIG.COLOR_STR.AMBER,
    });
    this.container.add(sizeText);

    // DEL button
    const delBtn = this.scene.add.text(x + w - 30, y, '[DEL]', {
      fontFamily: 'Courier New',
      fontSize: '11px',
      color: CONFIG.COLOR_STR.RED,
    }).setInteractive({ useHandCursor: true });
    this.container.add(delBtn);

    delBtn.on('pointerover', () => delBtn.setColor(CONFIG.COLOR_STR.AMBER));
    delBtn.on('pointerout', () => delBtn.setColor(CONFIG.COLOR_STR.RED));
    delBtn.on('pointerdown', () => {
      this.deleteFile(file.id, delBtn);
    });
  }

  private async deleteFile(fileId: number, btn: Phaser.GameObjects.Text) {
    btn.disableInteractive();
    btn.setText('...');
    btn.setColor(CONFIG.COLOR_STR.AMBER);

    try {
      await restClient.delete(
        `/api/player/${gameState.sessionId}/gateway/files/${fileId}`
      );
      // Refresh the panel
      await this.fetchAndRender();
    } catch (err) {
      console.error('[GatewayPanel] Failed to delete file:', err);
      btn.setText('ERR');
      btn.setColor(CONFIG.COLOR_STR.RED);
    }
  }

  private renderSpecialFeatures(gw: GatewayData, x: number, y: number, w: number) {
    const features: string[] = [];
    if (gw.has_self_destruct) features.push('Self Destruct');
    if (gw.has_motion_sensor) features.push('Motion Sensor');

    if (features.length > 0) {
      const featureStr = 'Special: ' + features.join(', ');
      const featureText = this.scene.add.text(x + w / 2, y, featureStr, {
        fontFamily: 'Courier New',
        fontSize: '11px',
        color: CONFIG.COLOR_STR.AMBER,
      }).setOrigin(0.5);
      this.container.add(featureText);
    }
  }

  private buildMemoryBar(used: number, total: number): string {
    const barLen = 8;
    const filledLen = total > 0 ? Math.round((used / total) * barLen) : 0;
    const emptyLen = barLen - filledLen;
    return '[' + '='.repeat(filledLen) + '-'.repeat(emptyLen) + ']';
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

  getHardwarePanel(): HardwarePanel {
    return this.hardwarePanel;
  }

  destroy() {
    this.hardwarePanel.destroy();
    this.container.destroy(true);
  }
}
