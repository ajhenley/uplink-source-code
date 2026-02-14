import Phaser from 'phaser';
import { CONFIG } from '../../config';
import { wsClient } from '../../net/WebSocketClient';

/** Rating index to display name, matching the original Uplink rating table. */
const RATING_NAMES: string[] = [
  'Unregistered',
  'Registered',
  'Beginner',
  'Novice',
  'Confident',
  'Intermediate',
  'Skilled',
  'Experienced',
  'Knowledgeable',
  'Uber-Skilled',
  'Professional',
  'Elite',
  'Mage',
  'Expert',
  'Veteren',
  'Techno-mage',
  'TERMINAL',
];

interface Mission {
  id: number;
  description: string;
  employer: string;
  payment: number;
  difficulty: number;
  min_rating: number;
}

/**
 * Bulletin Board System screen.
 *
 * Shows available contracts / missions that the player can accept.
 * Each mission is rendered as a bordered card with description,
 * employer, payment, difficulty bar, and an ACCEPT button.
 * Displays up to 5 missions (scrolling is deferred to a later phase).
 *
 * All game objects are added to `container`.
 */
export class BBSScreen {
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
    const missions: Mission[] = (screenData.missions || []).slice(0, 5);

    const contentWidth = CONFIG.SCREEN_WIDTH;
    const contentHeight =
      CONFIG.SCREEN_HEIGHT - CONFIG.HUD_HEIGHT - CONFIG.CONNECTION_BAR_HEIGHT - 30;

    // Box dimensions
    const cardHeight = 90;
    const cardGap = 10;
    const headerAreaH = 80;  // title + divider + "Available Contracts"
    const footerAreaH = 50;  // back button
    const cardsAreaH = missions.length > 0
      ? missions.length * cardHeight + (missions.length - 1) * cardGap
      : 30;
    const boxH = Math.min(
      Math.max(headerAreaH + cardsAreaH + footerAreaH + 20, 220),
      contentHeight - 20
    );
    const boxW = 700;
    const boxX = (contentWidth - boxW) / 2;
    const boxY = Math.max((contentHeight - boxH) / 2, 10);

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
      'BULLETIN BOARD SYSTEM',
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

    // ── Sub-header ──
    const subHeader = this.scene.add.text(
      boxX + 30,
      boxY + 58,
      'Available Contracts:',
      {
        fontFamily: 'Courier New',
        fontSize: '13px',
        color: CONFIG.COLOR_STR.GREEN,
      }
    );
    this.container.add(subHeader);

    // ── Mission cards ──
    const cardsStartY = boxY + headerAreaH;

    if (missions.length === 0) {
      const emptyText = this.scene.add.text(
        contentWidth / 2,
        cardsStartY + 10,
        'No contracts available at your clearance level.',
        {
          fontFamily: 'Courier New',
          fontSize: '13px',
          color: CONFIG.COLOR_STR.GREEN,
        }
      ).setOrigin(0.5);
      emptyText.setAlpha(0.6);
      this.container.add(emptyText);
    } else {
      for (let i = 0; i < missions.length; i++) {
        const mission = missions[i];
        const cardY = cardsStartY + i * (cardHeight + cardGap);
        this.createMissionCard(mission, boxX + 25, cardY, boxW - 50, cardHeight);
      }
    }

    // ── Back button ──
    this.createBackButton(contentWidth / 2, boxY + boxH - 25);
  }

  /**
   * Creates a bordered mission card with description, employer, payment,
   * difficulty bar, minimum rating, and an ACCEPT button.
   */
  private createMissionCard(
    mission: Mission,
    x: number,
    y: number,
    w: number,
    h: number
  ) {
    // Card border
    const cardGfx = this.scene.add.graphics();
    cardGfx.lineStyle(1, CONFIG.COLORS.GREEN, 0.6);
    cardGfx.strokeRect(x, y, w, h);
    this.container.add(cardGfx);

    // Description (first line, may need truncation)
    const maxDescLen = 70;
    const displayDesc =
      mission.description.length > maxDescLen
        ? mission.description.substring(0, maxDescLen - 3) + '...'
        : mission.description;

    const descText = this.scene.add.text(
      x + 12,
      y + 10,
      displayDesc,
      {
        fontFamily: 'Courier New',
        fontSize: '12px',
        color: CONFIG.COLOR_STR.GREEN,
      }
    );
    this.container.add(descText);

    // Employer and payment line
    const paymentStr = `${mission.payment.toLocaleString()}c`;
    const detailText = this.scene.add.text(
      x + 12,
      y + 32,
      `Employer: ${mission.employer}    Payment: ${paymentStr}`,
      {
        fontFamily: 'Courier New',
        fontSize: '11px',
        color: CONFIG.COLOR_STR.AMBER,
      }
    );
    this.container.add(detailText);

    // Difficulty bar and rating line
    const difficultyBar = this.buildDifficultyBar(mission.difficulty);
    const ratingName = RATING_NAMES[mission.min_rating] || 'Unknown';

    const diffText = this.scene.add.text(
      x + 12,
      y + 52,
      `Difficulty: ${difficultyBar}    Rating Required: ${ratingName}`,
      {
        fontFamily: 'Courier New',
        fontSize: '11px',
        color: CONFIG.COLOR_STR.GREEN,
      }
    );
    this.container.add(diffText);

    // ACCEPT button
    const acceptBtn = this.scene.add.text(x + w - 90, y + h - 22, '[ ACCEPT ]', {
      fontFamily: 'Courier New',
      fontSize: '11px',
      color: CONFIG.COLOR_STR.GREEN,
    }).setOrigin(0.5).setInteractive({ useHandCursor: true });
    this.container.add(acceptBtn);

    acceptBtn.on('pointerover', () => {
      if (acceptBtn.text === '[ ACCEPT ]') {
        acceptBtn.setColor(CONFIG.COLOR_STR.CYAN);
      }
    });
    acceptBtn.on('pointerout', () => {
      if (acceptBtn.text === '[ ACCEPT ]') {
        acceptBtn.setColor(CONFIG.COLOR_STR.GREEN);
      }
    });
    acceptBtn.on('pointerdown', () => {
      wsClient.send('accept_mission', { mission_id: mission.id });
      acceptBtn.setText('ACCEPTED');
      acceptBtn.setColor(CONFIG.COLOR_STR.CYAN);
      acceptBtn.disableInteractive();
    });
  }

  /**
   * Builds a simple 5-block difficulty bar, e.g. "###--" for difficulty 3.
   */
  private buildDifficultyBar(difficulty: number): string {
    const clamped = Math.max(0, Math.min(5, difficulty));
    const filled = '#'.repeat(clamped);
    const empty = '-'.repeat(5 - clamped);
    return filled + empty;
  }

  /**
   * Creates a small inline text button (used inside mission cards).
   */
  private createCardButton(label: string, x: number, y: number, onClick: () => void) {
    const text = this.scene.add.text(x, y, label, {
      fontFamily: 'Courier New',
      fontSize: '11px',
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

    text.on('pointerdown', onClick);
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
