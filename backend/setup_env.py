#!/usr/bin/env python3
"""
Cross-platform Python environment setup script for AutoFormal+ backend.
Automatically detects and configures virtual environment, installs dependencies including pytest.
Works on Windows, macOS, and Linux without admin privileges.
"""

import os
import sys
import subprocess
import platform
from pathlib import Path


def run_command(cmd, cwd=None, check=True):
    """Run a command and return result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"Error: {result.stderr}")
        sys.exit(1)
    return result


def main():
    # Get backend directory
    backend_dir = Path(__file__).parent
    venv_dir = backend_dir / ".venv"
    
    print("=" * 60)
    print("AutoFormal+ Backend Environment Setup")
    print("=" * 60)
    print(f"Backend directory: {backend_dir}")
    print(f"Python version: {platform.python_version()}")
    print(f"Platform: {platform.system()}")
    print()
    
    # Check if virtual environment exists
    if venv_dir.exists():
        print(f"[OK] Virtual environment found at: {venv_dir}")
    else:
        print(f"Creating virtual environment at: {venv_dir}")
        run_command([sys.executable, "-m", "venv", str(venv_dir)])
        print("[OK] Virtual environment created")
    
    # Determine activation command and Python executable
    if platform.system() == "Windows":
        venv_python = venv_dir / "Scripts" / "python.exe"
        venv_pip = venv_dir / "Scripts" / "pip.exe"
        activate_cmd = str(venv_dir / "Scripts" / "activate.bat")
        activate_ps = str(venv_dir / "Scripts" / "Activate.ps1")
    else:
        venv_python = venv_dir / "bin" / "python"
        venv_pip = venv_dir / "bin" / "pip"
        activate_cmd = f"source {venv_dir}/bin/activate"
        activate_ps = None
    
    # Upgrade pip
    print("\nUpgrading pip...")
    run_command([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
    print("[OK] pip upgraded")
    
    # Install dependencies from requirements.txt
    requirements_file = backend_dir / "requirements.txt"
    if requirements_file.exists():
        print(f"\nInstalling dependencies from {requirements_file}...")
        run_command([str(venv_python), "-m", "pip", "install", "-r", str(requirements_file)])
        print("[OK] Dependencies installed")
    else:
        print(f"\nWarning: {requirements_file} not found")
        print("Installing core dependencies manually...")
        core_deps = [
            "fastapi>=0.116.1",
            "uvicorn[standard]>=0.35.0",
            "huggingface-hub>=0.34.4",
            "pydantic>=2.11.7",
            "pydantic-settings>=2.10.1",
            "requests>=2.32.3",
            "pytest>=8.0.0"
        ]
        for dep in core_deps:
            run_command([str(venv_python), "-m", "pip", "install", dep])
        print("[OK] Core dependencies installed")
    
    # Verify pytest installation
    print("\nVerifying pytest installation...")
    result = run_command([str(venv_python), "-m", "pytest", "--version"], check=False)
    if result.returncode == 0:
        print(f"[OK] pytest installed: {result.stdout.strip()}")
    else:
        print("[ERROR] pytest not found, installing...")
        run_command([str(venv_python), "-m", "pip", "install", "pytest>=8.0.0"])
        print("[OK] pytest installed")
    
    # Print instructions
    print("\n" + "=" * 60)
    print("Setup Complete!")
    print("=" * 60)
    
    if platform.system() == "Windows":
        print("\nTo activate the virtual environment:")
        print(f"  PowerShell:  .venv\\Scripts\\Activate.ps1")
        print(f"  CMD:         .venv\\Scripts\\activate.bat")
        print("\nIf PowerShell blocks script execution:")
        print("  Run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser")
        print()
    else:
        print("\nTo activate the virtual environment:")
        print(f"  {activate_cmd}")
        print()
    
    print("To run tests:")
    print(f"  {venv_python} -m pytest tests/test_sanity.py -v")
    print()
    
    print("To start the backend server:")
    print(f"  {venv_python} -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001")
    print()
    
    print("To reinstall all dependencies:")
    print(f"  {venv_python} -m pip install -r requirements.txt")
    print()
    
    # Try running tests automatically
    print("=" * 60)
    print("Running tests automatically...")
    print("=" * 60)
    test_file = backend_dir / "tests" / "test_sanity.py"
    if test_file.exists():
        result = run_command([str(venv_python), "-m", "pytest", str(test_file), "-v"], check=False)
        if result.returncode == 0:
            print("\n[OK] All tests passed!")
        else:
            print("\n[ERROR] Some tests failed. Review output above.")
    else:
        print(f"\nTest file not found: {test_file}")
    
    print("\n" + "=" * 60)
    print("Environment is ready for development!")
    print("=" * 60)


if __name__ == "__main__":
    main()
