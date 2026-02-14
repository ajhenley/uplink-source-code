import Phaser from 'phaser';
import { CONFIG } from '../config';
import { wsClient } from '../net/WebSocketClient';
import { gameState } from '../net/StateSync';
import type { TaskData } from '../net/MessageTypes';

/**
 * A single task panel showing a running hacking tool's name, version,
 * progress bar, percentage, and a stop button.
 * Dimensions: ~300px wide, 45px tall.
 */
class TaskPanel {
  private scene: Phaser.Scene;
  private parentContainer: Phaser.GameObjects.Container;
  private container: Phaser.GameObjects.Container;
  private bg: Phaser.GameObjects.Graphics;
  private progressFill: Phaser.GameObjects.Graphics;
  private nameText: Phaser.GameObjects.Text;
  private percentText: Phaser.GameObjects.Text;
  private extraText: Phaser.GameObjects.Text | null = null;
  private stopBtn: Phaser.GameObjects.Text;
  private taskId: number;
  private destroyed: boolean = false;

  private static readonly WIDTH = 300;
  private static readonly HEIGHT = 45;
  private static readonly BAR_X = 8;
  private static readonly BAR_Y = 22;
  private static readonly BAR_WIDTH = 240;
  private static readonly BAR_HEIGHT = 12;

  constructor(scene: Phaser.Scene, parentContainer: Phaser.GameObjects.Container, task: TaskData) {
    this.scene = scene;
    this.parentContainer = parentContainer;
    this.taskId = task.task_id;

    this.container = scene.add.container(0, 0);
    parentContainer.add(this.container);

    // Background rectangle
    this.bg = scene.add.graphics();
    this.bg.fillStyle(CONFIG.COLORS.BLACK, 0.92);
    this.bg.fillRect(0, 0, TaskPanel.WIDTH, TaskPanel.HEIGHT);
    this.bg.lineStyle(1, CONFIG.COLORS.GREEN, 0.8);
    this.bg.strokeRect(0, 0, TaskPanel.WIDTH, TaskPanel.HEIGHT);
    this.container.add(this.bg);

    // Tool name and version label
    const displayName = task.tool_name.replace(/_/g, ' ');
    this.nameText = scene.add.text(8, 4, `${displayName} v${task.tool_version}.0`, {
      fontFamily: 'Courier New',
      fontSize: '11px',
      color: CONFIG.COLOR_STR.CYAN,
    });
    this.container.add(this.nameText);

    // Progress bar background (dark track)
    const barTrack = scene.add.graphics();
    barTrack.fillStyle(CONFIG.COLORS.DARK_GREEN, 0.5);
    barTrack.fillRect(TaskPanel.BAR_X, TaskPanel.BAR_Y, TaskPanel.BAR_WIDTH, TaskPanel.BAR_HEIGHT);
    barTrack.lineStyle(1, CONFIG.COLORS.GREEN, 0.4);
    barTrack.strokeRect(TaskPanel.BAR_X, TaskPanel.BAR_Y, TaskPanel.BAR_WIDTH, TaskPanel.BAR_HEIGHT);
    this.container.add(barTrack);

    // Progress bar fill
    this.progressFill = scene.add.graphics();
    this.container.add(this.progressFill);
    this.drawProgressBar(task.progress);

    // Percentage text
    const pctStr = `${Math.floor(task.progress * 100)}%`;
    this.percentText = scene.add.text(
      TaskPanel.BAR_X + TaskPanel.BAR_WIDTH + 6, TaskPanel.BAR_Y - 1,
      pctStr,
      {
        fontFamily: 'Courier New',
        fontSize: '11px',
        color: CONFIG.COLOR_STR.GREEN,
      }
    );
    this.container.add(this.percentText);

    // Stop button (red X)
    this.stopBtn = scene.add.text(TaskPanel.WIDTH - 18, 4, 'X', {
      fontFamily: 'Courier New',
      fontSize: '12px',
      fontStyle: 'bold',
      color: CONFIG.COLOR_STR.RED,
    });
    this.stopBtn.setInteractive({ useHandCursor: true });
    this.stopBtn.on('pointerover', () => {
      if (!this.destroyed) this.stopBtn.setColor(CONFIG.COLOR_STR.AMBER);
    });
    this.stopBtn.on('pointerout', () => {
      if (!this.destroyed) this.stopBtn.setColor(CONFIG.COLOR_STR.RED);
    });
    this.stopBtn.on('pointerdown', () => {
      wsClient.send('stop_tool', { task_id: this.taskId });
    });
    this.container.add(this.stopBtn);

    // Extra info line (e.g. password breaker revealed chars)
    if (task.tool_name === 'Password_Breaker' && task.extra?.revealed) {
      this.extraText = scene.add.text(8, TaskPanel.BAR_Y + TaskPanel.BAR_HEIGHT + 2,
        task.extra.revealed as string,
        {
          fontFamily: 'Courier New',
          fontSize: '10px',
          color: CONFIG.COLOR_STR.AMBER,
        }
      );
      this.container.add(this.extraText);
    }
  }

