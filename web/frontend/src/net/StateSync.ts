import { LocationData, PlayerData, WorldData, BounceNode, ScreenData, TaskData, MessageData, MissionData } from './MessageTypes';

export class GameState {
  locations: LocationData[] = [];
  playerData: PlayerData | null = null;
  sessionId: string = '';
  token: string = '';

  // Connection state
  bounceChain: BounceNode[] = [];
  isConnected: boolean = false;
  targetIp: string | null = null;
  currentScreen: ScreenData | null = null;
  traceProgress: number = 0;
  traceActive: boolean = false;
  tracedNodes: string[] = [];

  // Running hacking tools
  runningTasks: TaskData[] = [];

  // Messages and missions
  messages: MessageData[] = [];
  acceptedMissions: MissionData[] = [];

  setWorldData(data: WorldData) {
    this.locations = data.locations;
  }

  setPlayerData(data: PlayerData) {
    this.playerData = data;
  }

  setSession(sessionId: string, token: string) {
    this.sessionId = sessionId;
    this.token = token;
  }

  setBounceChain(nodes: BounceNode[]) {
    this.bounceChain = nodes;
  }

  setConnected(targetIp: string, screen: ScreenData) {
    this.isConnected = true;
    this.targetIp = targetIp;
    this.currentScreen = screen;
  }

  setDisconnected() {
    this.isConnected = false;
    this.targetIp = null;
    this.currentScreen = null;
    this.traceProgress = 0;
    this.traceActive = false;
    this.tracedNodes = [];
  }

  setCurrentScreen(screen: ScreenData) {
    this.currentScreen = screen;
  }

  setTraceState(progress: number, active: boolean, tracedNodes?: string[]) {
    this.traceProgress = progress;
    this.traceActive = active;
    if (tracedNodes) {
      this.tracedNodes = tracedNodes;
    }
  }

  updateTask(task: TaskData) {
    const idx = this.runningTasks.findIndex(t => t.task_id === task.task_id);
    if (idx >= 0) {
      this.runningTasks[idx] = task;
    } else {
      this.runningTasks.push(task);
    }
  }

  removeTask(taskId: number) {
    this.runningTasks = this.runningTasks.filter(t => t.task_id !== taskId);
  }

  setMessages(msgs: MessageData[]) {
    this.messages = msgs;
  }

  addMessage(msg: MessageData) {
    this.messages.unshift(msg);
  }

  markMessageRead(id: number) {
    const msg = this.messages.find(m => m.id === id);
    if (msg) msg.is_read = true;
  }

  setAcceptedMissions(missions: MissionData[]) {
    this.acceptedMissions = missions;
  }

  addAcceptedMission(mission: MissionData) {
    this.acceptedMissions.push(mission);
  }

  removeMission(id: number) {
    this.acceptedMissions = this.acceptedMissions.filter(m => m.id !== id);
  }
}

export const gameState = new GameState();
