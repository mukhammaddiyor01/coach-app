# Posture feedback and real-camera trials

## What the app evaluates

The app counts a confirmed upper → lower → upper sequence. It only describes
features visible in a side view; it does not certify complete exercise technique.
All angles and thresholds are experimental 2D measurements.

| Exercise | Visible feedback |
| --- | --- |
| Push Up | Hip above/below the shoulder-to-ankle line, bent knees, wrist position, and a usable plank view |
| Squats | Usable leg view, extreme torso lean, and whether lower/upper knee positions are confirmed |
| Stationary Lunge | Split stance, visible ankle/hip view, extreme torso lean, changes in relative stance, and both-knee transitions |

The displayed labels mean:

- **Visible checks**: the required joints can be used for the current checks.
  This does not mean every aspect of the exercise is correct.
- **Adjust position**: a specific visible feature needs attention, or a required
  movement position is not yet confirmed. Read the accompanying cue.
- **Not assessed**: the required observation is unavailable. Missing joints,
  low confidence, tracking pauses, and stopped cameras never imply good form.

Squats and Lunge also show torso lean from vertical in tracking details.
Push Up shows elbow, body, and knee angles. No correctness percentage is given.
The existing counting thresholds and posture gates remain the counting rules;
feedback explains these observations rather than adding a second counter.

Side-view landmarks cannot reliably establish joint loading, pain, foot pressure,
heel contact, all knee alignment errors, or every aspect of spine shape. Do not
interpret the visible checks as an assessment of these unobserved features.

## Run one real-camera trial

1. Open an exercise, press **Start workout**, choose a camera, then press
   **Start camera**. Keep the required joints in view and wait for tracking.
2. Press **Reset count**. Pick a small, comfortable number of full repetitions,
   for example 3–5. Count them yourself while the app counts independently.
3. Perform your normal movement using the side-view setup instructions. Do not
   deliberately introduce technique errors to test a warning. Synthetic tests
   cover those cases without requiring a person to perform them.
4. Press **Stop camera**. The displayed number is the last count received before
   stopping. A frame still in flight may not have reached the display; allow the
   final upper position to be confirmed before stopping.
5. Expand **Compare counts after a camera trial**, enter your manual tally, and
   press **Compare counts**.
6. Read the result: **match**, app counted **extra**, or app **missed** repetitions.
   This compares your tally with the displayed snapshot, not an independent
   automatic ground-truth measurement. One match does not establish accuracy.
7. Repeat with the same setup before changing any settings. Use separate trials
   for each exercise and each Lunge lead leg. No camera data or trial history is
   saved; record any trial notes yourself in a local worksheet if needed.

The comparison is available only after a count has been received and the camera
is stopped. A new Start or Reset clears the previous comparison and manual
input. Editing a manual tally also invalidates the old comparison. Counts are
bounded to whole numbers from 0 to 1000 for this comparison tool.

## Extra checks with ordinary movement

- With no person in the frame, the count must not increase and feedback must be
  **Not assessed**.
- Holding an upper position must not add repetitions. A partial movement that
  never reaches the lower threshold must not count as a full repetition.
- Leaving the frame discards an incomplete repetition and preserves the total.
- Stop, navigation, and hiding the tab must release the camera. Returning to the
  tab must not restart it automatically.
- Reset starts a new count at zero. Two browser windows have independent counts.
- For Lunge, both knees must be visible. After changing the lead leg, begin again
  at the upper split-stance position; walking lunges are outside this prototype.

## Real-camera results worksheet

**Status: pending user trials. No real exercise accuracy has been measured by
an automated agent.** The rows below are intentionally unfilled.

| Exercise | Trial | Manual tally | Last app count | Difference | Setup and observation |
| --- | --- | --- | --- | --- | --- |
| Push Up | 1 | pending | pending | pending | pending |
| Push Up | 2 | pending | pending | pending | pending |
| Push Up | 3 | pending | pending | pending | pending |
| Squats | 1 | pending | pending | pending | pending |
| Squats | 2 | pending | pending | pending | pending |
| Squats | 3 | pending | pending | pending | pending |
| Lunge | 1 | pending | pending | pending | pending |
| Lunge | 2 | pending | pending | pending | pending |
| Lunge | 3 | pending | pending | pending | pending |

Useful notes include selected camera, landscape/portrait orientation, lighting,
which side was visible, Lunge lead leg, any **Not assessed** intervals, and the
last relevant angle and feedback cue. Notes need not include names, images,
videos, device identifiers, addresses, or other personal information.

## Tune only after repeated visible trials

First correct framing, visibility, and lighting. A tracking interruption should
not be treated as evidence that an angle threshold is wrong. Keep test data and
normal movement consistent, change one named setting at a time, repeat the same
trials, and retain the regression tests. Do not claim tuning is complete without
new observations. There is no automatic per-person calibration in this version.

| Observation | Relevant named settings and files |
| --- | --- |
| Upper or lower position never confirms | `UP_ELBOW_ANGLE`, `DOWN_ELBOW_ANGLE` in `backend/services/pushup_service.py`; `UP_KNEE_ANGLE`, `DOWN_KNEE_ANGLE` in each leg service |
| Repetition interrupted by posture readiness | `MIN_BODY_ANGLE`, `MIN_KNEE_ANGLE`, and framing ratios in Push Up; `MIN_TORSO_VERTICAL_RATIO` and view ratios in leg services |
| Brief noisy observations or long tracking gaps | `POSITION_HOLD_SECONDS`, `MAX_OBSERVATION_GAP_SECONDS` in Push Up and `backend/services/repetition_counter.py` for leg exercises |
| Valid stationary Lunge stance repeatedly resets | `MAX_STANCE_RATIO_CHANGE` and stance/view ratios in `backend/services/lunge_service.py` |

No threshold was tuned from invented camera samples in this milestone. The new
feedback makes the existing gates observable so the user's trials can guide a
later, evidence-based adjustment.

## Automated verification

From the project root, with the virtual environment activated:

```bash
python -m unittest discover -s tests -p 'test_*.py'
node --test tests/camera.test.cjs tests/pose.test.cjs tests/count-check.test.cjs
```

Synthetic landmark sequences check full and incomplete repetitions, posture
cues, visibility loss, reset, and isolation. HTTP tests check feedback and count
comparison boundaries. Browser-script tests check paused feedback, trial
snapshots, and obsolete response rejection. An in-memory blank JPEG checks that
the installed MediaPipe model returns zero reps and unavailable feedback for
all three exercise endpoints. None of these substitutes for the pending human
camera trials above.
