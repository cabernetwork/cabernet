import os
import sys
x = sys.executable
if x is None or x == '':
    sys.exit(1)
else:
    print(x)
