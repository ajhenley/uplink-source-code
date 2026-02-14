import Phaser from 'phaser';
import { CONFIG } from '../config';
import { gameState } from '../net/StateSync';
import { wsClient } from '../net/WebSocketClient';

export class ConnectionBar {
  private scene: Phaser.Scene;
  private routeText: Phaser.GameObjects.Text;
  private connectBtn: Phaser.GameObjects.Text;
  private disconnectBtn: Phaser.GameObjects.Text;
  private clearBtn: Phaser.GameObjects.Text;
  private statusText: Phaser.GameObjects.Text;
  private connectBtnBg: Phaser.GameObjects.Graphics;
  private barY: number;

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
    this.barY = CONFIG.SCREEN_HEIGHT - CONFIG.CONNECTION_BAR_HEIGHT;

    const gfx = scene.add.graphics();

    // Background
    gfx.fillStyle(0x001100, 1);
    gfx.fillRect(0, this.barY, CONFIG.SCREEN_WIDTH, CONFIG.CONNECTION_BAR_HEIGHT);
    gfx.lineStyle(1, CONFIG.COLORS.GREEN);
    gfx.lineBetween(0, this.barY, CONFIG.SCREEN_WIDTH, this.barY);

    // Graphics for button outlines (redrawn on update)
    this.connectBtnBg = scene.add.graphics();

    // Route text (left side)
    this.routeText = scene.add.text(10, this.barY + 8, 'ROUTE:', {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.GREEN,
    });

    // Status text (shows connected target when connected)
    this.statusText = scene.add.text(10, this.barY + 8, '', {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.CYAN,
    }).setVisible(false);

    // CLEAR button
    this.clearBtn = scene.add.text(
      CONFIG.SCREEN_WIDTH - 250,
      this.barY + 8,
      '[CLEAR]',
      {
        fontFamily: 'Courier New',
        fontSize: '11px',
        color: CONFIG.COLOR_STR.AMBER,
      }
    ).setInteractive({ useHandCursor: true });

    this.clearBtn.on('pointerdown', () => {
      // Remove nodes one by one from the end
      const chain = gameState.bounceChain;
      for (let i = chain.length - 1; i >= 0; i--) {
        wsClient.send('bounce_remove', { position: chain[i].position });
      }
    });
    this.clearBtn.on('pointerover', () => this.clearBtn.setAlpha(0.7));
    this.clearBtn.on('pointerout', () => this.clearBtn.setAlpha(1));

    // CONNECT button
    this.connectBtn = scene.add.text(
      CONFIG.SCREEN_WIDTH - 170,
      this.barY + 8,
      '[CONNECT]',
      {
        fontFamily: 'Courier New',
        fontSize: '11px',
        color: CONFIG.COLOR_STR.GREEN,
      }
    ).setInteractive({ useHandCursor: true });

    this.connectBtn.on('pointerdown', () => {
      if (gameState.bounceChain.length > 0 && !gameState.isConnected) {
        wsClient.send('connect');
      }
    });
    this.connectBtn.on('pointerover', () => this.connectBtn.setAlpha(0.7));
    this.connectBtn.on('pointerout', () => this.connectBtn.setAlpha(1));

    // DISCONNECT button
    this.disconnectBtn = scene.add.text(
      CONFIG.SCREEN_WIDTH - 170,
      this.barY + 8,
      '[DISCONNECT]',
      {
        fontFamily: 'Courier New',
        fontSize: '11px',
        color: CONFIG.COLOR_STR.RED,
      }
    ).setInteractive({ useHandCursor: true });

    this.disconnectBtn.on('pointerdown', () => {
      wsClient.send('disconnect');
    });
    this.disconnectBtn.on('pointerover', () => this.disconnectBtn.setAlpha(0.7));
    this.disconnectBtn.on('pointerout', () => this.disconnectBtn.setAlpha(1));

    // Initial visibility
    this.disconnectBtn.setVisible(false);
  }

  update() {
    if (gameState.isConnected) {
      // Show connected status
      this.statusText.setText(`CONNECTED TO: ${gameState.targetIp}`);
      this.statusText.setVisible(true);
      this.routeText.setVisible(false);

      // Show disconnect, hide connect and clear
      this.disconnectBtn.setVisible(true);
      this.connectBtn.setVisible(false);
      this.clearBtn.setVisible(false);
    } else {
      // Show route
      this.statusText.setVisible(false);
      this.routeText.setVisible(true);

      if (gameState.bounceChain.length > 0) {
        const ips = gameState.bounceChain.map(n => n.ip);
        let routeStr = ips.join(' \u2192 ');

        // Truncate if too long to fit (leave room for buttons)
        const maxLen = 60;
        if (routeStr.length > maxLen) {
          routeStr = '... \u2192 ' + ips.slice(-3).join(' \u2192 ');
        }

        this.routeText.setText(`ROUTE: ${routeStr}`);
      } else {
        this.routeText.setText('ROUTE: (click map locations to add)');
      }

      // Show connect (enabled only if chain has nodes), show clear, hide disconnect
      this.disconnectBtn.setVisible(false);
      this.connectBtn.setVisible(true);
      this.clearBtn.setVisible(gameState.bounceChain.length > 0);

      // Dim connect button if no bounce nodes
      if (gameState.bounceChain.length === 0) {
        this.connectBtn.setAlpha(0.3);
      } else {
        this.connectBtn.setAlpha(1);
      }
    }
  }
}
