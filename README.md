# Ryxo AutoClicker

Professional open-source auto clicker for Windows with advanced human-like behavior and anti-detection features.

## Features
- Extremely low detection risk using native Windows `SendInput`
- Gaussian randomized click intervals + button hold time
- Optional micro-jitter movements
- Left / Right click support
- Modern GUI with CustomTkinter
- System Tray support (minimize to tray)
- Custom hotkey (default: F6)
- Max clicks / duration limits
- Save/load settings
- Real-time stats (CPS, clicks count, runtime)

## Installation

```bash
# Clone the repo
git clone https://github.com/itzsepanta/RyxoAutoClicker.git
cd RyxoAutoClicker

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -r requirements.txt
