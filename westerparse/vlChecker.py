# -----------------------------------------------------------------------------
# Name:         vlChecker.py
# Purpose:      Framework for analyzing voice leading in species counterpoint
#
# Author:       Robert Snarrenberg
# Copyright:    (c) 2022 by Robert Snarrenberg
# License:      BSD, see license.txt
# -----------------------------------------------------------------------------
"""
Voice Leading Checker
=====================

The Voice Leading Checker module takes a score with two or more parts (lines)
and examines the local voice leading for conformity with Westergaard's rules
of species counterpoint.

The module uses music21's theoryAnalyzer module to parse the score
into small bits for analysis, bits such as pairs of simultaneous notes,
complete verticalities, and voice-leading quartets.
The results are stored in the analyzer's analysisData
dictionary. The voice-leading checker then analyzes these bits of data.

A voice pair (vPair) is a pair of simultaneous notes in two parts:

   * v1: n
   * v0: n

A voice-leading quartet (VLQ) consists of pairs of simultaneous
notes in two parts:

   * v1: n1, n2
   * v2: n1, n2

[Note: Part-ordering in music21's definition VLQ is not fixed (i.e.,
voice 1 is not always the top or bottom voice).  Tony Li wrote a new
method for getting VLQs that fixes this problem:
v1 is always the top voice.]

The numbering of parts in vPairs and VLQs is, unfortunately,
not consistent.  This reflects a conceptual
conflict between music21's part-numbering scheme, which
numbers the parts of a score from
top to bottom (part 0 = the topmost part), and the
conceptual scheme of voice-leading
analysis in classical theory, which reckons intervals from the bottom
to the top (part 0 = the bass part).

Westergaard's rules for combining lines cover four areas:

   * intervals between consecutive notes
   * intervals between simultaneous notes: dissonance
   * intervals between simultaneous notes: sonority
   * motion between pairs of simultaneously sounding notes

While most of the rules for intervals between consecutive notes are
handled by the rules of linear syntax, there is one such rule
that has a contrapuntal component: the rule
that prohibits the implication of a six-four chord by controlling the
situations in which the bass leaps a perfect fourth. (Another rule in
this implementation (but not found in Westeraard) also has a contrapuntal
aspect: the global rule that ensures a step connection from the
penultimate measure to the final pitch of a primary line.)

The rules controlling leaps of a fourth in the bass, dissonance,
and motion are absolutes, hence any infractions automatically
yield an error report. The rules for controlling
sonority, on the other hand, are rules of advice.
Nonconformity with the sonority rules
is only reported on demand. [This option is not yet available.]

The rules for forbidden forms of motion vary with the rhythmic situation:

   * on the beat to on the beat
   * on the beat to next on the beat
   * on the beat to immediately following off the beat
   * off the beat to immediately following on the beat
   * off the beat to next but not immediately following on the beat
   * off the beat to immediately following off the beat
   * off the beat to off the beat in the next bar (fourth species)

Many of the rules apply across species.  For example, the rules of
first species, originally formulated for consecutive beats
(on the beat to on the beat) apply in all species
whenever both lines move to new notes on the beat.
This happens regularly in first, second, and third species,
and at the end of fourth species, where the syncopations are
broken.
A single function (:py:func:`forbiddenMotionsOntoBeatWithoutSyncope`)
checks these situations.  Each species also has a set of rules
that are peculiar to it, so there are
separate functions for each of these.

Control of dissonance is checked by one of two functions:
:py:func:'checkControlOfDissonance' for first, second, and third species,
or :py:func:'fourthSpeciesControlOfDissonance'.

[Etc.]

"""

# NB: vlq parts and score Parts are numbered top to bottom.
# NB: vPair parts are numbered bottom to top.

# import itertools
import unittest
import logging

from music21 import *

# from westerparse import csd
# from westerparse import context
from westerparse import theoryAnalyzerWP
# from westerparse import theoryResultWP
from westerparse.utilities import pairwise

# -----------------------------------------------------------------------------
# LOGGER
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# logging handlers
f_handler = logging.FileHandler('vl.txt', mode='w')
f_handler.setLevel(logging.DEBUG)
# logging formatters
f_formatter = logging.Formatter('%(message)s')
f_handler.setFormatter(f_formatter)
# add handlers to logger
logger.addHandler(f_handler)


# -----------------------------------------------------------------------------
# MODULE VARIABLES
# -----------------------------------------------------------------------------

# Variables set by instructor.
allowSecondSpeciesBreak = True
allowThirdSpeciesInsertions = True
sonorityCheck = False

# Create list to collect errors, for reporting to user.
vlErrors = []

# -----------------------------------------------------------------------------
# MAIN SCRIPT
# -----------------------------------------------------------------------------


def checkCounterpoint(context, report=True, sonorityCheck=False, **kwargs):
    """
    This is the main script.

    It creates the analysis database and then
    checks every pair of parts in the score for conformity with the
    rules that control dissonance and the rules that prohibit certain
    forms of motion.  A separate function checks for the rules that
    control leaps of a fourth in the bass.
    """

    twoPartContexts = context.makeTwoPartContexts()
    for duet in twoPartContexts:
        checkDuet(context, duet)

def checkDuet(context, duet):
    """
    """
    cond1 = duet.parts[0].species == 'first'
    cond2 = duet.parts[1].species == 'first'
    if cond1 and cond2:
        print('checking first species')
        print(duet.includesBass)
        checkFirstSpecies(context, duet)
    if ((cond1 and duet.parts[1].species == 'second')
            or (duet.parts[0].species == 'second' and cond2)):
        print('checking second species')
        print(duet.includesBass)
        # checkSecondSpecies(score, analyzer, numPair)
    if ((cond1 and duet.parts[1].species == 'third')
            or (duet.parts[0].species == 'third' and cond2)):
        print('checking third species')
        # checkThirdSpecies(score, analyzer, numPair)
    if ((cond1 and duet.parts[0].species == 'fourth')
            or (duet.parts[0].species == 'fourth' and cond2)):
        print('checking fourth species')
        # checkFourthSpecies(score, analyzer, numPair)
    # TODO Add pairs for combined species: Westergaard chapter 6:
    # second and second
    # third and third
    # fourth and fourth
    # second and third
    # second and fourth
    # third and fourth


def getVerticalitiesFromDuet(duet):
    tree = duet.asTimespans(classList=(note.Note,))
    vertList = tree.iterateVerticalities(reverse=False)
    return vertList

def getVoiceLeadingQuartetsFromDuet(duet):
    vlqs = []
    for v in getVerticalitiesFromDuet(duet):
        # use verticality method from music21
        vlqList = v.getAllVoiceLeadingQuartets()
        for vlq in vlqList:
            vlqs.append(vlq)
    return vlqs


def checkFirstSpecies(context, duet):
    """Check a pair of parts, where one line is in first species
    and the other is also in first species.
    Evaluate control of dissonance and forbidden forms of motion.
    Also check the final step for conformity with the global
    rule for upper lines.
    """
    VLQs = getVoiceLeadingQuartetsFromDuet(duet)
    firstSpeciesForbiddenMotions(context, VLQs, includesBass=duet.includesBass)
    #firstSpeciesForbiddenMotions(duet)
    # checkControlOfDissonance(score, analyzer, numPair)

def firstSpeciesForbiddenMotions(context, VLQs, includesBass=False):
    """Check the forbidden forms of motion for a pair
    of lines in first species.
    Essentially: :py:func:`forbiddenMotionsOntoBeatWithoutSyncope`.
    """
    for vlq in VLQs:
        if not includesBass:
            mn = vlq.v1n2.measureNumber
            vlqBassNote = context.parts[-1].measure(mn).getElementsByClass('Note')[0]
            print('bass', vlqBassNote)
        if vlq.similarMotion:
            print(f'similar motion going into {vlq.v2n2.measureNumber}')
        if isSimilarFifth(vlq):
            error = ('Forbidden similar motion to fifth going into bar '
                     + str(vlq.v2n2.measureNumber) + '.')
            print(error)
            vlErrors.append(error)
        pass
        # forbiddenMotionsOntoBeatWithoutSyncope(score, vlq, partNum1, partNum2)
    # checkFirstSpeciesNonconsecutiveParallels(score, analyzer,
    #                                                partNum1,
    #                                                partNum2)


def dummyFunction():
    # CURRENT VERSION: TEST EACH PAIR OF LINES
    # Information access to other activity in other lines is limited.
    # Works best for two-part simple species.
    # Each pairing has its own subroutines:
    #     1:1; 1:2; 1:3 and 1:4; and syncopated

    logger.debug(f'Checking voice leading in {context.filename}.')

    checkPartPairs(context.score, analytics)
    checkFourthLeapsInBass(context.score, analytics)

    # Report voice-leading errors, if asked.
    if report:
        if vlErrors == []:
            result = ('No voice-leading errors found.\n')
        else:
            result = ('VOICE LEADING REPORT \nThe following '
                      'voice-leading errors were found:')
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
    """Input two notes with pitch, a bass note and an upper note, and
    determine whether the pair forms a vertical consonance.
    The test determines whether the simple interval
    equivalent of the actual interval is in the list:
    'P1', 'm3', 'M3', 'P5', 'm6', 'M6'.
    Equivalent to music21.Interval.isConsonant().
    """
    vert_int = interval.Interval(b, u)
    if (interval.getAbsoluteLowerNote(b, u) == b and
       vert_int.simpleName in {'P1', 'm3', 'M3', 'P5', 'm6', 'M6'}):
        return True
    else:
        return False


