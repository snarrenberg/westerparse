import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import westerparse

source = 'test_data/FuxDorian.musicxml'
westerparse.evaluateLines(source, show=None)