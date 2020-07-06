#-------------------------------------------------------------------------------
# Name:         vlChecker.py
# Purpose:      Framework for analyzing voice leading in species counterpoint
#
# Author:       Robert Snarrenberg
# Copyright:    (c) 2020 by Robert Snarrenberg
# License:      LGPL or BSD, see license.txt
#-------------------------------------------------------------------------------
'''
Voice Leading Checker
=====================

The Voice Leading Checker module takes a score with two or more parts (lines)
and examines the local voice leading for conformity with Westergaard's rules 
of species counterpoint.

The module uses music21's theoryAnalyzer module to parse the score into small bits
for analysis, bits such as pairs of simultaneous notes, complete verticalities, 
and voice-leading quartets. The results are stored in the analyzer's analysisData 
dictionary. The voice-leading checker then analyzes these bits of data.

A voice pair (vPair) is a pair of simultaneous notes in two parts:

   * v1: n
   * v0: n

A voice-leading quartet (VLQ) consists of pairs of simultaneous notes in two parts:

   * v1: n1, n2
   * v2: n1, n2
    
[Note: Part-ordering in music21's definition VLQ is not fixed (i.e., voice 1 is not 
always the top or bottom voice). Tony Li wrote a new method for getting
VLQs that fixes this problem: v1 is always the top voice.]

The numbering of parts in vPairs and VLQs is, unfortunately, not consistent. This reflects a conceptual
conflict between music21's part-numbering scheme, which numbers the parts of a score from
top to bottom (part 0 = the topmost part), and the conceptual scheme of voice-leading
analysis in classical theory, which reckons intervals from the bottom 
to the top (part 0 = the bass part). 

Westergaard's rules for combining lines cover four areas: 

   * intervals between consecutive notes
   * intervals between simultaneous notes: dissonance
   * intervals between simultaneous notes: sonority
   * motion between pairs of simultaneously sounding notes 

While most of the rules for intervals between consecutive notes are handled by the rules of
linear syntax, there is one such rule that has a contrapuntal component: the rule
that prohibits the implication of a six-four chord by controlling the
situations in which the bass leaps a perfect fourth. 

The rules controlling leaps of a fourth in the bass, dissonance, and motion are absolutes,
hence any infractions automatically yield an error report. The rules for controlling 
sonority, on the other hand, are rules of advice. Nonconformity with the sonority rules
is only reported on demand. [This option is not yet available.]


[Etc.]

'''

# NB: vlq parts and score Parts are numbered top to bottom
# NB: vPair parts are numbered bottom to top

from music21 import *
# TODO may not need to import csd and context, since these are already active?
import csd
import context
import theoryAnalyzerWP
import theoryResultWP
import itertools
from utilities import *


# variables set by instructor
allowSecondSpeciesBreak = True

# create lists to collect errors, for reporting to user
vlErrors = []

# -----------------------------------------------------------------------------
# MAIN SCRIPT
# -----------------------------------------------------------------------------

def checkCounterpoint(context, report=True, sonorityCheck=False, **keywords):
    '''This is the main script. It creates the analysis database and then
    checks every pair of parts in the score for conformity with the rules that control
    dissonance and the rules that prohibit certain forms of motion.''''
    # extract relevant information from the score, if contrapuntal
    # use revised versions of music21 theory analyzer module
    analytics = theoryAnalyzerWP.Analyzer()
    analytics.addAnalysisData(context.score)

    # CURRENT VERSION: TEST EACH PAIR OF LINES
    # information access to other activity in other lines is limited
    # works best for two-part simple species
    # each pairing has its own subroutines: 1:1; 1:2; 1:3 and 1:4; and syncopated

    checkPartPairs(context.score, analytics)
    checkFourthLeapsInBass(context.score, analytics)

    # report voice-leading errors, if asked
    if report == True:
        if vlErrors == []:
            result = 'No voice-leading errors found.\n'
        else:
            result = 'Voice Leading Report \n\n\tThe following voice-leading errors were found:'
            for error in vlErrors: 
                result = result + '\n\t\t' + error
        print(result)
    else: 
        pass

# -----------------------------------------------------------------------------
# LIBRARY OF METHODS FOR EVALUTING VOICE LEADING ATOMS
# -----------------------------------------------------------------------------

# Methods for note pairs

def isConsonanceAboveBass(b, u):
    '''docstring'''
    # equivalent to music21.Interval.isConsonant()
    # input two notes with pitch, a bass note an upper note
    vert_int = interval.Interval(b, u)
    if interval.getAbsoluteLowerNote(b, u) == b and vert_int.simpleName in {'P1', 'm3', 'M3', 'P5', 'm6', 'M6'}:
        return True
    else: return False

def isThirdOrSixthAboveBass(b, u):
    '''docstring'''
    # input two notes with pitch, a bass note an upper note
    vert_int = interval.Interval(b, u)
    if interval.getAbsoluteLowerNote(b, u) == b and vert_int.simpleName in {'m3', 'M3', 'm6', 'M6'}:
        return True
    else: return False

def isConsonanceBetweenUpper(u1, u2):
    '''docstring'''
    # input two notes with pitch, two upper-line notes
    # P4, A4, and d5 require additional test with bass: isPermittedDissonanceBetweenUpper()
    vert_int = interval.Interval(u1, u2)
    if vert_int.simpleName in {'P1', 'm3', 'M3', 'P4', 'P5', 'm6', 'M6'}:
        return True
    else: return False
    
def isPermittedDissonanceBetweenUpper(u1, u2):
    '''docstring'''
    # input two notes with pitch, two upper-line notes
    # P4, A4, and d5 require additional test with bass
    vert_int = interval.Interval(u1, u2)
    if vert_int.simpleName in {'P4', 'A4', 'd5'}:
        return True
    else: return False
    
def isTriadicConsonance(n1, n2):
    '''docstring'''
    int = interval.Interval(n1, n2)
    if int.simpleName in {'P1', 'm3', 'M3', 'P4', 'P5', 'm6', 'M6'}:
        return True
    else: return False

def isTriadicInterval(n1, n2):
    '''docstring'''
    ivl = interval.Interval(n1, n2)
    if ivl.simpleName in {'P1', 'm3', 'M3', 'P4', 'A4', 'd5', 'P5', 'm6', 'M6'}:
        return True
    else: return False

def isPerfectVerticalConsonance(n1, n2):
    '''docstring'''
    ivl = interval.Interval(n1, n2)
    if ivl.simpleName in {'P1', 'P5', 'P8'}:
        return True
    else: return False

def isImperfectVerticalConsonance(n1, n2):
    '''docstring'''
    ivl = interval.Interval(n1, n2)
    if ivl.simpleName in {'m3', 'M3', 'm6', 'M6'}:
        return True
    else: return False

def isVerticalDissonance(n1, n2):
    '''docstring'''
    ivl = interval.Interval(n1, n2)
    if ivl.simpleName not in {'P1', 'P5', 'P8', 'm3', 'M3', 'm6', 'M6'}:
        return True
    else: return False

def isDiatonicStep(n1, n2):
    '''docstring'''
    lin_ivl = interval.Interval(n1, n2)
    if lin_ivl.name in {'m2', 'M2'}:
        return True
    else: return False
    
def isUnison(n1, n2):
    '''docstring'''
    lin_ivl = interval.Interval(n1, n2)
    if lin_ivl.name in {'P1'}:
        return True
    else: return False

def isOctave(n1, n2):
    '''docstring'''
    lin_ivl = interval.Interval(n1, n2)
    if lin_ivl.name in {'P8', 'P15'}:
        return True
    else: return False
        
# Methods for voice-leading quartets

def isSimilarUnison(vlq):
    '''docstring'''
    rules = [vlq.similarMotion() == True,
            vlq.vIntervals[1] != vlq.vIntervals[0],
            vlq.vIntervals[1].name == 'P1']
    if all(rules):
        return True
    else: return False

def isSimilarFromUnison(vlq):
    '''docstring'''
    rules = [vlq.similarMotion() == True,
            vlq.vIntervals[1] != vlq.vIntervals[0],
            vlq.vIntervals[0].name == 'P1']
    if all(rules):
        return True
    else: return False

def isSimilarFifth(vlq):
    '''docstring'''
    rules = [vlq.similarMotion() == True,
            vlq.vIntervals[1] != vlq.vIntervals[0],
            vlq.vIntervals[1].simpleName == 'P5']
    if all(rules):
        return True
    else: return False
                
