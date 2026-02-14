import Phaser from 'phaser';
import { CONFIG } from '../config';

/**
 * Adds a subtle CRT scanline overlay to the entire game canvas.
 * Creates horizontal semi-transparent lines and a slight vignette.
 */
export class CRTOverlay {
  constructor(scene: Phaser.Scene) {
    // Create a full-screen graphics overlay at very high depth
    const gfx = scene.add.graphics();
    gfx.setDepth(9999); // Always on top

    // Horizontal scanlines (every 3rd pixel)
    gfx.fillStyle(0x000000, 0.08);
    for (let y = 0; y < CONFIG.SCREEN_HEIGHT; y += 3) {
      gfx.fillRect(0, y, CONFIG.SCREEN_WIDTH, 1);
    }

    // Subtle vignette effect at edges
    // Use a radial gradient approximation with concentric rectangles
    const vignetteAlpha = [0.15, 0.1, 0.07, 0.04, 0.02];
    for (let i = 0; i < vignetteAlpha.length; i++) {
      const margin = i * 3;
      gfx.lineStyle(3, 0x000000, vignetteAlpha[i]);
      gfx.strokeRect(margin, margin,
        CONFIG.SCREEN_WIDTH - margin * 2,
        CONFIG.SCREEN_HEIGHT - margin * 2);
    }
  }
}