def isThirdOrSixthAboveBass(b, u):
    """Input two notes with pitch, a bass note and an upper note,
    and determine whether the pair forms a vertical third or sixth.
    The test determines whether the simple interval
    equivalent of the actual interval is in the list:
    'm3', 'M3', 'm6', 'M6'.
    """
    vert_int = interval.Interval(b, u)
    if (interval.getAbsoluteLowerNote(b, u) == b and
       vert_int.simpleName in {'m3', 'M3', 'm6', 'M6'}):
        return True
    else:
        return False


def isConsonanceBetweenUpper(u1, u2):
    """Input two notes with pitch, two upper-line notes, and determine
    whether the pair forms a vertical consonance.  The test determines
    whether the simple interval equivalent of the actual interval is
    in the list: 'P1', 'm3', 'M3', 'P4', 'P5', 'm6', 'M6'.
    """
    vert_int = interval.Interval(u1, u2)
    if vert_int.simpleName in {'P1', 'm3', 'M3', 'P4', 'P5', 'm6', 'M6'}:
        return True
    else:
        return False


def isPermittedDissonanceBetweenUpper(u1, u2):
    """Input two notes with pitch, two upper-line notes, and determine
    whether the pair forms a permitted vertical dissonance.  The test
    determines whether the simple interval
    equivalent of the actual interval is in the list: 'P4', 'A4', 'd5'.
    Each note requires additional test with bass:
    :py:func:`isThirdOrSixthAboveBass`.
    """
    vert_int = interval.Interval(u1, u2)
    if vert_int.simpleName in {'P4', 'A4', 'd5'}:
        return True
    else:
        return False


def isTriadicConsonance(n1, n2):
    """Input two notes, from any context, and determine whether
    the pair forms a triadic interval in a consonant triad (major or minor).
    The test determines whether the simple interval
    equivalent of the actual interval is in the list:
    'P1', 'm3', 'M3', 'P4', 'P5', 'm6', 'M6'.
    """
    int = interval.Interval(n1, n2)
    if int.simpleName in {'P1', 'm3', 'M3', 'P4', 'P5', 'm6', 'M6'}:
        return True
    else:
        return False


def isTriadicInterval(n1, n2):
    """Input two notes, from any context, and determine whether
    the pair forms a triadic interval in any type of triad
    (major, minor, diminished, augmented).
    The test determines whether the simple interval
    equivalent of the actual interval is in the list:
    'P1', 'm3', 'M3', 'P4', 'A4', 'd5', 'P5', 'm6', 'M6'.
    """
    ivl = interval.Interval(n1, n2)
    if ivl.simpleName in {'P1', 'm3', 'M3', 'P4',
                          'A4', 'd5', 'P5', 'm6', 'M6'}:
        return True
    else:
        return False


def isPerfectVerticalConsonance(n1, n2):
    """Input two simultaneous notes with pitch and determine whether
    the pair forms a perfect vertical consonance.  The test determines
    whether the simple interval equivalent of the actual interval
    is in the list: 'P1', 'P5', 'P8'.
    """
    ivl = interval.Interval(n1, n2)
    if ivl.simpleName in {'P1', 'P5', 'P8'}:
        return True
    else:
        return False


def isImperfectVerticalConsonance(n1, n2):
    """Input two simultaneous notes with pitch and determine whether
    the pair forms an imperfect vertical consonance.
    The test determines whether
    the simple interval equivalent of the actual
    interval is in the list:
    'm3', 'M3', 'm6', 'M6'.
    """
    ivl = interval.Interval(n1, n2)
    if ivl.simpleName in {'m3', 'M3', 'm6', 'M6'}:
        return True
    else:
        return False


def isVerticalDissonance(n1, n2):
    """Input two simultaneous notes with pitch and determine whether
    the pair forms a vertical dissonance.  The test determines whether
    the simple interval equivalent of the actual interval
    is not in the list:
    'P1', 'P5', 'P8', 'm3', 'M3', 'm6', 'M6'.
    """
    ivl = interval.Interval(n1, n2)
    if ivl.simpleName not in {'P1', 'P5', 'P8',
                              'm3', 'M3', 'm6', 'M6'}:
        return True
    else:
        return False


def isDiatonicStep(n1, n2):
    """Input two notes with pitch and determine whether
    the pair forms a diatonic step.  The test determines whether
    the actual interval is in the list:
    'm2', 'M2'.
    """
    lin_ivl = interval.Interval(n1, n2)
    if lin_ivl.name in {'m2', 'M2'}:
        return True
    else:
        return False


def isUnison(n1, n2):
    """Input two notes with pitch and determine whether
    the pair forms a unison.  The test determines whether
    the actual interval is in the list:
    'P1'.
    """
    lin_ivl = interval.Interval(n1, n2)
    if lin_ivl.name in {'P1'}:
        return True
    else:
        return False


def isOctave(n1, n2):
    """Input two notes with pitch and determine whether
    the pair forms an octave.  The test determines whether
    the actual interval is in the list:
    'P8', 'P15', 'P22'.
    """
    # TODO perhaps change this to lin_ivl.semiSimpleName == 'P8'
    lin_ivl = interval.Interval(n1, n2)
    if lin_ivl.name in {'P8', 'P15', 'P22'}:
        return True
    else:
        return False

# Methods for voice-leading quartets


def isSimilarUnison(vlq):
    """Input a VLQ and determine whether
    there is similar motion to a unison.
    """
    rules = [vlq.similarMotion(),
             vlq.vIntervals[1] != vlq.vIntervals[0],
             vlq.vIntervals[1].name == 'P1']
    if all(rules):
        return True
    else:
        return False


def isSimilarFromUnison(vlq):
    """Input a VLQ and determine whether
    there is similar motion from a unison.
    """
    rules = [vlq.similarMotion(),
             vlq.vIntervals[1] != vlq.vIntervals[0],
             vlq.vIntervals[0].name == 'P1']
    if all(rules):
        return True
    else:
        return False


def isSimilarFifth(vlq):
    """Input a VLQ and determine whether there is similar motion to
    a perfect fifth (simple or compound).
    """
    rules = [vlq.similarMotion(),
             vlq.vIntervals[1] != vlq.vIntervals[0],
             vlq.vIntervals[1].simpleName == 'P5']
    if all(rules):
        return True
    else:
        return False


def isSimilarOctave(vlq):
    """Input a VLQ and determine whether there is similar motion to
    an octave (simple or compound).
    """
    rules = [vlq.similarMotion(),
             vlq.vIntervals[1] != vlq.vIntervals[0],
             vlq.vIntervals[1].name in ['P8', 'P15', 'P22']]
    if all(rules):
        return True
    else:
        return False


def isParallelUnison(vlq):
    """Input a VLQ and determine whether there is parallel motion
    from one unison to another.
    """
    rules = [vlq.parallelMotion(),
             vlq.vIntervals[1].name in ['P1']]
    if all(rules):
        return True
    else:
        return False


def isParallelFifth(vlq):
    """Input a VLQ and determine whether there is parallel motion
    to a perfect fifth (the first fifth need not be perfect).
    """
    rules = [vlq.parallelMotion(),
             vlq.vIntervals[1].simpleName == 'P5']
    if all(rules):
        return True
    else:
        return False


def isParallelOctave(vlq):
    """Input a VLQ and determine whether there is parallel motion
    from one octave (simple or compound) to another.
    """
    rules = [vlq.parallelMotion(),
             vlq.vIntervals[1].name in ['P8', 'P15', 'P22']]
    if all(rules):
        return True
    else:
        return False


def isVoiceOverlap(vlq):
    """Input a VLQ and determine whether the voices overlap:
    either v1n2 < v2n1 or v2n2 > v1n1.
    """
    rules = [vlq.v1n2.pitch < vlq.v2n1.pitch,
             vlq.v2n2.pitch > vlq.v1n1.pitch]
    if any(rules):
        return True
    else:
        return False


def isVoiceCrossing(vlq):
    """Input a VLQ and determine whether
    the voices cross: v1n1 < v2n1 or v1n2 < v2n2.
    """
    rules = [vlq.v1n1.pitch < vlq.v2n1.pitch,
             vlq.v1n2.pitch < vlq.v2n2.pitch]
    if any(rules):
        return True
    else:
        return False


def isCrossRelation(vlq):
    """Input a VLQ and determine whether the there is a cross relation.
    The test determines whether the simple interval of either contiguous
    interval is in the list: 'd1', 'A1'.
    """
    rules = [interval.Interval(vlq.v1n1, vlq.v2n2).simpleName in ['d1', 'A1'],
             interval.Interval(vlq.v2n1, vlq.v1n2).simpleName in ['d1', 'A1']]
    if any(rules):
        return True
    else:
        return False


def isDisplaced(vlq):
    """Input a VLQ and determine whether either of the pitches in the first
     verticality is displaced by a pitch in the second verticality.
     The test determines whether the simple interval of any contiguous
     or consecutive
     interval is not in the list: 'P1', 'm3', 'M3', 'P4', 'P5', 'm6', 'M6'.
     """
    intervals = [interval.Interval(vlq.v1n1, vlq.v1n2).simpleName,
                 interval.Interval(vlq.v1n1, vlq.v2n1).simpleName,
                 interval.Interval(vlq.v2n1, vlq.v2n2).simpleName,
                 interval.Interval(vlq.v2n1, vlq.v1n2).simpleName]
    displacements = [i for i in intervals if i
                     not in ['P1', 'm3', 'M3', 'P4', 'P5', 'm6', 'M6', 'P8']]
    if displacements == []:
        return False
    else:
        return True


# Methods for notes


