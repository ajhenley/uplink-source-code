import Phaser from 'phaser';
import { CONFIG } from '../../config';
import { gameState } from '../../net/StateSync';

/**
 * FinancePanel: a popup overlay showing the player's financial summary.
 *
 * Opened via the HUD "Finance" toolbar button. Displays current balance
 * and credit rating from the local game state.
 */
export class FinancePanel {
  private scene: Phaser.Scene;
  private container: Phaser.GameObjects.Container;
  private visible: boolean = false;

  // Panel layout constants
  private readonly PANEL_W = 400;
  private readonly PANEL_H = 300;
  private readonly panelX: number;
  private readonly panelY: number;

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
      this.render();
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
    const title = this.scene.add.text(x + w / 2, y + 20, 'FINANCIAL SUMMARY', {
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

    const player = gameState.playerData;
    const balance = player?.balance ?? 0;
    const creditRating = player?.credit_rating ?? 0;

    const labelStyle = {
      fontFamily: 'Courier New',
      fontSize: '14px',
      color: CONFIG.COLOR_STR.GREEN,
    };

    const valueStyle = {
      fontFamily: 'Courier New',
      fontSize: '14px',
      color: CONFIG.COLOR_STR.AMBER,
    };

    // Balance row
    const balLabelY = y + 80;
    this.container.add(
      this.scene.add.text(x + 40, balLabelY, 'Balance:', labelStyle)
    );
    this.container.add(
      this.scene.add.text(x + w - 40, balLabelY, `${balance.toLocaleString()}c`, valueStyle)
        .setOrigin(1, 0)
    );

    // Credit Rating row
    const creditLabelY = y + 120;
    this.container.add(
      this.scene.add.text(x + 40, creditLabelY, 'Credit Rating:', labelStyle)
    );
    this.container.add(
      this.scene.add.text(x + w - 40, creditLabelY, `${creditRating}`, valueStyle)
        .setOrigin(1, 0)
    );

    // Uplink Rating row
    const uplinkRating = player?.uplink_rating ?? 0;
    const ratingNames = [
      'Unregistered', 'Registered', 'Beginner', 'Novice', 'Confident',
      'Intermediate', 'Skilled', 'Experienced', 'Knowledgeable', 'Uber-Skilled',
      'Professional', 'Elite', 'Mage', 'Expert', 'Veteren', 'Techno-mage', 'TERMINAL'
    ];
    const ratingIdx = Math.min(uplinkRating, ratingNames.length - 1);
    const ratingLabelY = y + 160;
    this.container.add(
      this.scene.add.text(x + 40, ratingLabelY, 'Uplink Rating:', labelStyle)
    );
    this.container.add(
      this.scene.add.text(x + w - 40, ratingLabelY, ratingNames[ratingIdx], valueStyle)
        .setOrigin(1, 0)
    );

    // Neuromancer Rating row
    const neuroRating = player?.neuromancer_rating ?? 0;
    const neuroLabelY = y + 200;
    this.container.add(
      this.scene.add.text(x + 40, neuroLabelY, 'Neuromancer Rating:', labelStyle)
    );
    this.container.add(
      this.scene.add.text(x + w - 40, neuroLabelY, `${neuroRating}`, valueStyle)
        .setOrigin(1, 0)
    );
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
