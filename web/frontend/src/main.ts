import Phaser from 'phaser';
import { CONFIG } from './config';
import { BootScene } from './scenes/BootScene';
import { PreloadScene } from './scenes/PreloadScene';
import { LoginScene } from './scenes/LoginScene';
import { MainGameScene } from './scenes/MainGameScene';
import { RemoteScreenScene } from './scenes/RemoteScreenScene';
import { TaskManagerScene } from './scenes/TaskManagerScene';
import { GameOverScene } from './scenes/GameOverScene';

const config: Phaser.Types.Core.GameConfig = {
  type: Phaser.AUTO,
  parent: 'game-container',
  width: CONFIG.SCREEN_WIDTH,
  height: CONFIG.SCREEN_HEIGHT,
  backgroundColor: '#000000',
  scene: [BootScene, PreloadScene, LoginScene, MainGameScene, RemoteScreenScene, TaskManagerScene, GameOverScene],
  render: {
    pixelArt: false,
    antialias: true,
  },
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH,
  },
};

new Phaser.Game(config);
