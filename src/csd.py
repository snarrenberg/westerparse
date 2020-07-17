# ------------------------------------------------------------------------------
# Name:         csd.py
# Purpose:      Object for storing scale degree properties of a note
#
# Author:       Robert Snarrenberg
# Copyright:    (c) 2020 by Robert Snarrenberg
# License:      BSD, see license.txt
# ------------------------------------------------------------------------------
"""
Concrete Scale Degree (CSD)
===========================
"""
# This should be converted to a method, using the key of a Note's Context.

from music21 import *


class CSDError(Exception):
    logfile = 'logfile.txt'

    def __init__(self, desc):
        self.desc = desc
        self.logfile = 'logfile.txt'

    def logerror(self):
        log = open(self.logfile, 'a')
        print('CSD Error:', self.desc, file=log)

# -----------------------------------------------------------------------------
# MAIN CLASS
# -----------------------------------------------------------------------------


class ConcreteScaleDegree:
    """A scale degree value based on an actual pitch object.
    Tonic = 0. Leading tone = -1. The upper octave = 7.
    The fifth above = 4.
    Scale degree residue classes are easily inferred from
    these values using mod7.
    """
    # given a ConcreteScale (scale) with registrally defined keynote
    # return the scale degree of a pitch p, if it is in the scale
    # for example, if the scale is C major and the keynote is middle C (C4),
    # the CSD.value of C4 is 0, though we call it 'scale degree 1'
    # the CSD.value of D4 is 1, though we call it 'scale degree 2'
    # the CSD.value of B3 is -1, though we call it 'scale degree 7'
    # CSDs also have a Direction property

    # Uses music21's scale.MajorScale or scale.MelodicMinorScale

    # TODO incorporate chromatic alterations: tuple (value, alteration)

    def __init__(self, p, scale):
        keynote = scale.getTonic()
        dist = int(p.diatonicNoteNum) - int(keynote.diatonicNoteNum)
        self.errors = []
        if not scale.isConcrete:
            error = 'Cannot assign scale degrees using the given scale.'
            raise CSDError(error)
            return False
        else:
            if scale.type == 'major':
                scale.getScaleDegreeFromPitch(p)
                self.direction = 'bidirectional'
            elif scale.type == 'melodic minor':
                if scale.getScaleDegreeFromPitch(p) in {1, 2, 3, 4, 5, 6}:
                    self.direction = 'bidirectional'
                elif scale.getScaleDegreeFromPitch(p) in {7}:
                    self.direction = 'ascending'
                elif scale.getScaleDegreeFromPitch(p.transpose('A1')) in {6, 7}:
                    self.direction = 'descending'
                else:
                    error = ('CSD Error: At least one of pitches in the line'
                             'is not in the given scale of '
                             + scale.name + ': ' + p.nameWithOctave + '.')
                    raise CSDError(error)
                    return False
        if dist >= 0:
            csd = 1 + dist
            dir = ''
        # this only works for one octave below tonic
        elif dist < 0:
            csd = 8 + dist
            dir = '-'
        self.dir = dir
        # self.value for use in calculations
        self.value = dist
        self.degree = str(csd)
        self.name = p.nameWithOctave
        # in case I want to use this script to output content for a LaTeX file,
        # I've created properties that assign the LaTeX codes that I use to
        # obtain scale degree names: integers with a hat or bar above it
        if dist >= 0:
            self.latexcode = '\\sd{' + self.degree + '}'
        # this only works for one octave below tonic
        elif dist < 0:
            self.latexcode = '\\sdd{' + self.degree + '}'

    def __repr__(self):
        csd = self.value
        return ('<' + self.name + ': scale degree '
                + self.dir + self.degree + ' direction='
                + self.direction + '>')

# -----------------------------------------------------------------------------


if __name__ == '__main__':
    # self_test code
    pass
# -----------------------------------------------------------------------------
# eof
