# -----------------------------------------------------------------------------
# Name:         vlChecker.py
# Purpose:      Framework for analyzing voice leading in species counterpoint
#
# Author:       Robert Snarrenberg
# Copyright:    (c) 2023 by Robert Snarrenberg
# License:      BSD, see license.txt
# -----------------------------------------------------------------------------
"""
Voice Leading Checker
=====================

The Voice Leading Checker module takes a score with two or more parts (lines)
and examines the local voice leading for conformity with Westergaard's rules
of species counterpoint.

The module divides the score into small bits for analysis,
bits such as pairs of simultaneous notes,
complete verticalities, and voice-leading quartets.
The voice-leading checker then analyzes these bits of data.

The base functions consist of the following:

   :py:func:`getOffsetList(score)` - Compiles a list of timepoints when events
   are initiated in a score. Accepts as input either a duet of parts
   extracted from a score or all of the score parts.

   :py:func:`getVerticalityContentDictFromDuet(duet, offset)` - Given a duet
   and a particular offset, this function constructs a dictionary of
   the notes still sounding or starting to sound at that offset.
   The dictionary is arranged by part number.

   :py:func:`getVerticalPairs(duet)` - Uses :py:func:`getOffsetList(score)`
   to construct an ordered list of all the pairs of simultaneous notes
   occurring between the parts of the duet. Useful for checking the control
   of dissonance.

   :py:func:`getAllVLQsFromDuet(duet)` - Uses :py:func:`getOffsetList(score)`
   to extract an ordered list of the
   :class:`~music21.voiceLeading.VoiceLeadingQuartet` objects in the duet.
   A voice-leading quartet (VLQ) consists of pairs of simultaneous
   notes in two parts:

      * v1: n1, n2
      * v2: n1, n2

   VLQs are useful for checking forbidden forms of motion.

Modified versions of these functions are used to extra vertical pairs and
VLQs that involve nonconsecutive simulataneities (see below).

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
is only reported on demand [this option is not yet available].

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

import unittest
import logging

from music21 import *

from westerparse.utilities import pairwise, create_html_report

# -----------------------------------------------------------------------------
# LOGGER
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)
logger.propagate = False
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
allowThirdSpeciesInsertions = True  # currently not in use
sonorityCheck = False

# Create lists to collect errors and advice, for reporting to user.
vlErrors = []
vlAdvice = []


# -----------------------------------------------------------------------------
# MAIN SCRIPT
# -----------------------------------------------------------------------------


def checkCounterpoint(context, report=True):
    """
    This is the main script.

    It creates a duet for each pair of parts in the score and then
    checks every duet for conformity with the
    rules that control dissonance and the rules that prohibit certain
    forms of motion.  A separate function checks for the rules that
    control leaps of a fourth in the bass.
    """
    # CURRENT VERSION: TEST EACH PAIR OF LINES
    # Information access to other activity in other lines is limited.
    # Works best for two-part simple species.
    # Each pairing has its own subroutines:
    #     1:1; 1:2; 1:3 and 1:4; and syncopated

    twoPartContexts = context.makeTwoPartContexts()
    for duet in twoPartContexts:
        checkDuet(context, duet)
    checkFourthLeapsInBass(context)

    # Report voice-leading errors, if asked.
    if report:
        if not vlErrors:
            result = ('VOICE LEADING REPORT\nNo voice-leading errors found.\n')
        else:
            result = ('VOICE LEADING REPORT\nThe following '
                      'voice-leading errors were found:')
            for error in vlErrors:
                result = result + '\n\t\t' + error
        if report == 'html':
            print(create_html_report(result))
        else:
            print(result)

        # Report sonority advice, if enabled.
        if sonorityCheck:
            if not vlAdvice:
                advice = None
            elif vlAdvice:
                advice = ('SONORITY ADVICE \nThe following '
                          'situations may need attention:')
                for item in vlAdvice:
                    advice = advice + '\n\t' + item
            if advice:
                if report == 'html':
                    print(create_html_report(advice))
                else:
                    print(advice)
    else:
        pass

def checkDuet(context, duet):
    """
    Check the voice-leading of each duet, depending upon which simple
    species the pair represents (e.g., first, second, third, fourth).
    The function is not yet able to evaluate combined species.
    """
    cond1 = duet.parts[0].species == 'first'
    cond2 = duet.parts[1].species == 'first'
    if cond1 and cond2:
        checkFirstSpecies(context, duet)
    if ((cond1 and duet.parts[1].species == 'second')
            or (duet.parts[0].species == 'second' and cond2)):
        checkSecondSpecies(context, duet)
    if ((cond1 and duet.parts[1].species == 'third')
            or (duet.parts[0].species == 'third' and cond2)):
        checkThirdSpecies(context, duet)
    if ((cond1 and duet.parts[1].species == 'fourth')
            or (duet.parts[0].species == 'fourth' and cond2)):
        checkFourthSpecies(context, duet)
    # TODO Add pairs for combined species: Westergaard chapter 6:
    # second and second
    # third and third
    # fourth and fourth
    # second and third
    # second and fourth
    # third and fourth


def checkFirstSpecies(context, duet):
    """
    Check a duet, where both lines are in first species.
    Evaluate control of dissonance and forbidden forms of motion.
    """
    VLQs = getAllVLQsFromDuet(duet)
    checkFirstSpeciesForbiddenMotions(context, duet, VLQs)
    checkControlOfDissonance(context, duet, VLQs)
    if sonorityCheck and len(context.parts) == 2:
        checkFirstSpeciesSonority(context, duet)


def checkSecondSpecies(context, duet):
    """
    Check a duet, where one line is in first species
    and the other is in second species.
    Check the intervals between consecutive notes (no local
    repetitions in the second species line).
    Evaluate control of dissonance and forbidden forms of motion,
    including the rules for nonconsecutive unisons and octaves.
    """
    VLQs = getAllVLQsFromDuet(duet)
    checkConsecutions(context)
    checkSecondSpeciesForbiddenMotions(context, duet, VLQs)
    checkControlOfDissonance(context, duet, VLQs)
    checkSecondSpeciesNonconsecutiveUnisons(duet)
    checkSecondSpeciesNonconsecutiveOctaves(duet)


def checkThirdSpecies(context, duet):
    """
    Check a duet, where one line is in first species
    and the other is in third species.
    Check the intervals between consecutive notes (no local repetitions
    in the third species line).
    Evaluate control of dissonance and forbidden forms of motion.
    """
    VLQs = getAllVLQsFromDuet(duet)
    checkConsecutions(context)
    checkThirdSpeciesForbiddenMotions(context, duet, VLQs)
    checkControlOfDissonance(context, duet, VLQs)


def checkFourthSpecies(context, duet):
    """
    Check a duet, where one line is in first species
    and the other is in fourth species.
    Check the intervals between consecutive notes (no local repetitions
    in the fourth species line).
    Evaluate control of dissonance and forbidden forms of motion.
    """
    checkConsecutions(context)
    VLQs = getAllVLQsFromDuet(duet)
    checkFourthSpeciesForbiddenMotions(context, duet, VLQs)
    checkFourthSpeciesControlOfDissonance(context, duet, VLQs)


# -----------------------------------------------------------------------------
# SCRIPTS FOR EVALUATING VOICE LEADING, BY SPECIES
# -----------------------------------------------------------------------------


def checkControlOfDissonance(context, duet, VLQs):
    """
    Check a duet for conformity with the rules that control
    dissonance in first, second, or third species. Requires access not only
    to notes in the duet but also the bass line, if not included in the duet.

    On the beat: notes must be consonant.

    Off the beat: notes may be dissonant but only if approached
    and left by step.

    Off the beat: consecutive dissonances must be approached
    and left by step in the same direction.
    """
    # Get the list of event offsets.
    eventOffsets = getOffsetList(duet)
    # Construct vertical dictionaries for every offset and evaluate for
    # control of dissonance. Get bass note, if not included in duet.
    for offset in eventOffsets:
        contentDict = getVerticalityContentDictFromDuet(duet, offset)
        upperNote = contentDict[0]
        lowerNote = contentDict[1]
        if not duet.includesBass:
            bassNotes = [el for el in
                         context.parts[-1].flatten().notes.getElementsByOffset(
                             offset, mustBeginInSpan=False)]
            bassNote = bassNotes[0]
        else:
            bassNote = lowerNote

        # Do not evaluate a simultaneity if one note is a rest.
        # TODO This is okay for now, but need to check
        #   the rules for all gambits.
        #   And what if there's a rest during a line?
        #   Consider using getVerticalPairs(duet)...
        #   Parts in the ContentDict may contain rests; parts in
        #       VewrticalPairs contain only notes (already filtered)
        if upperNote.isRest or lowerNote.isRest:
            continue

        # Rules for co-initiated simultaneities.
        # (1) Both notes start at the same time, neither is tied over:
        rules1 = [upperNote.beat == lowerNote.beat,
                  (upperNote.tie is None or upperNote.tie.type == 'start'),
                  (lowerNote.tie is None or lowerNote.tie.type == 'start')]
        # (2a) The pair constitutes a permissible consonance above the bass:
        rules2a = [duet.includesBass,
                   isConsonanceAboveBass(lowerNote, upperNote)]
        # (2b) The pair constitutes a permissible consonance between upper parts:
        rules2b = [not duet.includesBass,
                   isConsonanceBetweenUpper(lowerNote, upperNote)]
        # (2c) The pair is a permissible dissonance between upper parts:
        # TODO This won't work if the bass is a rest and not a note.
        rules2c = [not duet.includesBass,
                   isPermittedDissonanceBetweenUpper(lowerNote, upperNote),
                   isThirdOrSixthAboveBass(bassNote, upperNote),
                   isThirdOrSixthAboveBass(bassNote, lowerNote)]

        # Test co-initiated simultaneities.
        if (all(rules1) and not (all(rules2a)
                                 or all(rules2b)
                                 or all(rules2c))):
            error = ('Dissonance between co-initiated notes in bar '
                     + str(upperNote.measureNumber) + ': '
                     + str(interval.Interval(lowerNote, upperNote).name)
                     + '.')
            vlErrors.append(error)

        # Rules for non-co-initiated simultaneities.
        # (3) One note starts after the other and is neither consonant
        # nor included among the permissible dissonances:
        rules3 = [upperNote.beat != lowerNote.beat,
                  not (all(rules2a) or all(rules2b) or all(rules2c))]
        # (4) Upper note is later.
        rules4 = [upperNote.beat > lowerNote.beat]
        # (5a) The upper note is approached and left by step.
        rules5a = [upperNote.consecutions.leftType == 'step',
                   upperNote.consecutions.rightType == 'step']
        # (5b) The lower note is approached and left by step.
        rules5b = [lowerNote.consecutions.leftType == 'step',
                   lowerNote.consecutions.rightType == 'step']

        # Test non-co-initiated sumultaneities.
        if (all(rules3) and ((all(rules4) and not all(rules5a))
                             or (not all(rules4) and not all(rules5b)))):
            error = ('Dissonant interval off the beat that is not '
                     'approached and left by step in bar '
                     + str(lowerNote.measureNumber) + ': '
                     + str(interval.Interval(lowerNote, upperNote).name)
                     + '.')
            vlErrors.append(error)

        # Both notes start at the same time, both of them are tied over:
        # TODO ???

    # Check whether consecutive dissonances move in one direction.
    for vlq in VLQs:
        # Rules for finding consecutive dissonances:
        # (1a) Either both of the intervals are dissonant above the bass:
        rules1a = [duet.includesBass,
                   isVerticalDissonance(vlq.v1n1, vlq.v2n1),
                   isVerticalDissonance(vlq.v1n2, vlq.v2n2)]
        # (1b) Or both of the intervals are prohibited dissonances
        # between upper parts:
        rules1b = [not duet.includesBass,
                   isVerticalDissonance(vlq.v1n1, vlq.v2n1),
                   not isPermittedDissonanceBetweenUpper(vlq.v1n1,
                                                         vlq.v2n1),
                   isVerticalDissonance(vlq.v1n2, vlq.v2n2),
                   not isPermittedDissonanceBetweenUpper(vlq.v1n2,
                                                         vlq.v2n2)]
        # (2a) Either the first voice is stationary and
        # the second voice moves in one direction:
        rules2a = [vlq.v1n1 == vlq.v1n2,
                   (vlq.v2n1.consecutions.leftDirection
                    == vlq.v2n2.consecutions.leftDirection),
                   (vlq.v2n1.consecutions.rightDirection
                    == vlq.v2n2.consecutions.rightDirection)]
        # (2b) Or the second voice is stationary and
        # the first voice moves in one direction:
        rules2b = [vlq.v2n1 == vlq.v2n2,
                   (vlq.v1n1.consecutions.leftDirection
                    == vlq.v1n2.consecutions.leftDirection),
                   (vlq.v1n1.consecutions.rightDirection
                    == vlq.v1n2.consecutions.rightDirection)]
        # (3) Must be in the same measure:
        rules3 = [vlq.v1n1.measureNumber == vlq.v1n2.measureNumber]
        # Evaluate the VLQ.
        if ((all(rules1a) or all(rules1b))
                and not (all(rules2a) or all(rules2b))
                and (all(rules3))):
            error = ('Consecutive dissonant intervals in bar '
                     + str(vlq.v1n1.measureNumber)
                     + ' are not approached and left '
                       'in the same direction.')
            vlErrors.append(error)

    # TODO Fix so that it works with higher species
    #   line that start with rests in the bass. ????

    # TODO Check fourth species control of dissonance.
    #  Check resolution of diss relative to onbeat note
    #  (which may move if not whole notes) to determine category of susp;
    #  this can be extracted from the vlq: e.g., v1n1,v2n1 and v1n2,v2n1.
    #  Separately check the consonance of the resolution in the
    #  vlq (v1n2, v2n2).
    #  Add rules for multiple parts.
    # TODO Add contiguous intervals to vlqs ?? xint1, xint2.


def checkFourthSpeciesControlOfDissonance(context, duet, VLQs):
    """
    Check the duet for conformity the rules that
    control dissonance in fourth species.
    """
    if duet.parts[0].species == 'fourth':
        speciesPart = 0
    elif duet.parts[1].species == 'fourth':
        speciesPart = 1

    for vPair in getVerticalPairs(duet):
        # Evaluate on- and offbeat intervals when one of the parts
        # is the bass.
        if duet.includesBass:
            # Look for onbeat note that is dissonant
            # and improperly treated.
            rules = [
                vPair[speciesPart].beat == 1.0,
                not isConsonanceAboveBass(vPair[1], vPair[0]),
                not vPair[speciesPart].consecutions.leftType == 'same',
                not vPair[speciesPart].consecutions.rightType == 'step'
            ]
            if all(rules):
                error = ('Dissonant interval on the beat that is '
                         'either not prepared or not resolved in bar '
                         + str(vPair[0].measureNumber) + ': '
                         + str(interval.Interval(vPair[0], vPair[1]).name)
                         + '.')
                vlErrors.append(error)
            # Look for second-species onbeat dissonance.
            rules = [vPair[speciesPart].beat == 1.0,
                     vPair[speciesPart].tie is None,
                     not isConsonanceAboveBass(vPair[1], vPair[0])]
            if all(rules):
                error = ('Dissonant interval on the beat that is not '
                         'permitted when fourth species is broken in bar '
                         + str(vPair[0].measureNumber) + ': '
                         + str(interval.Interval(vPair[1], vPair[0]).name)
                         + '.')
                vlErrors.append(error)
            # Look for offbeat note that is dissonant and tied over.
            rules = [vPair[speciesPart].beat > 1.0,
                     not isConsonanceAboveBass(vPair[1], vPair[0]),
                     vPair[0].tie is not None or vPair[1].tie is not None]
            if all(rules):
                error = ('Dissonant interval off the beat in bar '
                         + str(vPair[0].measureNumber) + ': '
                         + str(interval.Interval(vPair[1], vPair[0]).name)
                         + '.')
                vlErrors.append(error)
        # TODO Need to figure out rules for 3 or more parts.
        elif not duet.includesBass:
            pass

    # Determine whether breaking of species is permitted,
    # and, if so, whether proper.
    breakcount = 0
    earliestBreak = 4
    latestBreak = context.score.measures - 4
    for vlq in VLQs:
        # Look for vlq where second note in species line is not tied over.
        if speciesPart == 0:
            speciesNote = vlq.v1n2
        elif speciesPart == 1:
            speciesNote = vlq.v2n2
        if speciesNote.tie is None and speciesNote.beat > 1.0:
            if (not allowSecondSpeciesBreak
                    and speciesNote.measureNumber != context.score.measures - 1):
                error = ('Breaking of fourth species is allowed only '
                         'at the end and not in bars '
                         + str(speciesNote.measureNumber) + ' to '
                         + str(speciesNote.measureNumber + 1) + '.')
                vlErrors.append(error)
            elif (allowSecondSpeciesBreak
                  and speciesNote.measureNumber != context.score.measures - 1):
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
                             + ' to ' + str(speciesNote.measureNumber + 1)
                             + ' occurs too early.')
                    vlErrors.append(error)
                elif speciesNote.measureNumber > latestBreak:
                    error = ('Breaking of fourth species in bars '
                             + str(speciesNote.measureNumber)
                             + ' to ' + str(speciesNote.measureNumber + 1)
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
    validDissonances = ['m2', 'M2', 'A2', 'd4', 'P4', 'A4',
                        'A5', 'd5', 'A5', 'm7', 'd7', 'M7']

    # Function for distinguishing between intervals 9 and 2 in upper lines.
    def dissName(ivl):
        if (ivl.simpleName in ['m2', 'M2', 'A2']
                and ivl.name not in ['m2', 'M2', 'A2']):
            intervalName = interval.add([ivl.simpleName, 'P8']).name
        else:
            intervalName = ivl.simpleName
        return intervalName

    # Make list of dissonant syncopes and verify that each is permitted.
    syncopeList = {}
    for vlq in VLQs:
        if speciesPart == 0:
            if vlq.v1n1.tie:
                if vlq.v1n1.tie.type == 'stop':
                    if vlq.vIntervals[0].simpleName in validDissonances:
                        syncopeList[vlq.v1n1.measureNumber] = (
                                dissName(vlq.vIntervals[0])
                                + '-' + vlq.vIntervals[1].semiSimpleName[-1]
                        )
        elif speciesPart == 1:
            if vlq.v2n1.tie:
                if vlq.v2n1.tie.type == 'stop':
                    if vlq.vIntervals[0].simpleName in validDissonances:
                        syncopeList[vlq.v2n1.measureNumber] = (
                                vlq.vIntervals[0].simpleName
                                + '-' + vlq.vIntervals[1].semiSimpleName[-1]
                        )
    if speciesPart == 0:
        for bar in syncopeList:
            if (syncopeList[bar] not in strongSuspensions['upper']
                    and syncopeList[bar] not in intermediateSuspensions[
                        'upper']):
                error = ('The dissonant syncopation in bar '
                         + str(bar) + ' is not permitted: '
                         + str(syncopeList[bar]) + '.')
                vlErrors.append(error)
    elif speciesPart == 1:
        for bar in syncopeList:
            if (syncopeList[bar] not in strongSuspensions['lower']
                    and syncopeList[bar] not in intermediateSuspensions[
                        'lower']):
                error = ('The dissonant syncopation in bar '
                         + str(bar) + ' is not permitted: '
                         + str(syncopeList[bar]) + '.')
                vlErrors.append(error)
    # logger.debug(f'Syncopes list: {syncopeList}.')


def checkForbiddenMotionsOntoBeatWithoutSyncope(context, duet, vlq):
    """Check a voice-leading quartet for conformity with the rules that
    prohibit or restrict certain kinds of motion onto the beat:

       * similar motion to or from a unison
       * similar motion to an octave
       * similar motion to a fifth
       * parallel motion to unison, octave, or fifth
       * voice crossing, voice overlap, cross relation
    """
    # get the bass note in the second verticality of the vlq
    vlqBassNote = \
    context.parts[-1].measure(vlq.v1n2.measureNumber).getElementsByClass(
        'Note')[0]
    # check the types of forbidden motion
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
                 vlq.v1n2.measureNumber == context.score.measures,
                 vlq.v2n2.measureNumber == context.score.measures]
        if not all(rules):
            error = ('Forbidden similar motion to octave going into bar '
                     + str(vlq.v2n2.measureNumber) + '.')
            vlErrors.append(error)
    if isSimilarFifth(vlq):
        rules1 = [vlq.hIntervals[0].name in ['m2', 'M2']]
        rules2 = [vlq.v1n2.csd.value % 7 in [1, 4]]
        # If fifth in upper parts, compare with pitch of the
        # simultaneous bass note.
        rules3 = [not duet.includesBass,
                  vlq.v1n2.csd.value % 7 != vlqBassNote.csd.value % 7,
                  vlq.v2n2.csd.value % 7 != vlqBassNote.csd.value % 7]
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
        # Voice crossing can happen when both parts move or obliquely
        # Strict rule when the bass is involved.
        if duet.parts[0].parentID == len(context.parts) - 1 or duet.parts[
            1].parentID == len(context.parts) - 1:
            if vlq.v1n1.beatStrength > vlq.v1n2.beatStrength:
                error = f'Voice crossing in bar {vlq.v2n2.measureNumber}.'
            else:
                error = (f'Voice crossing going into bar '
                         f'{vlq.v2n2.measureNumber}.')
            vlErrors.append(error)
        else:
            if vlq.v1n1.beatStrength > vlq.v1n2.beatStrength:
                alert = (f'ALERT: Upper voices cross in bar '
                         f'{vlq.v2n2.measureNumber}.')
            else:
                alert = (f'ALERT: Upper voices cross going into bar '
                         f'{vlq.v2n2.measureNumber}.')
            vlErrors.append(alert)
    if isVoiceOverlap(vlq):
        # Voice overlap can only happen with both parts move
        if duet.parts[0].parentID == len(context.parts) - 1 or duet.parts[
            1].parentID == len(context.parts) - 1:
            error = ('Voice overlap going into bar '
                     + str(vlq.v2n2.measureNumber) + ".")
            vlErrors.append(error)
        else:
            alert = ('ALERT: Upper voices overlap going into bar '
                     + str(vlq.v2n2.measureNumber) + '.')
            vlErrors.append(alert)
    if isCrossRelation(vlq):
        # TODO add permissions for second (and third?) species, ITT, p. 115
        if len(context.parts) < 3:
            cond1 = [duet.parts[0].species == 'second',
                     isDiatonicStep(vlq.v1n1, vlq.v1n2)]
            cond2 = [duet.parts[1].species == 'second',
                     isDiatonicStep(vlq.v2n1, vlq.v2n2)]
            if not (all(cond1) or all(cond2)):
                error = ('Cross relation going into bar '
                         + str(vlq.v2n2.measureNumber) + '.')
                vlErrors.append(error)
        else:
            # Test for step motion in another part.
            # TODO TEST TEST TEST
            crossStep = False
            for part in context.parts:
                if (part != duet.parts[0]
                        and part != duet.parts[1]):
                    vlqOtherNote1 = \
                    part.measure(vlq.v1n1.measureNumber).getElementsByClass(
                        'Note')[0]
                    vlqOtherNote2 = \
                    part.measure(vlq.v1n2.measureNumber).getElementsByClass(
                        'Note')[0]
                    if vlqOtherNote1.csd.value - vlqOtherNote2.csd.value == 1:
                        crossStep = True
                        break
            if not crossStep:
                error = ('Cross relation going into bar '
                         + str(vlq.v2n2.measureNumber) + '.')
                vlErrors.append(error)


def checkFirstSpeciesForbiddenMotions(context, duet, VLQs):
    """Check the forbidden forms of motion for a duet in first species.
    Essentially: :py:func:`forbiddenMotionsOntoBeatWithoutSyncope` and
    :py:funct:`checkFirstSpeciesNonconsecutiveParallels`.
    """
    for vlq in VLQs:
        checkForbiddenMotionsOntoBeatWithoutSyncope(context, duet, vlq)
    checkFirstSpeciesNonconsecutiveParallels(context, duet)


def checkSecondSpeciesForbiddenMotions(context, duet, VLQs):
    """Check the forbidden forms of motion for a duet in second species.
    Use :py:func:`forbiddenMotionsOntoBeatWithoutSyncope`
    to check motion across the barline and then check motion from beat to beat.
    """
    # Check motion across the barline.
    for vlq in VLQs:
        checkForbiddenMotionsOntoBeatWithoutSyncope(context, duet, vlq)

    # Check motion from beat to beat.
    vlqOnbeatList = getOnbeatVLQs(duet)
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
            localNotes = [note for note in context.parts[vSpeciesPartNum].notes
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


def checkThirdSpeciesForbiddenMotions(context, duet, VLQs):
    """Check the forbidden forms of motion for a duet in
    third species.  Use :py:func:`forbiddenMotionsOntoBeatWithoutSyncope`
    to check motion across the barline and then check motion from beat
    to beat, from off the beat to next but not immediately following
    on the beat.
    """
    # TODO: Finish this script.

    def checkMotionsOntoBeat():
        # Check motion across the barline.
        for vlq in VLQs:
            # Check motion across the barline, as in first and second species.
            if vlq.v1n2.beat == 1.0 and vlq.v2n2.beat == 1.0:
                checkForbiddenMotionsOntoBeatWithoutSyncope(context, duet, vlq)
            else:
                # Check motion within the bar.
                if isVoiceCrossing(vlq):
                    # Strict rule when the bass is involved.
                    if duet.includesBass:
                        error = ('Voice crossing in bar '
                                 + str(vlq.v2n2.measureNumber) + '.')
                        vlErrors.append(error)
                    else:
                        alert = ('ALERT: Upper voices cross in bar '
                                 + str(vlq.v2n2.measureNumber) + '.')
                        vlErrors.append(alert)

    def checkMotionsBeatToBeat():
        # Check motion from beat to beat.
        for vlq in getOnbeatVLQs(duet):
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
                    vSpeciesPartNum = vlq.v1n1.getContextByClass(
                        'Part').partNum
                elif vlq.v2n1.getContextByClass('Part').species == 'third':
                    vSpeciesNote1 = vlq.v2n1
                    vSpeciesNote2 = vlq.v2n2
                    vCantusNote1 = vlq.v1n1
                    vSpeciesPartNum = vlq.v2n1.getContextByClass(
                        'Part').partNum
                localSpeciesMeasure = context.parts[vSpeciesPartNum].measures(
                    vCantusNote1.measureNumber, vCantusNote1.measureNumber)
                localNotes = localSpeciesMeasure.getElementsByClass('Measure')[
                    0].notes
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
        vlqNonconsecutivesList = getNonconsecutiveOffbeatToOnbeatVLQs(duet)
        for vlq in vlqNonconsecutivesList:
            if isParallelUnison(vlq):
                error = ('Forbidden parallel motion to unison from bar '
                         + str(vlq.v1n1.measureNumber) + ' to bar '
                         + str(vlq.v1n2.measureNumber) + '.')
                vlErrors.append(error)
            if isParallelOctave(vlq):
                parDirection = interval.Interval(vlq.v1n1, vlq.v1n2).direction
                if vlq.v1n1.getContextByClass('Part').species == 'third':
                    # vSpeciesNote1 = vlq.v1n1
                    vSpeciesNote2 = vlq.v1n2
                    vCantusNote1 = vlq.v2n1
                    vSpeciesPartNum = vlq.v1n1.getContextByClass(
                        'Part').partNum
                elif vlq.v2n1.getContextByClass('Part').species == 'third':
                    # vSpeciesNote1 = vlq.v2n1
                    vSpeciesNote2 = vlq.v2n2
                    vCantusNote1 = vlq.v1n1
                    vSpeciesPartNum = vlq.v2n1.getContextByClass(
                        'Part').partNum
                # Make a list of notes in the species line that are
                # simultaneous with the first cantus tone.
                localSpeciesMeasure = context.parts[vSpeciesPartNum].measures(
                    vCantusNote1.measureNumber, vCantusNote1.measureNumber)
                localNotes = localSpeciesMeasure.getElementsByClass('Measure')[
                    0].notes
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


def checkFourthSpeciesForbiddenMotions(context, duet, VLQs):
    """Check the forbidden forms of motion for a duet in fourth
    species. Mostly limited to looking for parallel unisons and octaves
    in consecutive meausures.
    Use :py:func:`forbiddenMotionsOntoBeatWithoutSyncope`
    to check motion across the
    barline whenever the syncopations are broken.
    """
    if duet.parts[0].species == 'fourth':
        speciesPart = 0
    elif duet.parts[1].species == 'fourth':
        speciesPart = 1
    # gather the simultaneities by location
    vPairsOnbeat = []
    vPairsOnbeatDict = {}
    vPairsOffbeat = []
    # get the lists of onbeat  and offbeat VPs
    for vPair in getVerticalPairs(duet):
        if vPair is not None:
            # Evaluate offbeat intervals when one of the parts is the bass.
            if vPair[speciesPart].beat == 1.0:
                vPairsOnbeat.append(vPair)
                vPairsOnbeatDict[vPair[speciesPart].measureNumber] = vPair
            else:
                vPairsOffbeat.append(vPair)
    # make lists of VLQs for each
    vlqsOffbeat = makeVLQFromVPairList(vPairsOffbeat)
    vlqsOnbeat = makeVLQFromVPairList(vPairsOnbeat)
    # evaluate the offbeat VLQs
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
    # evaluate the onbeat VLQs
    for vlq in vlqsOnbeat:
        if isParallelUnison(vlq):
            error = ('Forbidden parallel motion to unison going into bar '
                     + str(vlq.v2n2.measureNumber))
            vlErrors.append(error)
    # Check second-species motion across barlines,
    # looking at vlq with initial untied offbeat note.
    for vlq in VLQs:
        if speciesPart == 0:
            speciesNote = vlq.v1n1
        elif speciesPart == 1:
            speciesNote = vlq.v2n1
        if speciesNote.tie is None and speciesNote.beat > 1.0:
            checkForbiddenMotionsOntoBeatWithoutSyncope(context, duet, vlq)
    # check second-species motion across final barline
    for vlq in vlqsOnbeat:
        if (isParallelOctave(vlq)
                and vlq.v1n2.tie is None
                and vlq.v2n2.tie is None):
            error = ('Forbidden parallel motion to octave going into bar '
                     + str(vlq.v2n2.measureNumber))
            vlErrors.append(error)


def checkFirstSpeciesNonconsecutiveParallels(context, duet):
    """Check for restrictions on nonconsecutive parallel unisons
    and octaves in first species."""
    vPairList = getVerticalPairs(duet)
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
                          or vlq1.v1n2.csd.value % 7 == vpt[2][
                              1].csd.value % 7):
                        pass
                    else:
                        bar1 = vpt[0][0].measureNumber
                        bar2 = vpt[2][0].measureNumber
                        error = (
                            f'Non-consecutive parallel {p_int} in bars {bar1}'
                            f' and {bar2}.')
                        vlErrors.append(error)


def checkSecondSpeciesNonconsecutiveUnisons(duet):
    """Check for restrictions on nonconsecutive parallel unisons."""
    vPairList = getVerticalPairs(duet)
    if duet.parts[0].species == 'second':
        speciesPart = 0
    elif duet.parts[1].species == 'second':
        speciesPart = 1
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


def checkSecondSpeciesNonconsecutiveOctaves(duet):
    """Check for restrictions on nonconsecutive parallel octaves."""
    vPairList = getVerticalPairs(duet)
    if duet.parts[0].species == 'second':
        speciesPart = 0
    elif duet.parts[1].species == 'second':
        speciesPart = 1
    else:
        return
    firstOctave = None
    for vPair in vPairList:
        if firstOctave:
            if (interval.Interval(vPair[0], vPair[1]).name == 'P8'
                    and vPair[speciesPart].beat > 1.0
                    and vPair[speciesPart].measureNumber - 1
                    == firstOctave[0]):
                if interval.Interval(firstOctave[1][speciesPart],
                                     vPair[speciesPart]).isDiatonicStep:
                    if (vPair[speciesPart].consecutions.leftDirection
                            == firstOctave[1][
                                speciesPart].consecutions.leftDirection):
                        error = ('Offbeat octaves in bars ' + str(
                            firstOctave[0])
                                 + ' and '
                                 + str(vPair[speciesPart].measureNumber))
                        vlErrors.append(error)
                elif interval.Interval(firstOctave[1][speciesPart],
                                       vPair[speciesPart]).generic.isSkip:
                    if (vPair[speciesPart].consecutions.leftDirection
                            != firstOctave[1][
                                speciesPart].consecutions.leftDirection
                            or firstOctave[1][
                                speciesPart].consecutions.rightInterval.isDiatonicStep):
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


def checkConsecutions(context):
    """Check the intervals between consecutive notes. If the line is
    in second or third species, confirm that there are no direct
    repetitions. If the line is in fourth species,
    confirm that the pitches of tied-over notes match and
    that there are no direct repetitions.
    """
    for part in context.parts:
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
                                 'into bar ' + str(n.measureNumber + 1) + '.')
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


def checkFourthLeapsInBass(context):
    """Check fourth leaps in the bass to ensure that there is no
    implication of a six-four chord during the meausure in which
    the lower note of the fourth occurs.
    """
    # find all the consecutive fourths in the bass line
    bassFourthsList = getFourthLeapsInBassDict(context)
    for bassFourth in bassFourthsList:
        bn1 = bassFourth[0]
        bn2 = bassFourth[1]
        bnPartNum = len(context.parts) - 1
        bn1Meas = bn1.measureNumber
        bn2Meas = bn2.measureNumber
        bn1Start = context.parts[bnPartNum].flatten().notes[bn1.index].offset
        bn2Start = context.parts[bnPartNum].flatten().notes[bn2.index].offset
        bn1End = bn1Start + bn1.quarterLength
        bn2End = bn2Start + bn2.quarterLength
        # Implication is true until proven otherwise.
        impliedSixFour = True

        # Leaps of a fourth within a measure.
        if bn1Meas == bn2Meas:
            fourthBass = interval.getAbsoluteLowerNote(bn1, bn2)
            for n in context.parts[bnPartNum].measure(bn1Meas).notes:
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
        elif bn1Meas == bn2Meas - 1:
            # Check upper parts for note that denies the implication.
            for part in context.parts[0:bnPartNum]:
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
                        offsetStart=bn1Start - bar.offset,
                        offsetEnd=bn1End - bar.offset,
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
                        offsetStart=bn2Start - bar.offset,
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
                                  n.offset + n.quarterLength
                                  == context.score.measure(
                                      bn1Meas).quarterLength]
                        if all(rules1) and any(rules2):
                            impliedSixFour = False
                            break

                    # rules for third species
                    elif len(barseg1) > 2:
                        # first in bar or last in bar (hence
                        # contiguous with bn2)
                        rules3a = [n.offset == 0.0,
                                   n.offset + n.quarterLength
                                   == context.score.measure(
                                       bn1Meas).quarterLength]
                        # not first or last in bar and no step follows
                        stepfollows = [x for x in barseg1
                                       if x.offset > n.offset
                                       and isConsonanceAboveBass(bn1, x)
                                       and isDiatonicStep(x, n)]
                        rules3b = [n.offset > 0.0,
                                   n.offset + n.quarterLength
                                   < context.score.measure(
                                       bn1Meas).quarterLength,
                                   stepfollows == []]

                        if all(rules1) and (any(rules3a) or all(rules3b)):
                            impliedSixFour = False
                            break

                    # rules for fourth species
                    elif len(barseg1) == 2 and barseg1[1].tie:
                        # TODO verify that no additional rule is needed
                        rules4 = []  # [n.tie.type == 'start']
                        if all(rules1) and all(rules4):
                            impliedSixFour = False
                            break

                    # if fourth species is broken
                    elif len(barseg1) == 2 and not barseg1[1].tie:
                        # first in bar, leapt to, or last in bar
                        # (hence contiguous with bn2)
                        rules2 = [n.offset == 0.0,
                                  n.consecutions.leftType == 'skip',
                                  n.offset + n.quarterLength
                                  == context.score.measure(
                                      bn1Meas).quarterLength]
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
                        rules4 = []  # [n.tie.type == 'start']
                        if all(rules1) and all(rules4):
                            impliedSixFour = False
                            break

            # Check third species bass part for note that
            # denies the implication.
            if context.parts[bnPartNum].species == 'third':
                bn1Measure = bn1.measureNumber
                # Get the notes in the bar of the first bass note.
                bassnotes = context.parts[bnPartNum].flatten().notes
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
                     + str(bn1Meas) + '-' + str(bn2Meas) + '.')
            vlErrors.append(error)


def checkFirstSpeciesSonority(context, duet):
    onBeatIvls = getOnbeatIntervals(duet)
    imperfectIvls = []
    fifthsAndOctaves = []
    unisons = []
    compounds = []
    for ivl in onBeatIvls:
        if ivl.simpleName in ['m3', 'M3', 'm6', 'M6']:
            imperfectIvls.append(ivl)
        if ivl.semiSimpleName != ivl.name:
            compounds.append(ivl)
    for ivl in onBeatIvls[1:-1]:
        if ivl.semiSimpleName in ['P5', 'P8']:
            fifthsAndOctaves.append(ivl)
        if ivl.name in ['P1']:
            unisons.append(ivl)
    imperfectScore = len(imperfectIvls) / len(onBeatIvls)
    # count the number of imperfect intervals simpleName in [m3, M3, m6, M6]
    if imperfectScore < 0.6:
        advice = (f'* Use more imperfect intervals.' )
        vlAdvice.append(advice)
    # count the number of nonterminal fifths and octaves and
    if fifthsAndOctaves:
        advice = (f'* There is a least one perfect fifth or octave in the '
                  f'\n\tmiddle of the composition. Ensure that the emphasis '
                  f'\n\tprovided by this interval helps to stress a '
                  f'\n\tpitch that belongs to the background structure.')
        vlAdvice.append(advice)
    # identify the location of any nonfinal unisons and advise to reconsider
    if unisons:
        advice = (f'* There is at least one unison in the middle of the '
                  f'\n\tcomposition. Consider finding a solution that avoids '
                  f'\n\tunisons except in the first and last measures.')
        vlAdvice.append(advice)
    # count the number of nonsimple intervals and give advice
    compoundScore = len(compounds) / len(onBeatIvls)
    if 0.9 >= compoundScore > 0.5:
        advice = (f'* There are many compound intervals. Avoid intervals '
                  f'\n\tlarger than a tenth.')
        vlAdvice.append(advice)
    elif compoundScore > 0.9:
        advice = (f'* Almost all sonorities are compound intervals. Rewrite'
                  f'\n\tso that most intervals are not larger than a tenth.')
        vlAdvice.append(advice)


def checkThreePartOnbeatSonority(context):
    pass


# -----------------------------------------------------------------------------
# UTILITY SCRIPTS
# -----------------------------------------------------------------------------


# utility function for finding pairs of parts
def getAllPartNumPairs(score):
    """
    Assemble a list of the pairwise combinations of parts in a score.
    Adopted from music21's theory analyzer
    """
    partNumPairs = []
    numParts = len(score.parts)
    for partNum1 in range(numParts - 1):
        for partNum2 in range(partNum1 + 1, numParts):
            partNumPairs.append((partNum1, partNum2))
    return partNumPairs


def getOffsetList(score):
    """
    Get a list of note/rest offsets for all event initiations in a score.
    Accepts a stream as input: duet, context.score
    Use as input to building the context dictionary of verticals
    """
    tsTree = score.asTimespans(classList=(note.Note,note.Rest))
    offsetList = [os for os in tsTree.allOffsets()]
    return offsetList


def getOnbeatOffsetList(score):
    """
    Get a list of offsets for all downbeats in a score.
    Accepts a stream as input: duet, context.score.
    """
    measureOffsetsDict = score.measureOffsetMap()
    downbeatOffsetList = []
    for offset in measureOffsetsDict:
        downbeatOffsetList.append(offset)
    # Get the start/stop offsets for each measure.
    return downbeatOffsetList


def getOffbeatOffsetList(score):
    """
    Get a list of offsets for all offbeats in a score.
    Accepts a stream as input: duet, context.score.
    """
    offsetList = getOffsetList(score)
    downbeatOffsetList = getOnbeatOffsetList(score)
    offbeatOffsetList = [offset for offset in offsetList if offset not in downbeatOffsetList]
    return offbeatOffsetList


def getOnbeatIntervals(duet):
    """
    Extract an ordered list of onbeat intervals in the duet.
    """
    vertPairs = getVerticalPairs(duet)
    intervalList = []
    # get interval of onbeat vertical pair
    for vp in vertPairs:
        if vp[0].beatStrength == 1.0 and vp[1].beatStrength == 1.0:
            intervalList.append(interval.Interval(vp[1],vp[0]))
    return intervalList


def getOffbeatIntervals(duet):
    """
    Extract an ordered list of offbeat intervals in the duet.
    """
    vertPairs = getVerticalPairs(duet)
    intervalList = []
    # get interval of offbeat vertical pair
    for vp in vertPairs:
        if vp[0].beatStrength > 1.0 or vp[1].beatStrength > 1.0:
            intervalList.append(interval.Interval(vp[1],vp[0]))
    return intervalList


# TODO needs a lot of work
def getGenericKlangs(score):
    """Extract a list of generic intervals above the bass for a score with
    any number of parts"""
    contentDicts = getAllVerticalContentDictionaries(score)
    upperParts = range(0, (len(score.parts)-1))
    bassPartNum = score.parts[-1].partNum
    klangList = []
    for offset in contentDicts:
        contentDict = contentDicts[offset]
        intervals = []
        for partNum in upperParts:
            nUpper = contentDict[partNum]
            nBass = contentDict[bassPartNum]
            intervals.append(interval.Interval(nBass, nUpper).generic.semiSimpleUndirected)
        klangList.append(intervals)
    return klangList


def getVerticalityContentDictFromDuet(duet, offset):
    """
    Assume that the parts in a duet contain a single note or rest each
    at any given offset. Get the content of each part at the offset and
    construct a content dictionary: the keys are part numbers in the duet
    and the values are notes (rests).
    """
    contentDict = {}
    partCount = 2
    partNum = 0
    while partNum < partCount:
        partNotes = [el for el in
                     duet.parts[
                         partNum].flatten().getElementsByOffset(
                         offset, mustBeginInSpan=False, classList=[note.Note, note.Rest])]
        # assume that there's just one note or rest to a part here
        contentDict[partNum] = partNotes[0]
        partNum += 1
    return contentDict


# NOT CURRENTLY IN USE, MAY COME IN HANDY FOR SONORITY CHECKING
def getVerticalContentDictionariesList(score, offsets='all'):
    """
    Generate an offset list for a score, then construct a content dictionary
    for the parts at every offset: the keys are part numbers in the duet
    and the values are notes (rests). Accepts as input: duet, context.score.
    """
    contentDictList = {}
    if offsets == 'all':
        offsetList = getOffsetList(score)
    elif offsets == 'on':
        offsetList = getOnbeatOffsetList(score)
    elif offsets == 'off':
        offsetList = getOffbeatOffsetList(score)
    for offset in offsetList:
        partCount = len(score.parts)
        partNum = 0
        contentDict = {}
        while partNum < partCount:
            partNotes = [el for el in
                         score.parts[
                             partNum].flatten().getElementsByOffset(
                             offset, mustBeginInSpan=False, classList=[
                                 note.Note, note.Rest])]
            # assume that there's just one note or rest to a part here
            contentDict[partNum] = partNotes[0]
            partNum += 1
            # key = common.opFrac(offset)
        contentDictList[offset] = contentDict
    return contentDictList


def getVerticalPairs(duet):
    """
    Generate an offset list for the duet and then construct a list of all
    the simultaneities (vertical pairs of notes) occurring
    between the parts of the duet.
    """
    vPairList = []
    offsetList = getOffsetList(duet)
    for offset in offsetList:
        nUpper = getVerticalityContentDictFromDuet(duet, offset)[0]
        nLower = getVerticalityContentDictFromDuet(duet, offset)[1]
        if nUpper is None or nLower is None:
            vPair = None
        elif not nUpper.isNote or not nLower.isNote:
            vPair = None
        else:
            vPair = (nUpper, nLower)
        if vPair:
            vPairList.append(vPair)
    return vPairList


def getAllVLQsFromDuet(duet):
    """
    Generate an offset list for the duet, make a pairwise list of offsets,
    and then construct a list of all the
    :class:`~music21.voiceLeading.VoiceLeadingQuartet`
    objects in the duet.
    """
    allVLQs = []
    # extract the relevant parts from the score
    part1 = duet.parts[0]
    part2 = duet.parts[1]
    # get offsets of verticals
    offsetList = getOffsetList(duet)
    # make VLQs
    for i in range(len(offsetList) - 1):
        # get the pitches and offsets of the verticalities
        # at index i and the following one
        os1 = offsetList[i]
        os2 = offsetList[i+1]
        # check that there are no rests before making the VLQ
        if (part1.flatten().getElementAtOrBefore(os1, classList=[note.Note, note.Rest]).isNote and
                part1.flatten().getElementAtOrBefore(
                    os2, classList=[note.Note, note.Rest]).isNote and
                part2.flatten().getElementAtOrBefore(
                    os1, classList=[note.Note, note.Rest]).isNote and
                part2.flatten().getElementAtOrBefore(
                    os2, classList=[note.Note, note.Rest]).isNote):
            v1n1 = part1.flatten().getElementAtOrBefore(os1, classList=[note.Note])
            v1n2 = part1.flatten().getElementAtOrBefore(os2, classList=[note.Note])
            v2n1 = part2.flatten().getElementAtOrBefore(os1, classList=[note.Note])
            v2n2 = part2.flatten().getElementAtOrBefore(os2, classList=[note.Note])
            a = voiceLeading.VoiceLeadingQuartet(v1n1, v1n2, v2n1, v2n2)
            allVLQs.append(a)
    return allVLQs


def getOnbeatVLQs(duet):
    """
    Generate an offset list of downbeats in the duet, make a pairwise list
    from it, and then construct a list of
    :class:`~music21.voiceLeading.VoiceLeadingQuartet` objects.
    """
    allVLQs = []
    # extract the relevant parts from the score
    part1 = duet.parts[0]
    part2 = duet.parts[1]
    # get onbeat offsets of verticals
    offsetList = getOnbeatOffsetList(duet)
    # make VLQs
    for i in range(len(offsetList) - 1):
        # get the pitches and offsets of the verticalities at index i and the following one
        os1 = offsetList[i]
        os2 = offsetList[i+1]
        # check that there are no rests before making the VLQ
        if (part1.flatten().getElementAtOrBefore(os1, classList=[note.Note, note.Rest]).isNote and
                part1.flatten().getElementAtOrBefore(
                    os2, classList=[note.Note, note.Rest]).isNote and
                part2.flatten().getElementAtOrBefore(
                    os1, classList=[note.Note, note.Rest]).isNote and
                part2.flatten().getElementAtOrBefore(
                    os2, classList=[note.Note, note.Rest]).isNote):
            v1n1 = part1.flatten().getElementAtOrBefore(os1, classList=[note.Note])
            v1n2 = part1.flatten().getElementAtOrBefore(os2, classList=[note.Note])
            v2n1 = part2.flatten().getElementAtOrBefore(os1, classList=[note.Note])
            v2n2 = part2.flatten().getElementAtOrBefore(os2, classList=[note.Note])
            a = voiceLeading.VoiceLeadingQuartet(v1n1, v1n2, v2n1, v2n2)
            allVLQs.append(a)
    return allVLQs


def getNonconsecutiveOffbeatToOnbeatVLQs(duet):
    """
    Generate an offset list for the duet in which the first offset
    is off the beat and the second is on the next downbeat,
    and then construct a list of
    :class:`~music21.voiceLeading.VoiceLeadingQuartet` objects.
    """
    allVLQs = []
    # extract the relevant parts from the score
    part1 = duet.parts[0]
    part2 = duet.parts[1]
    # get offsets of verticals
    offsetList = getOffsetList(duet)
    # make VLQs
    for i in range(len(offsetList) - 1):
        # get the pitches and offsets of the verticalities at index i
        # if i is offbeat, look at next vert j
        # if j is onbeat, pass
        # if j is offbeat, look ahead to find next onbeat vert and make vlq
        os1 = offsetList[i]
        os2 = offsetList[i+1]
        # check that there are no rests before proceeding
        if (part1.flatten().getElementAtOrBefore(os1, classList=[note.Note, note.Rest]).isNote and
                part1.flatten().getElementAtOrBefore(
                    os2, classList=[note.Note, note.Rest]).isNote and
                part2.flatten().getElementAtOrBefore(
                    os1, classList=[note.Note, note.Rest]).isNote and
                part2.flatten().getElementAtOrBefore(
                    os2, classList=[note.Note, note.Rest]).isNote):
            if (part1.flatten().getElementAtOrBefore(os1).beat > 1.0 or
                    part2.flatten().getElementAtOrBefore(
                        os1, classList=[note.Note]).beat > 1.0):
                if not (part1.flatten().getElementAtOrBefore(
                        os2, classList=[note.Note]).beat == 1.0 and
                        part2.flatten().getElementAtOrBefore(
                            os2, classList=[note.Note]).beat == 1.0):
                    nextOnbeat = False
                    n = 2
                    while nextOnbeat == False:
                        os2 = offsetList[i+n]
                        if (part1.flatten().getElementAtOrBefore(
                                os2, classList=[note.Note]).beat == 1.0 and
                                part2.flatten().getElementAtOrBefore(
                                    os2, classList=[note.Note]).beat == 1.0):
                            nextOnbeat = True
                            v1n1 = part1.flatten().getElementAtOrBefore(
                                os1, classList=[note.Note])
                            v1n2 = part1.flatten().getElementAtOrBefore(
                                os2, classList=[note.Note])
                            v2n1 = part2.flatten().getElementAtOrBefore(
                                os1, classList=[note.Note])
                            v2n2 = part2.flatten().getElementAtOrBefore(
                                os2, classList=[note.Note])
                            a = voiceLeading.VoiceLeadingQuartet(v1n1, v1n2,
                                                                 v2n1, v2n2)
                            allVLQs.append(a)
                        else:
                            n += 1
        else:
            pass

    return allVLQs


def makeVLQFromVPairList(vPairList):
    """
    Given a list of simultaneous note pairs, create a voice-leading
    quartet for each consecutive pair of pairs and return the list of VLQs.
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


