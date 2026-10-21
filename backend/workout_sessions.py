"""Bounded, temporary counting state for independent camera sessions."""
from threading import Lock
from time import monotonic
from uuid import uuid4

from backend.services.pushup_service import PushUpService

MAX_SESSIONS = 32
SESSION_IDLE_SECONDS = 600


class SessionNotFoundError(ValueError):
    """The camera session ended or expired."""


class SessionLimitError(RuntimeError):
    """The local app already has its maximum number of camera sessions."""


class WorkoutSession:
    def __init__(self, created_at):
        self.service = PushUpService()
        self.last_used_at = created_at
        self.lock = Lock()

    def analyze(self, detector, frame):
        # Keep concurrent requests for this session in order through detection and counting.
        with self.lock:
            pose = detector.detect(frame)
            workout = self.service.update(
                pose["landmarks"], pose["width"], pose["height"], monotonic(),
            )
            return {**pose, "workout": workout}


class WorkoutSessions:
    def __init__(self, clock=monotonic):
        self.clock = clock
        self.sessions = {}
        self.lock = Lock()

    def _remove_expired(self, now):
        expired = [
            token for token, session in self.sessions.items()
            if now - session.last_used_at >= SESSION_IDLE_SECONDS
        ]
        for token in expired:
            del self.sessions[token]

    def create(self):
        with self.lock:
            now = self.clock()
            self._remove_expired(now)
            if len(self.sessions) >= MAX_SESSIONS:
                raise SessionLimitError("Close another camera session and try again.")
            token = uuid4().hex
            session = WorkoutSession(now)
            self.sessions[token] = session
            return token, session.service.reset()

    def get(self, token):
        with self.lock:
            now = self.clock()
            self._remove_expired(now)
            session = self.sessions.get(token)
            if session is None:
                raise SessionNotFoundError("Camera session ended. Start the camera again.")
            session.last_used_at = now
            return session

    def close(self, token):
        with self.lock:
            # Closing twice is harmless, including cleanup after an expired session.
            self.sessions.pop(token, None)

    def clear(self):
        with self.lock:
            self.sessions.clear()


workout_sessions = WorkoutSessions()


def get_workout_sessions():
    return workout_sessions
