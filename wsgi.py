# from app import app

# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port=10000)

import os
import sys

# Add your project directory to path
path = '/home/AnilKumarK/mysite'
if path not in sys.path:
    sys.path.append(path)

from app import app as application
