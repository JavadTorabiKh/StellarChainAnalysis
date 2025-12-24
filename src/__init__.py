__version__ = "1.0.0"
__author__ = "javad torabi"
__email__ = "j.2528840@gmail.com"

import sys
from pathlib import Path

# اضافه کردن مسیر src به sys.path
src_path = Path(__file__).parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

# Importهای اصلی
from .core.stellar_client import StellarHorizonClient, StellarTransaction, StellarAccount
from .core.stream_processor import TransactionProcessor, StreamManager

__all__ = [
    'StellarHorizonClient',
    'StellarTransaction',
    'StellarAccount',
    'TransactionProcessor',
    'StreamManager'
]