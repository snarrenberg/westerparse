# -----------------------------------------------------------------------------
# Name:         consecutions.py
# Purpose:      Object for storing a note's consecutive
#               relationships in its line
#
# Author:       Robert Snarrenberg
#
# Copyright:    (c) 2021 by Robert Snarrenberg
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
import unittest
import logging

from music21 import *

# -----------------------------------------------------------------------------
# MAIN CLASS
# -----------------------------------------------------------------------------


class Consecutions:
    """An object holding the generic types of melodic consecution
    for a note to the left and right (approach and departure):
    the interval, its direction, (-1, 0, 1) and the consecution type
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


def setConsecutions(part):
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


def getConsecutions(idx, part):
    """
    Given a note index in a part, set the note's Consecution object
    if not already extant.
    """
    if part.recurse.notes(idx).consecutions is None:
        n = part.recurse().notes[idx]
        if idx == 0:
            nLeft = None
        else:
            nLeft = part.recurse().notes[idx-1]
        if idx == len(part.recurse().notes)-1:
            nRight = None
        else:
            nRight = part.recurse().notes[idx+1]
        part.recurse.notes(idx).consecutions = Consecutions(n, nLeft, nRight)

# -----------------------------------------------------------------------------


class Test(unittest.TestCase):

    def runTest(self):
        pass

    def test_setConsecutions(self):
        p = stream.Part()
        n1 = note.Note('C4')
        n2 = note.Note('D4')
        n3 = note.Note('E4')
        n4 = note.Note('G3')
        n5 = note.Rest()
        n6 = note.Note('C4')
        p.append(n1)
        p.append(n2)
        p.append(n3)
        p.append(n4)
        p.append(n5)
        p.append(n6)
        setConsecutions(p)
        self.assertTrue(n1.consecutions.leftInterval is None)
        self.assertTrue(n2.consecutions.leftType == 'step')
        self.assertTrue(n4.consecutions.rightType == 'skip')
        self.assertTrue(n2.consecutions.leftDirection == 1)
        self.assertFalse(n3.consecutions.rightDirection == 1)
        self.assertTrue(n4.consecutions.rightType == 'skip')
        pass

    def test_getConsecutions(self):
        pass


# -----------------------------------------------------------------------------


if __name__ == "__main__":
    unittest.main()


# -----------------------------------------------------------------------------
# eof