def isSimilarOctave(vlq):
    '''docstring'''
    rules = [vlq.similarMotion() == True,
            vlq.vIntervals[1] != vlq.vIntervals[0],
            vlq.vIntervals[1].name in ['P8', 'P15', 'P22']]
    if all(rules):
        return True
    else: return False
    
def isParallelUnison(vlq):
    '''docstring'''
    rules = [vlq.parallelMotion() == True,
            vlq.vIntervals[1].name in ['P1']]
    if all(rules):
        return True
    else: return False

def isParallelFifth(vlq):
    '''docstring'''
    rules = [vlq.parallelMotion() == True,
            vlq.vIntervals[1].simpleName == 'P5']
    if all(rules):
        return True
    else: return False

def isParallelOctave(vlq):
    '''docstring'''
    rules = [vlq.parallelMotion() == True,
            vlq.vIntervals[1].name in ['P8', 'P15', 'P22']]
    if all(rules):
        return True
    else: return False

def isVoiceOverlap(vlq):
    '''docstring'''
    rules = [vlq.v1n2.pitch < vlq.v2n1.pitch,
            vlq.v2n2.pitch > vlq.v1n1.pitch]
    if any(rules):
        return True
    else: return False

def isVoiceCrossing(vlq):
    '''docstring'''
    rules = [vlq.v1n1.pitch > vlq.v2n1.pitch,
            vlq.v1n2.pitch < vlq.v2n2.pitch]
    if all(rules):
        return True
    else: return False

def isCrossRelation(vlq):
    '''docstring'''
    rules = [interval.Interval(vlq.v1n1, vlq.v2n2).simpleName in ['d1', 'A1'],
            interval.Interval(vlq.v2n1, vlq.v1n2).simpleName in ['d1', 'A1']]
    if any(rules):
        return True
    else: return False
    
# Methods for notes

def isOnbeat(note):
    '''docstring'''
    rules = [note.beat == 1.0]
    if any(rules):
        return True
    else: return False

def isSyncopated(score, note):
    '''docstring'''
    # TODO this is a first attempt at defining the syncopation property
    #    given a time signature and music21's default metric system for it
    # this works for duple simple meter, not sure about compound or triple
    
    # get the time signature
    ts = score.recurse().getElementsByClass(meter.TimeSignature)[0]    

    # determine the length of the note
    # tied-over notes have no independent duration
    if note.tie == None:
        note.len = note.quarterLength
    elif note.tie.type == 'start':
        note.len = note.quarterLength + note.next().quarterLength
    elif note.tie.type == 'stop':
        note.len = 0
    # find the maximum metrically stable duration of a note initiated at t
    maxlen = note.beatStrength * note.beatDuration.quarterLength * ts.beatCount
    # determine whether the note is syncopated
    if n.len > maxlen: 
        return True
    elif n.len == 0:
        return None
    else:
        return False
    
# -----------------------------------------------------------------------------
# SCRIPTS FOR EVALUATING VOICE LEADING, BY SPECIES
# -----------------------------------------------------------------------------

def checkPartPairs(score, analyzer):
    '''docstring'''
    partNumPairs = getAllPartNumPairs(score)
    for numPair in partNumPairs:
        if score.parts[numPair[0]].species == 'first' and score.parts[numPair[1]].species == 'first':
            checkFirstSpecies(score, analyzer, numPair)
        if (score.parts[numPair[0]].species == 'first' and score.parts[numPair[1]].species == 'second'
                or score.parts[0].species == 'second' and score.parts[numPair[1]].species == 'first'):
            checkSecondSpecies(score, analyzer, numPair)
        if (score.parts[numPair[0]].species == 'first' and score.parts[numPair[1]].species == 'third'
                or score.parts[0].species == 'third' and score.parts[numPair[1]].species == 'first'):
            checkThirdSpecies(score, analyzer, numPair)
        if (score.parts[numPair[0]].species == 'first' and score.parts[numPair[1]].species == 'fourth'
                or score.parts[0].species == 'fourth' and score.parts[numPair[1]].species == 'first'):
            checkFourthSpecies(score, analyzer, numPair)
    # TODO add pairs for combined species: Westergaard chapter 6
    # second and second
    # third and third
    # fourth and fourth
    # second and third
    # second and fourth
    # third and fourth

def checkFirstSpecies(score, analyzer, numPair):
    '''docstring'''
    analytics = theoryAnalyzerWP.Analyzer()
    analytics.addAnalysisData(score)
    checkFinalStep(score, analytics, partNum1=numPair[0], partNum2=numPair[1])
    firstSpeciesForbiddenMotions(score, analytics, partNum1=numPair[0], partNum2=numPair[1])
#
    checkControlOfDissonance(score, analyzer)
#
#    firstSpeciesControlOfDissonance(score, analytics, partNum1=numPair[0], partNum2=numPair[1])
#    getOnbeatIntervals(score, analytics, partNum1=numPair[0], partNum2=numPair[1])
#    firstSpeciesSonority(score, analyzer)
    
def checkSecondSpecies(score, analyzer, numPair):
    '''docstring'''
    analytics = theoryAnalyzerWP.Analyzer()
    analytics.addAnalysisData(score)
    checkConsecutions(score)
    checkFinalStep(score, analytics, partNum1=numPair[0], partNum2=numPair[1])
    secondSpeciesForbiddenMotions(score, analytics, partNum1=numPair[0], partNum2=numPair[1])
#
    checkControlOfDissonance(score, analyzer)
#
#    secondSpeciesControlOfDissonance(score, analytics, partNum1=numPair[0], partNum2=numPair[1])
    checkSecondSpeciesNonconsecutiveUnisons(score, analytics, partNum1=numPair[0], partNum2=numPair[1])
    checkSecondSpeciesNonconsecutiveOctaves(score, analytics, partNum1=numPair[0], partNum2=numPair[1])

def checkThirdSpecies(score, analyzer, numPair):
    '''docstring'''
    analytics = theoryAnalyzerWP.Analyzer()
    analytics.addAnalysisData(score)
    checkConsecutions(score)
    checkFinalStep(score, analytics, partNum1=numPair[0], partNum2=numPair[1])
    partNumPairs = getAllPartNumPairs(score)
    thirdSpeciesForbiddenMotions(score, analytics, partNum1=numPair[0], partNum2=numPair[1])
#
    checkControlOfDissonance(score, analyzer)
#
#    thirdSpeciesControlOfDissonance(score, analytics, partNum1=numPair[0], partNum2=numPair[1])

def checkFourthSpecies(score, analyzer, numPair):
    '''docstring'''
    analytics = theoryAnalyzerWP.Analyzer()
    analytics.addAnalysisData(score)
    checkConsecutions(score)
    checkFinalStep(score, analytics, partNum1=numPair[0], partNum2=numPair[1])
    partNumPairs = getAllPartNumPairs(score)
    fourthSpeciesForbiddenMotions(score, analytics, partNum1=numPair[0], partNum2=numPair[1])
    fourthSpeciesControlOfDissonance(score, analytics, partNum1=numPair[0], partNum2=numPair[1])

def checkConsecutions(score):
    '''docstring'''
    for part in score.parts:
        if part.species in ['second', 'third']:
            for n in part.recurse().notes:
                if n.consecutions.leftType == 'same':
                    error = 'Direct repetition in bar ' + str(n.measureNumber)
                    vlErrors.append(error)
        if part.species == 'fourth':
            for n in part.recurse().notes:
                if n.tie:
                    if n.tie.type == 'start' and n.consecutions.rightType != 'same':
                        error = 'Pitch not tied across the barline into bar ' + str(n.measureNumber+1)
                        vlErrors.append(error)
                    elif n.tie.type == 'stop' and n.consecutions.leftType != 'same':
                        error = 'Pitch not tied across the barline into bar ' + str(n.measureNumber)
                        vlErrors.append(error)
                # TODO allow breaking into second species
                elif not n.tie:
                    if n.consecutions.rightType == 'same':
                        error = 'Direct repetition around bar ' + str(n.measureNumber)
                        vlErrors.append(error)

