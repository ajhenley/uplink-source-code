import Phaser from 'phaser';
import { CONFIG } from '../config';
import { gameState } from '../net/StateSync';
import { wsClient } from '../net/WebSocketClient';

export class WorldMap {
  private scene: Phaser.Scene;
  private graphics: Phaser.GameObjects.Graphics;
  private mapImage: Phaser.GameObjects.Image;
  private locationDots: { x: number; y: number; ip: string }[] = [];
  private pulsePhase = 0;
  private tooltipText: Phaser.GameObjects.Text;

  constructor(scene: Phaser.Scene) {
    this.scene = scene;

    const mapY = CONFIG.HUD_HEIGHT;
    const mapH = CONFIG.SCREEN_HEIGHT - CONFIG.HUD_HEIGHT - CONFIG.CONNECTION_BAR_HEIGHT;

    // Map background
    this.mapImage = scene.add.image(
      CONFIG.SCREEN_WIDTH / 2,
      mapY + mapH / 2,
      'worldmap'
    );
    this.mapImage.setDisplaySize(CONFIG.SCREEN_WIDTH, mapH);

    // Graphics layer for dots and lines
    this.graphics = scene.add.graphics();

    // Tooltip for hovering over locations
    this.tooltipText = scene.add.text(0, 0, '', {
      fontFamily: 'Courier New',
      fontSize: '11px',
      color: CONFIG.COLOR_STR.GREEN,
      backgroundColor: '#000000',
      padding: { x: 4, y: 2 },
    }).setVisible(false).setDepth(100);

    // Process locations
    this.loadLocations();

    // Setup mouse interaction
    scene.input.on('pointermove', (pointer: Phaser.Input.Pointer) => {
      this.handleHover(pointer.x, pointer.y);
    });

    scene.input.on('pointerdown', (pointer: Phaser.Input.Pointer) => {
      this.handleClick(pointer.x, pointer.y);
    });
  }

  private loadLocations() {
    this.locationDots = gameState.locations.map((loc) => ({
      x: this.mapToScreenX(loc.x),
      y: this.mapToScreenY(loc.y),
      ip: loc.ip,
    }));
  }

  private mapToScreenX(mapX: number): number {
    return (mapX / CONFIG.MAP_WIDTH) * CONFIG.SCREEN_WIDTH;
  }

  private mapToScreenY(mapY: number): number {
    const mapAreaTop = CONFIG.HUD_HEIGHT;
    const mapAreaHeight = CONFIG.SCREEN_HEIGHT - CONFIG.HUD_HEIGHT - CONFIG.CONNECTION_BAR_HEIGHT;
    return mapAreaTop + (mapY / CONFIG.MAP_HEIGHT) * mapAreaHeight;
  }

  private handleHover(px: number, py: number) {
    const hoverRadius = 8;
    let found = false;

    for (const dot of this.locationDots) {
      const dx = px - dot.x;
      const dy = py - dot.y;
      if (dx * dx + dy * dy < hoverRadius * hoverRadius) {
        this.tooltipText.setText(dot.ip);
        this.tooltipText.setPosition(dot.x + 10, dot.y - 15);
        this.tooltipText.setVisible(true);
        found = true;
        break;
      }
    }

    if (!found) {
      this.tooltipText.setVisible(false);
    }
  }

  private handleClick(px: number, py: number) {
    const clickRadius = 10;
    for (const dot of this.locationDots) {
      const dx = px - dot.x;
      const dy = py - dot.y;
      if (dx * dx + dy * dy < clickRadius * clickRadius) {
        // Add to bounce chain
        wsClient.send('bounce_add', { ip: dot.ip });
        break;
      }
    }
  }

  private findDotByIp(ip: string) {
    return this.locationDots.find(d => d.ip === ip) || null;
  }

