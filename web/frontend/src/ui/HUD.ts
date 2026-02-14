import Phaser from 'phaser';
import { CONFIG } from '../config';
import { gameState } from '../net/StateSync';
import { wsClient } from '../net/WebSocketClient';
import { audioManager } from '../audio/AudioManager';
import { SoftwareMenu } from './SoftwareMenu';
import { EmailPanel } from './panels/EmailPanel';
import { MissionPanel } from './panels/MissionPanel';
import { GatewayPanel } from './panels/GatewayPanel';
import { HardwarePanel } from './panels/HardwarePanel';
import { FinancePanel } from './panels/FinancePanel';

export class HUD {
  private scene: Phaser.Scene;
  private balanceText: Phaser.GameObjects.Text;
  private ratingText: Phaser.GameObjects.Text;
  private softwareMenu: SoftwareMenu;
  private emailPanel: EmailPanel;
  private missionPanel: MissionPanel;
  private gatewayPanel: GatewayPanel;
  private hardwarePanel: HardwarePanel;
  private financePanel: FinancePanel;
  private unreadIndicator: Phaser.GameObjects.Text | null = null;
  private emailButtonX: number = 0;
  private emailButtonY: number = 0;
  private speedTexts: Phaser.GameObjects.Text[] = [];
  private speedIndicator!: Phaser.GameObjects.Text;
  private currentSpeed: number = 1;
  private muteText!: Phaser.GameObjects.Text;