def checkFinalStep(score, analyzer, partNum1=None, partNum2=None):
    '''docstring'''
    # TODO rewrite based on parser's lineType value
    # determine whether the the upper part is a primary upper line
    # if score.parts[partNum1].isPrimary == True:
    if score.parts[partNum1].id == 'Primary Upper Line':
        # assume there is no acceptable final step connection until proven true
        finalStepConnection = False
        # get the last note of the primary upper line
        ultimaNote = score.parts[partNum1].recurse().notes[-1]
        # get the penultimate note of the bass 
        penultBass = score.parts[partNum2].recurse().notes[-2]
        # collect the notes in the penultimate bar of the upper line
        penultBar = score.parts[partNum1].getElementsByClass(stream.Measure)[-2].notes
        buffer = []
        stack = []
        def shiftBuffer(stack, buffer):
            nextnote = buffer[0]
            buffer.pop(0)
            stack.append(nextnote)            
        # fill buffer with notes of penultimate bar in reverse
        for n in reversed(penultBar): 
            buffer.append(n)
        blen = len(buffer)
        # start looking for a viable step connection
        while blen > 0:
            if isDiatonicStep(ultimaNote, buffer[0]) and isConsonanceAboveBass(penultBass, buffer[0]):
                # check penultimate note
                if len(stack) == 0:
                    finalStepConnection = True
                    break
                # check other notes, if needed
                elif len(stack) > 0:
                    for s in stack:
                        if isDiatonicStep(s, buffer[0]):
                            finalStepConnection = False
                            break
                        else:
                            finalStepConnection = True
            shiftBuffer(stack, buffer)
            blen = len(buffer)
        if finalStepConnection == False:
            error = 'No final step connection in the primary upper line'
            vlErrors.append(error)
    else:
        pass
   
def checkControlOfDissonance(score, analyzer):
    '''docstring'''
    partNumPairs = getAllPartNumPairs(score)
    verts = analyzer.getVerticalities(score)
    bassPartNum = len(score.parts)-1
    for numPair in partNumPairs:
        for vert in verts:
            upperNote = vert.objects[numPair[0]]
            lowerNote = vert.objects[numPair[1]]
            laterNote = None
            if upperNote.beat > lowerNote.beat:
                laterNote = upperNote
            elif upperNote.beat < lowerNote.beat:
                laterNote = lowerNote
            
            # do not evaluate a vertical pair if one note is a rest
            # TODO this is okay for now, but need to check the rules for all gambits
            # ? and what if there's a rest during a line?
            if upperNote.isRest or lowerNote.isRest: continue
            
            # both notes start at the same time, neither is tied over
            rules1 = [upperNote.beat == lowerNote.beat,
                (upperNote.tie == None or upperNote.tie.type == 'start'),
                (lowerNote.tie == None or lowerNote.tie.type == 'start')]
            # the pair constitutes a permissible consonance above the bass
            rules2a = [bassPartNum in numPair,
                isConsonanceAboveBass(lowerNote, upperNote)]
            # the pair constitutes a permissible consonance between upper parts
            rules2b = [bassPartNum not in numPair,
                isConsonanceBetweenUpper(lowerNote, upperNote)]
            # the pair is a permissible dissonance between upper parts
            # TODO this won't work if the bass is a rest and not a note
            rules2c = [bassPartNum not in numPair,
                isPermittedDissonanceBetweenUpper(lowerNote, upperNote),
                isThirdOrSixthAboveBass(vert.objects[bassPartNum], upperNote),
                isThirdOrSixthAboveBass(vert.objects[bassPartNum], lowerNote)]
            
            # test co-initiated simultaneities
            if all(rules1) and not (all(rules2a) or all(rules2b) or all(rules2c)):
                    error = 'Dissonance between co-initiated notes in bar ' + str(upperNote.measureNumber) + \
                        ': ' + str(interval.Interval(lowerNote, upperNote).name)
                    vlErrors.append(error)

            # one note starts after the other
            rules3 = [upperNote.beat != lowerNote.beat, 
                    not (all(rules2a) or all(rules2b) or all(rules2c))]
            rules4 = [upperNote.beat > lowerNote.beat]
            rules5a = [upperNote.consecutions.leftType == 'step',
                    upperNote.consecutions.rightType == 'step']
            rules5b = [lowerNote.consecutions.leftType == 'step',
                    lowerNote.consecutions.rightType == 'step']


            # both notes start at the same time, one of them is tied over
            
#             rules1 = [upperNote.beat == lowerNote.beat,
#                 (upperNote.tie == None or upperNote.tie.type == 'start'),
#                 (lowerNote.tie == None or lowerNote.tie.type == 'start')]
# 
#             if score.parts[-1] in [score.parts[partNum1], score.parts[partNum2]]:
#                 # look for onbeat note that is dissonant and improperly treated
#                 rules = [vPair[speciesPart].beat == 1.0,
#                         not isConsonanceAboveBass(vPair[0], vPair[1]),
#                         not vPair[speciesPart].consecutions.leftType == 'same',
#                         not vPair[speciesPart].consecutions.rightType == 'step']
#                 if all(rules):
#                     error = 'Dissonant interval on the beat that is either not prepared '\
#                             'or not resolved in bar ' + str(vPair[0].measureNumber) + ': '\
#                              + str(interval.Interval(vPair[1], vPair[0]).name)
#                     vlErrors.append(error)
#                 # look for second-species onbeat dissonance
#                 rules = [vPair[speciesPart].beat == 1.0,
#                         vPair[speciesPart].tie == None,
#                         not isConsonanceAboveBass(vPair[0], vPair[1])]
#                 if all(rules):
#                     error = 'Dissonant interval on the beat that is not permitted when ' \
#                             'fourth species is broken in ' + str(vPair[0].measureNumber) + ': ' \
#                              + str(interval.Interval(vPair[1], vPair[0]).name)
#                     vlErrors.append(error)
#                 # look for offbeat note that is dissonant and tied over
#                 rules = [vPair[speciesPart].beat > 1.0,
#                             not isConsonanceAboveBass(vPair[0], vPair[1]),
#                             vPair[0].tie != None or vPair[1].tie != None]
#                 if all(rules):
#                     error = 'Dissonant interval off the beat in bar ' + \
#                             str(vPair[0].measureNumber) + ': ' + \
#                             str(interval.Interval(vPair[1], vPair[0]).name)
#                     vlErrors.append(error)

            # both notes start at the same time, both of them are tied over
            


            if all(rules3) and ((all(rules4) and not all(rules5a)) or (not all(rules4) and not all(rules5b))):
                error = 'Dissonant interval off the beat that is not approached and left by step in bar ' + str(lowerNote.measureNumber) + ': ' + str(interval.Interval(lowerNote, upperNote).name)
                vlErrors.append(error)

        # check whether consecutive dissonances move in one directions
        vlqList = analyzer.getVLQs(score, numPair[0], numPair[1])
        for vlq in vlqList:
#            if vlq.v1n1 == vlq.v1n2 or vlq.v2n1 == vlq.v2n2:
#                print('motion is oblique against sustained tone')
            # either both of the intervals are dissonant above the bass
            rules1a = [bassPartNum in numPair,
                    isVerticalDissonance(vlq.v1n1, vlq.v2n1),
                    isVerticalDissonance(vlq.v1n2, vlq.v2n2)]
            # or both of the intervals are prohibited dissonances between upper parts
            rules1b = [bassPartNum not in numPair,
                    isVerticalDissonance(vlq.v1n1, vlq.v2n1),
                    not isPermittedDissonanceBetweenUpper(vlq.v1n1, vlq.v2n1),
                    isVerticalDissonance(vlq.v1n2, vlq.v2n2),
                    not isPermittedDissonanceBetweenUpper(vlq.v1n2, vlq.v2n2)]
            # either the first voice is stationary and the second voice moves in one direction
            rules2a = [vlq.v1n1 == vlq.v1n2,
                    vlq.v2n1.consecutions.leftDirection == vlq.v2n2.consecutions.leftDirection,
                    vlq.v2n1.consecutions.rightDirection == vlq.v2n2.consecutions.rightDirection]
            # or the second voice is stationary and the first voice moves in one direction
            rules2b = [vlq.v2n1 == vlq.v2n2,
                    vlq.v1n1.consecutions.leftDirection == vlq.v1n2.consecutions.leftDirection,
                    vlq.v1n1.consecutions.rightDirection == vlq.v1n2.consecutions.rightDirection]
            # must be in the same measure
            rules3 = [vlq.v1n1.measureNumber != vlq.v1n2.measureNumber]
            if (all(rules1a) or all(rules1b)) and not (all(rules2a) or all(rules2b)) and not(all(rules3)):
                error = 'Consecutive dissonant intervals in bar ' \
                    + str(vlq.v1n1.measureNumber) + ' are not approached and left '\
                    'in the same direction'
                vlErrors.append(error)

        
    # TODO check third species consecutive dissonances
    
    # TODO fix so that it works with higher species line that start with rests in the bass
    
    # TODO check fourth species control of dissonance
    # check resolution of diss relative to onbeat note (which may move if not whole notes) to determine category of susp
    #     this can be extracted from the vlq: e.g., v1n1,v2n1 and v1n2,v2n1
    # separately check the consonance of the resolution in the vlq (v1n2, v2n2)
    # add rules for multiple parts
    # TODO add contiguous intervals to vlqs ?? xint1, xint2

    pass

