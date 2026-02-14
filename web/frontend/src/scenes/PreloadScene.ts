import Phaser from 'phaser';
import { CONFIG } from '../config';

export class PreloadScene extends Phaser.Scene {
  constructor() {
    super({ key: 'PreloadScene' });
  }

  preload() {
    // Create loading bar
    const barWidth = 400;
    const barHeight = 20;
    const barX = (CONFIG.SCREEN_WIDTH - barWidth) / 2;
    const barY = CONFIG.SCREEN_HEIGHT / 2 + 30;

    const border = this.add.graphics();
    border.lineStyle(1, CONFIG.COLORS.GREEN);
    border.strokeRect(barX, barY, barWidth, barHeight);

    const fill = this.add.graphics();

    this.load.on('progress', (value: number) => {
      fill.clear();
      fill.fillStyle(CONFIG.COLORS.GREEN, 1);
      fill.fillRect(barX + 2, barY + 2, (barWidth - 4) * value, barHeight - 4);
    });

    this.add.text(
      CONFIG.SCREEN_WIDTH / 2,
      CONFIG.SCREEN_HEIGHT / 2 - 20,
      'UPLINK AGENT SYSTEM',
      {
        fontFamily: 'Courier New',
        fontSize: '24px',
        color: CONFIG.COLOR_STR.GREEN,
      }
    ).setOrigin(0.5);

    // Generate world map texture programmatically
    this.createWorldMapTexture();
  }

  createWorldMapTexture() {
    // Create a procedural world map (dark green continents on black)
    const w = 595;
    const h = 315;
    const gfx = this.add.graphics();
    gfx.setVisible(false);

    gfx.fillStyle(0x001100, 1);
    gfx.fillRect(0, 0, w, h);

    // Simplified continent shapes
    gfx.fillStyle(0x003300, 1);

    // North America
    gfx.fillRoundedRect(50, 30, 120, 80, 8);
    gfx.fillRoundedRect(60, 80, 80, 60, 5);

    // South America
    gfx.fillRoundedRect(130, 160, 50, 90, 8);
    gfx.fillRoundedRect(120, 150, 40, 30, 5);

    // Europe
    gfx.fillRoundedRect(260, 30, 60, 60, 5);
    gfx.fillRoundedRect(270, 50, 40, 40, 5);

    // Africa
    gfx.fillRoundedRect(270, 100, 60, 100, 8);
    gfx.fillRoundedRect(260, 110, 30, 50, 5);

    // Asia
    gfx.fillRoundedRect(320, 25, 150, 80, 8);
    gfx.fillRoundedRect(380, 80, 80, 50, 5);
    gfx.fillRoundedRect(460, 60, 60, 60, 5);

    // Australia
    gfx.fillRoundedRect(500, 200, 60, 40, 5);

    gfx.generateTexture('worldmap', w, h);
    gfx.destroy();
  }

  create() {
    this.scene.start('LoginScene');
  }
}