def isOnbeat(note):
    """Tests whether a note is initiated on the downbeat."""
    rules = [note.beat == 1.0]
    if any(rules):
        return True
    else:
        return False


def isSyncopated(score, note):
    """Test whether a note is syncopated. [Not yet functional]"""
    # TODO This is a first attempt at defining the syncopation property.
    # Given a time signature and music21's default metric system for it.
    # This works for duple simple meter, not sure about compound or triple.

    # Get the time signature.
    ts = score.recurse().getElementsByClass(meter.TimeSignature)[0]

    # Determine the length of the note.
    # Tied-over notes have no independent duration.
    if note.tie is None:
        note.len = note.quarterLength
    elif note.tie.type == 'start':
        note.len = note.quarterLength + note.next().quarterLength
    elif note.tie.type == 'stop':
        note.len = 0
    # Find the maximum metrically stable duration of a note initiated at t.
    maxlen = (note.beatStrength
              * note.beatDuration.quarterLength
              * ts.beatCount)
    # Determine whether the note is syncopated.
    if note.len > maxlen:
        return True
    elif note.len == 0:
        return None
    else:
        return False

# -----------------------------------------------------------------------------
# SCRIPTS FOR EVALUATING VOICE LEADING, BY SPECIES
# -----------------------------------------------------------------------------


# def checkPartPairs(score, analyzer):
#     """Find all of the pairwise combinations of parts and check the
#     voice-leading of each pair, depending upon which simple species
#     the pair represents (e.g., first, second, third, fourth).
#     The function is currently not able to evaluate combined species.
#     """
#     partNumPairs = getAllPartNumPairs(score)
#     for numPair in partNumPairs:
#         cond1 = score.parts[numPair[0]].species == 'first'
#         cond2 = score.parts[numPair[1]].species == 'first'
#         if cond1 and cond2:
#             checkFirstSpecies(score, analyzer, numPair)
#         if ((cond1 and score.parts[numPair[1]].species == 'second')
#                 or (score.parts[numPair[0]].species == 'second' and cond2)):
#             checkSecondSpecies(score, analyzer, numPair)
#         if ((cond1 and score.parts[numPair[1]].species == 'third')
#                 or (score.parts[numPair[0]].species == 'third' and cond2)):
#             checkThirdSpecies(score, analyzer, numPair)
#         if ((cond1 and score.parts[numPair[1]].species == 'fourth')
#                 or (score.parts[numPair[0]].species == 'fourth' and cond2)):
#             checkFourthSpecies(score, analyzer, numPair)
#     # TODO Add pairs for combined species: Westergaard chapter 6:
#     # second and second
#     # third and third
#     # fourth and fourth
#     # second and third
#     # second and fourth
#     # third and fourth


# def checkFirstSpecies(score, analyzer, numPair):
#     """Check a pair of parts, where one line is in first species
#     and the other is also in first species.
#     Evaluate control of dissonance and forbidden forms of motion.
#     Also check the final step for conformity with the global
#     rule for upper lines.
#     """
#     analytics = theoryAnalyzerWP.Analyzer()
#     analytics.addAnalysisData(score)
#     firstSpeciesForbiddenMotions(score, analytics,
#                                  partNum1=numPair[0],
#                                  partNum2=numPair[1])
#     checkControlOfDissonance(score, analyzer, numPair)



def checkSecondSpecies(score, analyzer, numPair):
    """Check a pair of parts, where one line is in first species
    and the other is in second species.
    Check the intervals between consecutive notes (no local
    repetitions in the second species line).
    Evaluate control of dissonance and forbidden forms of motion,
    including the rules for nonconsecutive unisons and octaves.
    Also check the final step for conformity with the global rule
    for upper lines.
    """
    analytics = theoryAnalyzerWP.Analyzer()
    analytics.addAnalysisData(score)
    checkConsecutions(score)
    secondSpeciesForbiddenMotions(score, analytics,
                                  partNum1=numPair[0], partNum2=numPair[1])
    checkControlOfDissonance(score, analyzer, numPair)
    checkSecondSpeciesNonconsecutiveUnisons(score, analytics,
                                            partNum1=numPair[0],
                                            partNum2=numPair[1])
    checkSecondSpeciesNonconsecutiveOctaves(score, analytics,
                                            partNum1=numPair[0],
                                            partNum2=numPair[1])


def checkThirdSpecies(score, analyzer, numPair):
    """Check a pair of parts, where one line is in first species
    and the other is in third species.
    Check the intervals between consecutive notes (no local repetitions
    in the third species line).
    Evaluate control of dissonance and forbidden forms of motion.
    Also check the final step for conformity with the global rule
    for upper lines.
    """
    analytics = theoryAnalyzerWP.Analyzer()
    analytics.addAnalysisData(score)
    checkConsecutions(score)
    partNumPairs = getAllPartNumPairs(score)
    thirdSpeciesForbiddenMotions(score, analytics,
                                 partNum1=numPair[0],
                                 partNum2=numPair[1])
    checkControlOfDissonance(score, analyzer, numPair)


def checkFourthSpecies(score, analyzer, numPair):
    """Check a pair of parts, where one line is in first species
    and the other is in fourth species.
    Check the intervals between consecutive notes (no local repetitions
    in the fourth species line).
    Evaluate control of dissonance and forbidden forms of motion.
    Also check the final step for conformity with the global rule
    for upper lines.
    """
    analytics = theoryAnalyzerWP.Analyzer()
    analytics.addAnalysisData(score)
    checkConsecutions(score)
    fourthSpeciesForbiddenMotions(score, analytics,
                                  partNum1=numPair[0],
                                  partNum2=numPair[1])
    fourthSpeciesControlOfDissonance(score, analytics,
                                     partNum1=numPair[0],
                                     partNum2=numPair[1])


def checkConsecutions(score):
    """Check the intervals between consecutive notes. If the line is
    in second or third species, confirm that there are no direct
    repetitions. If the line is in fourth species,
    confirm that the pitches of tied-over notes match and
    that there are no direct repetitions.
    """
    for part in score.parts:
        if part.species in ['second', 'third']:
            for n in part.recurse().notes:
                if n.consecutions.leftType == 'same':
                    error = ('Direct repetition in bar '
                             + str(n.measureNumber) + '.')
                    vlErrors.append(error)
        if part.species == 'fourth':
            for n in part.recurse().notes:
                if n.tie:
                    if (n.tie.type == 'start'
                       and n.consecutions.rightType != 'same'):
                        error = ('Pitch not tied across the barline '
                                 'into bar ' + str(n.measureNumber+1) + '.')
                        vlErrors.append(error)
                    elif (n.tie.type == 'stop'
                          and n.consecutions.leftType != 'same'):
                        error = ('Pitch not tied across the barline '
                                 'into bar ' + str(n.measureNumber) + '.')
                        vlErrors.append(error)
                # TODO allow breaking into second species
                elif not n.tie:
                    if n.consecutions.rightType == 'same':
                        error = ('Direct repetition around bar '
                                 + str(n.measureNumber) + '.')
                        vlErrors.append(error)