def firstSpeciesControlOfDissonance(score, analyzer, partNum1=None, partNum2=None):
    '''docstring'''
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)
    for vPair in vPairList:
        # check intervals above bass
        if len(score.parts) == partNum2+1:
            if not isConsonanceAboveBass(vPair[0], vPair[1]):
                error = 'Dissonance above bass in bar ' + str(vPair[0].measureNumber) + \
                    ': ' + str(interval.Interval(vPair[1], vPair[0]).simpleName)
                vlErrors.append(error)
        # check intervals between upper voices
        elif len(score.parts) != partNum2+1:
            if not isConsonanceBetweenUpper(vPair[0], vPair[1]):
                error = 'Dissonance between upper parts in bar ' + \
                    str(vPair[0].measureNumber) + ': ' + \
                    str(interval.Interval(vPair[1], vPair[0]).simpleName)
                vlErrors.append(error)
        
def secondSpeciesControlOfDissonance(score, analyzer, partNum1=None, partNum2=None):
    '''docstring'''
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)
    # NB: parts are numbered top to bottom and vPairs are numbered bottom to top
    if score.parts[partNum1].species == 'second':
        speciesPart = 1 # upper part, hence upper member of vpair
    elif score.parts[partNum2].species == 'second':
        speciesPart = 0 # lower part, hence lower member of vpair
    for vPair in vPairList:
        if vPair != None:
            # evaluate intervals when one of the parts is the bass
            if score.parts[-1] in [score.parts[partNum1], score.parts[partNum2]]:
# TODO vPair[speciesPart] FIX this, speciesPart is not the right index for vPair, also fix in the other species
# how to figure out which member of the vPair is the species line?
# vPairs are numbered bottom to top, parts are numbered top to bottom
                if vPair[speciesPart].beat == 1.0 and not isConsonanceAboveBass(vPair[0], vPair[1]):
                    error = 'Dissonant interval on the beat in bar ' + str(vPair[0].measureNumber) + ': ' + str(interval.Interval(vPair[1], vPair[0]).name)
                    vlErrors.append(error)
                elif vPair[speciesPart].beat > 1.0 and not isConsonanceAboveBass(vPair[0], vPair[1]):
                    rules = [vPair[speciesPart].consecutions.leftType == 'step',
                            vPair[speciesPart].consecutions.rightType == 'step']
                    if not all(rules):
                        error = 'Dissonant interval off the beat that is not approached and left by step in bar ' + str(vPair[0].measureNumber) + ': ' + str(interval.Interval(vPair[1], vPair[0]).name)
                        vlErrors.append(error)

def thirdSpeciesControlOfDissonance(score, analyzer, partNum1=None, partNum2=None):
    '''docstring'''
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)
    # NB: parts are numbered top to bottom and vPairs are numbered bottom to top
    if score.parts[partNum1].species == 'third':
        speciesPart = partNum2
    elif score.parts[partNum2].species == 'third':
        speciesPart = partNum1
    for vPair in vPairList:
        if vPair != None:
            # evaluate intervals when one of the parts is the bass
            if score.parts[-1] in [score.parts[partNum1], score.parts[partNum2]]:
                if vPair[speciesPart].beat == 1.0 and not isConsonanceAboveBass(vPair[0], vPair[1]):
                    error = 'Dissonant interval on the beat in bar ' + str(vPair[0].measureNumber) + ': ' + str(interval.Interval(vPair[1], vPair[0]).name)
                    vlErrors.append(error)
                elif vPair[speciesPart].beat > 1.0 and not isConsonanceAboveBass(vPair[0], vPair[1]):
                    rules = [vPair[speciesPart].consecutions.leftType == 'step',
                            vPair[speciesPart].consecutions.rightType == 'step']
                    if not all(rules):
                        error = 'Dissonant interval off the beat that is not approached and left by step in bar ' + str(vPair[0].measureNumber) + ': ' + str(interval.Interval(vPair[1], vPair[0]).name)
                        vlErrors.append(error)
    # check consecutive dissonant intervals
    # TODO may have to revise for counterpoint in three or more parts
    vlqList = analyzer.getVLQs(score, partNum1, partNum2)
    for vlq in vlqList:
        rules1 = [isVerticalDissonance(vlq.v1n1, vlq.v2n1),
                isVerticalDissonance(vlq.v1n2, vlq.v2n2)]
        rules2 = [vlq.v1n1 == vlq.v1n2,
                vlq.v2n1.consecutions.leftDirection == vlq.v2n2.consecutions.leftDirection,
                vlq.v2n1.consecutions.rightDirection == vlq.v2n2.consecutions.rightDirection]
        rules3 = [vlq.v2n1 == vlq.v2n2,
                vlq.v1n1.consecutions.leftDirection == vlq.v1n2.consecutions.leftDirection,
                vlq.v1n1.consecutions.rightDirection == vlq.v1n2.consecutions.rightDirection]
        if all(rules1) and not (all(rules2) or all(rules3)):
            error = 'Consecutive dissonant intervals in bar ' \
                + str(vlq.v1n1.measureNumber) + ' are not approached and left '\
                'in the same direction'
            vlErrors.append(error)

def fourthSpeciesControlOfDissonance(score, analyzer, partNum1=None, partNum2=None):
    '''docstring'''
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)
    # NB: score Parts are numbered top to bottom and vPair parts are numbered bottom to top

    if score.parts[partNum1].species == 'fourth': # species line on top
        speciesPart = 1
    elif score.parts[partNum2].species == 'fourth': # species line on bottom
        speciesPart = 0
    for vPair in vPairList:
        if vPair != None:
            # evaluate on- and offbeat intervals when one of the parts is the bass
            # TODO need to figure out rules for 3 or more parts
            if score.parts[-1] in [score.parts[partNum1], score.parts[partNum2]]:
                # look for onbeat note that is dissonant and improperly treated
                rules = [vPair[speciesPart].beat == 1.0,
                        not isConsonanceAboveBass(vPair[0], vPair[1]),
                        not vPair[speciesPart].consecutions.leftType == 'same',
                        not vPair[speciesPart].consecutions.rightType == 'step']
                if all(rules):
                    error = 'Dissonant interval on the beat that is either not prepared '\
                            'or not resolved in bar ' + str(vPair[0].measureNumber) + ': '\
                             + str(interval.Interval(vPair[1], vPair[0]).name)
                    vlErrors.append(error)
                # look for second-species onbeat dissonance
                rules = [vPair[speciesPart].beat == 1.0,
                        vPair[speciesPart].tie == None,
                        not isConsonanceAboveBass(vPair[0], vPair[1])]
                if all(rules):
                    error = 'Dissonant interval on the beat that is not permitted when ' \
                            'fourth species is broken in ' + str(vPair[0].measureNumber) + ': ' \
                             + str(interval.Interval(vPair[1], vPair[0]).name)
                    vlErrors.append(error)
                # look for offbeat note that is dissonant and tied over
                rules = [vPair[speciesPart].beat > 1.0,
                            not isConsonanceAboveBass(vPair[0], vPair[1]),
                            vPair[0].tie != None or vPair[1].tie != None]
                if all(rules):
                    error = 'Dissonant interval off the beat in bar ' + \
                            str(vPair[0].measureNumber) + ': ' + \
                            str(interval.Interval(vPair[1], vPair[0]).name)
                    vlErrors.append(error)

    # NB: vlq parts and score Parts are numbered top to bottom
    vlqList = analyzer.getVLQs(score, partNum1, partNum2)

    # determine whether breaking of species is permitted
    #     and, if so, whether proper
    breakcount = 0
    earliestBreak = 4
    latestBreak = score.measures - 4
    for vlq in vlqList:
        # look for vlq where second note in species line is not tied over
        if speciesPart == 1: 
            speciesNote = vlq.v1n2
        elif speciesPart == 0:
            speciesNote = vlq.v2n2
        if speciesNote.tie == None and speciesNote.beat > 1.0:
            if allowSecondSpeciesBreak == False and speciesNote.measureNumber != score.measures-1:
                error = 'Breaking of fourth species is allowed only at the end and not in \
                    bars ' + str(speciesNote.measureNumber) + ' to ' + str(speciesNote.measureNumber+1)
                vlErrors.append(error)
            elif allowSecondSpeciesBreak == True and speciesNote.measureNumber != score.measures-1:
                rules = [earliestBreak < speciesNote.measureNumber < latestBreak,
                    breakcount < 1]
                if all(rules):
                    breakcount += 1
                elif breakcount >= 1:
