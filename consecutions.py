#-------------------------------------------------------------------------------
# Name:         consecutions.py
# Purpose:      Object for storing a note's consecutive relationships in its line
#
# Author:       Robert Snarrenberg
#
#-------------------------------------------------------------------------------
'''This should be converted to a method.'''

from music21 import *

class Consecutions():
    '''An object holding the generic types of melodic consecution for a note
    left and right = approach and departure. 
    an interval, its direction, and the consecution type
    Calculated from a three-note linear segment'''
    def __init__(self, targetNote, leftNote=None, rightNote=None):

#        validConsecutionTypes = ('same', 'step', 'skip', None)    
        self.leftNote = leftNote
        self.rightNote = rightNote
        self.targetNote = targetNote
        
    def get_leftInterval(self):
        if self.leftNote !=None:
            leftInterval = interval.Interval(self.leftNote, self.targetNote)
        else: leftInterval = None
        return leftInterval

    def get_rightInterval(self):
        if self.rightNote !=None:
            rightInterval = interval.Interval(self.targetNote, self.rightNote)
        else: rightInterval = None
        return rightInterval

    def get_leftDirection(self):
        if self.leftInterval:
            leftDirection = self.leftInterval.direction
        else: leftDirection = None
        return leftDirection

    def get_leftType(self):
        if self.leftInterval:
            if self.leftInterval.isDiatonicStep:
                leftType = 'step'
            elif self.leftInterval.name == 'P1':
                leftType = 'same'
            else:
                leftType = 'skip'
        else: leftType = None
        return leftType
            
    def get_rightDirection(self):
        if self.rightInterval:
            rightDirection = self.rightInterval.direction
        else: rightDirection = None
        return rightDirection

    def get_rightType(self):
        if self.rightInterval:
            if self.rightInterval.isDiatonicStep:
                rightType = 'step'
            elif self.rightInterval.name == 'P1':
                rightType = 'same'
            else:
                rightType = 'skip'
        else: rightType = None
        return rightType
    
    leftInterval = property(get_leftInterval)
    rightInterval = property(get_rightInterval)
    leftDirection = property(get_leftDirection)
    rightDirection = property(get_rightDirection)
    leftType = property(get_leftType)
    rightType = property(get_rightType)
        
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