  update() {
    this.pulsePhase += 0.05;
    this.graphics.clear();

    // Draw location dots
    const alpha = 0.6 + 0.4 * Math.sin(this.pulsePhase);

    for (const dot of this.locationDots) {
      // Outer glow
      this.graphics.fillStyle(CONFIG.COLORS.GREEN, alpha * 0.3);
      this.graphics.fillCircle(dot.x, dot.y, 4);

      // Inner dot
      this.graphics.fillStyle(CONFIG.COLORS.GREEN, alpha);
      this.graphics.fillCircle(dot.x, dot.y, 2);
    }

    // Draw bounce chain connections
    if (gameState.bounceChain.length > 0) {
      this.graphics.lineStyle(1, CONFIG.COLORS.CYAN, 0.6);

      const chain = gameState.bounceChain;

      // Draw line from player localhost to first bounce node
      const localhostIp = gameState.playerData?.localhost_ip;
      if (localhostIp) {
        const localhostDot = this.findDotByIp(localhostIp);
        const firstBounceDot = this.findDotByIp(chain[0].ip);
        if (localhostDot && firstBounceDot) {
          this.graphics.lineBetween(localhostDot.x, localhostDot.y, firstBounceDot.x, firstBounceDot.y);
        }
      }

      // Draw lines between bounce nodes
      for (let i = 0; i < chain.length - 1; i++) {
        const from = this.findDotByIp(chain[i].ip);
        const to = this.findDotByIp(chain[i + 1].ip);
        if (from && to) {
          this.graphics.lineBetween(from.x, from.y, to.x, to.y);
        }
      }

      // Highlight bounce chain nodes in cyan
      for (const node of chain) {
        const dot = this.findDotByIp(node.ip);
        if (dot) {
          this.graphics.fillStyle(CONFIG.COLORS.CYAN, 0.8);
          this.graphics.fillCircle(dot.x, dot.y, 3);
        }
      }
    }

    // Draw trace progress on the world map
    if (gameState.traceActive && gameState.bounceChain.length > 0) {
      const chain = gameState.bounceChain;
      const progress = gameState.traceProgress;
      const totalNodes = chain.length;

      // Trace goes backward: from last node (target) toward first node (near player)
      // progress 0.0 = no trace, 1.0 = fully traced
      const nodesTraced = Math.floor(progress * totalNodes);
      const partialProgress = (progress * totalNodes) - nodesTraced;

      // Draw traced nodes in red (from end of chain backward)
      for (let i = chain.length - 1; i >= chain.length - nodesTraced && i >= 0; i--) {
        const dot = this.findDotByIp(chain[i].ip);
        if (dot) {
          // Red pulsing glow for traced nodes
          const traceAlpha = 0.6 + 0.4 * Math.sin(this.pulsePhase * 2);
          this.graphics.fillStyle(CONFIG.COLORS.RED, traceAlpha);
          this.graphics.fillCircle(dot.x, dot.y, 5);
        }
      }

      // Draw red lines along traced portion
      this.graphics.lineStyle(2, CONFIG.COLORS.RED, 0.8);
      for (let i = chain.length - 1; i > chain.length - nodesTraced && i > 0; i--) {
        const from = this.findDotByIp(chain[i].ip);
        const to = this.findDotByIp(chain[i - 1].ip);
        if (from && to) {
          this.graphics.lineBetween(from.x, from.y, to.x, to.y);
        }
      }

      // Draw partial trace line (animated leading edge)
      if (nodesTraced < totalNodes && nodesTraced > 0) {
        const currentIdx = chain.length - nodesTraced;
        const nextIdx = currentIdx - 1;
        if (nextIdx >= 0) {
          const currentDot = this.findDotByIp(chain[currentIdx].ip);
          const nextDot = this.findDotByIp(chain[nextIdx].ip);
          if (currentDot && nextDot) {
            const interpX = currentDot.x + (nextDot.x - currentDot.x) * partialProgress;
            const interpY = currentDot.y + (nextDot.y - currentDot.y) * partialProgress;
            this.graphics.lineStyle(2, CONFIG.COLORS.RED, 0.6);
            this.graphics.lineBetween(currentDot.x, currentDot.y, interpX, interpY);
            // Animated leading dot
            this.graphics.fillStyle(CONFIG.COLORS.RED, 1);
            this.graphics.fillCircle(interpX, interpY, 3);
          }
        }
      }
    }
  }
}
