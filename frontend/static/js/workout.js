// Bu ma'lumotlar faqat sahifadagi ko'rsatmalar uchun. Hisoblash service'da bo'ladi.
const exerciseInstructions = {
  pushup: {
    title: "Push Up",
    description: "Otjimaniya uchun kamera va boshlang‘ich holatni tayyorlang.",
    cameraGuidance: "Kamera sizni yon tomondan ko‘rsin. Yelka, bilak, son va oyoqlaringiz kadrga sig‘sin.",
    steps: [
      { title: "Kamerani joylashtiring", description: "Qurilmani barqaror joyga qo‘ying. Kamera sizni yon tomondan ko‘rsin va mashq uchun yetarli joy qolsin." },
      { title: "Boshlang‘ich holatga o‘ting", description: "Qo‘llar yozilgan plank holatiga o‘ting. Butun tanangiz kamerada ko‘rinsin." },
      { title: "Tanani tekis tuting", description: "Yelka, son va oyoqlarni bir tekis tutishga harakat qiling." },
      { title: "Harakatni sekin bajaring", description: "Tirsaklarni bukib pastga tushing, so‘ng boshlang‘ich holatga qayting." },
    ],
  },
  squats: {
    title: "Squats",
    description: "O‘tirib-turish uchun butun tanangiz ko‘rinadigan joy tanlang.",
    cameraGuidance: "Kamera yon tomonda bo‘lsin. Yelka, son, tizza va ikkala oyoq kadrda ko‘rinsin.",
    steps: [
      { title: "Kamerani joylashtiring", description: "Kamera sizni yon tomondan ko‘rsin. O‘tirganingizda ham boshingiz va oyoqlaringiz kadrdan chiqmasin." },
      { title: "Tik holatdan boshlang", description: "Oyoqlarni taxminan yelka kengligida qo‘ying. Harakatni tik turgan holatdan boshlang." },
      { title: "Sekin pastga tushing", description: "Tizza va sonlarni bukib, nazorat bilan pastga tushing. Tovonlaringizni yerda saqlang." },
      { title: "Boshlang‘ich holatga qayting", description: "Muvozanatni saqlagan holda yana tik turing. Harakat davomida butun tanangiz ko‘rinsin." },
    ],
  },
  lunge: {
    title: "Lunge",
    description: "Bu sahifa joyida bajariladigan Lunge mashqi uchun tayyorgarlikni ko‘rsatadi.",
    cameraGuidance: "Kamera yon tomonda bo‘lsin. Oldingi va orqadagi oyoq, ayniqsa ikkala tizza, kadrga sig‘sin.",
    steps: [
      { title: "Kamerani joylashtiring", description: "Qurilmani yon tomonga qo‘ying. Ikkala oyog‘ingiz ham mashq davomida ko‘rinadigan masofani tanlang." },
      { title: "Oyoqlarni ajrating", description: "Bir oyoqni oldinga, ikkinchisini orqaga qo‘ying. Muvozanatni ushlay oladigan holatni tanlang." },
      { title: "Joyingizda pastga tushing", description: "Gavdani boshqargan holda ikkala tizzani bukib pastga tushing. Oyoqlaringizning joyini saqlang." },
      { title: "Yuqori holatga qayting", description: "Sekin yuqoriga ko‘tariling. Bu variantda har bir takror orasida oldinga yurish shart emas." },
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

  // Faqat belgilangan uchta mashq qabul qilinadi; noma'lum URL baholanmaydi.
  if (!Object.hasOwn(exerciseInstructions, exerciseId)) {
    workoutTitle.textContent = "Mashq topilmadi";
    workoutDescription.textContent = "Mashqlarga qaytib, Push Up, Squats yoki Lunge’ni tanlang.";
    document.title = "Mashq topilmadi — Coach App";
    return;
  }

  const selectedTab = document.querySelector(`[data-exercise="${exerciseId}"]`);
  selectedTab.setAttribute("aria-current", "page");
  showInstructions(exerciseInstructions[exerciseId]);
}

loadWorkout();
