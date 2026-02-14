import Phaser from 'phaser';
import { CONFIG } from '../../config';
import { wsClient } from '../../net/WebSocketClient';

interface LogEntry {
  id: number;
  log_time: string;
  from_ip: string;
  from_name: string;
  subject: string;
  log_type: number;
}

/**
 * Terminal-style access-log viewer screen.
 *
 * Displays the access logs recorded on the remote computer in a
 * tabular layout with columns for time, originating IP, and subject.
 * Shows up to 20 entries; if more exist, a "..." indicator is shown.
 *
 * All game objects are added to `container`.
 */
export class LogScreen {
  private scene: Phaser.Scene;
  private container: Phaser.GameObjects.Container;

  constructor(
    scene: Phaser.Scene,
    container: Phaser.GameObjects.Container,
    screenData: any
  ) {
    this.scene = scene;
    this.container = container;

    this.buildUI(screenData);
  }

  // ── UI Construction ──────────────────────────────────────────────

  private buildUI(screenData: any) {
    const logs: LogEntry[] = screenData.logs || [];
    const maxVisible = 20;
    const hasMore = logs.length > maxVisible;
    const visibleLogs = logs.slice(0, maxVisible);

    const contentWidth = CONFIG.SCREEN_WIDTH;
    const contentHeight =
      CONFIG.SCREEN_HEIGHT - CONFIG.HUD_HEIGHT - CONFIG.CONNECTION_BAR_HEIGHT - 30;

    // Box dimensions
    const lineHeight = 22;
    const headerAreaH = 90;   // title + divider + column headers + underline
    const footerAreaH = 70;   // summary + back button
    const rowsH = Math.max(visibleLogs.length, 1) * lineHeight + (hasMore ? 24 : 0);
    const boxH = Math.min(
      Math.max(headerAreaH + rowsH + footerAreaH, 220),
      contentHeight - 40
    );
    const boxW = 700;
    const boxX = (contentWidth - boxW) / 2;
    const boxY = (contentHeight - boxH) / 2;

    // ── Border ──
    const gfx = this.scene.add.graphics();
    gfx.lineStyle(2, CONFIG.COLORS.GREEN, 1);
    gfx.strokeRect(boxX, boxY, boxW, boxH);
    gfx.lineStyle(1, CONFIG.COLORS.GREEN, 0.4);
    gfx.strokeRect(boxX + 4, boxY + 4, boxW - 8, boxH - 8);
    this.container.add(gfx);

    // ── Title ──
    const titleText = this.scene.add.text(
      contentWidth / 2,
      boxY + 28,
      'ACCESS LOGS',
      {
        fontFamily: 'Courier New',
        fontSize: '18px',
        color: CONFIG.COLOR_STR.CYAN,
      }
    ).setOrigin(0.5);
    this.container.add(titleText);

    // ── Divider below title ──
    const divider = this.scene.add.graphics();
    divider.lineStyle(1, CONFIG.COLORS.GREEN, 0.5);
    divider.lineBetween(boxX + 20, boxY + 48, boxX + boxW - 20, boxY + 48);
    this.container.add(divider);

    // ── Column layout ──
    const colX = {
      time: boxX + 30,
      ip: boxX + 200,
      subject: boxX + 370,
    };

    // ── Column headers ──
    const headerY = boxY + 60;
    const headerStyle: Phaser.Types.GameObjects.Text.TextStyle = {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.AMBER,
    };

    this.container.add(this.scene.add.text(colX.time, headerY, 'TIME', headerStyle));
    this.container.add(this.scene.add.text(colX.ip, headerY, 'FROM IP', headerStyle));
    this.container.add(this.scene.add.text(colX.subject, headerY, 'SUBJECT', headerStyle));

    // ── Header underline ──
    const headerDivider = this.scene.add.graphics();
    headerDivider.lineStyle(1, CONFIG.COLORS.GREEN, 0.3);
    headerDivider.lineBetween(boxX + 25, headerY + 18, boxX + boxW - 25, headerY + 18);
    this.container.add(headerDivider);

    // ── Log rows ──
    const rowStartY = headerY + 26;
    const rowStyle: Phaser.Types.GameObjects.Text.TextStyle = {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.GREEN,
    };

    if (logs.length === 0) {
      const emptyText = this.scene.add.text(
        contentWidth / 2,
        rowStartY + 10,
        'No access logs recorded.',
        {
          fontFamily: 'Courier New',
          fontSize: '13px',
          color: CONFIG.COLOR_STR.GREEN,
        }
      ).setOrigin(0.5);
      emptyText.setAlpha(0.6);
      this.container.add(emptyText);
    } else {
      for (let i = 0; i < visibleLogs.length; i++) {
        const log = visibleLogs[i];
        const rowY = rowStartY + i * lineHeight;

        // Truncate long subjects
        const displaySubject =
          log.subject.length > 36
            ? log.subject.substring(0, 33) + '...'
            : log.subject;

        this.container.add(this.scene.add.text(colX.time, rowY, log.log_time, rowStyle));
        this.container.add(this.scene.add.text(colX.ip, rowY, log.from_ip, rowStyle));
        this.container.add(this.scene.add.text(colX.subject, rowY, displaySubject, rowStyle));
      }

      // "..." indicator when there are more entries than shown
      if (hasMore) {
        const moreY = rowStartY + visibleLogs.length * lineHeight;
        const moreText = this.scene.add.text(
          contentWidth / 2,
          moreY + 4,
          `... and ${logs.length - maxVisible} more entries`,
          {
            fontFamily: 'Courier New',
            fontSize: '11px',
            color: CONFIG.COLOR_STR.GREEN,
          }
        ).setOrigin(0.5);
        moreText.setAlpha(0.5);
        this.container.add(moreText);
      }
    }

    // ── Summary ──
    const summaryY = boxY + boxH - footerAreaH + 10;
    const summaryStr = `${logs.length} log entr${logs.length !== 1 ? 'ies' : 'y'}`;
    const summaryText = this.scene.add.text(
      boxX + 30,
      summaryY,
      summaryStr,
      {
        fontFamily: 'Courier New',
        fontSize: '11px',
        color: CONFIG.COLOR_STR.GREEN,
      }
    );
    summaryText.setAlpha(0.6);
    this.container.add(summaryText);

    // ── Back button ──
    this.createBackButton(contentWidth / 2, boxY + boxH - 25);
  }

  /**
   * Creates the "BACK TO MENU" button.
   */
  private createBackButton(x: number, y: number) {
    const text = this.scene.add.text(x, y, '[ BACK TO MENU ]', {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setOrigin(0.5);
    this.container.add(text);

    text.setInteractive({ useHandCursor: true });

    text.on('pointerover', () => {
      text.setColor(CONFIG.COLOR_STR.CYAN);
    });

    text.on('pointerout', () => {
      text.setColor(CONFIG.COLOR_STR.GREEN);
    });

    text.on('pointerdown', () => {
      wsClient.send('screen_action', { action: 'go_back' });
    });
  }

  // ── Cleanup ──────────────────────────────────────────────────────

  destroy() {
    // No persistent listeners to clean up; all game objects are
    // managed by the container and destroyed with removeAll(true).
  }
}
