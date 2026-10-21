import unittest
from concurrent.futures import ThreadPoolExecutor

from backend.workout_sessions import (
    MAX_SESSIONS, SESSION_IDLE_SECONDS, SessionLimitError,
    SessionNotFoundError, WorkoutSessions,
)


class WorkoutSessionTests(unittest.TestCase):
    def test_camera_sessions_have_independent_counts(self):
        sessions = WorkoutSessions()
        first_token, first_result = sessions.create()
        second_token, _ = sessions.create()
        self.assertNotEqual(first_token, second_token)
        self.assertEqual(first_result["rep_count"], 0)
        sessions.get(first_token).service.rep_count = 3
        self.assertEqual(sessions.get(second_token).service.rep_count, 0)

    def test_idle_sessions_expire_and_active_sessions_survive(self):
        now = [0]
        sessions = WorkoutSessions(clock=lambda: now[0])
        idle, _ = sessions.create()
        active, _ = sessions.create()
        now[0] = SESSION_IDLE_SECONDS - 1
        sessions.get(active)
        now[0] = SESSION_IDLE_SECONDS
        with self.assertRaises(SessionNotFoundError):
            sessions.get(idle)
        self.assertIsNotNone(sessions.get(active))

    def test_capacity_is_bounded_and_expired_slots_are_reused(self):
        now = [0]
        sessions = WorkoutSessions(clock=lambda: now[0])
        for _ in range(MAX_SESSIONS):
            sessions.create()
        with self.assertRaises(SessionLimitError):
            sessions.create()
        now[0] = SESSION_IDLE_SECONDS
        token, _ = sessions.create()
        self.assertEqual(len(sessions.sessions), 1)
        self.assertIsNotNone(sessions.get(token))

    def test_close_and_clear_remove_state(self):
        sessions = WorkoutSessions()
        token, _ = sessions.create()
        sessions.close(token)
        sessions.close(token)
        with self.assertRaises(SessionNotFoundError):
            sessions.get(token)
        sessions.create()
        sessions.clear()
        self.assertEqual(sessions.sessions, {})

    def test_concurrent_creation_respects_capacity(self):
        sessions = WorkoutSessions()

        def create_one(_):
            try:
                sessions.create()
                return True
            except SessionLimitError:
                return False

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(create_one, range(MAX_SESSIONS + 10)))
        self.assertEqual(sum(results), MAX_SESSIONS)

    def test_analysis_returns_results_without_retaining_frame_or_landmarks(self):
        class Detector:
            def detect(self, frame):
                return {"landmarks": [], "width": 640, "height": 480}

        sessions = WorkoutSessions()
        token, _ = sessions.create()
        session = sessions.get(token)
        result = session.analyze(Detector(), b"temporary-frame")
        self.assertEqual(result["workout"]["status"], "waiting")
        self.assertEqual(set(vars(session)), {"service", "exercise_id", "last_used_at", "lock"})


if __name__ == "__main__":
    unittest.main()