  constructor(scene: Phaser.Scene) {
    this.scene = scene;

    const gfx = scene.add.graphics();

    // HUD background bar
    gfx.fillStyle(0x001100, 1);
    gfx.fillRect(0, 0, CONFIG.SCREEN_WIDTH, CONFIG.HUD_HEIGHT);
    gfx.lineStyle(1, CONFIG.COLORS.GREEN);
    gfx.lineBetween(0, CONFIG.HUD_HEIGHT, CONFIG.SCREEN_WIDTH, CONFIG.HUD_HEIGHT);

    // "UPLINK" brand
    scene.add.text(10, 8, 'UPLINK', {
      fontFamily: 'Courier New',
      fontSize: '18px',
      color: CONFIG.COLOR_STR.GREEN,
    });

    // Toolbar buttons
    const buttonStyle = {
      fontFamily: 'Courier New',
      fontSize: '11px',
      color: CONFIG.COLOR_STR.GREEN,
    };

    let btnX = 120;
    for (const label of CONFIG.TOOLBAR_BUTTONS) {
      const btnW = label.length * 8 + 16;
      const btnH = 24;
      const btnY = 10;

      gfx.lineStyle(1, CONFIG.COLORS.GREEN, 0.5);
      gfx.strokeRect(btnX, btnY, btnW, btnH);

      const text = scene.add.text(btnX + btnW / 2, btnY + btnH / 2, label, buttonStyle)
        .setOrigin(0.5);

      const hitArea = scene.add.rectangle(btnX + btnW / 2, btnY + btnH / 2, btnW, btnH)
        .setInteractive({ useHandCursor: true })
        .setAlpha(0.001);

      hitArea.on('pointerover', () => {
        text.setColor(CONFIG.COLOR_STR.CYAN);
      });
      hitArea.on('pointerout', () => {
        text.setColor(CONFIG.COLOR_STR.GREEN);
      });
      hitArea.on('pointerdown', () => {
        this.handleToolbarClick(label);
      });

      // Track Email button position for unread indicator
      if (label === 'Email') {
        this.emailButtonX = btnX + btnW;
        this.emailButtonY = btnY;
      }

      btnX += btnW + 6;
    }

    // Speed control section (after toolbar buttons)
    const speedX = btnX + 10;
    const speedY = 14;
    const speedSmallStyle = {
      fontFamily: 'Courier New',
      fontSize: '10px',
      color: CONFIG.COLOR_STR.GREEN,
    };

    this.speedIndicator = scene.add.text(speedX, speedY - 2, '1x', {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.AMBER,
    });

    const speeds = [
      { label: '>', speed: 1 },
      { label: '>>', speed: 3 },
      { label: '>>>', speed: 8 },
    ];

    let speedBtnX = speedX + 30;
    for (const s of speeds) {
      const sBtnW = s.label.length * 7 + 10;
      const sBtnH = 18;

      gfx.lineStyle(1, CONFIG.COLORS.GREEN, 0.4);
      gfx.strokeRect(speedBtnX, speedY - 2, sBtnW, sBtnH);

      const speedText = scene.add.text(speedBtnX + sBtnW / 2, speedY + sBtnH / 2 - 2, s.label, speedSmallStyle)
        .setOrigin(0.5);
      this.speedTexts.push(speedText);

      const speedHit = scene.add.rectangle(speedBtnX + sBtnW / 2, speedY + sBtnH / 2 - 2, sBtnW, sBtnH)
        .setInteractive({ useHandCursor: true })
        .setAlpha(0.001);

      speedHit.on('pointerover', () => speedText.setColor(CONFIG.COLOR_STR.CYAN));
      speedHit.on('pointerout', () => {
        speedText.setColor(s.speed === this.currentSpeed ? CONFIG.COLOR_STR.AMBER : CONFIG.COLOR_STR.GREEN);
      });
      speedHit.on('pointerdown', () => {
        audioManager.playClick();
        this.currentSpeed = s.speed;
        this.speedIndicator.setText(`${s.speed}x`);
        wsClient.send('set_speed', { speed: s.speed });
        this.updateSpeedHighlights();
      });

      speedBtnX += sBtnW + 4;
    }

    // Listen for server speed_changed events
    wsClient.on('speed_changed', (data) => {
      this.currentSpeed = data.speed as number;
      this.speedIndicator.setText(`${this.currentSpeed}x`);
      this.updateSpeedHighlights();
    });

    // Sound mute toggle (far right of HUD bar)
    this.muteText = scene.add.text(CONFIG.SCREEN_WIDTH - 130, 8, '[SND]', {
      fontFamily: 'Courier New',
      fontSize: '10px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setInteractive({ useHandCursor: true });

    this.muteText.on('pointerdown', () => {
      const muted = audioManager.toggleMute();
      this.muteText.setAlpha(muted ? 0.3 : 1);
    });
    this.muteText.on('pointerover', () => this.muteText.setColor(CONFIG.COLOR_STR.CYAN));
    this.muteText.on('pointerout', () => this.muteText.setColor(CONFIG.COLOR_STR.GREEN));

    // Player info on right side
    const player = gameState.playerData;
    const handle = player?.handle || 'Agent';
    const balance = player?.balance ?? 0;

    scene.add.text(CONFIG.SCREEN_WIDTH - 10, 8, handle, {
      ...buttonStyle,
      color: CONFIG.COLOR_STR.CYAN,
    }).setOrigin(1, 0);

    this.balanceText = scene.add.text(CONFIG.SCREEN_WIDTH - 10, 24, `${balance}c`, {
      ...buttonStyle,
      color: CONFIG.COLOR_STR.AMBER,
    }).setOrigin(1, 0);

    // Rating display
    const ratingNames = [
      'Unregistered', 'Registered', 'Beginner', 'Novice', 'Confident',
      'Intermediate', 'Skilled', 'Experienced', 'Knowledgeable', 'Uber-Skilled',
      'Professional', 'Elite', 'Mage', 'Expert', 'Veteren', 'Techno-mage', 'TERMINAL'
    ];
    const ratingIdx = Math.min(player?.uplink_rating ?? 0, ratingNames.length - 1);
    this.ratingText = scene.add.text(CONFIG.SCREEN_WIDTH - 150, 24, ratingNames[ratingIdx], {
      fontFamily: 'Courier New',
      fontSize: '10px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setOrigin(1, 0);

    // Create popup menus and panels
    this.softwareMenu = new SoftwareMenu(scene);
    this.emailPanel = new EmailPanel(scene);
    this.missionPanel = new MissionPanel(scene);
    this.hardwarePanel = new HardwarePanel(scene);
    this.gatewayPanel = new GatewayPanel(scene, this.hardwarePanel, (amount: number) => {
      this.updateBalance(amount);
    });
    this.financePanel = new FinancePanel(scene);
  }

  private updateSpeedHighlights() {
    const speedValues = [1, 3, 8];
    for (let i = 0; i < this.speedTexts.length; i++) {
      if (speedValues[i] === this.currentSpeed) {
        this.speedTexts[i].setColor(CONFIG.COLOR_STR.AMBER);
      } else {
        this.speedTexts[i].setColor(CONFIG.COLOR_STR.GREEN);
      }
    }
  }

  private handleToolbarClick(label: string) {
    switch (label) {
      case 'Software':
        this.softwareMenu.toggle();
        break;
      case 'Hardware':
        this.gatewayPanel.toggle();
        break;
      case 'Email':
        this.emailPanel.toggle();
        break;
      case 'Status':
        this.missionPanel.toggle();
        break;
      case 'Finance':
        this.financePanel.toggle();
        break;
      default:
        console.log(`Toolbar click: ${label}`);
        break;
    }
  }

  updateBalance(amount: number) {
    this.balanceText.setText(`${amount}c`);
  }

  updateRating(ratingIdx: number) {
    const ratingNames = [
      'Unregistered', 'Registered', 'Beginner', 'Novice', 'Confident',
      'Intermediate', 'Skilled', 'Experienced', 'Knowledgeable', 'Uber-Skilled',
      'Professional', 'Elite', 'Mage', 'Expert', 'Veteren', 'Techno-mage', 'TERMINAL'
    ];
    const idx = Math.min(ratingIdx, ratingNames.length - 1);
    this.ratingText.setText(ratingNames[idx]);
  }

  updateUnreadIndicator() {
    const count = this.emailPanel.getUnreadCount();
    if (count > 0) {
      if (!this.unreadIndicator) {
        this.unreadIndicator = this.scene.add.text(
          this.emailButtonX - 2,
          this.emailButtonY,
          '',
          {
            fontFamily: 'Courier New',
            fontSize: '9px',
            color: CONFIG.COLOR_STR.AMBER,
          }
        ).setDepth(10);
      }
      this.unreadIndicator.setText(`${count}`);
      this.unreadIndicator.setVisible(true);
    } else if (this.unreadIndicator) {
      this.unreadIndicator.setVisible(false);
    }
  }

  getMissionPanel(): MissionPanel {
    return this.missionPanel;
  }

  getHardwarePanel(): HardwarePanel {
    return this.hardwarePanel;
  }

  getGatewayPanel(): GatewayPanel {
    return this.gatewayPanel;
  }

  destroy() {
    this.emailPanel.destroy();
    this.missionPanel.destroy();
    this.softwareMenu.destroy();
    this.gatewayPanel.destroy();
    this.financePanel.destroy();
    if (this.unreadIndicator) {
      this.unreadIndicator.destroy();
    }
    if (this.muteText) {
      this.muteText.destroy();
    }
  }
}
