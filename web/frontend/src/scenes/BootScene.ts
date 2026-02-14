import Phaser from 'phaser';
import { CONFIG } from '../config';

export class BootScene extends Phaser.Scene {
  constructor() {
    super({ key: 'BootScene' });
  }

  create() {
    // Minimal loading text
    this.add.text(
      CONFIG.SCREEN_WIDTH / 2,
      CONFIG.SCREEN_HEIGHT / 2,
      'UPLINK',
      {
        fontFamily: 'Courier New',
        fontSize: '32px',
        color: CONFIG.COLOR_STR.GREEN,
      }
    ).setOrigin(0.5);

    this.add.text(
      CONFIG.SCREEN_WIDTH / 2,
      CONFIG.SCREEN_HEIGHT / 2 + 50,
      'LOADING...',
      {
        fontFamily: 'Courier New',
        fontSize: '14px',
        color: CONFIG.COLOR_STR.GREEN,
      }
    ).setOrigin(0.5);

    // Move to preload after brief display
    this.time.delayedCall(500, () => {
      this.scene.start('PreloadScene');
    });
  }
}