def checkControlOfDissonance(score, analyzer, numPair):
    """Check the score for conformity with the rules that control
    dissonance in first, second, or third species. Requires access not only
    to notes in a given pair of lines but also the bass line, if different.

    On the beat: notes must be consonant.

    Off the beat: notes may be dissonant but only if approached
    and left by step.

    Off the beat: consecutive dissonances must be approached
    and left by step in the same direction.
    """
    # collect sequence of intervals for logging and data analysis
    verts = analyzer.getVerticalities(score)
    bassPartNum = len(score.parts)-1

    # for logging and analysis
    part_pair_ivls = []

    for vert in verts:
        upperNote = vert.objects[numPair[0]]
        lowerNote = vert.objects[numPair[1]]
        laterNote = None
        if upperNote.beat > lowerNote.beat:
            laterNote = upperNote
        elif upperNote.beat < lowerNote.beat:
            laterNote = lowerNote

        # Do not evaluate a vertical pair if one note is a rest.
        # TODO This is okay for now, but need to check
        #   the rules for all gambits.
        #   And what if there's a rest during a line?
        if upperNote.isRest or lowerNote.isRest:
            continue

        # get interval for logging and data analysis
        part_pair_ivls.append(interval.Interval(lowerNote, upperNote).name)

        # Both notes start at the same time, neither is tied over:
        rules1 = [upperNote.beat == lowerNote.beat,
                  (upperNote.tie is None or upperNote.tie.type == 'start'),
                  (lowerNote.tie is None or lowerNote.tie.type == 'start')]
        # The pair constitutes a permissible consonance above the bass:
        rules2a = [bassPartNum in numPair,
                   isConsonanceAboveBass(lowerNote, upperNote)]
        # The pair constitutes a permissible consonance between upper parts:
        rules2b = [bassPartNum not in numPair,
                   isConsonanceBetweenUpper(lowerNote, upperNote)]
        # The pair is a permissible dissonance between upper parts:
        # TODO This won't work if the bass is a rest and not a note.
        rules2c = [bassPartNum not in numPair,
                   isPermittedDissonanceBetweenUpper(lowerNote, upperNote),
                   isThirdOrSixthAboveBass(vert.objects[bassPartNum],
                                           upperNote),
                   isThirdOrSixthAboveBass(vert.objects[bassPartNum],
                                           lowerNote)]

        # Test co-initiated simultaneities.
        if (all(rules1) and not (all(rules2a)
                                 or all(rules2b)
                                 or all(rules2c))):
            error = ('Dissonance between co-initiated notes in bar '
                     + str(upperNote.measureNumber) + ': '
                     + str(interval.Interval(lowerNote, upperNote).name)
                     + '.')
            vlErrors.append(error)

        # One note starts after the other:
        rules3 = [upperNote.beat != lowerNote.beat,
                  not (all(rules2a) or all(rules2b) or all(rules2c))]
        rules4 = [upperNote.beat > lowerNote.beat]
        rules5a = [upperNote.consecutions.leftType == 'step',
                   upperNote.consecutions.rightType == 'step']
        rules5b = [lowerNote.consecutions.leftType == 'step',
                   lowerNote.consecutions.rightType == 'step']

        # Both notes start at the same time, one of them is tied over:

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

        # Both notes start at the same time, both of them are tied over:
        if (all(rules3) and ((all(rules4) and not all(rules5a))
           or (not all(rules4) and not all(rules5b)))):
            error = ('Dissonant interval off the beat that is not '
                     'approached and left by step in bar '
                     + str(lowerNote.measureNumber) + ': '
                     + str(interval.Interval(lowerNote, upperNote).name)
                     + '.')
            vlErrors.append(error)

    # Check whether consecutive dissonances move in one directions.
    vlqList = analyzer.getVLQs(score, numPair[0], numPair[1])
    for vlq in vlqList:
        # if vlq.v1n1 == vlq.v1n2 or vlq.v2n1 == vlq.v2n2:
        #     print('motion is oblique against sustained tone')
        # Either both of the intervals are dissonant above the bass:
        rules1a = [bassPartNum in numPair,
                   isVerticalDissonance(vlq.v1n1, vlq.v2n1),
                   isVerticalDissonance(vlq.v1n2, vlq.v2n2)]
        # Or both of the intervals are prohibited dissonances
        # between upper parts:
        rules1b = [bassPartNum not in numPair,
                   isVerticalDissonance(vlq.v1n1, vlq.v2n1),
                   not isPermittedDissonanceBetweenUpper(vlq.v1n1,
                                                         vlq.v2n1),
                   isVerticalDissonance(vlq.v1n2, vlq.v2n2),
                   not isPermittedDissonanceBetweenUpper(vlq.v1n2,
                                                         vlq.v2n2)]
        # Either the first voice is stationary and
        # the second voice moves in one direction:
        rules2a = [vlq.v1n1 == vlq.v1n2,
                   (vlq.v2n1.consecutions.leftDirection
                    == vlq.v2n2.consecutions.leftDirection),
                   (vlq.v2n1.consecutions.rightDirection
                    == vlq.v2n2.consecutions.rightDirection)]
        # Or the second voice is stationary and
        # the first voice moves in one direction:
        rules2b = [vlq.v2n1 == vlq.v2n2,
                   (vlq.v1n1.consecutions.leftDirection
                    == vlq.v1n2.consecutions.leftDirection),
                   (vlq.v1n1.consecutions.rightDirection
                    == vlq.v1n2.consecutions.rightDirection)]
        # Must be in the same measure:
        rules3 = [vlq.v1n1.measureNumber != vlq.v1n2.measureNumber]
        if ((all(rules1a) or all(rules1b))
           and not (all(rules2a) or all(rules2b)) and not(all(rules3))):
            error = ('Consecutive dissonant intervals in bar '
                     + str(vlq.v1n1.measureNumber)
                     + ' are not approached and left '
                     'in the same direction.')
            vlErrors.append(error)

    # get the interval sequence for logging and data analysis
    part_pair_ivlData = (''.join(['{:>5}'.format(ivl)
                        for ivl in part_pair_ivls])
             )

    # log the intervals
    logger.debug(part_pair_ivlData)

    # TODO Check third species consecutive dissonances rules (above).

    # TODO Fix so that it works with higher species
    # line that start with rests in the bass.

    # TODO Check fourth species control of dissonance.
    # Check resolution of diss relative to onbeat note
    # (which may move if not whole notes) to determine category of susp;
    # this can be extracted from the vlq: e.g., v1n1,v2n1 and v1n2,v2n1.
    # Separately check the consonance of the resolution in the
    # vlq (v1n2, v2n2).
    # Add rules for multiple parts.
    # TODO Add contiguous intervals to vlqs ?? xint1, xint2.

    pass


def fourthSpeciesControlOfDissonance(score, analyzer,
                                     partNum1=None, partNum2=None):
    """Check the score for conformity the rules that
    control dissonance in fourth species.
    """
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)

    if score.parts[partNum1].species == 'fourth':
        speciesPart = 1
    elif score.parts[partNum2].species == 'fourth':
        speciesPart = 0
    for vPair in vPairList:
        if vPair is not None:
            # Evaluate on- and offbeat intervals when one of the parts
            # is the bass.
            # TODO Need to figure out rules for 3 or more parts.
            if score.parts[-1] in [score.parts[partNum1],
                                   score.parts[partNum2]]:
                # Look for onbeat note that is dissonant
                # and improperly treated.
                rules = [
                    vPair[speciesPart].beat == 1.0,
                    not isConsonanceAboveBass(vPair[0], vPair[1]),
                    not vPair[speciesPart].consecutions.leftType == 'same',
                    not vPair[speciesPart].consecutions.rightType == 'step'
                    ]
                if all(rules):
                    error = ('Dissonant interval on the beat that is '
                             'either not prepared or not resolved in bar '
                             + str(vPair[0].measureNumber) + ': '
                             + str(interval.Interval(vPair[1], vPair[0]).name)
                             + '.')
                    vlErrors.append(error)
                # Look for second-species onbeat dissonance.
                rules = [vPair[speciesPart].beat == 1.0,
                         vPair[speciesPart].tie is None,
                         not isConsonanceAboveBass(vPair[0], vPair[1])]
                if all(rules):
                    error = ('Dissonant interval on the beat that is not '
                             'permitted when fourth species is broken in '
                             + str(vPair[0].measureNumber) + ': '
                             + str(interval.Interval(vPair[1], vPair[0]).name)
                             + '.')
                    vlErrors.append(error)
                # Look for offbeat note that is dissonant and tied over.
                rules = [vPair[speciesPart].beat > 1.0,
                         not isConsonanceAboveBass(vPair[0], vPair[1]),
                         vPair[0].tie is not None or vPair[1].tie is not None]
                if all(rules):
                    error = ('Dissonant interval off the beat in bar '
                             + str(vPair[0].measureNumber) + ': '
                             + str(interval.Interval(vPair[1], vPair[0]).name)
                             + '.')
                    vlErrors.append(error)

    vlqList = analyzer.getVLQs(score, partNum1, partNum2)

    # Determine whether breaking of species is permitted,
    # and, if so, whether proper.
    breakcount = 0
    earliestBreak = 4
    latestBreak = score.measures - 4
    for vlq in vlqList:
        # Look for vlq where second note in species line is not tied over.
        if speciesPart == 1:
            speciesNote = vlq.v1n2
        elif speciesPart == 0:
            speciesNote = vlq.v2n2
        if speciesNote.tie is None and speciesNote.beat > 1.0:
            if (not allowSecondSpeciesBreak
               and speciesNote.measureNumber != score.measures-1):
                error = ('Breaking of fourth species is allowed only '
                         'at the end and not in bars '
                         + str(speciesNote.measureNumber) + ' to '
                         + str(speciesNote.measureNumber+1) + '.')
                vlErrors.append(error)
            elif (allowSecondSpeciesBreak
                  and speciesNote.measureNumber != score.measures-1):
                rules = [earliestBreak < speciesNote.measureNumber
                         < latestBreak,
                         breakcount < 1]
                if all(rules):
                    breakcount += 1
                elif breakcount >= 1:
                    error = ('Breaking of fourth species is only '
                             'allowed once during the exercise.')
                    vlErrors.append(error)
                elif earliestBreak > speciesNote.measureNumber:
                    error = ('Breaking of fourth species in bars '
                             + str(speciesNote.measureNumber)
                             + ' to ' + str(speciesNote.measureNumber+1)
                             + ' occurs too early.')
                    vlErrors.append(error)
                elif speciesNote.measureNumber > latestBreak:
                    error = ('Breaking of fourth species in bars '
                             + str(speciesNote.measureNumber)
                             + ' to ' + str(speciesNote.measureNumber+1)
                             + ' occurs too late.')
                    vlErrors.append(error)
                # If the first vInt is dissonant, the speciesNote
                # will be checked later.
                # If the first vInt is consonant, the speciesNote
                # might be dissonant.
                cond1 = [isVerticalDissonance(vlq.v1n2, vlq.v2n2)]
                cond2 = [not isVerticalDissonance(vlq.v1n1, vlq.v2n1),
                         speciesNote.consecutions.leftType == 'step',
                         speciesNote.consecutions.rightType == 'step']
                if all(cond1) and not all(cond2):
                    logger.debug(f'{isVerticalDissonance(vlq.v1n1, vlq.v2n1)}'
                                 f'{isVerticalDissonance(vlq.v1n2, vlq.v2n2)}'
                                 )
                    error = ('Dissonance off the beat in bar '
                             + str(speciesNote.measureNumber)
                             + ' is not approached and left by step.')
                    vlErrors.append(error)

    # Westergaard's lists of suspensions, by type:
    strongSuspensions = {'upper': ['d7-6', 'm7-6', 'M7-6'],
                         'lower': ['m2-3', 'M2-3', 'A2-3']}
    intermediateSuspensions = {'upper': ['m9-8', 'M9-8', 'd4-3',
                                         'P4-3', 'A4-3'],
                               'lower': ['A4-5', 'd5-6', 'A5-6']}
    weakSuspensions = {'upper': ['m2-1', 'M2-1'],
                       'lower': ['m7-8', 'M7-8', 'P4-5']}
    # List of dissonances inferred from Westergaard lists:
    validDissonances = ['m2', 'M2', 'A2', 'd4', 'P4',
                        'A5', 'd5', 'A5', 'm7', 'd7', 'M7']

    # Function for distinguishing between intervals 9 and 2 in upper lines.
    def dissName(intval):
        if (intval.simpleName in ['m2', 'M2', 'A2']
           and intval.name not in ['m2', 'M2', 'A2']):
            intervalName = interval.add([intval.simpleName, 'P8']).name
        else:
            intervalName = intval.simpleName
        return intervalName

    # Make list of dissonant syncopes.
    syncopeList = {}
    for vlq in vlqList:
        if speciesPart == 1:
            if vlq.v1n1.tie:
                if vlq.v1n1.tie.type == 'stop':
                    if vlq.vIntervals[0].simpleName in validDissonances:
                        syncopeList[vlq.v1n1.measureNumber] = (
                            dissName(vlq.vIntervals[0])
                            + '-' + vlq.vIntervals[1].semiSimpleName[-1]
                            )
        elif speciesPart == 0:
            if vlq.v2n1.tie:
                if vlq.v2n1.tie.type == 'stop':
                    if vlq.vIntervals[0].simpleName in validDissonances:
                        syncopeList[vlq.v2n1.measureNumber] = (
                            vlq.vIntervals[0].simpleName
                            + '-' + vlq.vIntervals[1].semiSimpleName[-1]
                            )
    if speciesPart == 1:
        for bar in syncopeList:
            if (syncopeList[bar] not in strongSuspensions['upper']
               and syncopeList[bar] not in intermediateSuspensions['upper']):
                error = ('The dissonant syncopation in bar '
                         + str(bar) + ' is not permitted: '
                         + str(syncopeList[bar]) + '.')
                vlErrors.append(error)
    elif speciesPart == 0:
        for bar in syncopeList:
            if (syncopeList[bar] not in strongSuspensions['lower']
               and syncopeList[bar] not in intermediateSuspensions['lower']):
                error = ('The dissonant syncopation in bar '
                         + str(bar) + ' is not permitted: '
                         + str(syncopeList[bar]) + '.')
                vlErrors.append(error)


