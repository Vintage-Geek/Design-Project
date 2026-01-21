import sys
import os

# Manually tell Python to look in your .venv folder first
venv_path = r"D:\Design Project\Use Case\Project\.venv\Lib\site-packages"
if venv_path not in sys.path:
    sys.path.insert(0, venv_path)

# Now try the import
try:
    import audioop_lts
    print("✅ Success! audioop_lts is now found.")
except ImportError:
    print("❌ Still not found. Check the path again.")