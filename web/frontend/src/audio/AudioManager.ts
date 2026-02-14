/**
 * AudioManager - Generates retro synth sounds for the Uplink UI.
 * Uses Web Audio API to create beeps, clicks, and alarm tones.
 * All sounds are procedurally generated (no audio files needed).
 */
export class AudioManager {
  private ctx: AudioContext | null = null;
  private muted: boolean = false;

  private getContext(): AudioContext {
    if (!this.ctx) {
      this.ctx = new AudioContext();
    }
    return this.ctx;
  }

  /**
   * Helper to play a single tone with given parameters.
   */
  private playTone(
    frequency: number,
    duration: number,
    volume: number,
    type: OscillatorType,
    startDelay: number = 0,
  ): void {
    if (this.muted) return;

    const ctx = this.getContext();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();

    osc.type = type;
    osc.frequency.value = frequency;
    gain.gain.value = volume;

    osc.connect(gain);
    gain.connect(ctx.destination);

    const startTime = ctx.currentTime + startDelay;
    const endTime = startTime + duration;

    osc.start(startTime);
    // Quick fade-out to avoid clicks
    gain.gain.setValueAtTime(volume, endTime - 0.005);
    gain.gain.linearRampToValueAtTime(0, endTime);
    osc.stop(endTime + 0.01);
  }

  /** Short UI click/beep for button presses */
  playClick(): void {
    this.playTone(800, 0.05, 0.1, 'square');
  }

  /** Confirmation beep (higher pitch, slightly longer) */
  playConfirm(): void {
    this.playTone(1200, 0.1, 0.15, 'sine');
  }

  /** Error buzz (low frequency, short) */
  playError(): void {
    this.playTone(200, 0.15, 0.2, 'sawtooth');
  }

  /** Connection established sound (ascending two-tone) */
  playConnect(): void {
    this.playTone(600, 0.08, 0.15, 'sine', 0);
    this.playTone(900, 0.08, 0.15, 'sine', 0.08);
  }

  /** Disconnection sound (descending two-tone) */
  playDisconnect(): void {
    this.playTone(900, 0.08, 0.15, 'sine', 0);
    this.playTone(600, 0.08, 0.15, 'sine', 0.08);
  }

  /**
   * Trace alarm - escalating beep that gets faster as trace progresses.
   * Call this repeatedly with increasing progress (0.0 to 1.0).
   * At low progress: slow beeps. At high progress: rapid beeping.
   */
  playTraceAlarm(progress: number): void {
    const clampedProgress = Math.max(0, Math.min(1, progress));
    const frequency = 440 * (1 + clampedProgress);
    const duration = 0.1 * (1 - clampedProgress * 0.7);
    const volume = 0.15 + clampedProgress * 0.15;

    this.playTone(frequency, duration, volume, 'square');
  }

  /** Task complete chime */
  playTaskComplete(): void {
    this.playTone(800, 0.06, 0.15, 'sine', 0);
    this.playTone(1200, 0.06, 0.15, 'sine', 0.06);
    this.playTone(1600, 0.06, 0.15, 'sine', 0.12);
  }

  /** Toggle mute */
  toggleMute(): boolean {
    this.muted = !this.muted;
    return this.muted;
  }

  /** Check if muted */
  isMuted(): boolean {
    return this.muted;
  }
}

export const audioManager = new AudioManager();