def forbiddenMotionsOntoBeatWithoutSyncope(score, vlq,
                                           partNum1, partNum2):
    """Check a pair of parts for conformity with the rules that
    prohibit or restrict certain kinds of motion onto the beat:

       * similar motion to or from a unison
       * similar motion to an octave
       * similar motion to a fifth
       * parallel motion to unison, octave, or fifth
       * voice crossing, voice overlap, cross relation
    """
    vlqBassNote = score.parts[-1].measure(vlq.v1n2.measureNumber).getElementsByClass('Note')[0]
    if isSimilarUnison(vlq):
        error = ('Forbidden similar motion to unison going into bar '
                 + str(vlq.v2n2.measureNumber) + '.')
        vlErrors.append(error)
    if isSimilarFromUnison(vlq):
        error = ('Forbidden similar motion from unison in bar '
                 + str(vlq.v2n1.measureNumber) + '.')
        vlErrors.append(error)
    if isSimilarOctave(vlq):
        rules = [vlq.hIntervals[0].name in ['m2', 'M2'],
                 vlq.v1n2.csd.value % 7 == 0,
                 vlq.v1n2.measureNumber == score.measures,
                 vlq.v2n2.measureNumber == score.measures]
        if not all(rules):
            error = ('Forbidden similar motion to octave going into bar '
                     + str(vlq.v2n2.measureNumber) + '.')
            vlErrors.append(error)
    if isSimilarFifth(vlq):
        rules1 = [vlq.hIntervals[0].name in ['m2', 'M2']]
        rules2 = [vlq.v1n2.csd.value % 7 in [1, 4]]
        # If fifth in upper parts, compare with pitch of the
        # simultaneous bass note.
        rules3 = [partNum1 != len(score.parts)-1,
                  partNum2 != len(score.parts)-1,
                  vlq.v1n2.csd.value % 7 != vlqBassNote.csd.value % 7,
                  vlq.v2n2.csd.value % 7 != vlqBassNote.csd.value % 7]
        # TODO Recheck the logic of this.
        if not ((all(rules1) and all(rules2))
           or (all(rules1) and all(rules3))):
            error = ('Forbidden similar motion to fifth going into bar '
                     + str(vlq.v2n2.measureNumber) + '.')
            vlErrors.append(error)
    if isParallelUnison(vlq):
        error = ('Forbidden parallel motion to unison going into bar '
                 + str(vlq.v2n2.measureNumber) + '.')
        vlErrors.append(error)
    if isParallelOctave(vlq):
        error = ('Forbidden parallel motion to octave going into bar '
                 + str(vlq.v2n2.measureNumber) + '.')
        vlErrors.append(error)
    if isParallelFifth(vlq):
        error = ('Forbidden parallel motion to fifth going '
                 'into bar ' + str(vlq.v2n2.measureNumber) + '.')
        vlErrors.append(error)
    if isVoiceCrossing(vlq):
        # Strict rule when the bass is involved.
        if partNum1 == len(score.parts)-1 or partNum2 == len(score.parts)-1:
            error = ('Voice crossing going into bar '
                     + str(vlq.v2n2.measureNumber) + '.')
            vlErrors.append(error)
        else:
            alert = ('ALERT: Upper voices cross going into bar '
                     + str(vlq.v2n2.measureNumber) + '.')
            vlErrors.append(alert)
    if isVoiceOverlap(vlq):
        if partNum1 == len(score.parts)-1 or partNum2 == len(score.parts)-1:
            error = ('Voice overlap going into bar '
                     + str(vlq.v2n2.measureNumber) + ".")
            vlErrors.append(error)
        else:
            alert = ('ALERT: Upper voices overlap going into bar '
                     + str(vlq.v2n2.measureNumber) + '.')
            vlErrors.append(alert)
    if isCrossRelation(vlq):
        # TODO add permissions for second (and third?) species, ITT, p. 115
        if len(score.parts) < 3:
            cond1 = [score.parts[partNum1].species == 'second',
                     isDiatonicStep(vlq.v1n1, vlq.v1n2)]
            cond2 = [score.parts[partNum2].species == 'second',
                     isDiatonicStep(vlq.v2n1, vlq.v2n2)]
            if not (all(cond1) or all(cond2)):
                error = ('Cross relation going into bar '
                         + str(vlq.v2n2.measureNumber) + '.')
                vlErrors.append(error)
        else:
            # Test for step motion in another part.
            crossStep = False
            for part in score.parts:
                if (part != score.parts[partNum1]
                   and part != score.parts[partNum2]):
                    vlqOtherNote1 = part.measure(vlq.v1n1.measureNumber).getElementsByClass('Note')[0]
                    vlqOtherNote2 = part.measure(vlq.v1n2.measureNumber).getElementsByClass('Note')[0]
                    if vlqOtherNote1.csd.value - vlqOtherNote2.csd.value == 1:
                        crossStep = True
                        break
            if not crossStep:
                error = ('Cross relation going into bar '
                         + str(vlq.v2n2.measureNumber) + '.')
                vlErrors.append(error)


# def firstSpeciesForbiddenMotions(score, analyzer,
#                                  partNum1=None, partNum2=None):
#     """Check the forbidden forms of motion for a pair
#     of lines in first species.
#     Essentially: :py:func:`forbiddenMotionsOntoBeatWithoutSyncope`.
#     """
#     vlqList = analyzer.getVLQs(score, partNum1, partNum2)
#     for vlq in vlqList:
#         forbiddenMotionsOntoBeatWithoutSyncope(score, vlq, partNum1, partNum2)
#     checkFirstSpeciesNonconsecutiveParallels(score, analyzer,
#                                                    partNum1,
#                                                    partNum2)



def secondSpeciesForbiddenMotions(score, analyzer,
                                  partNum1=None, partNum2=None):
    """Check the forbidden forms of motion for a pair of lines
    in second species.
    Use :py:func:`forbiddenMotionsOntoBeatWithoutSyncope`
    to check motion across the
    barline and then check motion from beat to beat.
    """
    # TODO Check oblique motion within the bar for voice crossing?

    # Check motion across the barline.
    vlqList = analyzer.getVLQs(score, partNum1, partNum2)
    for vlq in vlqList:
        forbiddenMotionsOntoBeatWithoutSyncope(score, vlq, partNum1, partNum2)

    # Check motion from beat to beat.
    vlqOnbeatList = analyzer.getOnbeatVLQs(score, partNum1, partNum2)
    for vlq in vlqOnbeatList:
        if isParallelUnison(vlq):
            error = ('Forbidden parallel motion to unison from bar '
                     + str(vlq.v1n1.measureNumber) + ' to bar '
                     + str(vlq.v1n2.measureNumber) + '.')
            vlErrors.append(error)
        # TODO Revise for three parts, Westergaard p. 143.
        # Requires looking at simultaneous VLQs in a pair of verticalities.
        if isParallelOctave(vlq):
            error = ('Forbidden parallel motion to octave from bar '
                     + str(vlq.v1n1.measureNumber) + ' to bar '
                     + str(vlq.v1n2.measureNumber) + '.')
            vlErrors.append(error)
        if isParallelFifth(vlq):
            parDirection = interval.Interval(vlq.v1n1, vlq.v1n2).direction
            if vlq.v1n1.getContextByClass('Part').species == 'second':
                vSpeciesNote1 = vlq.v1n1
                vSpeciesNote2 = vlq.v1n2
                vCantusNote1 = vlq.v2n1
                vSpeciesPartNum = vlq.v1n1.getContextByClass('Part').partNum
            elif vlq.v2n1.getContextByClass('Part').species == 'second':
                vSpeciesNote1 = vlq.v2n1
                vSpeciesNote2 = vlq.v2n2
                vCantusNote1 = vlq.v1n1
                vSpeciesPartNum = vlq.v2n1.getContextByClass('Part').partNum
            localNotes = [note for note in score.parts[vSpeciesPartNum].notes
                          if (vSpeciesNote1.index
                              < note.index
                              < vSpeciesNote2.index)]
            # Test for step motion contrary to parallels.
            rules1 = [vSpeciesNote2.consecutions.leftDirection
                      != parDirection,
                      vSpeciesNote2.consecutions.rightDirection
                      != parDirection,
                      vSpeciesNote2.consecutions.leftType == 'step',
                      vSpeciesNote2.consecutions.leftType == 'step']
            # test for appearance of note as consonance in first bar
            # TODO figure out better way to test for consonance
            rules2 = False
            for note in localNotes:
                if (note.pitch == vSpeciesNote2.pitch
                   and isConsonanceAboveBass(vCantusNote1, note)):
                    rules2 = True
                    break
            # TODO verify that the logic of the rules evaluation is correct
            if not (all(rules1) or rules2):
                error = ('Forbidden parallel motion to pefect fifth from the '
                         'downbeat of bar ' + str(vlq.v1n1.measureNumber)
                         + ' to the downbeat of bar '
                         + str(vlq.v1n2.measureNumber) + '.')
                vlErrors.append(error)


