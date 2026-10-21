"""Allow running with ``python -m fluxop``."""
import sys
import traceback

if __name__ == "__main__":
    # Remove the Windows "Mark of the Web" from the app files BEFORE
    # pywebview/pythonnet are imported: the .NET runtime refuses to load
    # managed DLLs that carry that mark, which broke the frozen build.
    # This runs automatically, so users never need to type a command.
    try:
        from fluxop.core.unblock import unblock_app_files

        unblock_app_files()
    except Exception:
        pass

    try:
        from fluxop.app import main

        main()
    except Exception:
        print("\n" + "=" * 50)
        print("CRITICAL ERROR - The application has crashed:")
        print("=" * 50)
        traceback.print_exc()
        print("\n" + "=" * 50)
        input("\nPress ENTER to close...")
        sys.exit(1)