def makeVLQfromVertPairs(vpair1, vpair2):
    """
    Given a pair of simultaneous note pairs, create a voice-leading
    quartet.
    """
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


def getFourthLeapsInBassDict(context):
    """
    Identify P4 intervals in the bass part and make a list of the note pairs.
    """
    bassNotes = [note for note in context.parts[-1].flatten().notes]
    bassPairs = pairwise(bassNotes)
    bassFourthsList = []
    for pair in bassPairs:
        if interval.Interval(pair[0], pair[1]).name == "P4":
            fourthNotes = [pair[0], pair[1]]
            bassFourthsList.append(fourthNotes)
    return bassFourthsList


# -----------------------------------------------------------------------------
# LIBRARY OF METHODS FOR EVALUTING VOICE LEADING ATOMS
# -----------------------------------------------------------------------------

# Methods for note pairs


def isConsonanceAboveBass(b, u):
    """
    Input two notes with pitch, a bass note and an upper note, and
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
    """
    Input two notes with pitch, a bass note and an upper note,
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
    """
    Input two notes with pitch, two upper-line notes, and determine
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
    """
    Input two notes with pitch, two upper-line notes, and determine
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
    """
    Input two notes, from any context, and determine whether
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
    """
    Input two notes, from any context, and determine whether
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
    """
    Input two simultaneous notes with pitch and determine whether
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
    """
    Input two simultaneous notes with pitch and determine whether
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
    """
    Input two simultaneous notes with pitch and determine whether
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
    """
    Input two notes with pitch and determine whether
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
    """
    Input two notes with pitch and determine whether
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
    """
    Input two notes with pitch and determine whether
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
    """
    Input a VLQ and determine whether there is similar motion to a unison.
    """
    rules = [vlq.similarMotion(),
             vlq.vIntervals[1] != vlq.vIntervals[0],
             vlq.vIntervals[1].name == 'P1']
    if all(rules):
        return True
    else:
        return False