def thirdSpeciesForbiddenMotions(score, analyzer,
                                 partNum1=None, partNum2=None):
    """Check the forbidden forms of motion for a pair of lines in
    third species.  Use :py:func:`forbiddenMotionsOntoBeatWithoutSyncope`
    to check motion across the barline and then check motion from beat
    to beat, from off the beat to next but not immediately following
    on the beat.
    """
    # TODO: Finish this script.

    def checkMotionsOntoBeat():
        # Check motion across the barline.
        vlqList = analyzer.getVLQs(score, partNum1, partNum2)
        for vlq in vlqList:
            # Check motion across the barline, as in first and second species.
            if vlq.v1n2.beat == 1.0 and vlq.v2n2.beat == 1.0:
                forbiddenMotionsOntoBeatWithoutSyncope(score, vlq,
                                                       partNum1, partNum2)
            else:
                # Check motion within the bar.
                if isVoiceCrossing(vlq):
                    # Strict rule when the bass is involved.
                    if (partNum1 == len(score.parts)-1
                       or partNum2 == len(score.parts)-1):
                        error = ('Voice crossing in bar '
                                 + str(vlq.v2n2.measureNumber) + '.')
                        vlErrors.append(error)
                    else:
                        alert = ('ALERT: Upper voices cross in bar '
                                 + str(vlq.v2n2.measureNumber) + '.')
                        vlErrors.append(alert)

    def checkMotionsBeatToBeat():
        # Check motion from beat to beat.
        vlqOnbeatList = analyzer.getOnbeatVLQs(score, partNum1, partNum2)
        for vlq in vlqOnbeatList:
            if isParallelUnison(vlq):
                error = ('Forbidden parallel motion to unison from bar '
                         + str(vlq.v1n1.measureNumber) + ' to bar '
                         + str(vlq.v1n2.measureNumber) + '.')
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
                localNotes = [note for note in localNotes
                              if (vSpeciesNote1.index
                                  < note.index
                                  < vSpeciesNote2.index)]
                # Test for step motion contrary to parallels.
                rules1 = [vSpeciesNote2.consecutions.leftDirection
                          != parDirection,
                          vSpeciesNote2.consecutions.rightDirection
                          != parDirection,
                          vSpeciesNote2.consecutions.leftType == 'step',
                          vSpeciesNote2.consecutions.leftType == 'step']
                # Test for appearance of note as consonance in first bar.
                # TODO Figure out better way to test for consonance.
                rules2 = False
                for note in localNotes:
                    if (note.pitch == vSpeciesNote2.pitch
                       and isConsonanceAboveBass(vCantusNote1, note)):
                        rules2 = True
                        break
                # TODO Verify that the logic of the rules evaluation is correct.
                if not (all(rules1) or rules2):
                    error = ('Forbidden parallel motion from the downbeat '
                             'of bar ' + str(vlq.v1n1.measureNumber) +
                             ' to the downbeat of bar '
                             + str(vlq.v1n2.measureNumber) + '.')
                    vlErrors.append(error)

    def checkMotionsOffToOnBeat():
        # Check motions from off to next but not consecutive on beat.
        vlqNonconsecutivesList = analyzer.getNonconsecutiveOffbeatToOnbeatVLQs(score, partNum1, partNum2)
        for vlq in vlqNonconsecutivesList:
            if isParallelUnison(vlq):
                error = ('Forbidden parallel motion to unison from bar '
                         + str(vlq.v1n1.measureNumber) + ' to bar '
                         + str(vlq.v1n2.measureNumber) + '.')
                vlErrors.append(error)
            if isParallelOctave(vlq):
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
                # Make a list of notes in the species line that are
                # simultaneous with the first cantus tone.
                localSpeciesMeasure = score.parts[vSpeciesPartNum].measures(vCantusNote1.measureNumber, vCantusNote1.measureNumber)
                localNotes = localSpeciesMeasure.getElementsByClass('Measure')[0].notes
                localNotes = [note for note in localNotes]
                # Test for step motion contrary to parallels.
                rules1 = [vSpeciesNote2.consecutions.leftDirection
                          != parDirection,
                          vSpeciesNote2.consecutions.rightDirection
                          != parDirection,
                          vSpeciesNote2.consecutions.leftType == 'step',
                          vSpeciesNote2.consecutions.leftType == 'step']
                # Test for appearance of note as consonance in first bar.
                # TODO Figure out better way to test for consonance.
                rules2 = False
                for note in localNotes:
                    if (note.pitch == vSpeciesNote2.pitch and
                       isConsonanceAboveBass(vCantusNote1, note)):
                        rules2 = True
                        break
                if not (all(rules1) or rules2):
                    error = ('Forbidden parallel octaves from an offbeat '
                             'note in bar ' + str(vlq.v1n1.measureNumber)
                             + ' to the downbeat of bar '
                             + str(vlq.v1n2.measureNumber) + ".")
                    vlErrors.append(error)

    checkMotionsOntoBeat()
    checkMotionsBeatToBeat()
    checkMotionsOffToOnBeat()


def fourthSpeciesForbiddenMotions(score, analyzer,
                                  partNum1=None, partNum2=None):
    """Check the forbidden forms of motion for a pair of lines in fourth
    species. Mostly limited to looking for parallel unisons and octaves
    in consecutive meausures.
    Use :py:func:`forbiddenMotionsOntoBeatWithoutSyncope`
    to check motion across the
    barline whenever the syncopations are broken.
    """
    vlqList = analyzer.getVLQs(score, partNum1, partNum2)
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)

    if score.parts[partNum1].species == 'fourth':
        speciesPart = 1
    elif score.parts[partNum2].species == 'fourth':
        speciesPart = 0
    vPairsOnbeat = []
    vPairsOnbeatDict = {}
    vPairsOffbeat = []
    for vPair in vPairList:
        if vPair is not None:
            # Evaluate offbeat intervals when one of the parts is the bass.
            if vPair[speciesPart].beat == 1.0:
                vPairsOnbeat.append(vPair)
                vPairsOnbeatDict[vPair[speciesPart].measureNumber] = vPair
            else:
                vPairsOffbeat.append(vPair)
    vlqsOffbeat = makeVLQFromVPair(vPairsOffbeat)
    vlqsOnbeat = makeVLQFromVPair(vPairsOnbeat)
    for vlq in vlqsOffbeat:
        if isParallelUnison(vlq):
            error = ('Forbidden parallel motion to unison going into bar '
                     + str(vlq.v2n2.measureNumber))
            vlErrors.append(error)
        if isParallelOctave(vlq):
            thisBar = vlq.v1n2.measureNumber
            thisOnbeatPair = vPairsOnbeatDict[thisBar]
            if not isConsonanceAboveBass(thisOnbeatPair[0], thisOnbeatPair[1]):
                error = ('Forbidden parallel motion to octave going into bar '
                         + str(vlq.v2n2.measureNumber))
                vlErrors.append(error)
    for vlq in vlqsOnbeat:
        if isParallelUnison(vlq):
            error = ('Forbidden parallel motion to unison going into bar '
                     + str(vlq.v2n2.measureNumber))
            vlErrors.append(error)
    # Check second-species motion across barlines,
    # looking at vlq with initial untied offbeat note.
    for vlq in vlqList:
        if speciesPart == 1:
            speciesNote = vlq.v1n1
        elif speciesPart == 0:
            speciesNote = vlq.v2n1
        if speciesNote.tie is None and speciesNote.beat > 1.0:
            forbiddenMotionsOntoBeatWithoutSyncope(score, vlq,
                                                   partNum1, partNum2)
    # check second-species motion across final barline
    for vlq in vlqsOnbeat:
        if (isParallelOctave(vlq)
                and vlq.v1n2.tie is None
                and vlq.v2n2.tie is None):
            error = ('Forbidden parallel motion to octave going into bar '
                     + str(vlq.v2n2.measureNumber))
            vlErrors.append(error)


