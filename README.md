<p align="center">
  <img src="https://img.shields.io/badge/obs--quickstart-v1.0.0-6a0dad?style=for-the-badge&logo=obsstudio&logoColor=white" alt="obs-quickstart">
  <img src="https://img.shields.io/badge/Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows">
  <img src="https://img.shields.io/badge/macOS-000000?style=for-the-badge&logo=apple&logoColor=white" alt="macOS">
  <img src="https://img.shields.io/badge/Linux-FCC624?style=for-the-badge&logo=linux&logoColor=black" alt="Linux">
  <img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.9+">
</p>

# 🎬 obs-quickstart

**Plug-and-Play OBS Studio auto-configurator** — wykrywa Twój sprzęt, optymalnie konfiguruje OBS i tworzy kompletne sceny z źródłami w **jednym poleceniu**.

> 🚫 Zero ręcznego ustawiania. 🎯 Działa na Windows, macOS i Linux.

---

## ✨ Co robi?

| # | Krok | Automatycznie |
|---|------|---------------|
| 1 | 🔌 **Łączy się z OBS** przez WebSocket | Tak |
| 2 | 🖥️ **Skanuje sprzęt** — GPU, CPU, RAM, enkodery | Tak |
| 3 | 🌐 **Testuje internet** — dobiera bitrate pod Twoje łącze | Tak |
| 4 | ⚙️ **Konfiguruje OBS** — rozdzielczość, FPS, encoder, audio | ✅ |
| 5 | 🎬 **Tworzy 5 gotowych scen** ze źródłami | ✅ |
| 6 | 🔄 **Ustawia przejścia** (Fade) i hotkeye (F1-F7) | ✅ |
| 7 | 🎤 **Konfiguruje audio** — mikrofon (z Noise Gate), desktop audio | ✅ |

**Wynik:** Otwierasz OBS i masz wszystko gotowe. Wystarczy podmienić placeholder kamery na swoje urządzenie i możesz streamować.

---

## 📸 Sceny które powstają

```
┌─────────────────────────────────┐
│  🟢 Starting Soon               │  ← zapętlona animacja HyperFrames
├─────────────────────────────────┤
│  🎮 Gameplay                    │  ← Game Capture + kamera (PIP) + audio
│         ┌──────┐                │
│         │ 📷   │                │  ← kamera 480×270, prawy dół
│         └──────┘                │
├─────────────────────────────────┤
│  💬 Just Chatting               │  ← kamera na pełnym ekranie
├─────────────────────────────────┤
│  🔴 Be Right Back               │  ← zapętlona animacja intermission
├─────────────────────────────────┤
│  🚀 Stream Ending               │  ← animowane zakończenie transmisji
└─────────────────────────────────┘
```

---

## 🚀 Szybki start

### Wymagania

- **OBS Studio 28+** (z wbudowanym WebSocket)
- **Python 3.9+**
- WebSocket w OBS: **Tools → WebSocket Server Settings → Enable WebSocket server**

### Instalacja

**Windows:**
```batch
git clone https://github.com/Dejfdev/obs-quickstart.git
cd obs-quickstart
setup.bat
python -m obs_quickstart.main
```

**macOS / Linux:**
```bash
git clone https://github.com/Dejfdev/obs-quickstart.git
cd obs-quickstart
bash setup.sh
python3 -m obs_quickstart.main
```

Jeżeli uwierzytelnianie WebSocket jest włączone, kreator bezpiecznie poprosi
o hasło OBS. W trybie `--no-interactive` podaj je przez `--password`.

**Albo ręcznie (dowolna platforma):**
```bash
git clone https://github.com/Dejfdev/obs-quickstart.git
cd obs-quickstart
pip install obsws-python
pip install speedtest-cli   # opcjonalnie, dla testu łącza
python3 -m obs_quickstart.main
```

---

## 🎮 Użycie

Po uruchomieniu wizard zada Ci kilka prostych pytań:

```
❓ What do you want to do? [streaming/recording/both]: streaming
❓ Streaming platform? [twitch/youtube/kick/custom]: twitch
❓ Stream key (leave blank to set later):
❓ Do you have a webcam/camera? [Y/n]: y
```

I to wszystko. Resztą zajmuje się skrypt. Po zakończeniu możesz od razu streamować.

### Opcje CLI

