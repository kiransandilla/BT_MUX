"""BT-Mux Core Virtual Multiplexing Layer."""
from .buffer import StreamBuffer
from .chunk import Chunk
from .dedup_cache import DedupCache
from .scheduler import TDMScheduler
from .session_manager import SessionManager, TransportSendCallback
from .transport import BLETransport
from .virtual_socket import LogicalSocketState, VirtualSocket

__all__ = [
    "VirtualSocket",
    "LogicalSocketState",
    "Chunk",
    "DedupCache",
    "StreamBuffer",
    "SessionManager",
    "TransportSendCallback",
    "BLETransport",
    "TDMScheduler",
]