def checkFirstSpeciesNonconsecutiveParallels(score, analyzer,
                                            partNum1=None,
                                            partNum2=None):
    """Check for restrictions on nonconsecutive parallel unisons
    and octaves in first species."""
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)
    vPairTriples = [[vPairList[i], vPairList[i + 1], vPairList[i + 2]] for i in
           range(len(vPairList) - 2)]
    for vpt in vPairTriples:
        if isUnison(vpt[0][0], vpt[0][1]) or isOctave(vpt[0][0], vpt[0][1]):
            vlq1 = makeVLQfromVertPairs(vpt[0], vpt[2])
            p_int = None
            if isParallelUnison(vlq1):
                p_int = 'unisons'
            elif isParallelOctave(vlq1):
                p_int = 'octaves'
            if p_int:
                vlq2 = makeVLQfromVertPairs(vpt[0], vpt[1])
                if vlq2 is not None:
                    if isDisplaced(vlq2):
                        pass
                    elif (vlq1.v1n2.csd.value % 7 == vpt[2][0].csd.value % 7
                          or vlq1.v1n2.csd.value % 7 == vpt[2][1].csd.value % 7):
                        pass
                    else:
                        bar1 = vpt[0][0].measureNumber
                        bar2 = vpt[2][0].measureNumber
                        error = (f'Non-consecutive parallel {p_int} in bars {bar1}'
                             f' and {bar2}.')
                        vlErrors.append(error)


def checkSecondSpeciesNonconsecutiveUnisons(score, analyzer,
                                            partNum1=None,
                                            partNum2=None):
    """Check for restrictions on nonconsecutive parallel unisons."""
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)

    if score.parts[partNum1].species == 'second':
        speciesPart = 1
    elif score.parts[partNum2].species == 'second':
        speciesPart = 0
    else:
        return
    firstUnison = None
    for vPair in vPairList:
        if firstUnison:
            if (interval.Interval(vPair[0], vPair[1]).name == 'P1'
                    and vPair[speciesPart].beat == 1.5
                    and vPair[speciesPart].measureNumber - 1
                    == firstUnison[0]):
                error = ('Offbeat unisons in bars '
                         + str(firstUnison[0]) + ' and '
                         + str(vPair[speciesPart].measureNumber))
                vlErrors.append(error)
        if vPair is not None:
            if (interval.Interval(vPair[0], vPair[1]).name == 'P1'
                    and vPair[speciesPart].beat > 1.0):
                firstUnison = (vPair[speciesPart].measureNumber, vPair)


def checkSecondSpeciesNonconsecutiveOctaves(score, analyzer,
                                            partNum1=None,
                                            partNum2=None):
    """Check for restrictions on nonconsecutive parallel octaves."""
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)
    if score.parts[partNum1].species == 'second':
        speciesPart = 1
    elif score.parts[partNum2].species == 'second':
        speciesPart = 0
    else:
        return
    firstOctave = None
    for vPair in vPairList:
        if firstOctave:
            if (interval.Interval(vPair[0], vPair[1]).name == 'P8'
                    and vPair[speciesPart].beat > 1.0
                    and vPair[speciesPart].measureNumber-1
                    == firstOctave[0]):
                if interval.Interval(firstOctave[1][speciesPart], vPair[speciesPart]).isDiatonicStep:
                    if (vPair[speciesPart].consecutions.leftDirection
                       == firstOctave[1][speciesPart].consecutions.leftDirection):
                        error = ('Offbeat octaves in bars ' + str(firstOctave[0])
                                 + ' and '
                                 + str(vPair[speciesPart].measureNumber))
                        vlErrors.append(error)
                elif interval.Interval(firstOctave[1][speciesPart],
                                       vPair[speciesPart]).generic.isSkip:
                    if (vPair[speciesPart].consecutions.leftDirection
                       != firstOctave[1][speciesPart].consecutions.leftDirection
                       or firstOctave[1][speciesPart].consecutions.rightInterval.isDiatonicStep):
                        continue
                    else:
                        error = ('Offbeat octaves in bars '
                                 + str(firstOctave[0]) + ' and '
                                 + str(vPair[speciesPart].measureNumber))
                        vlErrors.append(error)
        if vPair is not None:
            if (interval.Interval(vPair[0], vPair[1]).name == 'P8'
                    and vPair[speciesPart].beat == 1.5):
                firstOctave = (vPair[speciesPart].measureNumber, vPair)


def checkFourthLeapsInBass(score, analyzer):
    """Check fourth leaps in the bass to ensure that there is no
    implication of a six-four chord during the meausure in which
    the lower note of the fourth occurs.
    """
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
        # Implication is true until proven otherwise.
        impliedSixFour = True

        # Leaps of a fourth within a measure.
        if bn1Meas == bn2Meas:
            fourthBass = interval.getAbsoluteLowerNote(bn1, bn2)
            for n in score.parts[bnPartNum].measure(bn1Meas).notes:
                rules1 = [n != bn1,
                          n != bn2,
                          n == interval.getAbsoluteLowerNote(n, fourthBass),
                          interval.Interval(n, fourthBass).semitones
                          < interval.Interval('P8').semitones,
                          isTriadicConsonance(n, bn1),
                          isTriadicConsonance(n, bn2)]
                if all(rules1):
                    impliedSixFour = False
                    break

        # Leaps of a fourth across the barline.
        elif bn1Meas == bn2Meas-1:
            # Check upper parts for note that denies the implication.
            for part in score.parts[0:bnPartNum]:
                # Get the two bars in the context of the bass fourth.
                bars = part.getElementsByOffset(
                    offsetStart=bn1Start,
                    offsetEnd=bn2End,
                    includeEndBoundary=False,
                    mustFinishInSpan=False,
                    mustBeginInSpan=False,
                    includeElementsThatEndAtStart=False,
                    classList=None
                    )
                # Make note list for each bar of the part, simultaneous
                # with notes of the fourth.
                barseg1 = []
                barseg2 = []
                for bar in bars:
                    # bar notes 1
                    barns1 = bar.getElementsByOffset(
                        offsetStart=bn1Start-bar.offset,
                        offsetEnd=bn1End-bar.offset,
                        includeEndBoundary=False,
                        mustFinishInSpan=False,
                        mustBeginInSpan=False,
                        includeElementsThatEndAtStart=False,
                        classList='Note'
                        )
                    for n in barns1:
                        barseg1.append(n)
                    # bar notes 2
                    barns2 = bar.getElementsByOffset(
                        offsetStart=bn2Start-bar.offset,
                        offsetEnd=bn2End,
                        includeEndBoundary=False,
                        mustFinishInSpan=False,
                        mustBeginInSpan=False,
                        includeElementsThatEndAtStart=False,
                        classList='Note'
                        )
                    for n in barns2:
                        barseg2.append(n)

                for n in barseg1:
                    # rules for all species
                    # locally consonant, step-class contiguity
                    rules1 = [isConsonanceAboveBass(bn1, n),
                              interval.Interval(bn2, n).simpleName
                              in ['m2', 'M2', 'm7', 'M7']]

                    # rules for first species
                    if len(barseg1) == 1:
                        if all(rules1):
                            impliedSixFour = False
                            break

                    # rules for second species
                    elif len(barseg1) == 2 and not barseg1[0].tie:
                        # first in bar, leapt to, or last in bar
                        # (hence contiguous with bn2)
                        rules2 = [n.offset == 0.0,
                                  n.consecutions.leftType == 'skip',
                                  n.offset+n.quarterLength
                                  == score.measure(bn1Meas).quarterLength]
                        if all(rules1) and any(rules2):
                            impliedSixFour = False
                            break

                    # rules for third species
                    elif len(barseg1) > 2:
                        # first in bar or last in bar (hence
                        # contiguous with bn2)
                        rules3a = [n.offset == 0.0,
                                   n.offset+n.quarterLength
                                   == score.measure(bn1Meas).quarterLength]
                        # not first or last in bar and no step follows
                        stepfollows = [x for x in barseg1
                                       if x.offset > n.offset
                                       and isConsonanceAboveBass(bn1, x)
                                       and isDiatonicStep(x, n)]
                        rules3b = [n.offset > 0.0,
                                   n.offset+n.quarterLength
                                   < score.measure(bn1Meas).quarterLength,
                                   stepfollows == []]

                        if all(rules1) and (any(rules3a) or all(rules3b)):
                            impliedSixFour = False
                            break

                    # rules for fourth species
                    elif len(barseg1) == 2 and barseg1[1].tie:
                        # TODO verify that no additional rule is needed
                        rules4 = [] # [n.tie.type == 'start']
                        if all(rules1) and all(rules4):
                            impliedSixFour = False
                            break
                    # if fourth species is broken
                    elif len(barseg1) == 2 and not barseg1[1].tie:
                        # first in bar, leapt to, or last in bar
                        # (hence contiguous with bn2)
                        rules2 = [n.offset == 0.0,
                                  n.consecutions.leftType == 'skip',
                                  n.offset+n.quarterLength
                                  == score.measure(bn1Meas).quarterLength]
                        if all(rules1) and any(rules2):
                            impliedSixFour = False
                            break

                for n in barseg2:
                    # locally consonant, step-class contiguity
                    rules1 = [isConsonanceAboveBass(bn2, n),
                              interval.Interval(bn1, n).simpleName
                              in ['m2', 'M2', 'm7', 'M7']]

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
                        stepprecedes = [x for x in barseg2
                                        if x.offset < n.offset
                                        and isConsonanceAboveBass(bn1, x)
                                        and isDiatonicStep(x, n)]
                        rules3 = [n.offset == 0.0,
                                  stepprecedes == []]
                        if all(rules1) and any(rules3):
                            impliedSixFour = False
                            break

                    # rules for fourth species
                    elif len(barseg2) == 2 and barseg2[0].tie:
                        # TODO verify that no additional rule is needed
                        rules4 = [] # [n.tie.type == 'start']
                        if all(rules1) and all(rules4):
                            impliedSixFour = False
                            break
            # Check third species bass part for note that
            # denies the implication.
            if score.parts[bnPartNum].species == 'third':
                bn1Measure = bn1.measureNumber
                # Get the notes in the bar of the first bass note.
                bassnotes = score.parts[bnPartNum].flat.notes
                barns1 = [n for n in bassnotes
                          if n.measureNumber == bn1Measure]

                # TODO Finish this test.
                for n in barns1:
                    rules3a = [isDiatonicStep(n, bn2)]
                    rules3b = [n.offset == 0.0,
                               n == barns1[-2]]
                    if all(rules3a) and any(rules3b):
                        impliedSixFour = False
                        break

        if impliedSixFour and bn1Meas == bn2Meas:
            error = ('Prohibited leap of a fourth in bar '
                     + str(bn1Meas) + '.')
            vlErrors.append(error)
        elif impliedSixFour and bn1Meas != bn2Meas:
            error = ('Prohibited leap of a fourth in bars '
                     + str(bn1Meas) + ' to ' + str(bn2Meas) + '.')
            vlErrors.append(error)