#                    print('no tie in bar', speciesNote.measureNumber)
                    error = 'Breaking of fourth species is only allowed once during the exercise.'
                    vlErrors.append(error)
                elif earliestBreak > speciesNote.measureNumber:
                    error = 'Breaking of fourth species in bars ' + str(speciesNote.measureNumber) + \
                        ' to ' + str(speciesNote.measureNumber+1) + ' occurs too early.'
                    vlErrors.append(error)
                elif speciesNote.measureNumber > latestBreak:
                    error = 'Breaking of fourth species in bars ' + str(speciesNote.measureNumber) + \
                        ' to ' + str(speciesNote.measureNumber+1) + ' occurs too late.'
                    vlErrors.append(error)
                # if the first vInt is dissonant, the speciesNote will be checked later
                # if the first vInt is consonant, the speciesNote might be dissonant
                rules = [not isVerticalDissonance(vlq.v1n1, vlq.v2n1),
                        isVerticalDissonance(vlq.v1n2, vlq.v2n2),
                        speciesNote.consecutions.leftType == 'step',
                        speciesNote.consecutions.rightType == 'step']
                if not all(rules):
                    error = 'Dissonance off the beat in bar ' + str(speciesNote.measureNumber) + \
                            ' is not approached and left by step.'
                    vlErrors.append(error)    

    # Westergaard lists
    strongSuspensions = {'upper': ['d7-6', 'm7-6', 'M7-6'], 
                        'lower': ['m2-3', 'M2-3', 'A2-3']}
    intermediateSuspensions = {'upper': ['m9-8', 'M9-8', 'd4-3', 'P4-3', 'A4-3'], 
                        'lower': ['A4-5', 'd5-6', 'A5-6']}
    weakSuspensions = {'upper': ['m2-1', 'M2-1'], 
                        'lower': [ 'm7-8', 'M7-8', 'P4-5']}
    # list of dissonances inferred from Westergaard lists
    validDissonances = ['m2', 'M2', 'A2', 'd4', 'P4', 'A5', 'd5', 'A5', 'm7', 'd7', 'M7']

    # function for distinguishing between intervals 9 and 2 in upper lines
    def dissName(intval):
        if intval.simpleName in ['m2', 'M2', 'A2'] and intval.name not in ['m2', 'M2', 'A2']:
            intervalName = interval.add([intval.simpleName, 'P8']).name
        else:
            intervalName = intval.simpleName
        return intervalName

    # make list of dissonant syncopes        
    syncopeList = {}
    for vlq in vlqList:
        if speciesPart == 1: # species line on top
            if vlq.v1n1.tie:
                if vlq.v1n1.tie.type == 'stop':
                    if vlq.vIntervals[0].simpleName in validDissonances:
                        syncopeList[vlq.v1n1.measureNumber] = (dissName(vlq.vIntervals[0]) + '-' + vlq.vIntervals[1].semiSimpleName[-1])
        elif speciesPart == 0: # species line on bottom
            if vlq.v2n1.tie:
                if vlq.v2n1.tie.type == 'stop':
                    if vlq.vIntervals[0].simpleName in validDissonances:
                        syncopeList[vlq.v2n1.measureNumber] = (vlq.vIntervals[0].simpleName + '-' + vlq.vIntervals[1].semiSimpleName[-1])
    if speciesPart == 1:
        for bar in syncopeList:
            if syncopeList[bar] not in strongSuspensions['upper'] and syncopeList[bar] not in  intermediateSuspensions['upper']:
                error = 'The dissonant syncopation in bar '+ str(bar) + ' is not permitted: ' + str(syncopeList[bar])
                vlErrors.append(error)
    elif speciesPart == 0:
        for bar in syncopeList:
            if syncopeList[bar] not in strongSuspensions['lower'] and syncopeList[bar] not in  intermediateSuspensions['lower']:
                error = 'The dissonant syncopation in bar ' + str(bar) + ' is not permitted: ' + str(syncopeList[bar])
                vlErrors.append(error)

def forbiddenMotionsOntoBeatWithoutSyncope(score, vlq, partNum1, partNum2):
    '''docstring'''
    vlqBassNote = score.parts[-1].measure(vlq.v1n2.measureNumber).getElementsByClass('Note')[0]
    if isSimilarUnison(vlq):
        error = 'Forbidden similar motion to unison going into bar ' + str(vlq.v2n2.measureNumber)
        vlErrors.append(error)
    if isSimilarFromUnison(vlq):
        error = 'Forbidden similar motion from unison in bar ' + str(vlq.v2n1.measureNumber)
        vlErrors.append(error)
    if isSimilarOctave(vlq):
        rules = [vlq.hIntervals[0].name in ['m2', 'M2'],
                vlq.v1n2.csd.value % 7 == 0,
                vlq.v1n2.measureNumber == score.measures,
                vlq.v2n2.measureNumber == score.measures]
        if not all(rules):
            error = 'Forbidden similar motion to octave going into bar ' + str(vlq.v2n2.measureNumber)
            vlErrors.append(error)
    if isSimilarFifth(vlq):
        rules1 = [vlq.hIntervals[0].name in ['m2', 'M2']]
        rules2 = [vlq.v1n2.csd.value % 7 in [1, 4]]
        # if fifth in upper parts, compare with pitch of the simultaneous bass note
        rules3 = [partNum1 != len(score.parts)-1,
                partNum2 != len(score.parts)-1,
                vlq.v1n2.csd.value % 7 != vlqBassNote.csd.value % 7,
                vlq.v2n2.csd.value % 7 != vlqBassNote.csd.value % 7]
        # TODO recheck the logic of this
        if not ((all(rules1) and all(rules2)) or (all(rules1) and all(rules3))):
            error = 'Forbidden similar motion to fifth going into bar ' + str(vlq.v2n2.measureNumber)
            vlErrors.append(error)
    if isParallelUnison(vlq):
        error = 'Forbidden parallel motion to unison going into bar ' + + str(vlq.v2n2.measureNumber)
        vlErrors.append(error)
    if isParallelOctave(vlq):
        error = 'Forbidden parallel motion to octave going into bar ' + str(vlq.v2n2.measureNumber)
        vlErrors.append(error)
    if isParallelFifth(vlq):
        error = 'Forbidden parallel motion to fifth going into bar ' + str(vlq.v2n2.measureNumber)
        vlErrors.append(error)
    if isVoiceCrossing(vlq):
        # strict rule when the bass is involved
        if partNum1 == len(score.parts)-1 or partNum2 == len(score.parts)-1:
            error = 'Voice crossing going into bar ' + str(vlq.v2n2.measureNumber)
            vlErrors.append(error)
        else:
            alert = 'ALERT: Upper voices cross going into bar '+ str(vlq.v2n2.measureNumber)
            vlErrors.append(alert)
    if isVoiceOverlap(vlq):
        if partNum1 == len(score.parts)-1 or partNum2 == len(score.parts)-1:
            error = 'Voice overlap going into bar ' + str(vlq.v2n2.measureNumber)
            vlErrors.append(error)
        else:
            alert = 'ALERT: Upper voices overlap going into bar ' + str(vlq.v2n2.measureNumber)
            vlErrors.append(alert)
    if isCrossRelation(vlq):
        if len(score.parts) < 3:
            error = 'Cross relation going into bar ' + str(vlq.v2n2.measureNumber)
            vlErrors.append(error)
        else:
            # test for step motion in another part
            crossStep = False
            for part in score.parts:
                if part != score.parts[partNum1] and part != score.parts[partNum2]:
                    vlqOtherNote1 = part.measure(vlq.v1n1.measureNumber).getElementsByClass('Note')[0]
                    vlqOtherNote2 = part.measure(vlq.v1n2.measureNumber).getElementsByClass('Note')[0]
                    if vlqOtherNote1.csd.value - vlqOtherNote2.csd.value == 1:
                        crossStep = True
                        break
            if crossStep == False:
                error = 'Cross relation going into bar ' + str(vlq.v2n2.measureNumber)
                vlErrors.append(error)    

