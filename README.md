# Coach App

Push Up, Squats va Lunge uchun mashq yordamchisi.

## Hozir nima ishlaydi?

Ikkinchi bosqich tayyor: Push Up, Squats va Lunge kartalari alohida
mashq sahifasini ochadi. Unda tanlangan mashqning ko‘rsatmalari va kamera
joylashuvi ko‘rsatiladi. Boshqa mashqqa o‘tish va bosh sahifaga qaytish ishlaydi.
Kamera tugmasi hozircha o‘chiq. FastAPI va takror sanash keyin qo‘shiladi.
Noma’lum mashq manzili ochilsa, tushunarli xabar chiqadi.

## Sahifani ochish

VS Code terminalida:

```bash
cd /Users/mukhammaddiyor/Desktop/coach-app
source .venv/bin/activate
python -m http.server 5500 --bind 127.0.0.1 --directory frontend
```

Brauzerda http://127.0.0.1:5500/templates/index.html ni oching.
Serverni to‘xtatish: terminalda `Ctrl + C`.
Hozirgi bosqichda Python'ning oddiy fayl serveridan foydalanamiz.
FastAPI ishga tushirish buyrug‘i backend yaratilganda qo‘shiladi.

## Fayllar

- `frontend/templates/index.html` — sahifadagi yozuvlar va tugmalar.
- `frontend/static/css/style.css` — sahifa ko‘rinishi.
- `frontend/templates/workout.html` — tanlangan mashqning sahifasi.
- `frontend/static/js/workout.js` — mashq nomi va ko‘rsatmalarini ko‘rsatish.
- `AGENTS.md` — MVC, service layer va kichik commitlar qoidalari.

`backend/services/`, `backend/vision/` va `models/` hozircha bo‘sh.
