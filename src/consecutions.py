# -----------------------------------------------------------------------------
# Name:         consecutions.py
# Purpose:      Object for storing a note's consecutive
#               relationships in its line
#
# Author:       Robert Snarrenberg
#
# Copyright:    (c) 2020 by Robert Snarrenberg
# License:      BSD, see license.txt
# -----------------------------------------------------------------------------
"""
Consecutions
============

The Consecutions class stores information about how a note
in a line is approached and left.
This should be converted to a method."""

# TODO add categories for chromatic semitones and other
# nondiatonic steps, currently set to None
# perhaps add modifier to step: diatonic (m2, M2),
# chromatic (A1, d1), nondiatonic (A2)

from music21 import *

# -----------------------------------------------------------------------------
# MAIN CLASS
# -----------------------------------------------------------------------------


class Consecutions():
    """An object holding the generic types of melodic consecution
    for a note to the left and right (approach and departure):
    the interval, its direction, and the consecution type
    ('same', 'step', 'skip', None) are calculated from a
    three-note linear segment."""
    def __init__(self, targetNote, leftNote=None, rightNote=None):
        # validConsecutionTypes = ('same', 'step', 'skip', None)
        self.leftNote = leftNote
        self.rightNote = rightNote
        self.targetNote = targetNote

    def get_leftInterval(self):
        if self.leftNote is not None:
            leftInterval = interval.Interval(self.leftNote, self.targetNote)
        else:
            leftInterval = None
        return leftInterval

    def get_rightInterval(self):
        if self.rightNote is not None:
            rightInterval = interval.Interval(self.targetNote, self.rightNote)
        else:
            rightInterval = None
        return rightInterval

    def get_leftDirection(self):
        if self.leftInterval:
            leftDirection = self.leftInterval.direction
        else:
            leftDirection = None
        return leftDirection

    def get_leftType(self):
        if self.leftInterval:
            if self.leftInterval.isDiatonicStep:
                leftType = 'step'
            elif self.leftInterval.name == 'P1':
                leftType = 'same'
            else:
                leftType = 'skip'
        else:
            leftType = None
        return leftType

    def get_rightDirection(self):
        if self.rightInterval:
            rightDirection = self.rightInterval.direction
        else:
            rightDirection = None
        return rightDirection

    def get_rightType(self):
        if self.rightInterval:
            if self.rightInterval.isDiatonicStep:
                rightType = 'step'
            elif self.rightInterval.name == 'P1':
                rightType = 'same'
            else:
                rightType = 'skip'
        else:
            rightType = None
        return rightType

    leftInterval = property(get_leftInterval)
    rightInterval = property(get_rightInterval)
    leftDirection = property(get_leftDirection)
    rightDirection = property(get_rightDirection)
    leftType = property(get_leftType)
    rightType = property(get_rightType)

# -----------------------------------------------------------------------------
# FUNCTIONS
# -----------------------------------------------------------------------------


def getConsecutions(part):
    idx = 0
    for n in part.recurse().notes:
        if idx == 0:
            nLeft = None
        else:
            nLeft = part.recurse().notes[idx-1]
        if idx == len(part.recurse().notes)-1:
            nRight = None
        else:
            nRight = part.recurse().notes[idx+1]
        n.consecutions = Consecutions(n, nLeft, nRight)
        idx += 1

# -----------------------------------------------------------------------------


if __name__ == "__main__":
    # self_test code
    pass

# -----------------------------------------------------------------------------
# eof
