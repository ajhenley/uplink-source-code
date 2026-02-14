import Phaser from 'phaser';
import { CONFIG } from '../config';
import { wsClient } from '../net/WebSocketClient';
import { ScreenFactory } from '../ui/screens/ScreenFactory';

interface ScreenData {
  screen_type: number;
  screen_index: number;
  computer_name: string;
  computer_ip: string;
  prompt?: string;
  error?: string;
  menu_options?: Array<{ label: string; screen_index: number }>;
}

export class RemoteScreenScene extends Phaser.Scene {
  private currentScreen: { destroy?: () => void } | null = null;
  private screenContainer!: Phaser.GameObjects.Container;
  private headerText!: Phaser.GameObjects.Text;
  private background!: Phaser.GameObjects.Graphics;

  constructor() {
    super({ key: 'RemoteScreenScene' });
  }

  create(data: { screen?: ScreenData }) {
    // Compute the drawable area between HUD and connection bar
    const topY = CONFIG.HUD_HEIGHT;
    const areaHeight = CONFIG.SCREEN_HEIGHT - CONFIG.HUD_HEIGHT - CONFIG.CONNECTION_BAR_HEIGHT;

    // Semi-transparent black overlay covering the map area
    this.background = this.add.graphics();
    this.background.fillStyle(CONFIG.COLORS.BLACK, 0.95);
    this.background.fillRect(0, topY, CONFIG.SCREEN_WIDTH, areaHeight);

    // Green border inset by 2px
    this.background.lineStyle(1, CONFIG.COLORS.GREEN);
    this.background.strokeRect(2, topY + 2, CONFIG.SCREEN_WIDTH - 4, areaHeight - 4);

    // Header bar background
    this.background.fillStyle(0x002200, 1);
    this.background.fillRect(2, topY + 2, CONFIG.SCREEN_WIDTH - 4, 25);

    // Header text showing computer name and IP
    this.headerText = this.add.text(10, topY + 8, '', {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.CYAN,
    });

    // Disconnect button in the header bar
    const disconnectBtn = this.add.text(
      CONFIG.SCREEN_WIDTH - 100,
      topY + 8,
      '[DISCONNECT]',
      {
        fontFamily: 'Courier New',
        fontSize: '12px',
        color: CONFIG.COLOR_STR.RED,
      }
    ).setInteractive({ useHandCursor: true });

    disconnectBtn.on('pointerdown', () => {
      wsClient.send('disconnect');
    });
    disconnectBtn.on('pointerover', () => disconnectBtn.setAlpha(0.7));
    disconnectBtn.on('pointerout', () => disconnectBtn.setAlpha(1));

    // Container for the screen content, positioned below the header bar
    this.screenContainer = this.add.container(0, topY + 30);

    // Register WebSocket listeners
    wsClient.on('screen_update', this.onScreenUpdate);
    wsClient.on('disconnected', this.onDisconnected);

    // Render the initial screen if provided
    if (data?.screen) {
      this.renderScreen(data.screen);
    }
  }

  private onScreenUpdate = (data: Record<string, unknown>) => {
    const screen = data.screen as ScreenData | undefined;
    if (screen) {
      this.renderScreen(screen);
    }
  };

  private onDisconnected = () => {
    this.cleanup();
    this.scene.stop();
  };

  private renderScreen(screenData: ScreenData) {
    // Destroy the previous screen renderer if it has a cleanup method
    if (this.currentScreen && this.currentScreen.destroy) {
      this.currentScreen.destroy();
    }

    // Remove all game objects from the screen container
    this.screenContainer.removeAll(true);

    // Update the header with the current computer info
    this.headerText.setText(
      `${screenData.computer_name || 'Unknown'} (${screenData.computer_ip || '?.?.?.?'})`
    );

    // Delegate to the factory to build the appropriate screen
    this.currentScreen = ScreenFactory.create(this, this.screenContainer, screenData);
  }

  private cleanup() {
    if (this.currentScreen && this.currentScreen.destroy) {
      this.currentScreen.destroy();
      this.currentScreen = null;
    }
    wsClient.off('screen_update', this.onScreenUpdate);
    wsClient.off('disconnected', this.onDisconnected);
  }

  shutdown() {
    this.cleanup();
  }
}
