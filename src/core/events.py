from typing import Callable, Dict, List, Any

class EventBus:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._subscribers = {}
        return cls._instance
        
    def subscribe(self, event_type: str, callback: Callable[[Any], None]):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)
        
    def publish(self, event_type: str, data: Any = None):
        if event_type in self._subscribers:
            for callback in self._subscribers[event_type]:
                try:
                    callback(data)
                except Exception as e:
                    # Logging will be injected or imported here later
                    print(f"Error in event handler for {event_type}: {e}")

event_bus = EventBus()
