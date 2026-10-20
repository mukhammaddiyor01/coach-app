// Display instructions only. Exercise calculations belong in Python services.
const exerciseInstructions = {
  pushup: {
    title: "Push Up",
    description: "Set up your camera and starting position for push ups.",
    cameraGuidance: "Use a side view. Keep your shoulders, wrists, hips, and feet in the frame.",
    steps: [
      { title: "Position your camera", description: "Place your device on a stable surface. Use a side view and leave enough room to exercise." },
      { title: "Find your starting position", description: "Start in a plank position with your arms extended. Keep your whole body in the frame." },
      { title: "Keep your body aligned", description: "Aim to keep your shoulders, hips, and feet in a straight line." },
      { title: "Move with control", description: "Bend your elbows to lower your body, then return to your starting position." },
    ],
  },
  squats: {
    title: "Squats",
    description: "Choose a spot where your whole body stays visible during squats.",
    cameraGuidance: "Use a side view. Keep your shoulders, hips, knees, and both feet visible.",
    steps: [
      { title: "Position your camera", description: "Position the camera to your side. Keep your head and feet in the frame, even as you lower your body." },
      { title: "Start standing", description: "Place your feet about shoulder-width apart. Begin from a standing position." },
      { title: "Lower with control", description: "Bend your knees and hips to lower your body with control. Keep your heels on the floor." },
      { title: "Return to standing", description: "Keep your balance as you stand back up. Make sure your whole body remains visible." },
    ],
  },
  lunge: {
    title: "Lunge",
    description: "Prepare for stationary lunges with a stable split stance.",
    cameraGuidance: "Use a side view. Keep your front and rear legs, especially both knees, in the frame.",
    steps: [
      { title: "Position your camera", description: "Place your device to your side. Choose a distance where both legs remain visible throughout the movement." },
      { title: "Set your split stance", description: "Place one foot forward and the other behind you. Choose a stance where you can keep your balance." },
      { title: "Lower in place", description: "Bend both knees to lower your body with control. Keep your feet in their starting positions." },
      { title: "Return to the upper position", description: "Rise slowly to your starting position. For this variation, you do not need to step forward between repetitions." },
    ],
  },
};

const workoutTitle = document.querySelector("#workout-title");
const workoutDescription = document.querySelector("#workout-description");
const workoutContent = document.querySelector("#workout-content");
const instructionList = document.querySelector("#instruction-list");
const cameraGuidance = document.querySelector("#camera-guidance");

function showInstructions(exercise) {
  workoutTitle.textContent = exercise.title;
  workoutDescription.textContent = exercise.description;
  cameraGuidance.textContent = exercise.cameraGuidance;
  document.title = `${exercise.title} — Coach App`;

  exercise.steps.forEach((step) => {
    const listItem = document.createElement("li");
    const title = document.createElement("h3");
    const description = document.createElement("p");

    title.textContent = step.title;
    description.textContent = step.description;
    listItem.append(title, description);
    instructionList.append(listItem);
  });

  workoutContent.hidden = false;
}

function loadWorkout() {
  const parameters = new URLSearchParams(window.location.search);
  const exerciseId = parameters.get("exercise");

  // Accept only the three supported exercises; reject unknown exercise IDs.
  if (!Object.hasOwn(exerciseInstructions, exerciseId)) {
    workoutTitle.textContent = "Exercise not found";
    workoutDescription.textContent = "Go back to exercises and choose Push Up, Squats, or Lunge.";
    document.title = "Exercise not found — Coach App";
    return;
  }

  const selectedTab = document.querySelector(`[data-exercise="${exerciseId}"]`);
  selectedTab.setAttribute("aria-current", "page");
  showInstructions(exerciseInstructions[exerciseId]);
}

loadWorkout();
