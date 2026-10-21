"""Allow running with ``python -m fluxoptimizer``."""
import sys
import traceback

if __name__ == "__main__":
    try:
        from fluxoptimizer.app import main

        main()
    except Exception:
        print("\n" + "=" * 50)
        print("CRITICAL ERROR - The application has crashed:")
        print("=" * 50)
        traceback.print_exc()
        print("\n" + "=" * 50)
        input("\nPress ENTER to close...")
        sys.exit(1)
