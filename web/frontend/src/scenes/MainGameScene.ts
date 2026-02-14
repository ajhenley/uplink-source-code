import Phaser from 'phaser';
import { CONFIG } from '../config';
import { restClient } from '../net/RestClient';
import { wsClient } from '../net/WebSocketClient';
import { gameState } from '../net/StateSync';
import { audioManager } from '../audio/AudioManager';
import { WorldMap } from '../ui/WorldMap';
import { HUD } from '../ui/HUD';
import { ConnectionBar } from '../ui/ConnectionBar';
import { CRTOverlay } from '../ui/CRTOverlay';
import type { WorldData, PlayerData, BounceNode, ScreenData, TaskData, MessageData, MissionData } from '../net/MessageTypes';

export class MainGameScene extends Phaser.Scene {
  private worldMap!: WorldMap;
  private hud!: HUD;
  private connectionBar!: ConnectionBar;
  private lastTraceAlarmTime: number = 0;

  constructor() {
    super({ key: 'MainGameScene' });
  }

  async create() {
    // Load world data from server
    try {
      const worldData = await restClient.get<WorldData>(
        `/api/game/${gameState.sessionId}/world`
      );
      gameState.setWorldData(worldData);

      const playerData = await restClient.get<PlayerData>(
        `/api/game/${gameState.sessionId}/player`
      );
      gameState.setPlayerData(playerData);

      // Load messages and accepted missions
      const messages = await restClient.get<MessageData[]>(
        `/api/player/${gameState.sessionId}/messages`
      );
      gameState.setMessages(messages);

      const missions = await restClient.get<MissionData[]>(
        `/api/player/${gameState.sessionId}/missions`
      );
      gameState.setAcceptedMissions(missions);
    } catch (err) {
      console.error('Failed to load game data:', err);
    }

    // Create HUD at top
    this.hud = new HUD(this);

    // Create world map in center
    this.worldMap = new WorldMap(this);

    // Create connection bar at bottom
    this.connectionBar = new ConnectionBar(this);

    // Connect WebSocket
    wsClient.connect(gameState.token, gameState.sessionId);

    // Launch the TaskManager overlay scene
    this.scene.launch('TaskManagerScene');

    // Register WebSocket event handlers for connection system
    wsClient.on('bounce_chain_updated', (data) => {
      gameState.setBounceChain(data.nodes as BounceNode[]);
    });

    wsClient.on('connected', (data) => {
      const screen = data.screen as ScreenData;
      const targetIp = data.target_ip as string;
      gameState.setConnected(targetIp, screen);
      audioManager.playConnect();
      // Launch remote screen overlay
      this.scene.launch('RemoteScreenScene', { screen });
    });

    wsClient.on('disconnected', () => {
      gameState.setDisconnected();
      audioManager.playDisconnect();
      // Stop remote screen overlay if running
      if (this.scene.isActive('RemoteScreenScene')) {
        this.scene.stop('RemoteScreenScene');
      }
    });

    wsClient.on('screen_update', (data) => {
      gameState.setCurrentScreen(data.screen as ScreenData);
    });

    wsClient.on('trace_update', (data) => {
      gameState.setTraceState(
        data.progress as number,
        data.active as boolean,
        data.traced_nodes as string[] | undefined,
      );
      // Play trace alarm sound, throttled to every 2 seconds
      if (data.active) {
        const now = Date.now();
        if (now - this.lastTraceAlarmTime >= 2000) {
          this.lastTraceAlarmTime = now;
          audioManager.playTraceAlarm(data.progress as number);
        }
      }
    });

    wsClient.on('game_over', (data) => {
      // Stop all overlay scenes
      if (this.scene.isActive('RemoteScreenScene')) {
        this.scene.stop('RemoteScreenScene');
      }
      if (this.scene.isActive('TaskManagerScene')) {
        this.scene.stop('TaskManagerScene');
      }
      this.scene.start('GameOverScene', { reason: data.reason });
    });

    wsClient.on('error', (data) => {
      console.error('Server error:', data.detail);
      audioManager.playError();
    });

    // Hacking tool task updates
    wsClient.on('task_update', (data) => {
      const tasks = data.tasks as TaskData[];
      for (const task of tasks) {
        gameState.updateTask(task);
      }
    });

    wsClient.on('task_complete', (data) => {
      const task = data.task as TaskData;
      gameState.removeTask(task.task_id);
      audioManager.playTaskComplete();
    });

    // Balance and rating updates
    wsClient.on('balance_changed', (data) => {
      if (gameState.playerData) {
        gameState.playerData.balance = data.balance as number;
      }
      this.hud.updateBalance(data.balance as number);
    });

    wsClient.on('rating_changed', (data) => {
      if (gameState.playerData) {
        gameState.playerData.uplink_rating = data.uplink_rating as number;
      }
      this.hud.updateRating(data.uplink_rating as number);
    });

    // Message and mission events
    wsClient.on('message_received', (data) => {
      const msg = data.message as MessageData;
      gameState.addMessage(msg);
      this.hud.updateUnreadIndicator();
    });

    wsClient.on('mission_accepted', (data) => {
      const mission = data.mission as MissionData;
      gameState.addAcceptedMission(mission);
    });

    wsClient.on('mission_completed', (data) => {
      gameState.removeMission(data.mission_id as number);
      this.hud.getMissionPanel().showCompletionFlash();
    });

    // Start heartbeat
    this.time.addEvent({
      delay: 10000,
      loop: true,
      callback: () => wsClient.send('heartbeat'),
    });

    // CRT scanline overlay for retro aesthetic
    new CRTOverlay(this);
  }

  update() {
    // Update world map animations (pulsing dots, etc.)
    if (this.worldMap) {
      this.worldMap.update();
    }

    // Update connection bar display
    if (this.connectionBar) {
      this.connectionBar.update();
    }
  }
}
