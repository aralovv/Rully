"""
RULLY Telegram Mini App & API Server Runner.
"""

import os
import sys
import uvicorn

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")
    print(f"🚀 Starting RULLY Mini App API on http://{host}:{port}")
    uvicorn.run("src.api.main:app", host=host, port=port, reload=False, log_level="info")
