"""Compare a user's manual tally with the last count displayed by the app."""
MAX_TRIAL_REPETITIONS = 1000


class InvalidCountCheckError(ValueError):
    """A manual trial must contain bounded whole-number counts."""


def compare_counts(manual_count, observed_count):
    for count in (manual_count, observed_count):
        if type(count) is not int or not 0 <= count <= MAX_TRIAL_REPETITIONS:
            raise InvalidCountCheckError("Trial counts must be whole numbers between 0 and 1000.")

    difference = observed_count - manual_count
    if difference > 0:
        outcome = "extra"
        message = f"The app counted {difference} more than your manual tally in this trial."
    elif difference < 0:
        outcome = "missed"
        message = f"The app counted {abs(difference)} fewer than your manual tally in this trial."
    else:
        outcome = "match"
        message = "The counts match in this trial. Repeat with the same camera setup to check consistency."

    return {
        "manual_count": manual_count,
        "observed_count": observed_count,
        "difference": difference,
        "outcome": outcome,
        "message": message,
    }
