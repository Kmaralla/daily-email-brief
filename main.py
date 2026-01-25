#!/usr/bin/env python3
"""Main entry point for Daily Email Brief - Opens Web UI."""

import sys
import os

# Check if running in venv (helpful warning)
def check_venv():
    """Check if running in virtual environment."""
    in_venv = (
        hasattr(sys, 'real_prefix') or
        (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    )
    return in_venv

if __name__ == '__main__':
    # If no arguments, launch the web UI directly
    if len(sys.argv) == 1:
        if not check_venv():
            print("⚠️  WARNING: You're not in a virtual environment!")
            print("   It's recommended to activate your venv first:")
            print("   source venv/bin/activate")
            print("")
            response = input("Continue anyway? (y/N): ")
            if response.lower() != 'y':
                sys.exit(1)
        
        # Just open the web UI - everything happens there
        print("\n🌐 Opening Daily Email Brief Web UI...")
        print("📱 All setup and configuration happens in your browser!")
        print("⚠️  Keep this terminal window open!\n")
        
        from src.ui.web_setup import app, open_browser
        from threading import Timer
        
        Timer(1, open_browser).start()
        try:
            app.run(debug=False, port=5000, host='127.0.0.1', use_reloader=False)
        except KeyboardInterrupt:
            print("\n✅ Goodbye!\n")
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
    else:
        # Use CLI for specific commands (for advanced users)
        from src.ui.cli import cli
        cli()
