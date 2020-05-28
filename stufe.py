#-------------------------------------------------------------------------------
# Name:         stufe.py
# Purpose:      Object for storing harmonic degrees (Stufen)
#
# Author:       Robert Snarrenberg
#-------------------------------------------------------------------------------


# from music21 import *
import csd

class Stufe():
    ''' An object for harmonic Stufen '''
    def __init__(self):
        pass
        self.name = None # Roman numeral: I, II, ...
        self.nameSimple = None  # Uppercase RN
        self.nameFancy = None # Upper or lowercase, +, °
        self.nameSimpleWithFiguredBass = None # Upper case plus fig bass shorthand

        self.value = None # Arabic numeral: 0, 1, ...

        self.onset = None # initial timepoint of the stufe span
        self.offset = None # endpoint of the stufe span
        self.harmonicFunctionName = None # Ti, P, D, Tc, Ts ....
    
    # list of csd combinations for each stufe value
    StufeDictionary = {
        0: [0,2,4],
        1: [1,3,5],
        2: [2,4,6],
        3: [3,5,7],
        4: [4,6,0],
        5: [5,7,1],
        6: [6,0,2],
        }

    StufeTranslationTable = {
        'I':     0,
        'II':     1,
        'III':     2,
        'IV':     3,
        'V':     4,
        'VI':     5,
        'VII':     6,
        }