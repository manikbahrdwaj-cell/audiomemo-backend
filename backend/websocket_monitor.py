"""
WebSocket Monitoring and Statistics Module
Tracks performance metrics and connection health
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ConnectionStats:
    """Statistics for a single connection"""
    connection_id: str
    connected_at: datetime
    disconnected_at: datetime = None
    messages_sent: int = 0
    messages_received: int = 0
    audio_chunks_received: int = 0
    total_audio_bytes: int = 0
    last_activity: datetime = None
    verifications_performed: int = 0
    enrollments_performed: int = 0
    errors_count: int = 0
    
    def get_duration(self) -> float:
        """Get connection duration in seconds"""
        end = self.disconnected_at or datetime.now()
        return (end - self.connected_at).total_seconds()
    
    def get_messages_per_second(self) -> float:
        """Get messages per second rate"""
        duration = self.get_duration()
        return self.messages_received / duration if duration > 0 else 0
    
    def get_audio_mb(self) -> float:
        """Get total audio in megabytes"""
        return self.total_audio_bytes / (1024 * 1024)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data["duration_seconds"] = self.get_duration()
        data["messages_per_second"] = self.get_messages_per_second()
        data["audio_mb"] = self.get_audio_mb()
        return data


class WebSocketMonitor:
    """Monitors WebSocket connections and collects metrics"""
    
    def __init__(self):
        self.active_stats: Dict[str, ConnectionStats] = {}
        self.historical_stats: List[ConnectionStats] = []
        self.event_log: List[Dict[str, Any]] = []
        self.errors_by_type: Dict[str, int] = defaultdict(int)
    
    def create_connection(self, connection_id: str) -> ConnectionStats:
        """Create a new connection stats entry"""
        stats = ConnectionStats(
            connection_id=connection_id,
            connected_at=datetime.now(),
            last_activity=datetime.now()
        )
        self.active_stats[connection_id] = stats
        self._log_event("connection_created", connection_id)
        return stats
    
    def close_connection(self, connection_id: str) -> ConnectionStats:
        """Close and archive connection stats"""
        if connection_id in self.active_stats:
            stats = self.active_stats.pop(connection_id)
            stats.disconnected_at = datetime.now()
            self.historical_stats.append(stats)
            self._log_event("connection_closed", connection_id)
            return stats
        return None
    
    def record_message_sent(self, connection_id: str):
        """Record an outgoing message"""
        if connection_id in self.active_stats:
            self.active_stats[connection_id].messages_sent += 1
            self.active_stats[connection_id].last_activity = datetime.now()
    
    def record_message_received(self, connection_id: str):
        """Record an incoming message"""
        if connection_id in self.active_stats:
            self.active_stats[connection_id].messages_received += 1
            self.active_stats[connection_id].last_activity = datetime.now()
    
    def record_audio_chunk(self, connection_id: str, size: int):
        """Record an audio chunk reception"""
        if connection_id in self.active_stats:
            stats = self.active_stats[connection_id]
            stats.audio_chunks_received += 1
            stats.total_audio_bytes += size
            stats.last_activity = datetime.now()
    
    def record_verification(self, connection_id: str):
        """Record a verification operation"""
        if connection_id in self.active_stats:
            self.active_stats[connection_id].verifications_performed += 1
            self._log_event("verification_performed", connection_id)
    
    def record_enrollment(self, connection_id: str):
        """Record an enrollment operation"""
        if connection_id in self.active_stats:
            self.active_stats[connection_id].enrollments_performed += 1
            self._log_event("enrollment_performed", connection_id)
    
    def record_error(self, connection_id: str, error_type: str):
        """Record an error occurrence"""
        if connection_id in self.active_stats:
            self.active_stats[connection_id].errors_count += 1
        self.errors_by_type[error_type] += 1
        self._log_event("error_occurred", connection_id, error_type)
    
    def get_connection_stats(self, connection_id: str) -> Dict[str, Any]:
        """Get stats for a specific connection"""
        if connection_id in self.active_stats:
            return self.active_stats[connection_id].to_dict()
        return None
    
    def get_all_active_stats(self) -> List[Dict[str, Any]]:
        """Get stats for all active connections"""
        return [stats.to_dict() for stats in self.active_stats.values()]
    
    def get_historical_stats(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get historical connection stats"""
        return [stats.to_dict() for stats in self.historical_stats[-limit:]]
    
    def get_aggregate_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics across all connections"""
        all_stats = list(self.active_stats.values()) + self.historical_stats
        
        if not all_stats:
            return {
                "total_connections": 0,
                "active_connections": 0,
                "total_messages": 0,
                "total_audio_bytes": 0,
                "total_verifications": 0,
                "total_enrollments": 0,
                "total_errors": 0
            }
        
        return {
            "total_connections": len(all_stats),
            "active_connections": len(self.active_stats),
            "total_messages": sum(s.messages_received for s in all_stats),
            "total_audio_bytes": sum(s.total_audio_bytes for s in all_stats),
            "total_verifications": sum(s.verifications_performed for s in all_stats),
            "total_enrollments": sum(s.enrollments_performed for s in all_stats),
            "total_errors": sum(s.errors_count for s in all_stats),
            "avg_connection_duration": sum(s.get_duration() for s in all_stats) / len(all_stats),
            "errors_by_type": dict(self.errors_by_type)
        }
    
    def _log_event(self, event_type: str, connection_id: str, details: str = None):
        """Log an event"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "connection_id": connection_id,
            "details": details
        }
        self.event_log.append(event)
        
        # Keep event log size manageable (last 1000 events)
        if len(self.event_log) > 1000:
            self.event_log = self.event_log[-1000:]
    
    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events"""
        return self.event_log[-limit:]
    
    def cleanup_old_historical(self, days: int = 7):
        """Clean up historical stats older than specified days"""
        cutoff = datetime.now() - timedelta(days=days)
        self.historical_stats = [
            s for s in self.historical_stats 
            if s.disconnected_at and s.disconnected_at > cutoff
        ]
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status"""
        stats = self.get_aggregate_stats()
        
        # Simple health checks
        health_checks = {
            "active_connections_ok": stats["active_connections"] < 100,
            "error_rate_ok": stats["total_errors"] < stats["total_messages"] * 0.1
                            if stats["total_messages"] > 0 else True,
            "recent_activity": len(self.event_log) > 0
        }
        
        overall_status = "healthy" if all(health_checks.values()) else "degraded"
        
        return {
            "status": overall_status,
            "active_connections": stats["active_connections"],
            "total_errors": stats["total_errors"],
            "health_checks": health_checks,
            "timestamp": datetime.now().isoformat()
        }


# Global monitor instance
monitor = WebSocketMonitor()
