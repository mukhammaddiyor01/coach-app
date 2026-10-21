"""Small upper/lower sequence tracker shared by the leg exercise services."""
POSITION_HOLD_SECONDS = 0.15
MAX_OBSERVATION_GAP_SECONDS = 1.0


class RepetitionCounter:
    def __init__(self):
        self.reset()

    def reset(self):
        self.rep_count = 0
        self.last_observed_at = None
        self.discard_incomplete_rep()

    def discard_incomplete_rep(self):
        self.current_phase = "ready"
        self.candidate_position = None
        self.candidate_since = None

    def track_time(self, observed_at):
        interrupted = (
            self.last_observed_at is not None
            and observed_at - self.last_observed_at > MAX_OBSERVATION_GAP_SECONDS
        )
        if interrupted:
            self.discard_incomplete_rep()
        self.last_observed_at = observed_at
        return interrupted

    def confirm_position(self, position, observed_at):
        # Requiring a short hold avoids counting a single noisy observation.
        if position != self.candidate_position:
            self.candidate_position = position
            self.candidate_since = observed_at
            return
        if position is None or observed_at - self.candidate_since < POSITION_HOLD_SECONDS:
            return
        if position == "down" and self.current_phase == "up":
            self.current_phase = "down"
        elif position == "up":
            if self.current_phase == "down":
                self.rep_count += 1
            self.current_phase = "up"

    def result(self, status, message):
        return {
            "rep_count": self.rep_count,
            "phase": self.current_phase,
            "status": status,
            "message": message,
        }