#        return impliedSixFour

# -----------------------------------------------------------------------------
# UTILITY SCRIPTS
# -----------------------------------------------------------------------------


# utility function for finding pairs of parts
def getAllPartNumPairs(score):
    """Assemble a list of the pairwise combinations of parts in a score."""
    # From theory analyzer:
    partNumPairs = []
    numParts = len(score.parts)
    for partNum1 in range(numParts - 1):
        for partNum2 in range(partNum1 + 1, numParts):
            partNumPairs.append((partNum1, partNum2))
    return partNumPairs


def makeVLQFromVPair(vPairList):
    """Given a list of simultaneous note pairs, create a voice-leading
    quartet for each consecutive pair of pairs.
    """
    quartetList = []
    for quartet in pairwise(vPairList):
        quartetList.append((quartet[0][1], quartet[1][1],
                            quartet[0][0], quartet[1][0]))
    vlqList = []
    for quartet in quartetList:
        vlqList.append(voiceLeading.VoiceLeadingQuartet(quartet[0],
                                                        quartet[1],
                                                        quartet[2],
                                                        quartet[3]))
    return vlqList


def makeVLQsFromVertPair(vertPair, partNumPairs):
    """Given a pair of multi-part verticalities and a list
    of the pairwise combinations of parts,
    create all the possible voice-leading quartets among
    notes (ignoring rests).
    """
    vlqList = []
    for numPair in partNumPairs:
        upperPart = numPair[0]
        lowerPart = numPair[1]
        v1n1 = vertPair[0].objects[upperPart]
        v1n2 = vertPair[1].objects[upperPart]
        v2n1 = vertPair[0].objects[lowerPart]
        v2n2 = vertPair[1].objects[lowerPart]
        # Do not make a VLQ if one note is a rest.
        if v1n1.isRest or v1n2.isRest or v2n1.isRest or v2n2.isRest:
            continue
        else:
            vlqList.append((numPair,
                            voiceLeading.VoiceLeadingQuartet(v1n1, v1n2,
                                                             v2n1, v2n2)))
    return vlqList


def makeVLQfromVertPairs(vpair1, vpair2):
    v1n1 = vpair1[0]
    v1n2 = vpair2[0]
    v2n1 = vpair1[1]
    v2n2 = vpair2[1]
    # Do not make a VLQ if one note is a rest.
    if v1n1.isRest or v1n2.isRest or v2n1.isRest or v2n2.isRest:
        vlq = None
    else:
        vlq = voiceLeading.VoiceLeadingQuartet(v1n1, v1n2, v2n1, v2n2)

    return vlq


# -----------------------------------------------------------------------------
# TESTS
# -----------------------------------------------------------------------------


class Test(unittest.TestCase):

    def runTest(self):
        pass

    def test_UnifiedIntervalTests(self):
        G3 = note.Note('G3')
        A3 = note.Note('A3')
        B3 = note.Note('B3')
        C4 = note.Note('C4')
        D4 = note.Note('D4')
        E4 = note.Note('E4')
        F4 = note.Note('F4')
        G4 = note.Note('G4')
        A4 = note.Note('A4')
        B4 = note.Note('B4')
        C5 = note.Note('C5')
        D5 = note.Note('D5')

        self.assertFalse(isConsonanceAboveBass(G3, C4))
        self.assertTrue(isConsonanceAboveBass(G3, D4))

        self.assertTrue(isThirdOrSixthAboveBass(G3, B3))
        self.assertFalse(isThirdOrSixthAboveBass(G3, C4))
        self.assertTrue(isThirdOrSixthAboveBass(G3, E4))

        self.assertFalse(isConsonanceBetweenUpper(F4, B4))
        self.assertTrue(isConsonanceBetweenUpper(D4, B4))

        self.assertTrue(isPermittedDissonanceBetweenUpper(F4, B4))
        self.assertFalse(isPermittedDissonanceBetweenUpper(F4, G4))

        self.assertFalse(isTriadicConsonance(F4, B4))
        self.assertTrue(isTriadicConsonance(D4, B4))

        self.assertFalse(isTriadicInterval(F4, G4))
        self.assertTrue(isTriadicInterval(F4, B4))
        self.assertTrue(isTriadicInterval(C4, C5))

        self.assertTrue(isPerfectVerticalConsonance(C4, G4))
        self.assertFalse(isPerfectVerticalConsonance(D4, G4))

        self.assertTrue(isImperfectVerticalConsonance(D4, B4))
        self.assertFalse(isImperfectVerticalConsonance(D4, A4))

        self.assertTrue(isVerticalDissonance(F4, B4))
        self.assertFalse(isVerticalDissonance(D4, B4))

        self.assertTrue(isDiatonicStep(F4, G4))
        self.assertFalse(isDiatonicStep(F4, A4))

        self.assertTrue(isUnison(G4, G4))
        self.assertFalse(isUnison(C4, C5))

        self.assertFalse(isOctave(G4, G4))
        self.assertTrue(isOctave(C4, C5))

    def test_unifiedVLQTests(self):
        G3 = note.Note('G3')
        A3 = note.Note('A3')
        B3 = note.Note('B3')
        C4 = note.Note('C4')
        D4 = note.Note('D4')
        E4 = note.Note('E4')
        F4 = note.Note('F4')
        G4 = note.Note('G4')
        A4 = note.Note('A4')
        Bb4 = note.Note('Bb4')
        B4 = note.Note('B4')
        C5 = note.Note('C5')
        D5 = note.Note('D5')

        a = voiceLeading.VoiceLeadingQuartet(C5, D5, A4, D5)
        self.assertTrue(isSimilarUnison(a))

        a = voiceLeading.VoiceLeadingQuartet(D5, C5, D5, A4)
        self.assertTrue(isSimilarFromUnison(a))

        a = voiceLeading.VoiceLeadingQuartet(C5, D5, E4, G4)
        self.assertTrue(isSimilarFifth(a))

        a = voiceLeading.VoiceLeadingQuartet(B4, C5, G3, C4)
        self.assertTrue(isSimilarOctave(a))

        a = voiceLeading.VoiceLeadingQuartet(C4, D4, C4, D4)
        self.assertTrue(isParallelUnison(a))

        a = voiceLeading.VoiceLeadingQuartet(G4, A4, C4, D4)
        self.assertTrue(isParallelFifth(a))

        a = voiceLeading.VoiceLeadingQuartet(C5, D5, C4, D4)
        self.assertTrue(isParallelOctave(a))

        a = voiceLeading.VoiceLeadingQuartet(G4, D5, F4, A4)
        self.assertTrue(isVoiceOverlap(a))

        a = voiceLeading.VoiceLeadingQuartet(G4, A4, E4, C5)
        self.assertTrue(isVoiceCrossing(a))

        a = voiceLeading.VoiceLeadingQuartet(B3, C4, G4, Bb4)
        self.assertTrue(isCrossRelation(a))

        a = voiceLeading.VoiceLeadingQuartet(C4, G3, C5, B4)
        self.assertTrue(isDisplaced(a))

    def test_isOnbeat(self):
        pass

    def test_isSyncopated(self):
        pass

    def test_checkPartPairs(self):
        pass

    def test_checkFirstSpecies(self):
        pass

    def test_checkSecondSpecies(self):
        pass

    def test_checkThirdSpecies(self):
        pass

    def test_checkFourthSpecies(self):
        pass

    def test_checkConsecutions(self):
        pass

    def test_checkControlOfDissonance(self):
        pass

    def test_fourthSpeciesControlOfDissonance(self):
        pass

    def test_forbiddenMotionsOntoBeatWithoutSyncope(self):
        pass

    def test_firstSpeciesForbiddenMotions(self):
        pass

    def test_secondSpeciesForbiddenMotions(self):
        pass

    def test_thirdSpeciesForbiddenMotions(self):
        pass

    def test_fourthSpeciesForbiddenMotions(self):
        pass

    def test_checkSecondSpeciesNonconsecutiveUnisons(self):
        pass

    def test_checkSecondSpeciesNonconsecutiveOctaves(self):
        pass

    def test_checkFourthLeapsInBass(self):
        pass

    def test_getAllPartNumPairs(self):
        pass

    def test_makeVLQFromVPair(self):
        pass

    def test_makeVLQsFromVertPair(self):
        pass

# -----------------------------------------------------------------------------


if __name__ == '__main__':
    unittest.main()

# -----------------------------------------------------------------------------
# eof
