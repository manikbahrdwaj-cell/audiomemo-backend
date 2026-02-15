/**
 * WebSocket Event Emitter
 * Simple event management system for WebSocket client
 */

class EventEmitter {
  constructor() {
    this.events = {};
  }

  /**
   * Register event listener
   */
  on(event, handler) {
    if (!this.events[event]) {
      this.events[event] = [];
    }
    this.events[event].push(handler);

    // Return unsubscribe function
    return () => this.off(event, handler);
  }

  /**
   * Register one-time event listener
   */
  once(event, handler) {
    const wrappedHandler = (...args) => {
      handler(...args);
      this.off(event, wrappedHandler);
    };
    this.on(event, wrappedHandler);
  }

  /**
   * Unregister event listener
   */
  off(event, handler) {
    if (!this.events[event]) return;

    this.events[event] = this.events[event].filter(h => h !== handler);

    if (this.events[event].length === 0) {
      delete this.events[event];
    }
  }

  /**
   * Emit event to all listeners
   */
  emit(event, ...args) {
    if (!this.events[event]) return;

    this.events[event].forEach(handler => {
      try {
        handler(...args);
      } catch (error) {
        console.error(`Error in listener for event "${event}":`, error);
      }
    });
  }

  /**
   * Remove all listeners for an event or all events
   */
  removeAllListeners(event = null) {
    if (event) {
      delete this.events[event];
    } else {
      this.events = {};
    }
  }

  /**
   * Get listener count for an event
   */
  listenerCount(event) {
    return this.events[event] ? this.events[event].length : 0;
  }
}

export default EventEmitter;