def isSimilarFromUnison(vlq):
    """
    Input a VLQ and determine whether there is similar motion from a unison.
    """
    rules = [vlq.similarMotion(),
             vlq.vIntervals[1] != vlq.vIntervals[0],
             vlq.vIntervals[0].name == 'P1']
    if all(rules):
        return True
    else:
        return False


def isSimilarFifth(vlq):
    """
    Input a VLQ and determine whether there is similar motion to
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
    """
    Input a VLQ and determine whether there is similar motion to
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
    """
    Input a VLQ and determine whether there is parallel motion
    from one unison to another.
    """
    rules = [vlq.parallelMotion(),
             vlq.vIntervals[1].name in ['P1']]
    if all(rules):
        return True
    else:
        return False


def isParallelFifth(vlq):
    """
    Input a VLQ and determine whether there is parallel motion
    to a perfect fifth (the first fifth need not be perfect).
    """
    rules = [vlq.parallelMotion(),
             vlq.vIntervals[1].simpleName == 'P5']
    if all(rules):
        return True
    else:
        return False


def isParallelOctave(vlq):
    """
    Input a VLQ and determine whether there is parallel motion
    from one octave (simple or compound) to another.
    """
    rules = [vlq.parallelMotion(),
             vlq.vIntervals[1].name in ['P8', 'P15', 'P22']]
    if all(rules):
        return True
    else:
        return False


