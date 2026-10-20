// Bu faqat sahifa holati. Mashqni hisoblash keyin Python service'ida bo'ladi.
const exerciseNames = {
  pushup: "Push Up — otjimaniya",
  squats: "Squats — o‘tirib-turish",
  lunge: "Lunge — bir oyoqda tushish",
};

const exerciseButtons = document.querySelectorAll("[data-exercise]");
const selectionTitle = document.querySelector("#selection-title");
const selectionDescription = document.querySelector("#selection-description");

function selectExercise(selectedButton) {
  const exerciseName = exerciseNames[selectedButton.dataset.exercise];

  if (!exerciseName) {
    return;
  }

  exerciseButtons.forEach((button) => {
    const isSelected = button === selectedButton;
    button.setAttribute("aria-pressed", String(isSelected));
  });

  selectionTitle.textContent = `${exerciseName} tanlandi`;
  selectionDescription.textContent =
    "Keyingi bosqichda shu mashqning kamera sahifasini ulaymiz.";
}

exerciseButtons.forEach((button) => {
  button.addEventListener("click", () => selectExercise(button));
});
