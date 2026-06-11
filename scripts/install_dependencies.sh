set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d venv ]]; then
  python3 -m venv venv
fi

source venv/bin/activate

pip install --upgrade pip
pip install opencv-python numpy Pillow img2pdf

if [[ "${1:-}" == "--full" ]]; then
  pip install PySide6
else
  pip install PySide6_Essentials shiboken6
fi

echo ""
echo "Installation complete. Run the app with:"
echo "  source venv/bin/activate && python main.py"