def isVoiceOverlap(vlq):
    """
    Input a VLQ and determine whether the voices overlap:
     v1n1 >= v2n1 and v1n2 >= v2n2, and either v1n2 < v2n1 or v2n2 > v1n1.
    """
    # parts stay in the proper registral position
    rules1 = [vlq.v1n1.pitch >= vlq.v2n1.pitch,
              vlq.v1n2.pitch >= vlq.v2n2.pitch]
    # then one part moves beyond where the other was
    rules2 = [vlq.v1n2.pitch < vlq.v2n1.pitch,
              vlq.v2n2.pitch > vlq.v1n1.pitch]
    if all(rules1) and any(rules2):
        return True
    else:
        return False


def isVoiceCrossing(vlq):
    """
    Input a VLQ and determine whether
    the voices cross: v1n1 >= v2n1, and v1n2 < v2n2.
    """
    # parts start out in the proper registral position
    rules1 = [vlq.v1n1.pitch >= vlq.v2n1.pitch]
    # then switch
    rules2 = [vlq.v1n2.pitch < vlq.v2n2.pitch]
    if all(rules1) and all(rules2):
        return True
    else:
        return False


def isCrossRelation(vlq):
    """
    Input a VLQ and determine whether the there is a cross relation.
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
    """
    Input a VLQ and determine whether either of the pitches in the first
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

    def test_checkFourthSpeciesControlOfDissonance(self):
        pass

    def test_checkForbiddenMotionsOntoBeatWithoutSyncope(self):
        pass

    def test_checkFirstSpeciesForbiddenMotions(self):
        pass

    def test_checkSecondSpeciesForbiddenMotions(self):
        pass

    def test_checkThirdSpeciesForbiddenMotions(self):
        pass

    def test_checkFourthSpeciesForbiddenMotions(self):
        pass

    def test_checkSecondSpeciesNonconsecutiveUnisons(self):
        pass

    def test_checkSecondSpeciesNonconsecutiveOctaves(self):
        pass

    def test_checkFourthLeapsInBass(self):
        pass

    def test_getAllPartNumPairs(self):
        pass

    def test_getVerticalitiesFromDuet(self):
        pass

    def test_getVerticalityContentDictFromDuet(self):
        pass

    def test_getAllVerticalitiesContentDictionary(self):
        pass

    def test_getVerticalPairs(self):
        pass

    def test_getAllVLQsFromDuet(self):
        pass

    def test_getOnbeatVLQs(self):
        pass

    def test_getNonconsecutiveOffbeatToOnbeatVLQs(self):
        pass

    def test_makeVLQFromVPairList(self):
        pass

    def test_makeVLQsFromVertPair(self):
        pass

    def test_getFourthLeapsInBassDict(self):
        pass


# -----------------------------------------------------------------------------


if __name__ == '__main__':
    unittest.main()

# -----------------------------------------------------------------------------
# eof
