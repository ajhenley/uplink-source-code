type MessageHandler = (data: Record<string, unknown>) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private handlers: Map<string, MessageHandler[]> = new Map();
  private reconnectTimer: number | null = null;
  private token: string = '';
  private sessionId: string = '';

  connect(token: string, sessionId: string) {
    this.token = token;
    this.sessionId = sessionId;
    this.doConnect();
  }

  private doConnect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const url = `${protocol}//${window.location.host}/ws?token=${this.token}&session_id=${this.sessionId}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      console.log('[WS] Connected');
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      const type = data.type as string;
      const handlers = this.handlers.get(type);
      if (handlers) {
        handlers.forEach((h) => h(data));
      }
    };

    this.ws.onclose = () => {
      console.log('[WS] Disconnected, reconnecting in 3s...');
      this.reconnectTimer = window.setTimeout(() => this.doConnect(), 3000);
    };

    this.ws.onerror = (err) => {
      console.error('[WS] Error:', err);
    };
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  send(type: string, payload: Record<string, unknown> = {}) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, ...payload }));
    }
  }

  on(type: string, handler: MessageHandler) {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, []);
    }
    this.handlers.get(type)!.push(handler);
  }

  off(type: string, handler: MessageHandler) {
    const handlers = this.handlers.get(type);
    if (handlers) {
      const idx = handlers.indexOf(handler);
      if (idx >= 0) handlers.splice(idx, 1);
    }
  }
}

export const wsClient = new WebSocketClient();
