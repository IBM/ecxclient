
import os
import sys

sdk_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(sdk_dir, ".."))
dependencies_dir = os.path.join(root_dir, "dependencies")

sys.path.insert(0, root_dir)
sys.path.insert(0, os.path.join(dependencies_dir, "click"))
sys.path.insert(0, os.path.join(dependencies_dir, "requests"))
