"""Allow ``python -m rfgenerator`` invocation."""

import sys

from .cli import main

sys.exit(main())