def firstSpeciesForbiddenMotions(score, analyzer, partNum1=None, partNum2=None):
    '''docstring'''
#    if partNum1 == None and partNum2 == None:
    vlqList = analyzer.getVLQs(score, partNum1, partNum2)
    for vlq in vlqList:
        forbiddenMotionsOntoBeatWithoutSyncope(score, vlq, partNum1, partNum2)

def secondSpeciesForbiddenMotions(score, analyzer, partNum1=None, partNum2=None):
    '''docstring'''
#    if partNum1 == None and partNum2 == None:

    # check motion across the barline
    vlqList = analyzer.getVLQs(score, partNum1, partNum2)
    for vlq in vlqList:
        forbiddenMotionsOntoBeatWithoutSyncope(score, vlq, partNum1, partNum2)

    # check motion from beat to beat
    vlqOnbeatList = analyzer.getOnbeatVLQs(score, partNum1, partNum2)
    for vlq in vlqOnbeatList:
        if isParallelUnison(vlq):
            error = 'Forbidden parallel motion to unison from bar ' + \
                str(vlq.v1n1.measureNumber) + ' to bar ' + str(vlq.v1n2.measureNumber)
            vlErrors.append(error)
        # TODO revise for three parts, Westergaard p. 143
        # requires looking at simultaneous VLQs in a pair of verticalities
        if isParallelOctave(vlq):
            error = 'Forbidden parallel motion to octave from bar ' + \
                str(vlq.v1n1.measureNumber) + ' to bar ' + str(vlq.v1n2.measureNumber)
            vlErrors.append(error)            
        if isParallelFifth(vlq):
            parDirection = interval.Interval(vlq.v1n1, vlq.v1n2).direction
            if vlq.v1n1.getContextByClass('Part').species == 'second':
                vSpeciesNote1 = vlq.v1n1
                vSpeciesNote2 = vlq.v1n2
                vCantusNote1 = vlq.v2n1
                vSpeciesPartNum = vlq.v1n1.getContextByClass('Part').partNum
            elif vlq.v1n1.getContextByClass('Part').species == 'second':
                vSpeciesNote1 = vlq.v2n1
                vSpeciesNote2 = vlq.v2n2
                vCantusNote1 = vlq.v1n1
                vSpeciesPartNum = vlq.v2n1.getContextByClass('Part').partNum
            localNotes = [note for note in score.parts[vSpeciesPartNum].notes if (vSpeciesNote1.index < note.index < vSpeciesNote2.index)]
            # test for step motion contrary to parallels
            rules1 = [vSpeciesNote2.consecutions.leftDirection != parDirection,
                    vSpeciesNote2.consecutions.rightDirection != parDirection,
                    vSpeciesNote2.consecutions.leftType == 'step',
                    vSpeciesNote2.consecutions.leftType == 'step']
            # test for appearance of note as consonance in first bar
            # TODO figure out better way to test for consonance
            rules2 = False
            for note in localNotes:
                if note.pitch == vSpeciesNote2.pitch and isConsonanceAboveBass(vCantusNote1, note):
                    rules2 == True
                    break
            # TODO verify that the logic of the rules evaluation is correct
            if not (all(rules1) or rules2):
                error = 'Forbidden parallel motion to pefect fifth from the downbeat of bar ' + \
                    str(vlq.v1n1.measureNumber) + ' to the downbeat of bar ' + str(vlq.v1n2.measureNumber)
                vlErrors.append(error)

def thirdSpeciesForbiddenMotions(score, analyzer, partNum1=None, partNum2=None):
    '''docstring'''
    # TODO: finish this script??
    
    def checkMotionsOntoBeat():
    # check motion across the barline
        vlqList = analyzer.getVLQs(score, partNum1, partNum2)
        for vlq in vlqList:
            # check motion across the barline, as in first and second species
            if vlq.v1n2.beat == 1.0 and vlq.v2n2.beat == 1.0:
                forbiddenMotionsOntoBeatWithoutSyncope(score, vlq, partNum1, partNum2)
            else:
            # check motion within the bar
                if isVoiceCrossing(vlq):
                # strict rule when the bass is involved
                    if partNum1 == len(score.parts)-1 or partNum2 == len(score.parts)-1:
                        error = 'Voice crossing in bar ' + str(vlq.v2n2.measureNumber)
                        vlErrors.append(error)
                    else:
                        alert = 'ALERT: Upper voices cross in bar '+ str(vlq.v2n2.measureNumber)
                        vlErrors.append(alert)

    def checkMotionsBeatToBeat():
    # check motion from beat to beat
        vlqOnbeatList = analyzer.getOnbeatVLQs(score, partNum1, partNum2)
        for vlq in vlqOnbeatList:
            if isParallelUnison(vlq):
                error = 'Forbidden parallel motion to unison from bar ' + \
                    str(vlq.v1n1.measureNumber) + ' to bar ' + str(vlq.v1n2.measureNumber)
                vlErrors.append(error)
            if isParallelOctave(vlq) or isParallelFifth(vlq):
                parDirection = interval.Interval(vlq.v1n1, vlq.v1n2).direction
                if vlq.v1n1.getContextByClass('Part').species == 'third':
                    vSpeciesNote1 = vlq.v1n1
                    vSpeciesNote2 = vlq.v1n2
                    vCantusNote1 = vlq.v2n1
                    vSpeciesPartNum = vlq.v1n1.getContextByClass('Part').partNum
                elif vlq.v2n1.getContextByClass('Part').species == 'third':
                    vSpeciesNote1 = vlq.v2n1
                    vSpeciesNote2 = vlq.v2n2
                    vCantusNote1 = vlq.v1n1
                    vSpeciesPartNum = vlq.v2n1.getContextByClass('Part').partNum
                localSpeciesMeasure = score.parts[vSpeciesPartNum].measures(vCantusNote1.measureNumber, vCantusNote1.measureNumber)
                localNotes = localSpeciesMeasure.getElementsByClass('Measure')[0].notes
                localNotes = [note for note in localNotes if (vSpeciesNote1.index < note.index < vSpeciesNote2.index)]
                # test for step motion contrary to parallels
                rules1 = [vSpeciesNote2.consecutions.leftDirection != parDirection,
                        vSpeciesNote2.consecutions.rightDirection != parDirection,
                        vSpeciesNote2.consecutions.leftType == 'step',
                        vSpeciesNote2.consecutions.leftType == 'step']
                # test for appearance of note as consonance in first bar
                # TODO figure out better way to test for consonance
                rules2 = False
                for note in localNotes:
                    if note.pitch == vSpeciesNote2.pitch and isConsonanceAboveBass(vCantusNote1, note):
                        rules2 = True
                        break
                # TODO verify that the logic of the rules evaluation is correct
                if not (all(rules1) or rules2):
                    error = 'Forbidden parallel motion from the downbeat of bar ' + \
                        str(vlq.v1n1.measureNumber) + ' to the downbeat of bar ' + str(vlq.v1n2.measureNumber)
                    vlErrors.append(error)

    def checkMotionsOffToOnBeat():
    # check motions from off to nonconsecutive onbeat
        vlqNonconsecutivesList = analyzer.getNonconsecutiveOffbeatToOnbeatVLQs(score, partNum1, partNum2)
        for vlq in vlqNonconsecutivesList:
            if isParallelUnison(vlq):
                error = 'Forbidden parallel motion to unison from bar ' + \
                    str(vlq.v1n1.measureNumber) + ' to bar ' + str(vlq.v1n2.measureNumber)
                vlErrors.append(error)
            if isParallelOctave(vlq):
                parDirection = interval.Interval(vlq.v1n1, vlq.v1n2).direction
                if vlq.v1n1.getContextByClass('Part').species == 'third':
                    vSpeciesNote1 = vlq.v1n1
                    vSpeciesNote2 = vlq.v1n2
                    vCantusNote1 = vlq.v2n1
                    vSpeciesPartNum = vlq.v1n1.getContextByClass('Part').partNum
                elif vlq.v1n1.getContextByClass('Part').species == 'third':
                    vSpeciesNote1 = vlq.v2n1
                    vSpeciesNote2 = vlq.v2n2
                    vCantusNote1 = vlq.v1n1
                    vSpeciesPartNum = vlq.v2n1.getContextByClass('Part').partNum
                # make a list of notes in the species line simultaneous with the first cantus tone
                localSpeciesMeasure = score.parts[vSpeciesPartNum].measures(vCantusNote1.measureNumber, vCantusNote1.measureNumber)
                localNotes = localSpeciesMeasure.getElementsByClass('Measure')[0].notes
                localNotes = [note for note in localNotes]
                # test for step motion contrary to parallels
                rules1 = [vSpeciesNote2.consecutions.leftDirection != parDirection,
                        vSpeciesNote2.consecutions.rightDirection != parDirection,
                        vSpeciesNote2.consecutions.leftType == 'step',
                        vSpeciesNote2.consecutions.leftType == 'step']
                # test for appearance of note as consonance in first bar
                # TODO figure out better way to test for consonance
                rules2 = False
                for note in localNotes:
                    if note.pitch == vSpeciesNote2.pitch and isConsonanceAboveBass(vCantusNote1, note):
                        rules2 = True
                        break
                if not (all(rules1) or rules2):
                    error = 'Forbidden parallel octaves from an offbeat note in bar ' + \
                        str(vlq.v1n1.measureNumber) + ' to the downbeat of bar ' + str(vlq.v1n2.measureNumber)
                    vlErrors.append(error)
    # check leaps of a fourth in the bass: function called in checkCounterpoint()
    
    checkMotionsOntoBeat()
    checkMotionsBeatToBeat()
    checkMotionsOffToOnBeat()

