/**
 * WebSocket Service for real-time updates
 */

type MessageHandler = (data: any) => void;
type ConnectionHandler = () => void;

class WebSocketService {
  private sockets: Map<string, WebSocket> = new Map();
  private messageHandlers: Map<string, Set<MessageHandler>> = new Map();
  private reconnectAttempts: Map<string, number> = new Map();
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;

  private readonly WS_BASE_URL =
    import.meta.env.VITE_WS_URL ||
    `ws://${window.location.hostname}:8000`;

  /**
   * Connect to a WebSocket channel
   */
  connect(channel: string, onConnect?: ConnectionHandler): void {
    if (this.sockets.has(channel)) {
      console.log(`Already connected to channel: ${channel}`);
      return;
    }

    const url = `${this.WS_BASE_URL}/ws/${channel}`;
    console.log(`Connecting to WebSocket: ${url}`);

    try {
      const socket = new WebSocket(url);

      socket.onopen = () => {
        console.log(`WebSocket connected: ${channel}`);
        this.reconnectAttempts.set(channel, 0);
        if (onConnect) onConnect();
      };

      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          this.handleMessage(channel, data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      socket.onerror = (error) => {
        console.error(`WebSocket error on ${channel}:`, error);
      };

      socket.onclose = () => {
        console.log(`WebSocket closed: ${channel}`);
        this.sockets.delete(channel);
        this.attemptReconnect(channel, onConnect);
      };

      this.sockets.set(channel, socket);
    } catch (error) {
      console.error(`Failed to connect to WebSocket ${channel}:`, error);
    }
  }

  /**
   * Disconnect from a WebSocket channel
   */
  disconnect(channel: string): void {
    const socket = this.sockets.get(channel);
    if (socket) {
      socket.close();
      this.sockets.delete(channel);
      this.messageHandlers.delete(channel);
      this.reconnectAttempts.delete(channel);
      console.log(`Disconnected from WebSocket: ${channel}`);
    }
  }

  /**
   * Disconnect from all WebSocket channels
   */
  disconnectAll(): void {
    this.sockets.forEach((socket) => {
      socket.close();
    });
    this.sockets.clear();
    this.messageHandlers.clear();
    this.reconnectAttempts.clear();
  }

  /**
   * Subscribe to messages from a channel
   */
  subscribe(channel: string, handler: MessageHandler): () => void {
    if (!this.messageHandlers.has(channel)) {
      this.messageHandlers.set(channel, new Set());
    }

    this.messageHandlers.get(channel)!.add(handler);

    // Return unsubscribe function
    return () => {
      const handlers = this.messageHandlers.get(channel);
      if (handlers) {
        handlers.delete(handler);
      }
    };
  }

  /**
   * Send a message to a channel
   */
  send(channel: string, data: any): void {
    const socket = this.sockets.get(channel);
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify(data));
    } else {
      console.error(`Cannot send message: WebSocket ${channel} is not connected`);
    }
  }

  /**
   * Check if connected to a channel
   */
  isConnected(channel: string): boolean {
    const socket = this.sockets.get(channel);
    return socket ? socket.readyState === WebSocket.OPEN : false;
  }

  /**
   * Handle incoming message
   */
  private handleMessage(channel: string, data: any): void {
    const handlers = this.messageHandlers.get(channel);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(data);
        } catch (error) {
          console.error('Error in message handler:', error);
        }
      });
    }
  }

  /**
   * Attempt to reconnect to a channel
   */
  private attemptReconnect(channel: string, onConnect?: ConnectionHandler): void {
    const attempts = this.reconnectAttempts.get(channel) || 0;

    if (attempts < this.maxReconnectAttempts) {
      console.log(`Attempting to reconnect to ${channel} (attempt ${attempts + 1}/${this.maxReconnectAttempts})`);

      setTimeout(() => {
        this.reconnectAttempts.set(channel, attempts + 1);
        this.connect(channel, onConnect);
      }, this.reconnectDelay * (attempts + 1)); // Exponential backoff
    } else {
      console.error(`Max reconnect attempts reached for ${channel}`);
      this.reconnectAttempts.delete(channel);
    }
  }
}

// Export singleton instance
export const websocket = new WebSocketService();

// Channel constants
export const WS_CHANNELS = {
  SYSTEM: 'system',
  AGENTS: 'agents',
  ERRORS: 'errors',
  LOGS: 'logs',
} as const;

// Message types
export interface WebSocketMessage {
  type: string;
  timestamp: string;
  [key: string]: any;
}

export interface SystemUpdateMessage extends WebSocketMessage {
  type: 'system_update';
  data: any;
}

export interface AgentUpdateMessage extends WebSocketMessage {
  type: 'agent_update';
  agent_name: string;
  status: string;
  data: any;
}

export interface ErrorMessage extends WebSocketMessage {
  type: 'error';
  error: any;
}

export interface LogMessage extends WebSocketMessage {
  type: 'log';
  log: any;
}