  private drawProgressBar(progress: number) {
    this.progressFill.clear();
    const fillWidth = Math.max(0, Math.min(progress, 1)) * TaskPanel.BAR_WIDTH;
    if (fillWidth > 0) {
      this.progressFill.fillStyle(CONFIG.COLORS.GREEN, 0.8);
      this.progressFill.fillRect(TaskPanel.BAR_X, TaskPanel.BAR_Y, fillWidth, TaskPanel.BAR_HEIGHT);
    }
  }

  update(task: TaskData) {
    if (this.destroyed) return;

    this.drawProgressBar(task.progress);
    this.percentText.setText(`${Math.floor(task.progress * 100)}%`);

    // Update extra text for Password_Breaker
    if (task.tool_name === 'Password_Breaker' && task.extra?.revealed) {
      const chars = task.extra.revealed as string;
      if (this.extraText) {
        this.extraText.setText(chars);
      } else {
        this.extraText = this.scene.add.text(8, TaskPanel.BAR_Y + TaskPanel.BAR_HEIGHT + 2,
          chars,
          {
            fontFamily: 'Courier New',
            fontSize: '10px',
            color: CONFIG.COLOR_STR.AMBER,
          }
        );
        this.container.add(this.extraText);
      }
    }
  }

  showComplete() {
    if (this.destroyed) return;

    // Flash the bar green and update text
    this.drawProgressBar(1.0);
    this.percentText.setText('DONE');
    this.percentText.setColor(CONFIG.COLOR_STR.CYAN);
    this.nameText.setColor(CONFIG.COLOR_STR.GREEN);

    // Flash effect
    this.scene.tweens.add({
      targets: this.container,
      alpha: { from: 1, to: 0.3 },
      yoyo: true,
      repeat: 2,
      duration: 200,
    });
  }

  setPosition(x: number, y: number) {
    if (!this.destroyed) {
      this.container.setPosition(x, y);
    }
  }

  destroy() {
    this.destroyed = true;
    this.container.destroy(true);
  }
}

/**
 * TaskManagerScene: an overlay scene launched alongside MainGameScene.
 * Displays running hacking tool progress panels at the bottom-right,
 * above the connection bar.
 */
export class TaskManagerScene extends Phaser.Scene {
  private taskPanels: Map<number, TaskPanel> = new Map();
  private container!: Phaser.GameObjects.Container;

  constructor() {
    super({ key: 'TaskManagerScene' });
  }

  create() {
    // Container for all task panels, positioned at bottom-right
    this.container = this.add.container(0, 0);

    // Listen for task updates from WS
    wsClient.on('task_update', (data) => {
      const tasks = data.tasks as TaskData[];
      for (const task of tasks) {
        this.updateTask(task);
      }
    });

    wsClient.on('task_complete', (data) => {
      const task = data.task as TaskData;
      this.completeTask(task);
    });
  }

  private updateTask(task: TaskData) {
    let panel = this.taskPanels.get(task.task_id);
    if (!panel) {
      panel = new TaskPanel(this, this.container, task);
      this.taskPanels.set(task.task_id, panel);
      this.layoutPanels();
    }
    panel.update(task);
  }

  private completeTask(task: TaskData) {
    const panel = this.taskPanels.get(task.task_id);
    if (panel) {
      panel.showComplete();
      // Remove after brief delay so the player sees the "DONE" flash
      this.time.delayedCall(2000, () => {
        panel.destroy();
        this.taskPanels.delete(task.task_id);
        this.layoutPanels();
      });
    }
  }

  private layoutPanels() {
    const panelHeight = 50;
    const padding = 5;
    const startX = CONFIG.SCREEN_WIDTH - 320;
    const startY = CONFIG.SCREEN_HEIGHT - CONFIG.CONNECTION_BAR_HEIGHT - 10;

    let idx = 0;
    for (const panel of this.taskPanels.values()) {
      const y = startY - (idx + 1) * (panelHeight + padding);
      panel.setPosition(startX, y);
      idx++;
    }
  }
}