#    print('NOTICE: Forbidden forms of motion in third species have not been thoroughly checked!')
    pass

def fourthSpeciesForbiddenMotions(score, analyzer, partNum1=None, partNum2=None):
    '''docstring'''
    vlqList = analyzer.getVLQs(score, partNum1, partNum2)

    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)
    # NB: score Parts are numbered top to bottom and vPair parts are numbered bottom to top
    if score.parts[partNum1].species == 'fourth': # species line on top
        speciesPart = 1
    elif score.parts[partNum2].species == 'fourth': # species line on bottom
        speciesPart = 0
    vPairsOnbeat = []
    vPairsOnbeatDict = {}
    vPairsOffbeat = []
    for vPair in vPairList:
        if vPair != None:
            # evaluate offbeat intervals when one of the parts is the bass
            if vPair[speciesPart].beat == 1.0:
                vPairsOnbeat.append(vPair)
                vPairsOnbeatDict[vPair[speciesPart].measureNumber] = vPair
            else:
                vPairsOffbeat.append(vPair)
    vlqsOffbeat = makeVLQFromVPair(vPairsOffbeat)
    vlqsOnbeat = makeVLQFromVPair(vPairsOnbeat)
    for vlq in vlqsOffbeat:
        if isParallelUnison(vlq):
            error = 'Forbidden parallel motion to unison going into bar ' + str(vlq.v2n2.measureNumber)
            vlErrors.append(error)
        if isParallelOctave(vlq):
            thisBar = vlq.v1n2.measureNumber
            thisOnbeatPair = vPairsOnbeatDict[thisBar]
            if not isConsonanceAboveBass(thisOnbeatPair[0], thisOnbeatPair[1]):
                error = 'Forbidden parallel motion to octave going into bar ' + str(vlq.v2n2.measureNumber)
                vlErrors.append(error)
    for vlq in vlqsOnbeat:
        if isParallelUnison(vlq):
            error = 'Forbidden parallel motion to unison going into bar ' + str(vlq.v2n2.measureNumber)
            vlErrors.append(error)        
    # check second-species motion across barlines, looking at vlq with initial untied offbeat note
    for vlq in vlqList:
        if speciesPart == 1: 
            speciesNote = vlq.v1n1
        elif speciesPart == 0:
            speciesNote = vlq.v2n1
        if speciesNote.tie == None and speciesNote.beat > 1.0:
            forbiddenMotionsOntoBeatWithoutSyncope(score, vlq, partNum1, partNum2)    

def checkSecondSpeciesNonconsecutiveUnisons(score, analyzer, partNum1=None, partNum2=None):
    '''docstring'''
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)
    # NB: parts are numbered top to bottom and vPairs are numbered bottom to top
    if score.parts[partNum1].species == 'second':
        speciesPart = 1
    elif score.parts[partNum2].species == 'second':
        speciesPart = 0
    else:#neither part is second species
        return
    firstUnison = None
    for vPair in vPairList:
        if firstUnison:
            if (interval.Interval(vPair[0], vPair[1]).name == 'P1'
                    and vPair[speciesPart].beat == 1.5
                    and vPair[speciesPart].measureNumber -1 == firstUnison[0]):
#                if vPair[speciesPart].consecutions.leftDirection == firstUnison[1][speciesPart].consecutions.leftDirection:
                error = 'Offbeat unisons in bars ' +  str(firstUnison[0]) + ' and ' + str(vPair[speciesPart].measureNumber)
                vlErrors.append(error)
        if vPair != None:
            if (interval.Interval(vPair[0], vPair[1]).name == 'P1'
                    and vPair[speciesPart].beat > 1.0):
                firstUnison = (vPair[speciesPart].measureNumber, vPair)
    
def checkSecondSpeciesNonconsecutiveOctaves(score, analyzer, partNum1=None, partNum2=None):
    '''docstring'''
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)
    # NB: parts are numbered top to bottom and vPairs are numbered bottom to top
    if score.parts[partNum1].species == 'second':
        speciesPart = 1
    elif score.parts[partNum2].species == 'second':
        speciesPart = 0
    else:#neither part is second species
        return
    firstOctave = None
    for vPair in vPairList:
        if firstOctave:
            if (interval.Interval(vPair[0], vPair[1]).name == 'P8'
                    and vPair[speciesPart].beat > 1.0
                    and vPair[speciesPart].measureNumber-1 == firstOctave[0]):
                if interval.Interval(firstOctave[1][speciesPart], vPair[speciesPart]).isDiatonicStep:
                    if vPair[speciesPart].consecutions.leftDirection == firstOctave[1][speciesPart].consecutions.leftDirection:
                        error = 'Offbeat octaves in bars ' + str(firstOctave[0]) + ' and ' + str(vPair[speciesPart].measureNumber)
                        vlErrors.append(error)
                elif interval.Interval(firstOctave[1][speciesPart], vPair[speciesPart]).generic.isSkip:
                    if (vPair[speciesPart].consecutions.leftDirection != firstOctave[1][speciesPart].consecutions.leftDirection
                            or firstOctave[1][speciesPart].consecutions.rightInterval.isDiatonicStep):
                        continue
                    else:
                        error = 'Offbeat octaves in bars ' + str(firstOctave[0]) + ' and ' + str(vPair[speciesPart].measureNumber)
                        vlErrors.append(error)
        if vPair != None:
            if (interval.Interval(vPair[0], vPair[1]).name == 'P8'
                    and vPair[speciesPart].beat == 1.5):
                firstOctave = (vPair[speciesPart].measureNumber, vPair)

