#!/usr/bin/env python3
"""
VM Balancer - Entry point module
Модуль точки входа для запуска через python -m vm_balancer
"""

import os
import sys

from .main import main

# Add current directory to path for development
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

if __name__ == "__main__":
    main()
