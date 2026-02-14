import Phaser from 'phaser';
import { CONFIG } from '../../config';
import { PasswordScreen } from './PasswordScreen';
import { MenuScreen } from './MenuScreen';
import { DisconnectedScreen } from './DisconnectedScreen';
import { SWSalesScreen } from './SWSalesScreen';
import { HWSalesScreen } from './HWSalesScreen';
import { HighSecurityScreen } from './HighSecurityScreen';
import { FileServerScreen } from './FileServerScreen';
import { LogScreen } from './LogScreen';
import { BBSScreen } from './BBSScreen';
import { MessageScreen } from './MessageScreen';

// Screen type constants matching the original Uplink remote interface screen IDs
const SCREEN_MESSAGESCREEN = 1;
const SCREEN_PASSWORDSCREEN = 2;
const SCREEN_MENUSCREEN = 3;
const SCREEN_BBSSCREEN = 4;
const SCREEN_FILESERVERSCREEN = 6;
const SCREEN_LOGSCREEN = 8;
const SCREEN_SWSALESSCREEN = 9;
const SCREEN_HWSALESSCREEN = 10;
const SCREEN_HIGHSECURITYSCREEN = 30;
const SCREEN_DISCONNECTEDSCREEN = 34;

/**
 * PlaceholderScreen -- rendered for any screen_type that hasn't been
 * implemented yet (FileServer, LogScreen, BBS, etc. come in Phase 3).
 */
class PlaceholderScreen {
  constructor(
    scene: Phaser.Scene,
    container: Phaser.GameObjects.Container,
    screenData: { screen_type: number }
  ) {
    const contentHeight =
      CONFIG.SCREEN_HEIGHT - CONFIG.HUD_HEIGHT - CONFIG.CONNECTION_BAR_HEIGHT - 30;
    const contentWidth = CONFIG.SCREEN_WIDTH;

    // Border box
    const gfx = scene.add.graphics();
    const boxW = 440;
    const boxH = 120;
    const boxX = (contentWidth - boxW) / 2;
    const boxY = (contentHeight - boxH) / 2;

    gfx.lineStyle(1, CONFIG.COLORS.GREEN, 0.6);
    gfx.strokeRect(boxX, boxY, boxW, boxH);

    container.add(gfx);

    // "Not yet implemented" text
    const titleText = scene.add.text(
      contentWidth / 2,
      boxY + 30,
      `Screen type ${screenData.screen_type}`,
      {
        fontFamily: 'Courier New',
        fontSize: '16px',
        color: CONFIG.COLOR_STR.AMBER,
      }
    ).setOrigin(0.5);

    container.add(titleText);

    const subtitleText = scene.add.text(
      contentWidth / 2,
      boxY + 60,
      'Not yet implemented',
      {
        fontFamily: 'Courier New',
        fontSize: '14px',
        color: CONFIG.COLOR_STR.GREEN,
      }
    ).setOrigin(0.5);

    container.add(subtitleText);

    const hintText = scene.add.text(
      contentWidth / 2,
      boxY + 85,
      'This screen will be available in a future update.',
      {
        fontFamily: 'Courier New',
        fontSize: '11px',
        color: CONFIG.COLOR_STR.GREEN,
      }
    ).setOrigin(0.5);
    hintText.setAlpha(0.6);

    container.add(hintText);
  }

  destroy() {
    // Nothing to clean up for the placeholder
  }
}

export class ScreenFactory {
  /**
   * Creates the appropriate screen renderer based on screenData.screen_type.
   * All Phaser game objects are added to `container` so RemoteScreenScene can
   * manage their lifecycle (removeAll on screen transitions).
   */
  static create(
    scene: Phaser.Scene,
    container: Phaser.GameObjects.Container,
    screenData: any
  ): { destroy?: () => void } {
    switch (screenData.screen_type) {
      case SCREEN_PASSWORDSCREEN:
        return new PasswordScreen(scene, container, screenData);

      case SCREEN_MENUSCREEN:
        return new MenuScreen(scene, container, screenData);

      case SCREEN_SWSALESSCREEN:
        return new SWSalesScreen(scene, container, screenData);

      case SCREEN_HWSALESSCREEN:
        return new HWSalesScreen(scene, container, screenData);

      case SCREEN_HIGHSECURITYSCREEN:
        return new HighSecurityScreen(scene, container, screenData);

      case SCREEN_DISCONNECTEDSCREEN:
        return new DisconnectedScreen(scene, container, screenData);

      case SCREEN_MESSAGESCREEN:
        return new MessageScreen(scene, container, screenData);

      case SCREEN_BBSSCREEN:
        return new BBSScreen(scene, container, screenData);

      case SCREEN_FILESERVERSCREEN:
        return new FileServerScreen(scene, container, screenData);

      case SCREEN_LOGSCREEN:
        return new LogScreen(scene, container, screenData);

      default:
        return new PlaceholderScreen(scene, container, screenData);
    }
  }
}
