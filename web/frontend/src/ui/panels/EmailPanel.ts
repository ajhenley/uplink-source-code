import Phaser from 'phaser';
import { CONFIG } from '../../config';
import { restClient } from '../../net/RestClient';
import { gameState } from '../../net/StateSync';
import type { MessageData } from '../../net/MessageTypes';

/**
 * EmailPanel: a popup overlay that shows the player's email inbox.
 *
 * Opened via the HUD "Email" toolbar button. Fetches messages from
 * the REST API and displays them in a scrollable list. Clicking a
 * message reveals its full body in a detail view.
 */
export class EmailPanel {
  private scene: Phaser.Scene;
  private container: Phaser.GameObjects.Container;
  private visible: boolean = false;

  // Panel layout constants
  private readonly PANEL_W = 500;
  private readonly PANEL_H = 450;
  private readonly panelX: number;
  private readonly panelY: number;

  constructor(scene: Phaser.Scene) {
    this.scene = scene;
    this.panelX = (CONFIG.SCREEN_WIDTH - this.PANEL_W) / 2;
    this.panelY = (CONFIG.SCREEN_HEIGHT - this.PANEL_H) / 2;

    this.container = scene.add.container(0, 0);
    this.container.setVisible(false);
    this.container.setDepth(200);
  }

  toggle() {
    this.visible = !this.visible;
    this.container.setVisible(this.visible);
    if (this.visible) {
      this.fetchAndRender();
    }
  }

  isVisible(): boolean {
    return this.visible;
  }

  private async fetchAndRender() {
    try {
      const messages = await restClient.get<MessageData[]>(
        `/api/player/${gameState.sessionId}/messages`
      );
      gameState.setMessages(messages);
    } catch (err) {
      console.error('[EmailPanel] Failed to fetch messages:', err);
    }
    this.renderInbox();
  }

  private renderInbox() {
    this.container.removeAll(true);

    const { panelX: x, panelY: y, PANEL_W: w, PANEL_H: h } = this;

    // Background
    const bg = this.scene.add.graphics();
    bg.fillStyle(0x001100, 0.95);
    bg.fillRect(x, y, w, h);
    bg.lineStyle(2, CONFIG.COLORS.GREEN, 1);
    bg.strokeRect(x, y, w, h);
    bg.lineStyle(1, CONFIG.COLORS.GREEN, 0.4);
    bg.strokeRect(x + 3, y + 3, w - 6, h - 6);
    this.container.add(bg);

    // Title
    const title = this.scene.add.text(x + w / 2, y + 20, 'EMAIL INBOX', {
      fontFamily: 'Courier New',
      fontSize: '16px',
      color: CONFIG.COLOR_STR.CYAN,
    }).setOrigin(0.5);
    this.container.add(title);

    // Divider
    const divider = this.scene.add.graphics();
    divider.lineStyle(1, CONFIG.COLORS.GREEN, 0.5);
    divider.lineBetween(x + 15, y + 38, x + w - 15, y + 38);
    this.container.add(divider);

    // Close button
    this.createCloseButton(x + w - 20, y + 12);

    // Message list
    const messages = gameState.messages;
    const listStartY = y + 50;
    const itemH = 36;
    const maxVisible = Math.floor((h - 80) / itemH);

    if (messages.length === 0) {
      const empty = this.scene.add.text(x + w / 2, listStartY + 40, 'No messages.', {
        fontFamily: 'Courier New',
        fontSize: '13px',
        color: CONFIG.COLOR_STR.GREEN,
      }).setOrigin(0.5).setAlpha(0.6);
      this.container.add(empty);
    } else {
      const visibleMsgs = messages.slice(0, maxVisible);
      for (let i = 0; i < visibleMsgs.length; i++) {
        const msg = visibleMsgs[i];
        const itemY = listStartY + i * itemH;
        this.renderMessageRow(msg, x + 15, itemY, w - 30);
      }
    }
  }

