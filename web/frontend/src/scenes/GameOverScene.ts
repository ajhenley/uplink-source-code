import Phaser from 'phaser';
import { CONFIG } from '../config';
import { gameState } from '../net/StateSync';

export class GameOverScene extends Phaser.Scene {
  constructor() {
    super({ key: 'GameOverScene' });
  }

  create(data: { reason?: string }) {
    const reason = data?.reason || 'traced';

    // Full black background
    this.cameras.main.setBackgroundColor('#000000');

    // Red border
    const gfx = this.add.graphics();
    gfx.lineStyle(2, CONFIG.COLORS.RED, 1);
    gfx.strokeRect(20, 20, CONFIG.SCREEN_WIDTH - 40, CONFIG.SCREEN_HEIGHT - 40);
    gfx.lineStyle(1, CONFIG.COLORS.RED, 0.5);
    gfx.strokeRect(30, 30, CONFIG.SCREEN_WIDTH - 60, CONFIG.SCREEN_HEIGHT - 60);

    // Title
    this.add.text(CONFIG.SCREEN_WIDTH / 2, 80, 'CONNECTION TERMINATED', {
      fontFamily: 'Courier New',
      fontSize: '28px',
      color: CONFIG.COLOR_STR.RED,
    }).setOrigin(0.5);

    // Subtitle based on reason
    let subtitle = 'Your connection has been traced.';
    if (reason === 'traced') {
      subtitle = 'TRACE COMPLETE — YOUR IDENTITY HAS BEEN COMPROMISED';
    } else if (reason === 'arrested') {
      subtitle = 'FEDERAL AGENTS HAVE SEIZED YOUR GATEWAY';
    }

    this.add.text(CONFIG.SCREEN_WIDTH / 2, 130, subtitle, {
      fontFamily: 'Courier New',
      fontSize: '14px',
      color: CONFIG.COLOR_STR.AMBER,
    }).setOrigin(0.5);

    // Separator line
    gfx.lineStyle(1, CONFIG.COLORS.RED, 0.6);
    gfx.lineBetween(100, 165, CONFIG.SCREEN_WIDTH - 100, 165);

    // Agent stats
    const statsX = CONFIG.SCREEN_WIDTH / 2 - 150;
    let statsY = 200;
    const lineH = 28;

    const playerData = gameState.playerData;
    const stats = [
      { label: 'AGENT HANDLE:', value: playerData?.handle || 'Unknown' },
      { label: 'AGENT NAME:', value: playerData?.name || 'Unknown' },
      { label: 'UPLINK RATING:', value: String(playerData?.uplink_rating || 0) },
      { label: 'CREDIT RATING:', value: String(playerData?.credit_rating || 0) },
      { label: 'FINAL BALANCE:', value: `${playerData?.balance || 0}c` },
    ];

    for (const stat of stats) {
      this.add.text(statsX, statsY, stat.label, {
        fontFamily: 'Courier New',
        fontSize: '14px',
        color: CONFIG.COLOR_STR.GREEN,
      });
      this.add.text(statsX + 200, statsY, stat.value, {
        fontFamily: 'Courier New',
        fontSize: '14px',
        color: CONFIG.COLOR_STR.CYAN,
      });
      statsY += lineH;
    }

    // Separator
    gfx.lineBetween(100, statsY + 10, CONFIG.SCREEN_WIDTH - 100, statsY + 10);

    // Obituary text
    this.add.text(CONFIG.SCREEN_WIDTH / 2, statsY + 50,
      'Your Uplink account has been revoked.\nAll records of your activities have been archived.', {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.GREEN,
      align: 'center',
    }).setOrigin(0.5);

    // Disavowed stamp - typewriter effect
    const stampText = '[ D I S A V O W E D ]';
    const stamp = this.add.text(CONFIG.SCREEN_WIDTH / 2, statsY + 130, '', {
      fontFamily: 'Courier New',
      fontSize: '32px',
      color: CONFIG.COLOR_STR.RED,
    }).setOrigin(0.5);

    // Typewriter animation for stamp
    let charIdx = 0;
    this.time.addEvent({
      delay: 80,
      repeat: stampText.length - 1,
      callback: () => {
        charIdx++;
        stamp.setText(stampText.substring(0, charIdx));
      },
    });

    // "Press any key" after a delay
    this.time.delayedCall(3000, () => {
      const pressKey = this.add.text(CONFIG.SCREEN_WIDTH / 2, CONFIG.SCREEN_HEIGHT - 80,
        'Press any key to return to login...', {
        fontFamily: 'Courier New',
        fontSize: '12px',
        color: CONFIG.COLOR_STR.GREEN,
      }).setOrigin(0.5);

      // Blink effect
      this.tweens.add({
        targets: pressKey,
        alpha: { from: 1, to: 0.3 },
        yoyo: true,
        repeat: -1,
        duration: 800,
      });

      // Listen for any key or click to go back to login
      this.input.keyboard!.on('keydown', () => {
        this.scene.stop('TaskManagerScene');
        this.scene.start('LoginScene');
      });
      this.input.on('pointerdown', () => {
        this.scene.stop('TaskManagerScene');
        this.scene.start('LoginScene');
      });
    });
  }
}
