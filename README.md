# Coach App

Push Up, Squats va Lunge uchun mashq yordamchisi.

## Hozir nima ishlaydi?

Birinchi bosqich tayyor: uchta mashq kartasi bor. Kartani bosganda
u tanlanadi va pastdagi panelda mashq nomi chiqadi.
Kamera, FastAPI sahifalari va takrorlarni sanash keyingi bosqichlarda qo‘shiladi.

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
- `frontend/static/js/exercises.js` — mashq tanlash harakati.
- `AGENTS.md` — MVC, service layer va kichik commitlar qoidalari.

`backend/services/`, `backend/vision/` va `models/` hozircha bo‘sh.