  private renderMessageRow(msg: MessageData, x: number, y: number, w: number) {
    // Unread indicator
    if (!msg.is_read) {
      const dot = this.scene.add.graphics();
      dot.fillStyle(CONFIG.COLORS.CYAN, 1);
      dot.fillCircle(x + 6, y + 12, 4);
      this.container.add(dot);
    }

    // From name
    const fromText = this.scene.add.text(x + 18, y + 4, msg.from_name, {
      fontFamily: 'Courier New',
      fontSize: '11px',
      color: msg.is_read ? CONFIG.COLOR_STR.GREEN : CONFIG.COLOR_STR.CYAN,
    });
    this.container.add(fromText);

    // Subject (truncated)
    const maxSubLen = 45;
    const displaySubject = msg.subject.length > maxSubLen
      ? msg.subject.substring(0, maxSubLen - 3) + '...'
      : msg.subject;

    const subjectText = this.scene.add.text(x + 18, y + 18, displaySubject, {
      fontFamily: 'Courier New',
      fontSize: '10px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setAlpha(0.7);
    this.container.add(subjectText);

    // Row separator
    const sep = this.scene.add.graphics();
    sep.lineStyle(1, CONFIG.COLORS.GREEN, 0.2);
    sep.lineBetween(x, y + 34, x + w, y + 34);
    this.container.add(sep);

    // Hit area for clicking the row
    const hitArea = this.scene.add.rectangle(x + w / 2, y + 17, w, 34)
      .setInteractive({ useHandCursor: true })
      .setAlpha(0.001);
    this.container.add(hitArea);

    hitArea.on('pointerover', () => {
      fromText.setColor(CONFIG.COLOR_STR.CYAN);
      subjectText.setColor(CONFIG.COLOR_STR.CYAN).setAlpha(1);
    });
    hitArea.on('pointerout', () => {
      fromText.setColor(msg.is_read ? CONFIG.COLOR_STR.GREEN : CONFIG.COLOR_STR.CYAN);
      subjectText.setColor(CONFIG.COLOR_STR.GREEN).setAlpha(0.7);
    });
    hitArea.on('pointerdown', () => {
      this.showMessageDetail(msg);
    });
  }

  private async showMessageDetail(msg: MessageData) {
    // Mark as read on server
    if (!msg.is_read) {
      try {
        await restClient.post(
          `/api/player/${gameState.sessionId}/messages/${msg.id}/read`,
          {}
        );
        gameState.markMessageRead(msg.id);
      } catch (err) {
        console.error('[EmailPanel] Failed to mark message read:', err);
      }
    }

    this.container.removeAll(true);

    const { panelX: x, panelY: y, PANEL_W: w, PANEL_H: h } = this;

    // Background
    const bg = this.scene.add.graphics();
    bg.fillStyle(0x001100, 0.95);
    bg.fillRect(x, y, w, h);
    bg.lineStyle(2, CONFIG.COLORS.GREEN, 1);
    bg.strokeRect(x, y, w, h);
    bg.lineStyle(1, CONFIG.COLORS.GREEN, 0.4);
    bg.strokeRect(x + 3, y + 3, w - 6, h - 6);
    this.container.add(bg);

    // Close button
    this.createCloseButton(x + w - 20, y + 12);

    // From
    const fromLabel = this.scene.add.text(x + 20, y + 18, `From: ${msg.from_name}`, {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.CYAN,
    });
    this.container.add(fromLabel);

    // Subject
    const subjectLabel = this.scene.add.text(x + 20, y + 38, `Subject: ${msg.subject}`, {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.AMBER,
    });
    this.container.add(subjectLabel);

    // Divider
    const divider = this.scene.add.graphics();
    divider.lineStyle(1, CONFIG.COLORS.GREEN, 0.5);
    divider.lineBetween(x + 15, y + 58, x + w - 15, y + 58);
    this.container.add(divider);

    // Body text with word wrap
    const bodyText = this.scene.add.text(x + 20, y + 68, msg.body, {
      fontFamily: 'Courier New',
      fontSize: '11px',
      color: CONFIG.COLOR_STR.GREEN,
      wordWrap: { width: w - 50 },
      lineSpacing: 4,
    });
    this.container.add(bodyText);

    // Back button
    const backBtn = this.scene.add.text(x + w / 2, y + h - 25, '[ BACK TO INBOX ]', {
      fontFamily: 'Courier New',
      fontSize: '12px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setOrigin(0.5).setInteractive({ useHandCursor: true });
    this.container.add(backBtn);

    backBtn.on('pointerover', () => backBtn.setColor(CONFIG.COLOR_STR.CYAN));
    backBtn.on('pointerout', () => backBtn.setColor(CONFIG.COLOR_STR.GREEN));
    backBtn.on('pointerdown', () => this.renderInbox());
  }

  private createCloseButton(x: number, y: number) {
    const closeBtn = this.scene.add.text(x, y, 'X', {
      fontFamily: 'Courier New',
      fontSize: '14px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setOrigin(0.5).setInteractive({ useHandCursor: true });
    this.container.add(closeBtn);

    closeBtn.on('pointerover', () => closeBtn.setColor(CONFIG.COLOR_STR.RED));
    closeBtn.on('pointerout', () => closeBtn.setColor(CONFIG.COLOR_STR.GREEN));
    closeBtn.on('pointerdown', () => {
      this.visible = false;
      this.container.setVisible(false);
    });
  }

  getUnreadCount(): number {
    return gameState.messages.filter(m => !m.is_read).length;
  }

  destroy() {
    this.container.destroy(true);
  }
}