| Flaga | Opis |
|-------|------|
| `--settings-only` | Tylko konfiguracja ustawień (bez scen) |
| `--scenes-only` | Tylko tworzenie scen (bez zmian ustawień) |
| `--no-interactive` | Automatycznie, bez pytań (domyślne odpowiedzi) |
| `--host HOST` | Adres OBS WebSocket (domyślnie: localhost) |
| `--port PORT` | Port OBS WebSocket (domyślnie: 4455) |
| `--password PASS` | Hasło OBS WebSocket |
| `--verbose` | Szczegółowe logi |

**Przykłady:**
```bash
# Pełny setup
python3 -m obs_quickstart.main

# Tylko ustawienia (już masz swoje sceny)
python3 -m obs_quickstart.main --settings-only

# Automatyczny setup
python3 -m obs_quickstart.main --no-interactive

# Zdalna konfiguracja (streaming PC + gaming PC)
python3 -m obs_quickstart.main --host 192.168.1.100 --password mypass
```

---

## ⚙️ Jak działa detekcja sprzętu?

| Komponent | Metoda detekcji |
|-----------|----------------|
| **GPU encoder** | OBS WebSocket API — enumeracja dostępnych enkoderów |
| **CPU cores** | Physical + logical przez `os.cpu_count()` + platform-specific |
| **RAM** | GB przez OS (WMI, sysctl, /proc/meminfo) |
| **Platforma** | sys.platform + Apple Silicon detection |
| **Internet** | speedtest-cli (upload w Mbps) |
| **Audio devices** | OBS WebSocket API |

### Logika doboru ustawień

```
GPU ma NVENC?                → NVENC H.264, 1080p60, 6000kbps
GPU ma AMD AMF?              → AMF, 1080p60, 6000kbps
GPU ma Intel QSV?            → QSV, 1080p60, 6000kbps
Jest Apple Silicon?           → Apple VT, 1080p60, 6000kbps
Tylko x264, CPU >= 8 cores?  → x264, 1080p60, 6000kbps
Tylko x264, CPU < 8 cores?   → x264, 720p30, 4500kbps
Upload < 4 Mbps?             → 720p30, niższy bitrate
```

---

## 🔌 Jak to działa pod maską?

Narzędzie używa **OBS WebSocket API v5** (wbudowanego w OBS 28+) do sterowania OBS w czasie rzeczywistym:

1. `obs_quickstart/hardware.py` — wykrywa enkodery, CPU, RAM, platformę
2. `obs_quickstart/configurator.py` — ustawia video, audio, output, stream, hotkeys
3. `obs_quickstart/scene_builder.py` — tworzy sceny, źródła, przejścia, filtry audio
4. `obs_quickstart/main.py` — interaktywny wizard CLI

Animowane ekrany Starting Soon, Be Right Back i Stream Ending są tworzone
w otwartym frameworku [HyperFrames](https://github.com/heygen-com/hyperframes),
renderowane do MP4 i dodawane do OBS jako zapętlone źródła multimedialne.
Edytowalne kompozycje źródłowe znajdują się w katalogu `videos/`.

Wszystkie operacje są wykonywane przez API — nie ma modyfikacji plików konfiguracyjnych OBS "na surowo".

---

## 🐛 Znane ograniczenia

- **macOS:** `game_capture` nie istnieje — używane jest `window_capture` (może wymagać ręcznej korekty)
- **Kamera:** dodawana jako placeholder — trzeba wybrać właściwe urządzenie w OBS
- **Stream key:** nie jest przechowywany permanentnie — podawany przy każdym uruchomieniu
- **Speedtest:** wymaga osobnej instalacji (`pip install speedtest-cli`)
- **Linux:** używa `pulse_input_capture` / `pulse_output_capture` — wymaga PulseAudio

---

## 🧑‍💻 Rozwój

```bash
git clone https://github.com/Dejfdev/obs-quickstart.git
cd obs-quickstart
pip install -e .
# Teraz 'obs-quickstart' jest dostępne jako komenda
obs-quickstart
```

---

## 📄 Licencja

MIT — możesz używać, modyfikować i dystrybuować bez ograniczeń.

---

<p align="center">
  <sub>Built with ❤️ by <a href="https://github.com/ak100kk">ak100kk</a></sub>
</p>
