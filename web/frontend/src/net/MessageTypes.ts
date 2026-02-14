// Client -> Server
export const MSG_HEARTBEAT = 'heartbeat';
export const MSG_BOUNCE_ADD = 'bounce_add';
export const MSG_BOUNCE_REMOVE = 'bounce_remove';
export const MSG_CONNECT = 'connect';
export const MSG_DISCONNECT = 'disconnect';
export const MSG_SCREEN_ACTION = 'screen_action';
export const MSG_RUN_TOOL = 'run_tool';
export const MSG_SET_TOOL_TARGET = 'set_tool_target';
export const MSG_STOP_TOOL = 'stop_tool';
export const MSG_SET_SPEED = 'set_speed';

// Server -> Client
export const MSG_HEARTBEAT_ACK = 'heartbeat_ack';
export const MSG_BOUNCE_CHAIN_UPDATED = 'bounce_chain_updated';
export const MSG_CONNECTED = 'connected';
export const MSG_DISCONNECTED = 'disconnected';
export const MSG_SCREEN_UPDATE = 'screen_update';
export const MSG_TASK_UPDATE = 'task_update';
export const MSG_TASK_COMPLETE = 'task_complete';
export const MSG_TRACE_UPDATE = 'trace_update';
export const MSG_TRACE_COMPLETE = 'trace_complete';
export const MSG_BALANCE_CHANGED = 'balance_changed';
export const MSG_RATING_CHANGED = 'rating_changed';
export const MSG_MESSAGE_RECEIVED = 'message_received';
export const MSG_GAME_OVER = 'game_over';
export const MSG_ERROR = 'error';

export interface LocationData {
  ip: string;
  x: number;
  y: number;
}

export interface CompanyData {
  name: string;
  size: number;
}

export interface PlayerData {
  id: number;
  name: string;
  handle: string;
  balance: number;
  uplink_rating: number;
  neuromancer_rating: number;
  credit_rating: number;
  localhost_ip?: string;
}

export interface WorldData {
  locations: LocationData[];
  companies: CompanyData[];
}

export interface BounceNode {
  position: number;
  ip: string;
}

export interface ScreenData {
  screen_type: number;
  screen_index: number;
  computer_name: string;
  computer_ip: string;
  prompt?: string;
  error?: string;
  menu_options?: Array<{ label: string; screen_index: number }>;
}

export interface ConnectionState {
  isConnected: boolean;
  targetIp: string | null;
  bounceChain: BounceNode[];
  currentScreen: ScreenData | null;
  traceProgress: number;
  traceActive: boolean;
}

export interface TaskData {
  task_id: number;
  tool_name: string;
  tool_version: number;
  progress: number;
  ticks_remaining: number;
  target_ip: string | null;
  extra?: Record<string, unknown>;
}

export interface MessageData {
  id: number;
  from_name: string;
  subject: string;
  body: string;
  is_read: boolean;
  created_at_tick: number;
}

export interface MissionData {
  id: number;
  mission_type: number;
  description: string;
  employer_name: string;
  payment: number;
  difficulty: number;
  min_rating: number;
  target_computer_ip: string | null;
  is_accepted: boolean;
  is_completed: boolean;
}

export interface GatewayData {
  name: string;
  cpu_speed: number;
  modem_speed: number;
  memory_size: number;
  has_self_destruct: boolean;
  has_motion_sensor: boolean;
}

export interface GatewayFileData {
  id: number;
  filename: string;
  size: number;
  file_type: number;
  softwaretype: number;
}

export interface GatewayResponse {
  gateway: GatewayData;
  files: GatewayFileData[];
  memory_used: number;
  memory_total: number;
}

export interface SoftwareEntry {
  id: number;
  filename: string;
  softwaretype: number;
  size: number;
  version: string;
}