def checkFourthLeapsInBass(score, analyzer):
    '''docstring'''
    analyzer.identifyFourthLeapsInBass(score)
    bassFourthsList = analyzer.store[score.id]['ResultDict']['fourthLeapsBass']
    for bassFourth in bassFourthsList:
        bn1 = bassFourth.nnls.objectList[0]
        bn2 = bassFourth.nnls.objectList[1]
        bnPartNum = len(score.parts)-1
        bn1Meas = bn1.measureNumber
        bn2Meas = bn2.measureNumber
        bn1Start = bn1.offset
        bn2Start = bn2.offset
        bn1End = bn1Start + bn1.quarterLength
        bn2End = bn2Start + bn2.quarterLength
        # implication is true until proven otherwise
        impliedSixFour = True
                
        # leaps of a fourth within a measure 
        if bn1Meas == bn2Meas: 
            fourthBass = interval.getAbsoluteLowerNote(bn1, bn2)
            for n in score.parts[bnPartNum].measure(bn1Meas).notes:
                rules1 = [n != bn1,
                            n != bn2,
                            n == interval.getAbsoluteLowerNote(n, fourthBass),
                            interval.Interval(n, fourthBass).semitones < interval.Interval('P8').semitones,
                            isTriadicConsonance(n, bn1),
                            isTriadicConsonance(n, bn2)]
                if all(rules1):
                    impliedSixFour = False
                    break

        # leaps of a fourth across the barline
        elif bn1Meas == bn2Meas-1:
            # check upper parts for note that denies the implication
            for part in score.parts[0:bnPartNum]:
                # get the two bars in the context of the bass fourth
                bars = part.getElementsByOffset(offsetStart=bn1Start,
                                offsetEnd=bn2End,
                                includeEndBoundary=False,
                                mustFinishInSpan=False,
                                mustBeginInSpan=False,
                                includeElementsThatEndAtStart=False,
                                classList=None)
                # make note list for each bar of the part, simultaneous with notes of the fourth
                barseg1 = []
                barseg2 = []
                for bar in bars: 
                    # bar notes 1
                    barns1 = bar.getElementsByOffset(offsetStart=bn1Start-bar.offset,
                                    offsetEnd=bn1End-bar.offset,
                                    includeEndBoundary=False,
                                    mustFinishInSpan=False,
                                    mustBeginInSpan=False,
                                    includeElementsThatEndAtStart=False,
                                    classList='Note')
                    for n in barns1:
                        barseg1.append(n)
                    # bar notes 2
                    barns2 = bar.getElementsByOffset(offsetStart=bn2Start-bar.offset,
                                    offsetEnd=bn2End,
                                    includeEndBoundary=False,
                                    mustFinishInSpan=False,
                                    mustBeginInSpan=False,
                                    includeElementsThatEndAtStart=False,
                                    classList='Note')
                    for n in barns2:
                        barseg2.append(n)

                for n in barseg1:
                    # rules for all species
                    # locally consonant, step-class contiguity
                    rules1 = [isConsonanceAboveBass(bn1, n),
                            interval.Interval(bn2, n).simpleName in ['m2', 'M2', 'm7', 'M7']]

                    # rules for first species
                    if len(barseg1) == 1:
                        if all(rules1):
                            impliedSixFour = False
                            break

                    # rules for second species
                    elif len(barseg1) == 2 and not barseg1[0].tie:
                        # first in bar, leapt to, or last in bar (hence contiguous with bn2)
                        rules2 = [n.offset == 0.0,
                                n.consecutions.leftType == 'skip',
                                n.offset+n.quarterLength == score.measure(bn1Meas).quarterLength]
                        if all(rules1) and any(rules2):
                            impliedSixFour = False
                            break

                    # rules for third species
                    elif len(barseg1) > 2:
                        # first in bar or last in bar (hence contiguous with bn2)
                        rules3a = [n.offset == 0.0,
                                n.offset+n.quarterLength == score.measure(bn1Meas).quarterLength]
                        # not first or last in bar and no step follows
                        stepfollows = [x for x in barseg1 if x.offset > n.offset and isConsonanceAboveBass(bn1, x) and isDiatonicStep(x, n)]
                        rules3b = [n.offset > 0.0,
                                n.offset+n.quarterLength < score.measure(bn1Meas).quarterLength,
                                stepfollows == []]

                        if all(rules1) and (any(rules3a) or all(rules3b)):
                            impliedSixFour = False
                            break

                    # rules for fourth species
                    elif len(barseg1) == 2 and barseg1[0].tie:
                        rules4 = [n.tie.type == 'start']
                        if all(rules1) and all(rules4):
                            impliedSixFour = False
                            break

                for n in barseg2:
                    # locally consonant, step-class contiguity
                    rules1 = [isConsonanceAboveBass(bn2, n),
                            interval.Interval(bn1, n).simpleName in ['m2', 'M2', 'm7', 'M7']]

                    # rules for first species
                    if len(barseg2) == 1:
                        if all(rules1):
                            impliedSixFour = False
                            break

                    # rules for second species
                    elif len(barseg2) == 2 and not barseg2[0].tie:
                        rules2 = [n.offset == 0.0,
                                n.consecutions.leftType == 'skip']
                        if all(rules1) and any(rules2):
                            impliedSixFour = False
                            break

                    # rules for third species
                    elif len(barseg2) > 2:
                        # first in bar or not preceded by cons a step away
                        stepprecedes = [x for x in barseg2 if x.offset < n.offset and isConsonanceAboveBass(bn1, x) and isDiatonicStep(x, n)]
                        rules3 = [n.offset == 0.0, 
                                stepprecedes == []]
                        if all(rules1) and any(rules3):
                            impliedSixFour = False
                            break

                    # rules for fourth species
                    elif len(barseg2) == 2 and barseg2[0].tie:
                        # TODO verify that no additional rule is needed
                        rules4 = []#[n.tie.type == 'start']
                        if all(rules1) and all(rules4):
                            impliedSixFour = False
                            break
            # check third species bass part for note that denies the implication
            if score.parts[bnPartNum].species == 'third':
                bn1Measure = bn1.measureNumber
                # get the notes in the bar of the first bass note
                bassnotes = score.parts[bnPartNum].flat.notes
                barns1 = [n for n in bassnotes if n.measureNumber == bn1Measure]
                
                # TODO finish this test
                for n in barns1:
                    rules3a = [isDiatonicStep(n, bn2)]
                    rules3b = [n.offset == 0.0,
                            n == barns1[-2]]
                    if all(rules3a) and any(rules3b):
                        impliedSixFour = False
                        break    

        if impliedSixFour == True and bn1Meas == bn2Meas:
            error = 'Prohibited leap of a fourth in bar ' + str(bn1Meas)
            vlErrors.append(error)
        elif impliedSixFour == True and bn1Meas != bn2Meas:
            error = 'Prohibited leap of a fourth in bars ' + str(bn1Meas) +  ' to ' + str(bn2Meas)
            vlErrors.append(error)
#        return impliedSixFour

# -----------------------------------------------------------------------------
# UTILITY SCRIPTS
# -----------------------------------------------------------------------------

# utility function for finding pairs of parts    
def getAllPartNumPairs(score):
    '''docstring'''
    # from theory analyzer
    partNumPairs = []
    numParts = len(score.parts)
    for partNum1 in range(numParts - 1):
        for partNum2 in range(partNum1 + 1, numParts):
            partNumPairs.append((partNum1, partNum2))
    return partNumPairs    
    
def makeVLQFromVPair(vPairList):
    '''docstring'''
#    a, b = itertools.tee(vPairList)
#    next(b, None)
#    zipped = zip(a, b)
    quartetList = []
#    for quartet in list(zipped):
    for quartet in pairwise(vPairList):
        quartetList.append((quartet[0][1],quartet[1][1],quartet[0][0],quartet[1][0]))
    vlqList = []
    for quartet in quartetList:
        vlqList.append(voiceLeading.VoiceLeadingQuartet(quartet[0], quartet[1], quartet[2], quartet[3]))
    return vlqList

def makeVLQsFromVertPair(vertPair, partNumPairs):
    '''docstring'''
    # given a pair of verticalities and a list of component part pairing,
    # construct all the VLQs among notes
    vlqList = []
    for numPair in partNumPairs:
        upperPart = numPair[0]
        lowerPart = numPair[1]
        v1n1 = vertPair[0].objects[upperPart]
        v1n2 = vertPair[1].objects[upperPart]
        v2n1 = vertPair[0].objects[lowerPart]
        v2n2 = vertPair[1].objects[lowerPart]
        # do not make a VLQ if one note is a rest
        if v1n1.isRest or v1n2.isRest or v2n1.isRest or v2n2.isRest:
            continue
        else:
            vlqList.append((numPair, voiceLeading.VoiceLeadingQuartet(v1n1, v1n2, v2n1, v2n2)))
    return vlqList        

# -----------------------------------------------------------------------------

if __name__ == '__main__':
    # self_test code
    pass

    source='TestScoresXML/FirstSpecies10.musicxml'
    cxt = context.makeGlobalContext(source)
    checkCounterpoint(cxt, report=True)
# -----------------------------------------------------------------------------
# eof