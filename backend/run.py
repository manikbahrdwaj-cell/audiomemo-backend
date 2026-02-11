#!/usr/bin/env python
"""Run the FastAPI application with uvicorn"""

import uvicorn
import sys

if __name__ == "__main__":
    try:
        print(f"Current working directory: {sys.argv}")
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="info"
        )
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
