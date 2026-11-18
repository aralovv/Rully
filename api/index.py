"""
Vercel Serverless Entrypoint for RULLY Avtotest API.
"""

import sys
import os

# Ensure the repository root is in Python sys.path so 'src.*' imports work cleanly
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.api.main import app

# Vercel serverless functions look for 'app' ASGI instance
handler = app
