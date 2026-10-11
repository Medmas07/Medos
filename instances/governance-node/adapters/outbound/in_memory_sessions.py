"""SessionStore in memory (HC-211): every session ends when the Node restarts."""

from threading import Lock

from domain.authentication import Session


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = Lock()

    def add(self, key: str, session: Session) -> None:
        with self._lock:
            # Drop the sessions already expired when this one starts.
            self._sessions = {
                k: s
                for k, s in self._sessions.items()
                if not s.expired(session.issued_at)
            }
            self._sessions[key] = session

    def get(self, key: str) -> Session | None:
        with self._lock:
            return self._sessions.get(key)

    def remove(self, key: str) -> None:
        with self._lock:
            self._sessions.pop(key, None)
