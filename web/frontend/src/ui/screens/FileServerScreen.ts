import Phaser from 'phaser';
import { CONFIG } from '../../config';
import { wsClient } from '../../net/WebSocketClient';

/** File type numeric ID to human-readable label. */
const FILE_TYPE_NAMES: Record<number, string> = {
  0: 'Data',
  1: 'Program',
  2: 'Text',
  3: 'Log',
};

interface FileEntry {
  id: number;
  filename: string;
  size: number;
  file_type: number;
  encrypted_level: number;
  owner: string | null;
}

/**
 * Terminal-style file listing screen.
 *
 * Displays the files stored on the remote computer in a tabular
 * layout with columns for filename, size, type, encryption level,
 * and owner. Each row is clickable (reserved for Phase 4 file
 * operations) and highlights on hover.
 *
 * All game objects are added to `container`.
 */
export class FileServerScreen {
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
    const files: FileEntry[] = screenData.files || [];

    const contentWidth = CONFIG.SCREEN_WIDTH;
    const contentHeight =
      CONFIG.SCREEN_HEIGHT - CONFIG.HUD_HEIGHT - CONFIG.CONNECTION_BAR_HEIGHT - 30;

    // Box dimensions — sized to fit the content
    const lineHeight = 24;
    const headerAreaH = 90;   // title + divider + column headers + header divider
    const footerAreaH = 70;   // summary + back button
    const rowsH = Math.max(files.length, 1) * lineHeight;
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
      'FILE SERVER',
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
      filename: boxX + 30,
      size: boxX + 340,
      type: boxX + 420,
      enc: boxX + 500,
      owner: boxX + 560,
    };

    // ── Column headers ──
    const headerY = boxY + 60;
    const headerStyle: Phaser.Types.GameObjects.Text.TextStyle = {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.AMBER,
    };

    this.container.add(this.scene.add.text(colX.filename, headerY, 'FILENAME', headerStyle));
    this.container.add(this.scene.add.text(colX.size, headerY, 'SIZE', headerStyle));
    this.container.add(this.scene.add.text(colX.type, headerY, 'TYPE', headerStyle));
    this.container.add(this.scene.add.text(colX.enc, headerY, 'ENC', headerStyle));
    this.container.add(this.scene.add.text(colX.owner, headerY, 'OWNER', headerStyle));

    // ── Header underline ──
    const headerDivider = this.scene.add.graphics();
    headerDivider.lineStyle(1, CONFIG.COLORS.GREEN, 0.3);
    headerDivider.lineBetween(boxX + 25, headerY + 18, boxX + boxW - 25, headerY + 18);
    this.container.add(headerDivider);

    // ── File rows ──
    const rowStartY = headerY + 26;
    const rowWidth = boxW - 50;

    if (files.length === 0) {
      const emptyText = this.scene.add.text(
        contentWidth / 2,
        rowStartY + 10,
        'No files on this server.',
        {
          fontFamily: 'Courier New',
          fontSize: '13px',
          color: CONFIG.COLOR_STR.GREEN,
        }
      ).setOrigin(0.5);
      emptyText.setAlpha(0.6);
      this.container.add(emptyText);
    } else {
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const rowY = rowStartY + i * lineHeight;
        this.createFileRow(file, colX, rowY, boxX + 25, rowWidth);
      }
    }

    // ── Summary ──
    const summaryY = boxY + boxH - footerAreaH + 10;
    const totalSize = files.reduce((acc, f) => acc + f.size, 0);
    const summaryStr = `${files.length} file${files.length !== 1 ? 's' : ''} | ${formatSize(totalSize)} total`;
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
   * Creates a single file row with hover highlight.
   */
  private createFileRow(
    file: FileEntry,
    colX: Record<string, number>,
    y: number,
    rowX: number,
    rowWidth: number
  ) {
    const rowStyle: Phaser.Types.GameObjects.Text.TextStyle = {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.GREEN,
    };

    const rowBg = this.scene.add.graphics();
    this.container.add(rowBg);

    // Truncate long filenames
    const displayName =
      file.filename.length > 30
        ? file.filename.substring(0, 27) + '...'
        : file.filename;

    const nameText = this.scene.add.text(colX.filename, y, displayName, rowStyle);
    const sizeText = this.scene.add.text(colX.size, y, formatSize(file.size), rowStyle);
    const typeText = this.scene.add.text(colX.type, y, FILE_TYPE_NAMES[file.file_type] || 'Unknown', rowStyle);
    const encText = this.scene.add.text(colX.enc, y, file.encrypted_level > 0 ? String(file.encrypted_level) : '-', rowStyle);
    const ownerText = this.scene.add.text(colX.owner, y, file.owner || '-', rowStyle);

    const rowTexts = [nameText, sizeText, typeText, encText, ownerText];
    rowTexts.forEach((t) => this.container.add(t));

    // Hit area for hover/click
    const hitArea = this.scene.add.rectangle(
      rowX + rowWidth / 2,
      y + 8,
      rowWidth,
      lineHeightConst
    )
      .setInteractive({ useHandCursor: true })
      .setAlpha(0.001);
    this.container.add(hitArea);

    hitArea.on('pointerover', () => {
      rowTexts.forEach((t) => t.setColor(CONFIG.COLOR_STR.CYAN));
      rowBg.clear();
      rowBg.fillStyle(CONFIG.COLORS.DARK_GREEN, 0.6);
      rowBg.fillRect(rowX, y - 2, rowWidth, lineHeightConst);
    });

    hitArea.on('pointerout', () => {
      rowTexts.forEach((t) => t.setColor(CONFIG.COLOR_STR.GREEN));
      rowBg.clear();
    });

    hitArea.on('pointerdown', () => {
      // Placeholder for Phase 4 file operations
      console.log(`[FileServerScreen] Clicked file: ${file.filename} (id=${file.id})`);
    });
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

// ── Helpers ──────────────────────────────────────────────────────────

const lineHeightConst = 24;

/** Formats a byte size into a human-readable string (e.g. "4k", "1.2M"). */
function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}b`;
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)}k`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}M`;
}
