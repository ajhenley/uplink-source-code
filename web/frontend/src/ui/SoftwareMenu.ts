import Phaser from 'phaser';
import { CONFIG } from '../config';
import { wsClient } from '../net/WebSocketClient';
import { restClient } from '../net/RestClient';
import { gameState } from '../net/StateSync';
import type { SoftwareEntry } from '../net/MessageTypes';

interface ToolEntry {
  name: string;
  version: number;
  label: string;
}

/**
 * Parse a tool name and version from a software filename.
 * e.g. "Password Breaker v1.0" -> { tool_name: "Password_Breaker", version: 1 }
 */
function parseToolFromFilename(filename: string): { tool_name: string; version: number } | null {
  const match = filename.match(/^(.+?)\s+v(\d+)\.\d+$/i);
  if (!match) return null;
  const tool_name = match[1].replace(/\s+/g, '_');
  const version = parseInt(match[2], 10);
  return { tool_name, version };
}

/**
 * SoftwareMenu: a popup menu launched from the HUD "Software" button.
 * Lists the player's available hacking tools fetched from the gateway.
 * Clicking a tool sends a `run_tool` message via WebSocket.
 */
export class SoftwareMenu {
  private scene: Phaser.Scene;
  private container: Phaser.GameObjects.Container;
  private visible: boolean = false;

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
    this.container = scene.add.container(10, CONFIG.HUD_HEIGHT);
    this.container.setVisible(false);
    this.container.setDepth(100);

    this.buildMenu();
  }

  toggle() {
    this.visible = !this.visible;
    this.container.setVisible(this.visible);
    if (this.visible) {
      this.buildMenu(); // Refresh each time to reflect current state
    }
  }

  isVisible(): boolean {
    return this.visible;
  }

  private buildMenu() {
    this.container.removeAll(true);

    const panelWidth = 250;

    // Show loading state initially
    const loadingBg = this.scene.add.graphics();
    loadingBg.fillStyle(CONFIG.COLORS.BLACK, 0.95);
    loadingBg.fillRect(0, 0, panelWidth, 50);
    loadingBg.lineStyle(1, CONFIG.COLORS.GREEN, 1);
    loadingBg.strokeRect(0, 0, panelWidth, 50);
    this.container.add(loadingBg);

    const title = this.scene.add.text(10, 5, 'SOFTWARE', {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.CYAN,
    });
    this.container.add(title);

    const loadingText = this.scene.add.text(15, 26, 'Loading...', {
      fontFamily: 'Courier New',
      fontSize: '11px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setAlpha(0.6);
    this.container.add(loadingText);

    // Fetch software from server and rebuild
    this.fetchSoftware();
  }

  private async fetchSoftware() {
    let tools: ToolEntry[] = [];

    try {
      const software = await restClient.get<SoftwareEntry[]>(
        `/api/player/${gameState.sessionId}/software`
      );

      tools = software
        .map((entry) => {
          const parsed = parseToolFromFilename(entry.filename);
          if (!parsed) return null;
          return {
            name: parsed.tool_name,
            version: parsed.version,
            label: entry.filename,
          };
        })
        .filter((t): t is ToolEntry => t !== null);
    } catch (err) {
      console.error('[SoftwareMenu] Failed to fetch software:', err);
      // Fall back to empty list
    }

    // Only re-render if the menu is still visible
    if (this.visible) {
      this.renderTools(tools);
    }
  }

  private renderTools(tools: ToolEntry[]) {
    this.container.removeAll(true);

    const panelWidth = 250;
    const itemHeight = 24;
    const titleHeight = 22;
    const panelHeight = Math.max(tools.length, 1) * itemHeight + titleHeight + 10;

    // Background panel
    const bg = this.scene.add.graphics();
    bg.fillStyle(CONFIG.COLORS.BLACK, 0.95);
    bg.fillRect(0, 0, panelWidth, panelHeight);
    bg.lineStyle(1, CONFIG.COLORS.GREEN, 1);
    bg.strokeRect(0, 0, panelWidth, panelHeight);
    this.container.add(bg);

    // Title
    const title = this.scene.add.text(10, 5, 'SOFTWARE', {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.CYAN,
    });
    this.container.add(title);

    if (tools.length === 0) {
      const empty = this.scene.add.text(15, titleHeight + 4, 'No software installed.', {
        fontFamily: 'Courier New',
        fontSize: '11px',
        color: CONFIG.COLOR_STR.GREEN,
      }).setAlpha(0.6);
      this.container.add(empty);
      return;
    }

    // Tool entries
    tools.forEach((tool, i) => {
      const y = titleHeight + i * itemHeight;

      const text = this.scene.add.text(15, y, tool.label, {
        fontFamily: 'Courier New',
        fontSize: '11px',
        color: CONFIG.COLOR_STR.GREEN,
      });
      text.setInteractive({ useHandCursor: true });

      text.on('pointerover', () => text.setColor(CONFIG.COLOR_STR.CYAN));
      text.on('pointerout', () => text.setColor(CONFIG.COLOR_STR.GREEN));

      text.on('pointerdown', () => {
        // Must be connected to a target to run most tools (Trace_Tracker is an exception)
        if (!gameState.isConnected && tool.name !== 'Trace_Tracker') {
          return;
        }
        wsClient.send('run_tool', {
          tool_name: tool.name,
          tool_version: tool.version,
          target_ip: gameState.targetIp,
          target_data: {},
        });
        this.toggle(); // Close menu after selecting
      });

      this.container.add(text);
    });
  }

  destroy() {
    this.container.destroy(true);
  }
}
