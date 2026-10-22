"""PyInstaller entry point (absolute import so the frozen bundle resolves it)."""
import sys
import traceback

from fluxckore.app import main

if __name__ == "__main__":
    try:
        main()
    except Exception:
        print("\n" + "=" * 50)
        print("CRITICAL ERROR - The application has crashed:")
        print("=" * 50)
        traceback.print_exc()
        print("\n" + "=" * 50)
        sys.exit(1)
