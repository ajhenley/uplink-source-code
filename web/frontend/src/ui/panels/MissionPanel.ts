import Phaser from 'phaser';
import { CONFIG } from '../../config';
import { restClient } from '../../net/RestClient';
import { wsClient } from '../../net/WebSocketClient';
import { gameState } from '../../net/StateSync';
import type { MissionData } from '../../net/MessageTypes';

/**
 * MissionPanel: a popup overlay showing accepted missions and their status.
 *
 * Opened via the HUD "Status" toolbar button. Fetches active missions
 * from the REST API and displays them as cards with a COMPLETE button.
 */
export class MissionPanel {
  private scene: Phaser.Scene;
  private container: Phaser.GameObjects.Container;
  private visible: boolean = false;

  // Panel layout constants
  private readonly PANEL_W = 550;
  private readonly PANEL_H = 400;
  private readonly panelX: number;
  private readonly panelY: number;

  // Flash effect timer
  private flashTimer: Phaser.Time.TimerEvent | null = null;

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
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
      this.refresh();
    }
  }

  isVisible(): boolean {
    return this.visible;
  }

  async refresh() {
    try {
      const missions = await restClient.get<MissionData[]>(
        `/api/player/${gameState.sessionId}/missions`
      );
      gameState.setAcceptedMissions(missions);
    } catch (err) {
      console.error('[MissionPanel] Failed to fetch missions:', err);
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
    const title = this.scene.add.text(x + w / 2, y + 20, 'ACTIVE MISSIONS', {
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

    // Mission cards
    const missions = gameState.acceptedMissions;
    const cardStartY = y + 50;
    const cardH = 70;
    const cardGap = 8;
    const maxVisible = Math.floor((h - 80) / (cardH + cardGap));

    if (missions.length === 0) {
      const empty = this.scene.add.text(x + w / 2, cardStartY + 40, 'No active missions.', {
        fontFamily: 'Courier New',
        fontSize: '13px',
        color: CONFIG.COLOR_STR.GREEN,
      }).setOrigin(0.5).setAlpha(0.6);
      this.container.add(empty);
    } else {
      const visibleMissions = missions.slice(0, maxVisible);
      for (let i = 0; i < visibleMissions.length; i++) {
        const mission = visibleMissions[i];
        const cardY = cardStartY + i * (cardH + cardGap);
        this.renderMissionCard(mission, x + 15, cardY, w - 30, cardH);
      }
    }
  }

  private renderMissionCard(mission: MissionData, x: number, y: number, w: number, h: number) {
    // Card border
    const cardGfx = this.scene.add.graphics();
    cardGfx.lineStyle(1, CONFIG.COLORS.GREEN, 0.6);
    cardGfx.strokeRect(x, y, w, h);
    this.container.add(cardGfx);

    // Description (truncated)
    const maxDescLen = 55;
    const displayDesc = mission.description.length > maxDescLen
      ? mission.description.substring(0, maxDescLen - 3) + '...'
      : mission.description;

    const descText = this.scene.add.text(x + 10, y + 8, displayDesc, {
      fontFamily: 'Courier New',
      fontSize: '11px',
      color: CONFIG.COLOR_STR.GREEN,
    });
    this.container.add(descText);

    // Employer and payment
    const paymentStr = `${mission.payment.toLocaleString()}c`;
    const detailText = this.scene.add.text(
      x + 10,
      y + 26,
      `Employer: ${mission.employer_name}    Payment: ${paymentStr}`,
      {
        fontFamily: 'Courier New',
        fontSize: '10px',
        color: CONFIG.COLOR_STR.AMBER,
      }
    );
    this.container.add(detailText);

    // Status
    const statusStr = mission.is_completed ? 'COMPLETED' : 'IN PROGRESS';
    const statusColor = mission.is_completed ? CONFIG.COLOR_STR.CYAN : CONFIG.COLOR_STR.GREEN;
    const statusText = this.scene.add.text(x + 10, y + 44, `Status: ${statusStr}`, {
      fontFamily: 'Courier New',
      fontSize: '10px',
      color: statusColor,
    });
    this.container.add(statusText);

    // COMPLETE button
    if (!mission.is_completed) {
      const completeBtn = this.scene.add.text(
        x + w - 60,
        y + h / 2,
        '[ COMPLETE ]',
        {
          fontFamily: 'Courier New',
          fontSize: '11px',
          color: CONFIG.COLOR_STR.GREEN,
        }
      ).setOrigin(0.5).setInteractive({ useHandCursor: true });
      this.container.add(completeBtn);

      completeBtn.on('pointerover', () => completeBtn.setColor(CONFIG.COLOR_STR.CYAN));
      completeBtn.on('pointerout', () => completeBtn.setColor(CONFIG.COLOR_STR.GREEN));
      completeBtn.on('pointerdown', () => {
        wsClient.send('complete_mission', { mission_id: mission.id });
        // Disable the button after clicking
        completeBtn.disableInteractive();
        completeBtn.setColor(CONFIG.COLOR_STR.AMBER);
        completeBtn.setText('PENDING...');
      });
    }
  }

  /**
   * Shows a brief "MISSION COMPLETE" flash overlay in the center of the screen.
   */
  showCompletionFlash() {
    const flashText = this.scene.add.text(
      CONFIG.SCREEN_WIDTH / 2,
      CONFIG.SCREEN_HEIGHT / 2,
      'MISSION COMPLETE',
      {
        fontFamily: 'Courier New',
        fontSize: '28px',
        color: CONFIG.COLOR_STR.CYAN,
        stroke: CONFIG.COLOR_STR.BLACK,
        strokeThickness: 4,
      }
    ).setOrigin(0.5).setDepth(300);

    // Flash effect: fade out over 2 seconds
    this.scene.tweens.add({
      targets: flashText,
      alpha: 0,
      duration: 2000,
      ease: 'Power2',
      onComplete: () => {
        flashText.destroy();
      },
    });
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
    if (this.flashTimer) {
      this.flashTimer.destroy();
    }
    this.container.destroy(true);
  }
}
