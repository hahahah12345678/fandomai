import subprocess
import sys
import os

# Path to the main script
SCRIPT = "fandom_ai_gui.py"
EXE_NAME = "FandomAI"

# Ensure PyInstaller is installed
try:
    import PyInstaller
except ImportError:
    print("Installing PyInstaller...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

# Build the EXE
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm", "--onefile", "--windowed",
    f"--name={EXE_NAME}", SCRIPT
]
print("Building the EXE...")
subprocess.check_call(cmd)

# Open the output folder
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dist")
if os.path.exists(output_dir):
    if sys.platform == "win32":
        os.startfile(output_dir)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", output_dir])
print("Build complete! Your EXE is in the dist folder.")
