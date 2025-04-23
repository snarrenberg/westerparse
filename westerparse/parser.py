# -----------------------------------------------------------------------------
# Name:         parser.py
# Purpose:      Framework for analyzing the syntactic structure
#               of simple tonal lines
#
# Author:       Robert Snarrenberg
# Copyright:    (c) 2025 by Robert Snarrenberg
# License:      BSD, see license.txt
# -----------------------------------------------------------------------------
"""
Parser
======

A transition-based dependency parser. The WesterParse parser
analyzes the syntax of a rhythmically simple melodic line
and produces a set of valid interpretations.

Procedure:

#. Accept a part from a context.
#. Infer the possible line type(s) if not given in advance.
#. Parse the part for each possible line type.
#. Return a set of parses and errors.

The machinery consists of a buffer, a stack, and a scanner.
At initialization, the notes of the line are read into the buffer.
The scanner then shifts notes onto the stack one by one. With each
shift, the transition is evaluated in light of the previously analyzed
line.  The new note may be evaluated as (a) dependent upon an earlier note,
(b) extending a dependency from an earlier note, (c) resolving
an earlier note, or (d) independent.
As the scanning proceeds, the parser maintains lists of
open heads, open transitions, and syntactic units (arcs). These lists
shrink and grow as the interpretive process unfolds. When an arc is
formed (e.g., a passing or neighboring motion), a tuple of note positions
is placed in the list of arcs.  Meanwhile, dependent elements within the
arc are removed from the list of open transitions, but structural heads
are retained in the list of open heads for subsequent attachment.
The parser has a limited ability to
backtrack and reinterpret segments of a line.

The first stage of parsing ends when the buffer is exhausted.
Interpretation then continues by line type.

The parser compiles lists of all the valid interpretations.
The parser also records errors that arise.
"""
import itertools
import copy
import logging
import unittest

from music21 import *

from westerparse.utilities import pairwise, shiftBuffer, shiftStack
from westerparse import arc

# -----------------------------------------------------------------------------
# MODULE VARIABLES
# -----------------------------------------------------------------------------

# variables set by user
selectPreferredParses = False
getStructuralLevels = True
showWestergaardInterpretations = False
showPreParse = False
integrateFinalNeighbor = True

# for third species
localNeighborsOnly = False
extendLocalArcs = True
addLocalRepetitions = True

# -----------------------------------------------------------------------------
# LOGGER
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)
# logger.setLevel(logging.INFO)
logger.setLevel(logging.DEBUG)
logger.propagate = False
# logging handlers
f_handler = logging.FileHandler('parser.txt', mode='w')
f_handler.setLevel(logging.DEBUG)
# logging formatters
f_formatter = logging.Formatter('%(message)s')
f_handler.setFormatter(f_formatter)
# add handlers to logger
logger.addHandler(f_handler)


# -----------------------------------------------------------------------------
# MAIN CLASSES
# -----------------------------------------------------------------------------


class Parser:
    """
    The main engine of the parser.

    The bulk of the parser's work is done by :py:func:`~parseTransition`.
    After a preliminary parse of the line, the parser decides on a set
    of possible structural interpretations and creates a
    :py:class:`~Parser.Parse` object to store each interpretation.

    Upon initialization, the Parser automatically parses the line,
    using the following procedure:

    * Prepare placeholders for parses and errors.
    * Accept a line type if provided, otherwise infer the set
      of possible types.
    * Operate the preliminary parser: :py:func:`~preParseLine`.
    * Interrupt the parser if preliminary parsing is unsuccessful
      and report errors.
    * Determine the set of possible basic structures and test
      for each possibility: :py:func:`~prepareParses`.
    * Gather all the valid interpretations of the part by line type:
      :py:func:`~collectParses`.
    * Reduce the set of interpretations using preference rules:
      :py:func:`~selectPreferredParses`.

    The individual parses are contained in a :py:class:`~Parser.Parse`.
    These are created by :py:func:`~prepareParses`.
    """

    def __init__(self, part, context, **kwargs):
        # Set up base content.
        self.part = part
        self.context = context
        self.notes = self.part.flatten().notes

        # Collect errors by part, line type, and individual parse.
        # Raise exceptions in context.py: parseContext.
        self.errors = []  # syntax errors arising during pre-parse,
        #      by part
        #      results are collected for further evaluation
        self.typeErrorsDict = {}  # syntax errors arising during
        # prepare parses,
        #      by line type
        #      results are collected for further evaluation,
        #      only used for 'primary' and 'bass'
        self.parseErrorsDict = {}  # syntax errors arising during
        # final parse,
        #      by parse label
        #      used only internally to weed out specific failures

        # The following lists will be returned
        # to the Part at the end of the Parser.
        self.parses = []  # list of parseLabels
        self.interpretations = {}  # syntax interpretations
        #       of the part in the context,
        #       keyed by lineType, dictionary built parseLabels
        #       in self.parses

        # Lists of parseLabels for successful parses.
        self.Pinterps = []
        self.Binterps = []
        self.Ginterps = []
        # Generability attributes.
        self.isPrimary = False
        self.isGeneric = False
        self.isBass = False

        # Accept line type if already selected,
        # otherwise infer the set of possible types.
        if self.part.lineType is not None:
            self.part.lineTypes = [self.part.lineType]
        else:
            self.part.lineTypes = []
            self.inferLineTypes()
        # log result
        logger.debug(f'PARSE DEBUG REPORT: Part {self.part.partNum + 1} of '
                     f'{len(self.context.parts)} parts')
        logger.debug(f'Line types: {self.part.lineTypes}')

        # STEP ONE: Operate the preliminary parser.
        self.preParseLine()
        # log result
        logger.debug(f'\nPreliminary Arcs: {self.arcs}\n')
        logger.debug(f'\nPreliminary Heads: {self.openHeads}\n')
        # TODO show preliminary parse during testing phase
        if showPreParse:
            self.showPartialParse(self.notes[0],
                                  self.notes[-1], self.arcs, [], [])

        # Interrupt parser if preliminary parsing is unsuccessful.
        # and report errors
        if self.errors:
            return

        # STEP TWO: Determine the set of possible basic structures,
        # and parse for each possibility.
        if self.context.harmonicSpecies:
            self.prepareHarmonicParses()
        else:
            self.prepareMonotriadicParses()

        # STEP THREE: Gather all the valid interpretations
        # of the part by line type.
        self.collectParses()

        # STEP FOUR: Reduce the set of interpretations using preference rules.
        if selectPreferredParses:
            self.selectPreferredParses()

    def inferLineTypes(self):
        """If the line type is not specified, infer a set of possibilities."""
        cond1 = self.notes[0].csd.value % 7 in [0, 2, 4]
        cond2 = self.notes[-1].csd.value % 7 in [0, 2, 4]
        cond3 = self.notes[0].csd.value % 7 == 0
        cond4 = self.notes[-1].csd.value % 7 == 0
        cond5 = self.notes[-1].csd.value == 0
        cond6 = self.notes[-1].csd.value == 7
        if not cond1 and not cond2:
            error = ('Generic structure error: The line is not bounded '
                     'by tonic-triad pitches and hence not a valid '
                     'tonic line.')
            self.errors.append(error)
            return
        else:
            self.part.lineTypes.append('generic')
        # Make some educated guesses as to whether
        # the line can be a bass line or primary line.
        if (cond3 and cond4
                and (len(self.context.parts) == 1
                     or (len(self.context.parts) > 1
                         and self.part == self.context.parts[-1]))):
            for n in self.notes[1:-1]:
                if n.csd.value % 7 == 4:
                    self.part.lineTypes.append('bass')
                    break
        if (cond1 and cond5
                and (len(self.context.parts) == 1
                     or (len(self.context.parts) > 1
                         and self.part != self.context.parts[-1]))):
            for n in self.notes[:-1]:
                if n.csd.value in [2, 4, 7]:
                    self.part.lineTypes.append('primary')
                    break
        elif (cond1 and cond6
              and (len(self.context.parts) == 1
                   or (len(self.context.parts) > 1
                       and self.part != self.context.parts[-1]))):
            for n in self.notes[:-1]:
                if n.csd.value + 7 in [2, 4, 7]:
                    self.part.lineTypes.append('primary')
                    break

    def preParseLine(self):
        """
        Conduct a preliminary parse of the line.
        Initialize the buffer, stack, and arcs.
        Initialize the lists of open heads and transitions.
        Set the global harmonic referents.
        Run the scanner, parsing each transition.
        """
        # Initialize the buffer, stack, and arcs
        g_buffer = [n for n in self.notes
                    if not n.tie or n.tie.type == 'start']
        g_stack = []
        arcs = []
        # Initialize the lists of open heads and transitions
        openHeads = [0]
        openTransitions = []
        #        openLocals = []
        # Set the global harmonic referents
        harmonyStart = [p for p in self.part.tonicTriad.pitches]
        harmonyEnd = [p for p in self.part.tonicTriad.pitches]

        # Method for pre-parsing monotriadic species other than third or fifth
        if (self.part.species in ['first', 'second', 'fourth'] and
                not self.context.harmonicSpecies):
            # Run the line scanner.
            n = len(g_buffer)
            logger.debug(f'Parser state: 0'
                         f'\n\tHeads: {openHeads}'
                         f'\n\tTrans: {openTransitions}'
                         f'\n\tArcs:  {arcs}')
            while n > 1:
                shiftBuffer(g_stack, g_buffer)
                n = len(g_buffer)
                i = g_stack[-1]
                j = g_buffer[0]
                # Parse the transition i-j.
                self.parseTransition(g_stack, g_buffer, self.part, i, j,
                                     harmonyStart, harmonyEnd, openHeads,
                                     openTransitions, arcs)
                # log result
                logger.debug(f'Parser state: {j.index}'
                             f'\n\tHeads: {openHeads}'
                             f'\n\tTrans: {openTransitions}'
                             f'\n\tArcs:  {arcs}')
                # Break upon finding errors.
                if self.errors:
                    break

        # Method for pre-parsing harmonic species.
        elif self.context.harmonicSpecies:
            logger.debug(f'Parser state: 0'
                         f'\n\tHeads: {openHeads}'
                         f'\n\tTrans: {openTransitions}'
                         f'\n\tArcs:  {arcs}')
            # Scan each harmonic context in turn.
            offPre = self.context.harmonicSpanDict['offsetPredominant']
            offDom = self.context.harmonicSpanDict['offsetDominant']
            offClosTon = self.context.harmonicSpanDict['offsetClosingTonic']
            # create the buffer and reference harmonies for each harmonic span
            # (buffer, harmonyStart, harmonyEnd, harmonyName)
            harmonicSpans = []
            if offPre is not None:
                Ti_buffer = [n for n in self.notes
                             if ((not n.tie or n.tie.type == 'start')
                                 and n.offset <= offPre)]
                P_buffer = [n for n in self.notes
                            if ((not n.tie or n.tie.type == 'start')
                                and offPre <= n.offset <= offDom)]
                D_buffer = [n for n in self.notes
                            if ((not n.tie or n.tie.type == 'start')
                                and offDom <= n.offset <= offClosTon)]
                harmonicSpans.append((Ti_buffer,
                                      [p for p in
                                       self.part.tonicTriad.pitches],
                                      [p for p in
                                       self.part.predominantTriad.pitches],
                                      'initial tonic'))
                harmonicSpans.append((P_buffer,
                                      [p for p in
                                       self.part.predominantTriad.pitches],
                                      [p for p in
                                       self.part.dominantTriad.pitches],
                                      'predominant'))
                harmonicSpans.append((D_buffer,
                                      [p for p in
                                       self.part.dominantTriad.pitches],
                                      [p for p in
                                       self.part.tonicTriad.pitches],
                                      'dominant'))
            else:
                Ti_buffer = [n for n in self.notes
                             if ((not n.tie or n.tie.type == 'start')
                                 and n.offset <= offDom)]
                D_buffer = [n for n in self.notes
                            if ((not n.tie or n.tie.type == 'start')
                                and offDom <= n.offset <= offClosTon)]
                harmonicSpans.append((Ti_buffer,
                                      [p for p in
                                       self.part.tonicTriad.pitches],
                                      [p for p in
                                       self.part.dominantTriad.pitches],
                                      'initial tonic'))
                harmonicSpans.append((D_buffer,
                                      [p for p in
                                       self.part.dominantTriad.pitches],
                                      [p for p in
                                       self.part.tonicTriad.pitches],
                                      'dominant'))
            # create lists to pass heads and transitions
            # from one span to the next
            openTransitions = []
            openHeads = []

            # now parse each harmonic span
            for h_span in harmonicSpans:
                h_stack = []
                h_buffer = h_span[0]
                h_harmonyStart = h_span[1]
                h_harmonyEnd = h_span[2]
                h_openHeads = []
                # add index of first note of buffer to open heads
                # if it is harmonic
                if isHarmonic(h_span[0][0], h_span[1]):
                    h_openHeads.append(h_span[0][0].index)
                # TODO grab open trans from prior spans
                h_openTransitions = [h for h in openTransitions]
                if h_openTransitions:
                    h_openHeads = openHeads + h_openHeads
                n = len(h_buffer)
                while n > 1:
                    shiftBuffer(h_stack, h_buffer)
                    n = len(h_buffer)
                    i = h_stack[-1]
                    j = h_buffer[0]
                    # Parse the transition i-j.
                    self.parseTransition(h_stack, h_buffer, self.part, i, j,
                                         h_harmonyStart, h_harmonyEnd,
                                         h_openHeads,
                                         h_openTransitions, arcs)
                    # log result
                    logger.debug(f'Parser state: {j.index}'
                                 f'\n\tLocal Harmonic Heads: {h_openHeads}'
                                 f'\n\tLocal Harmonic Trans: {h_openTransitions}'
                                 f'\n\tArcs:  {arcs}')
                    # Break upon finding errors.
                    if self.errors:
                        break
                    if n == 1:
                        if h_span[3] == 'initial tonic':
                            self.T_openHeads = h_openHeads
                        elif h_span[3] == 'predominant':
                            self.P_openHeads = h_openHeads
                            # if there are unclosed transitions, copy them on
                            # for processing in the next harmonic span, along
                            # with open heads to which they might attach
                            openTransitions = h_openTransitions
                            if openTransitions:
                                openHeads = h_openHeads
                        elif h_span[3] == 'dominant':
                            self.D_openHeads = h_openHeads
                            openTransitions = h_openTransitions
                            if openTransitions:
                                openHeads = h_openHeads

            # TODO select S2cand and S3cands from the relevant harmonic spans

        # Method for parsing monotriadic third species (fifth is aspirational)
        elif self.part.species in ['third', 'fifth']:
            # Global variables for modifying the local parse:
            # (1) Admit local repetitions:
            #     addLocalRepetitions = True/False
            # (2) Limit local elaborations to neighboring and restrict
            #     local insertions and passing:
            #     localNeighborsOnly = True/False
            # (3) Attempt to extend local arcs beyond local context:
            #     extendLocalArcs = True/False

            logger.debug(f'Parser state: 0'
                         f'\n\tHeads: {openHeads}'
                         f'\n\tTrans: {openTransitions}'
                         f'\n\tArcs:  {arcs}')
            # Scan the global context.
            n = len(g_buffer)
            while n > 1:
                shiftBuffer(g_stack, g_buffer)
                n = len(g_buffer)
                i = g_stack[-1]
                j = g_buffer[0]

                # Parse the local span whenever i falls
                # at the start of the line or measure.
                localStart = g_stack[-1].index
                localEnd = 0
                if i.beat == 1.0 or i.index == 0:
                    l_stack = []
                    l_buffer = []
                    l_arcs = []
                    l_openHeads = []
                    l_openTransitions = []
                    # Set the local harmony.
                    if i.index == 0:
                        l_harmonyStart = [p for p
                                          in self.part.tonicTriad.pitches]
                    elif i.beat == 1.0 and i.index > 0:
                        l_harmonyStart = (
                            self.context.localHarmonyDict[i.offset]
                        )

                    # Fill the local buffer up to and including the next
                    # onbeat note and set l_harmonyEnd by that note.
                    for note in g_buffer:
                        if note.beat == 1.0:
                            l_buffer.append(note)
                            l_harmonyEnd = (
                                self.context.localHarmonyDict[note.offset]
                            )
                            localEnd = note.index
                            break
                        else:
                            l_buffer.append(note)
                    # Now put i in the local buffer so i--j can be parsed.
                    l_buffer.insert(0, i)

                    # Add first local note to local heads.
                    l_openHeads.append(i.index)

                    # Scan local context.
                    ln = len(l_buffer)
                    while ln > 1:
                        shiftBuffer(l_stack, l_buffer)
                        ln = len(l_buffer)
                        x = l_stack[-1]
                        y = l_buffer[0]
                        self.parseTransition(
                            l_stack, l_buffer,
                            self.part, x, y,
                            l_harmonyStart, l_harmonyEnd,
                            l_openHeads, l_openTransitions,
                            l_arcs
                        )
                        logger.debug(f'Parser state: {y.index}'
                                     f'\n\tLoc Heads: {l_openHeads}'
                                     f'\n\tLoc Trans: {l_openTransitions}'
                                     f'\n\tLoc Arcs:  {l_arcs}')
                    # Break upon finding errors.
                    # TODO: Collect errors and continue?

                    # Look for unattached local repetitions of first open head.
                    if addLocalRepetitions:
                        firstHead = l_openHeads[0]
                        for h in l_openHeads[1:]:
                            # check whether any open transitions intervene
                            interTrans = [t for t in l_openTransitions if
                                          t < h]
                            if (self.notes[h].csd.value
                                    == self.notes[firstHead].csd.value
                                    and not interTrans):
                                self.notes[h].dependency.lefthead = firstHead
                                self.notes[
                                    firstHead].dependency.dependents.append(h)
                                arcGenerateRepetition(h, self.part,
                                                      l_arcs)
                                # Skip any intervening local heads.
                                revisedHeads = [head for head
                                                in l_openHeads[1:]
                                                if head > h]
                                l_openHeads = ([firstHead]
                                               + revisedHeads)
                        logger.debug(f'Parser state: {y.index}'
                                     '--after adding local repetitions--'
                                     f'\n\tRevised Loc Arcs:  {l_arcs}')

                    # If local insertions are not allowed, limit local arcs
                    # to neighbors and repetitions.
                    # TODO: reset dependencies in local passing arcs.
                    if localNeighborsOnly:
                        l_arcs = [arc for arc in l_arcs if
                                  (isNeighboringArc(arc, self.notes) or
                                   isRepetitionArc(arc, self.notes))]
                        logger.debug(f'Parser state: {y.index}'
                                     '--after limiting to local neighbors--'
                                     f'\n\tRevised Loc Arcs:  {l_arcs}')

                    # Try to extend local passing motions from
                    # or into bordering context
                    if extendLocalArcs and not localNeighborsOnly:
                        # Try to extend local arcs leftward
                        # if lefthead in open transitions.
                        for arc in l_arcs:
                            if (arc[0] in openTransitions
                                    and not isEmbeddedInOtherArc(arc,
                                                                 l_arcs,
                                                                 startIndex=0,
                                                                 stopIndex=99)):
                                lh = self.notes[arc[0]].dependency.lefthead
                                # Get all the global notes connected to
                                # the open transition.
                                globalElems = [
                                    idx for idx in
                                    self.notes[arc[0]].dependency.dependents
                                    if self.notes[arc[0]].dependency.lefthead
                                       < idx < arc[0]
                                ]
                                extensions = [lh] + globalElems

                                # See whether the global lefthead
                                # is just a step away
                                if isPassingArc(arc, self.notes):
                                    tempArc = extensions + arc
                                    # See whether new arc passes through
                                    # a consonant interval
                                    rules = [
                                        isPassingArc(tempArc, self.notes),
                                        isLinearConsonance(
                                            self.notes[tempArc[0]],
                                            self.notes[tempArc[-1]])
                                    ]
                                    if all(rules):
                                        arcExtendTransition(self.notes, arc,
                                                            extensions)
                                        openTransitions.remove(arc[0])
                                        l_openHeads.remove(arc[0])
                                        l_arcs.remove(arc)
                                        l_arcs.append(tempArc)

                        # Try to extend local arcs rightward
                        # if righthead still locally open.
                        for arc in l_arcs:
                            if arc[-1] == localEnd - 1:
                                tempArc = arc + [localEnd]
                                rules = [
                                    arc[-1] in l_openHeads,
                                    isPassingArc(tempArc, self.notes),
                                    isLinearConsonance(self.notes[arc[0]],
                                                       self.notes[localEnd])
                                ]
                                if all(rules):
                                    arcExtendTransition(self.notes, arc,
                                                        extensions=[localEnd])
                                    l_openHeads.remove(arc[-1])
                                    l_arcs.remove(arc)
                                    l_arcs.append(tempArc)

                        # TODO: Try to extend leftward and rightward
                        # simultaneously?

                        # And now see whether any local repetitions
                        # remain available.
                        if len(l_openHeads) > 1:
                            pairs = itertools.combinations(l_openHeads, 2)
                            for pair in pairs:
                                i = self.notes[pair[0]]
                                j = self.notes[pair[1]]
                                interTrans = [t for t in l_openTransitions if
                                              i.index < t < j.index]
                                rules = [
                                    i.csd.value == j.csd.value,
                                    i.measureNumber == j.measureNumber,
                                    not isEmbeddedInArcs(pair[0], l_arcs),
                                    not isEmbeddedInArcs(pair[1], l_arcs),
                                    not interTrans
                                ]
                                if all(rules):
                                    j.dependency.lefthead = i.index
                                    i.dependency.dependents.append(j.index)
                                    arcGenerateRepetition(j.index, self.notes,
                                                          l_arcs)
                                    l_openHeads.remove(j.index)
                                    # Remove local heads embedded
                                    # in the repetition.
                                    for h in l_openHeads:
                                        if i.index < h < j.index:
                                            l_openHeads.remove(h)

                        logger.debug(f'Parser state: {y.index}'
                                     '--after extending local arcs--'
                                     f'\n\tRevised Loc Arcs:  {l_arcs}')
                # Copy local arcs to global arcs.
                for arc in l_arcs:
                    arcs.append(arc)
                # Shift locals into line stack if not locally closed.
                # Start with the top of the stack, which is
                # first in the local context.
                # Remove top of stack if it is now closed.
                if g_stack[-1].index not in l_openHeads:
                    g_stack.pop(-1)
                # Then proceed through the rest of the local context.
                while g_buffer[0].index < localEnd:
                    shiftBuffer(g_stack, g_buffer)
                    if g_stack[-1].index not in l_openHeads and g_stack[
                            -1].index not in l_openTransitions:
                        g_stack.pop(-1)

                # Restore the open locals to the buffer.
                while g_stack[-1].index > localStart:
                    shiftStack(g_stack, g_buffer)

                # Reparse the open locals in the global context.
                # TODO This is problematical when there are
                # several open locals.
                harmonyStart = [p for p in self.part.tonicTriad.pitches]
                harmonyEnd = [p for p in self.part.tonicTriad.pitches]
                while g_buffer[0].index < localEnd:
                    i = g_stack[-1]
                    j = g_buffer[0]
                    logger.debug(f'Parser state: {j.index}'
                                 '--before parsing local heads in global context--'
                                 f'--transition: {i.index}-{j.index}--'
                                 f'\n\tHeads: {openHeads}'
                                 f'\n\tTrans: {openTransitions}'
                                 f'\n\tArcs:  {arcs}')
                    self.parseTransition(g_stack, g_buffer,
                                         self.part, i, j,
                                         harmonyStart, harmonyEnd, openHeads,
                                         openTransitions, arcs)
                    logger.debug(f'Parser state: {j.index}'
                                 '--after parsing local heads--'
                                 f'\n\tHeads: {openHeads}'
                                 f'\n\tTrans: {openTransitions}'
                                 f'\n\tArcs:  {arcs}')
                    shiftBuffer(g_stack, g_buffer)

                # Parse the transition into the next span.
                if g_buffer[0].index == localEnd:
                    i = g_stack[-1]
                    j = g_buffer[0]
                    logger.debug(f'Parser state: {j.index}'
                                 '--before parsing into next local span--'
                                 f'\n\tHeads: {openHeads}'
                                 f'\n\tTrans: {openTransitions}'
                                 f'\n\tArcs:  {arcs}')
                    self.parseTransition(g_stack, g_buffer,
                                         self.part, i, j,
                                         harmonyStart, harmonyEnd, openHeads,
                                         openTransitions, arcs)
                    logger.debug(f'Parser state: {j.index}'
                                 '--after parsing into next local span--'
                                 f'\n\tHeads: {openHeads}'
                                 f'\n\tTrans: {openTransitions}'
                                 f'\n\tArcs:  {arcs}')
                n = len(g_buffer)

        if self.part.species in ['third', 'fifth'] and openTransitions:
            for idx in openTransitions:
                # TODO First look for 'resolution'.
                self.notes[idx].rule.name = 'L0'
        elif openTransitions:
            mns = [str(self.notes[t].measureNumber) for t in openTransitions]
            mns = ', '.join(mns)
            error = (f'There are unclosed transitions in '
                     'the following measures: '
                     + f'{mns}.')
            self.errors.append(error)
            logger.debug(f'{error}')
        self.arcs = arcs
        self.openHeads = openHeads

    def showPartialParse(self, stackTop, bufferBottom, arcs,
                         openHeads, openTransitions):
        stackTop.style.color = 'blue'
        bufferBottom.style.color = 'green'
        if openTransitions:
            for t in openTransitions:
                self.notes[t].style.color = 'red'
        if openHeads:
            for h in openHeads:
                self.notes[h].style.color = 'purple'
        westerparse.assignSlurs(self.part, arcs)
        self.part.show()
        for n in self.notes:
            n.style.color = 'black'

    def parseTransition(self, stack, buffer, part, i, j, harmonyStart,
                        harmonyEnd, openHeads, openTransitions, arcs):
        """
        Asks a series of questions at the transition from
        note *i* to note *j*.

        * Do *i* and *j* belong to the harmony of the context
          (tonic, in the case of global contexts)?
        * What is the intervallic relation between *i* and *j*
          (step or skip)?
        * How does *j* connect, if at all, with notes in the
          dynamic lists of open heads and transitions?

        Based on the answers, the parser assigns dependency relations,
        creates arcs where warranted,
        or returns error messages if the line is syntactically malformed.

        The specific cases are as follows:

        #. *Both pitches are harmonic*

           * If *i* and *j* are the same pitch, generate a repetition.
           * If there are open transitions, see whether *j*
             resolves a transition, starting with the most recent.

        #. *Step from the harmony of this bar to the harmony of the next*

           * If *i* is an open local transition, end the transition at *j*.

        #. *Step from harmonic to nonharmonic pitch*

           * If there are open transitions, see whether *j* continues
             a transition, starting with the most recent.
           * If there are no open transitions but there are open heads,
             try to attach *j* to an open head, starting with
             the most recent (*i*).

        #. *Step from nonharmonic to harmonic pitch*

           * In third species, add *j* to the local harmony if needed.
           * If there are no open transitions, see whether the
             directionality of *i* matches the direction of the step.

              * If so, make *i* the lefthead of *j*.
              * Otherwise, add *i* to the list of open transitions.

           * If there are open transitions, see whether *j* resolves
             a transition, starting with the most recent.

        #. *Step from nonharmonic to nonharmonic*

           * If the directionality of *i* and *j* match or *i*
             is bidirectional and *j* is ascending, ...
           * If *i* is ascending and *j* is descending, ...
           * If *i* is ascending and *j* is bidirectional, ...
           * If *i* is bidirectional and *j* is descending, ...

        #. *Consonant skip from nonharmonic to harmonic*

           * if *i* and *j* are linearly consonant ...

        #. *Consonant skip from harmonic to nonharmonic*

           * This is one of the more complex cases, often necessitating
             revision of the interpretation in order to connect the new
             nonharmonic pitch to a previous pitch.

           * If there are open transitions:

              * See whether *j* continues a transition in progress.
              * If not, see whether *j* connects to a head
                that precedes the open transitions.
              * If neither of these works, return an error: *j* appears
                out of the blue and cannot be generated.

           * If there are open heads:

              * Look for an open head to attach to *j*.
              * If that fails, search for possible step-related
                antecedent (head or transition).

                 * Look in reverse at the terminals of current arcs and
                   select the most recent that is step-related.
                 * Look for possible step-related transition that was
                   previously integrated into a neighbor arc.
                 * Look for possible step-related insertion that was
                   embedded in another arc.

              * If neither of these works, return an error:
                *j* appears out of the blue and cannot be generated.

        #. *Consonant skip from nonharmonic to nonharmonic*

           * Return an error.

        #. *Linear unison between nonharmonic pitches*

           * Return an error.

        #. *Dissonant skip*

           * Return an error.

        #. *Skip larger than an octave*

           * Return an error.

        """
        case1 = [(isHarmonic(i, harmonyStart)
                  and isHarmonic(j, harmonyStart)),
                 (isLinearConsonance(i, j)
                  or isLinearUnison(i, j))]
        case2 = [self.part.species in ['third', 'fifth'],
                 not isHarmonic(i, harmonyStart),
                 isHarmonic(j, harmonyEnd),
                 isDiatonicStep(i, j),
                 buffer[-1].index == j.index]
        case2H = [self.context.harmonicSpecies,
                  buffer[-1].index == j.index]
        case3 = [isHarmonic(i, harmonyStart),
                 not isHarmonic(j, harmonyStart),
                 isDiatonicStep(i, j),
                 buffer[-1].index != j.index]
        case4 = [not isHarmonic(i, harmonyStart),
                 isHarmonic(j, harmonyStart),
                 isDiatonicStep(i, j)]
        case5 = [not isHarmonic(i, harmonyStart),
                 not isHarmonic(j, harmonyStart),
                 isDiatonicStep(i, j)]
        case6 = [not isHarmonic(i, harmonyStart),
                 isHarmonic(j, harmonyStart),
                 isLinearConsonance(i, j)]
        case7 = [isHarmonic(i, harmonyStart),
                 not isHarmonic(j, harmonyStart),
                 isLinearConsonance(i, j),
                 buffer[-1].index != j.index]
        case8 = [not isHarmonic(i, harmonyStart),
                 not isHarmonic(j, harmonyStart),
                 isLinearConsonance(i, j)]
        case9 = [not isHarmonic(i, harmonyStart),
                 not isHarmonic(j, harmonyStart),
                 isLinearUnison(i, j)]
        case10 = [not isLinearConsonance(i, j),
                  not isLinearUnison(i, j),
                  not isDiatonicStep(i, j)]
        case11 = [not isSemiSimpleInterval(i, j)]

        # CASE ONE: Both pitches are harmonic and consonant.
        if all(case1):
            logger.debug(f'Parse transition {i.index}-{j.index}: case 1')
            if self.part.species in ['third', 'fifth']:
                if j.pitch not in harmonyStart:
                    harmonyStart.append(j.pitch)
            if i.csd.value == j.csd.value:
                j.dependency.lefthead = i.index
                i.dependency.dependents.append(j.index)
                arcGenerateRepetition(j.index, part, arcs)
            elif openTransitions:
                # See if j resolves the most recent open transition.
                for t in reversed(openTransitions):
                    h = self.notes[t]
                    if isDirectedStep(h, j):
                        # add the new arc only if it doesn't contradict
                        # an existing arc
                        testArc = [h.dependency.lefthead, h.index, j.index]
                        if conflictsWithOtherArc(testArc, arcs):
                            return
                        else:
                            pass
                        h.dependency.righthead = j.index
                        if h.dependency.dependents:
                            for d in h.dependency.dependents:
                                self.notes[d].dependency.righthead = j.index
                        j.dependency.dependents.append(h.index)
                        openTransitions.remove(h.index)
                        arcGenerateTransition(h.index, part, arcs)
                        pruneHeads = []
                        for x in openHeads:
                            if h.index < x < j.index:
                                pruneHeads.append(x)
                        openHeads[:] = [head for head in openHeads
                                        if head not in pruneHeads]
                        openHeads.append(j.index)
                        # 2023-08-28 removed the following return in order to
                        # capture resolution of multiple secondary structures
                        # return
                    else:
                        if i.index not in openHeads:
                            openHeads.append(i.index)
                        openHeads.append(j.index)
                        # 2024-09-23 added the following return in order to
                        # fix resolution with multiple secondary structures
                        # stops the search when the most recent open
                        #   transition remains unresolved
                        return
            else:
                openHeads.append(j.index)

        # CASE TWO: Transition through end of this bar
        # to the harmony of the next.
        elif all(case2):
            logger.debug(f'Parse transition {i.index}-{j.index}: case 2')
            if i.index in openTransitions:
                i.dependency.righthead = j.index
                j.dependency.dependents.append(i.index)
                openTransitions.remove(i.index)
                for d in i.dependency.dependents:
                    if i.dependency.lefthead is None:
                        logger.debug(f'Case marker 018')
                        i.dependency.lefthead = self.notes[
                            d].dependency.lefthead
                    # Add righthead to codependents if they share lefthead.
                    if (self.notes[d].dependency.lefthead
                            == i.dependency.lefthead):
                        self.notes[d].dependency.righthead = j.index
                arcGenerateTransition(i.index, part, arcs)
                logger.debug(f'evaluating transition to {j.index} '
                             'in the next local span'
                             f'\n\topen trans = {openTransitions}')

        elif all(case2H):
            logger.debug(f'Parse transition {i.index}-{j.index}: case 2H')
            if openTransitions:
                logger.debug(f'evaluating transitions to {j.index} '
                             'in the next harmonic span'
                             f'\n\topen trans = {openTransitions}')
                for t in reversed(openTransitions):
                    h = self.notes[t]
                    rules = [isDiatonicStep(h, j)]
                    if all(rules):
                        h.dependency.righthead = j.index
                        if h.dependency.dependents:
                            logger.debug(f'Case marker 024')
                            for d in h.dependency.dependents:
                                logger.debug(f'Case marker 025')
                                self.notes[d].dependency.righthead = j.index
                        j.dependency.dependents.append(h.index)
                        openTransitions.remove(h.index)
                        arcGenerateTransition(h.index, part, arcs)
                    else:
                        error = ('Unresolved transitions in the '
                                 + 'harmonic span: '
                                 + f'{h.nameWithOctave} in bar '
                                 + f'{h.measureNumber}.')
                        self.errors.append(error)
                        return
            # see whether j is a local suspension
            if not openTransitions and openHeads:
                for t in reversed(openHeads):
                    h = self.notes[t]
                    if h.csd.value == j.csd.value:
                        logger.debug(f'Case marker 029')
                        j.dependency.lefthead = h.index
                        h.dependency.dependents.append(j.index)
                        arcGenerateRepetition(j.index, part, arcs)
                        return
            if not isHarmonic(j, harmonyEnd):
                openTransitions.append(j.index)
                if j.dependency.lefthead is None:
                    error = ('This note does not belong to the '
                             + 'harmony of the span: '
                             + f'{j.nameWithOctave} in bar '
                             + f'{j.measureNumber}.')
                    self.errors.append(error)
                    return

        # CASE THREE: Step from harmonic to nonharmonic pitch.
        elif all(case3):
            logger.debug(f'Parse transition {i.index}-{j.index}: case 3')
            if openTransitions:
                for t in reversed(openTransitions):
                    h = self.notes[t]
                    rules1 = [isStepUp(h, j),
                              h.csd.direction
                              in ['ascending', 'bidirectional'],
                              j.csd.direction
                              in ['ascending', 'bidirectional'],
                              h.dependency.dependents == []
                              ]
                    rules2 = [isStepDown(h, j),
                              h.csd.direction
                              in ['descending', 'bidirectional'],
                              j.csd.direction
                              in ['descending', 'bidirectional'],
                              h.dependency.dependents == []
                              ]
                    # TODO The rules need to take into account where h is
                    # coming from ... WP021 ... and in whether it must continue
                    # in a particular direction or can be diverted back
                    if all(rules1) or all(rules2):
                        j.dependency.lefthead = h.dependency.lefthead
                        j.dependency.dependents.append(h.index)  # YES?
                        h.dependency.dependents.append(j.index)
                        self.notes[
                            h.dependency.lefthead].dependency.dependents.append(
                            j.index)
                        openTransitions.remove(h.index)
                        openTransitions.append(j.index)
                        # TODO could/should i.index instead be added to openHeads???
                        if i.index in openHeads:
                            openHeads.remove(i.index)
                        break
                    if openHeads:
                        connected = False
                        for oh in reversed(openHeads):
                            h = self.notes[oh]
                            # If i is the only open head, ...
                            if i.index == h.index:
                                j.dependency.lefthead = i.index
                                i.dependency.dependents.append(j.index)
                                openTransitions.append(j.index)
                                connected = True
                                break
                            elif h != i:
                                openHeads.remove(oh)
                            elif h == i:
                                j.dependency.lefthead = h.index
                                h.dependency.dependents.append(j.index)
                                openTransitions.append(j.index)
                                connected = True
                                break
                        if connected:
                            break
                        else:
                            logger.debug(f'Case marker 043')
                            j.dependency.lefthead = i.index
                            i.dependency.dependents.append(j.index)
                            openTransitions.append(j.index)
                            break
                    else:
                        logger.debug(f'Case marker 044')
                        j.dependency.lefthead = i.index
                        i.dependency.dependents.append(j.index)
                        openTransitions.append(j.index)
                        break
            elif not openTransitions:
                # Connect to an earlier head with the same
                # pitch as i, if available.
                if openHeads:
                    for t in reversed(openHeads):
                        h = self.notes[t]
                        # If i is the only open head, ...
                        if i.index == h.index:
                            j.dependency.lefthead = i.index
                            i.dependency.dependents.append(j.index)
                            break
                        elif h == i:
                            j.dependency.lefthead = h.index
                            h.dependency.dependents.append(j.index)
                            break
                    else:
                        j.dependency.lefthead = i.index
                        i.dependency.dependents.append(j.index)
                        openTransitions.append(j.index)
                else:
                    logger.debug(f'Case marker 051')
                    j.dependency.lefthead = i.index
                    i.dependency.dependents.append(j.index)
                if j not in openTransitions:
                    openTransitions.append(j.index)

        # CASE FOUR: Step from nonharmonic to harmonic pitch.
        elif all(case4):
            logger.debug(f'Parse transition {i.index}-{j.index}: case 4')
            # Complete the local harmony if possible.
            if self.part.species in ['third', 'fifth']:
                if j.pitch not in harmonyStart:
                    harmonyStart.append(j.pitch)
            if openTransitions:
                for t in reversed(openTransitions):
                    h = self.notes[t]
                    if t == i.index:
                        if (isStepUp(i, j)
                                and i.csd.direction
                                in ['ascending', 'bidirectional']):
                            i.dependency.righthead = j.index
                            j.dependency.dependents.append(i.index)
                            # Add dependents that aren't repetitions.
                            # TODO limit to dependents that should belong to the
                            #   new arc.
                            for d in i.dependency.dependents:
                                if self.notes[d].csd.value != i.csd.value:
                                    self.notes[
                                        d].dependency.righthead = j.index
                                    self.notes[j.index].dependency.dependents.append(d)
                            openTransitions.remove(i.index)
                            if (self.notes[i.dependency.lefthead]
                                    != self.notes[i.dependency.righthead]):
                                openHeads.append(j.index)
                            arcGenerateTransition(i.index, part, arcs)
                            # If lefthead of transition is not in triad,
                            # remove from open heads.
                            if not (
                                    isHarmonic(self.notes[i.dependency.lefthead],
                                               harmonyStart)):
                                openHeads.remove(i.dependency.lefthead)
                        elif (isStepDown(i, j)
                              and i.csd.direction
                              in ['descending', 'bidirectional']):
                            i.dependency.righthead = j.index
                            j.dependency.dependents.append(i.index)
                            # Add dependents that aren't repetitions.
                            # TODO limit to dependents that should belong to
                            #   the new arc.
                            for d in i.dependency.dependents:
                                if self.notes[d].csd.value != i.csd.value:
                                    self.notes[
                                        d].dependency.righthead = j.index
                                    j.dependency.dependents.append(d)
                                    self.notes[j.index].dependency.dependents.append(d)
                            openTransitions.remove(i.index)
                            if (self.notes[i.dependency.lefthead]
                                    != self.notes[i.dependency.righthead]):
                                if j.index not in openHeads:
                                    openHeads.append(j.index)
                            arcGenerateTransition(i.index, part, arcs)
                        elif (isStepUp(i, j)
                              and i.csd.direction == 'descending'
                              and isStepUp(self.notes[i.dependency.lefthead],
                                           i)):
                            i.dependency.righthead = j.index
                            j.dependency.dependents.append(i.index)
                            openTransitions.remove(i.index)
                            arcGenerateTransition(i.index, part, arcs)
                            # ?? also add j.index to open heads?
                            if j.index not in openHeads:
                                openHeads.append(j.index)
                        else:
                            openHeads.append(j.index)
                    elif isDiatonicStep(h, j) and t != i.index:
                        if (isStepUp(h, j)
                                and h.csd.direction
                                in ['ascending', 'bidirectional']):
                            # add the new arc only if it doesn't contradict
                            # an existing arc
                            testArc = [h.dependency.lefthead, h.index, j.index]
                            if conflictsWithOtherArc(testArc, arcs):
                                return
                            else:
                                pass
                            h.dependency.righthead = j.index
                            j.dependency.dependents.append(h.index)
                            for d in h.dependency.dependents:
                                if d < h.index and isStepUp(self.notes[d], h):
                                    logger.debug(f'Case marker 077')
                                    self.notes[
                                        d].dependency.righthead = j.index
                                    # TODO Remove condition if there's no reason
                                    #   why d is not still in openTransitions
                                    #   2022-06-15 no cases found
                                    # openTransitions[:] = [trans for trans
                                    #                       in openTransitions
                                    #                       if trans != d]
                            openTransitions.remove(h.index)
                            arcGenerateTransition(h.index, part, arcs)
                            openHeads[:] = [head for head in openHeads
                                            if head <= h.index]
                            if j.index not in openHeads:
                                openHeads.append(j.index)
                        elif (isStepDown(h, j)
                              and h.csd.direction
                              in ['descending', 'bidirectional']):
                            # add the new arc only if it doesn't contradict
                            # an existing arc
                            testArc = [h.dependency.lefthead, h.index, j.index]
                            if conflictsWithOtherArc(testArc, arcs):
                                logger.debug(f'Case marker 080')
                                return
                            else:
                                pass
                            h.dependency.righthead = j.index
                            j.dependency.dependents.append(h.index)
                            for d in h.dependency.dependents:
                                if (d < h.index
                                        and isStepDown(self.notes[d], h)):
                                    self.notes[
                                        d].dependency.righthead = j.index
                                    self.notes[j.index].dependency.dependents.append(d)
                            openTransitions.remove(h.index)
                            arcGenerateTransition(h.index, part, arcs)
                            openHeads[:] = [head for head in openHeads
                                            if head <= h.index]
                            if j.index not in openHeads:
                                openHeads.append(j.index)
                    elif i.index in openTransitions:
                        logger.debug(
                            f'Case 4, problematic code block')
                        # TODO 2024-11-08 incorrectly resolving b7-8 in minor
                        #   what does this block do?
                        #   See WP006: correctly resolves E-natural
                        i.dependency.righthead = j.index
                        j.dependency.dependents.append(i.index)
                        openTransitions.remove(i.index)
                        openHeads.append(j.index)
                        for d in i.dependency.dependents:
                            if i.dependency.lefthead is None:
                                logger.debug(f'Case marker 087')
                                i.dependency.lefthead = self.notes[
                                    d].dependency.lefthead
                            self.notes[d].dependency.righthead = j.index
                            j.dependency.dependents.append(d)
                        arcGenerateTransition(i.index, part, arcs)
                        break
                    elif not isStepDown(h, j) and not isStepUp(h, j):
                        break

        # CASE FIVE: Step from nonharmonic to nonharmonic.
        elif all(case5):
            logger.debug(f'Parse transition {i.index}-{j.index}: case 5')
            if (i.csd.direction == j.csd.direction or
                    i.csd.direction == 'bidirectional' and
                    j.csd.direction == 'ascending'):
                if i.dependency.lefthead is None:
                    pass
                    for t in reversed(openHeads):
                        h = self.notes[t]
                        if not isDiatonicStep(h, i):
                            openHeads.remove(t)
                        elif isDiatonicStep(h, i):
                            h.dependency.dependents.append(i.index)
                            h.dependency.dependents.append(j.index)
                            i.dependency.dependents.append(j.index)
                            j.dependency.dependents.append(i.index)
                            i.dependency.lefthead = h.index
                            j.dependency.lefthead = h.index
                            # TODO: I don't think i.index has in all cases
                            #  been added to openTransitions.
                            if i.index in openTransitions:
                                openTransitions.remove(i.index)
                            openTransitions.append(j.index)
                            break
                elif (i.csd.value % 7 == 5 and
                      j.csd.value % 7 == 6 and
                      i.csd.direction == 'descending'):
                    openTransitions.append(j.index)
                    i.dependency.dependents.append(j.index)
                    j.dependency.lefthead = i.index
                else:
                    if not i.dependency.dependents:
                        rules1 = [isStepDown(self.notes[i.dependency.lefthead],
                                             i),
                                  isStepDown(i, j)]
                        rules2 = [isStepUp(self.notes[i.dependency.lefthead],
                                           i),
                                  isStepUp(i, j)]
                        if all(rules1) or all(rules2):
                            j.dependency.lefthead = i.dependency.lefthead
                            i.dependency.dependents.append(j.index)
                            j.dependency.dependents.append(i.index)
                            openTransitions.remove(i.index)
                            openTransitions.append(j.index)
                        else:
                            error = ('Non-generable succession: '
                                     + i.nameWithOctave + ' to '
                                     + j.nameWithOctave)
                            self.errors.append(error)
                            return
                    else:
                        if (i.consecutions.leftDirection
                                == j.consecutions.leftDirection):
                            j.dependency.lefthead = i.dependency.lefthead
                            i.dependency.dependents.append(j.index)
                            j.dependency.dependents.append(i.index)
                            openTransitions.remove(i.index)
                            openTransitions.append(j.index)
                        else:
                            earlierHeads = [ind for ind in openHeads
                                            if ind < i.dependency.lefthead]
                            connectsToHead = False
                            for h in reversed(earlierHeads):
                                if h != 0 and not isDiatonicStep(self.notes[h],
                                                                 i):
                                    pass
                                elif isDiatonicStep(self.notes[h], i):
                                    # Generate a transition to i and then
                                    # reassign i's lefthead etc.
                                    connectsToHead = True
                                    self.notes[i.dependency.dependents[
                                        -1]].dependency.righthead = i.index
                                    arcGenerateTransition(
                                        i.dependency.dependents[-1],
                                        part, arcs)
                                    i.dependency.lefthead = h
                                    j.dependency.lefthead = h
                                    i.dependency.dependents.append(j.index)
                                    j.dependency.dependents.append(i.index)
                                    self.notes[h].dependency.dependents.append(
                                        j.index)
                                    self.notes[h].dependency.dependents.append(
                                        i.index)
                                    openHeads[:] = [head for head in openHeads
                                                    if not h < head < j.index]
                                    openTransitions.remove(i.index)
                                    openTransitions.append(j.index)
                                    break
                            if not connectsToHead:
                                # Set things up to allow for
                                # connection to a later head.
                                openHeads.append(i.index)
                                i.dependency.dependents.append(j.index)
                                j.dependency.lefthead = i.index
                                openTransitions.append(j.index)
            elif (i.csd.direction == 'ascending'
                  and j.csd.direction == 'descending'):
                logger.debug(f'Case marker 102')
                i.dependency.righthead = j.index
                j.dependency.dependents.append(i.index)
                openTransitions.remove(i.index)
                openTransitions.append(j.index)
                arcGenerateTransition(i.index, part, arcs)
            elif (i.csd.direction == 'ascending'
                  and j.csd.direction == 'bidirectional'):
                # Added this if-trap to capture 8-#7-#6-5 in minor
                # Westergaard057c
                if i.csd.value % 7 == 6 and j.csd.value % 7 == 5:
                    j.dependency.lefthead = i.index
                    i.dependency.dependents.append(j.index)
                    openTransitions.append(j.index)
                else:
                    j.dependency.lefthead = i.dependency.lefthead
                    i.dependency.dependents.append(j.index)
                    j.dependency.dependents.append(i.index)
                    self.notes[
                        j.dependency.lefthead].dependency.dependents.append(
                        j.index)
                    openTransitions.remove(i.index)
                    openTransitions.append(j.index)
            elif (i.csd.direction == 'bidirectional'
                  and j.csd.direction == 'descending'):
                # For catching 5-#6-b7 in minor, revised 2020-06-05
                i.dependency.righthead = j.index
                j.dependency.dependents.append(i.index)
                openTransitions.append(j.index)
                openTransitions.remove(i.index)
                arcGenerateTransition(i.index, part, arcs)
                openHeads.remove(i.dependency.lefthead)
            else:
                # For catching things in third species...
                j.dependency.lefthead = i.dependency.lefthead
                i.dependency.dependents.append(j.index)
                j.dependency.dependents.append(i.index)
                openTransitions.remove(i.index)
                openTransitions.append(j.index)

        # CASE SIX: Skip from nonharmonic to harmonic.
        elif all(case6):
            logger.debug(f'Parse transition {i.index}-{j.index}: case 6')
            openLocals = []
            if i.dependency.lefthead is None:
                # look for a lefthead
                for t in reversed(openHeads):
                    h = self.notes[t]
                    if isDiatonicStep(h, i):
                        i.dependency.lefthead = h.index
                        h.dependency.dependents.append(i.index)
                        if i.index not in openTransitions:
                            openTransitions.append(i.index)
                        openHeads.append(j.index)
                        break
                # if third species and no lefthead was found,
                # make it a local insertion and try to parse j
                if (i.dependency.lefthead is None
                        and self.part.species in ['third', 'fifth']):
                    openLocals.append(i.index)
                    if i.index in openTransitions:
                        logger.debug(f'Case marker 114')
                        openTransitions.remove(i.index)
                    if openTransitions:
                        for t in reversed(openTransitions):
                            h = self.notes[t]
                            if isDirectedStep(h, j):
                                h.dependency.righthead = j.index
                                j.dependency.dependents.append(t)
                                openTransitions.remove(t)
                                openHeads.append(j.index)
                                arcGenerateTransition(t, part, arcs)
                # TODO trying to allow sd3 at start of dominant span in upper line
                #   check only if this is the first note in the span??
                #   and in the upper part
                if self.context.harmonicSpecies and len(stack) == 1:
                    logger.debug(f'Case marker 118')
                    if i.index not in openTransitions:
                        logger.debug(f'Case marker 119')
                        pass
            else:
                openHeads.append(j.index)

        # CASE SEVEN: Skip from harmonic to nonharmonic.
        elif all(case7):
            logger.debug(f'Parse transition {i.index}-{j.index}: case 7')
            if openTransitions:
                # A. See whether j continues a transition in progress.
                continuesTransition = False
                for t in reversed(openTransitions):
                    h = self.notes[t]
                    if isDiatonicStep(h, j):
                        h.dependency.dependents.append(j.index)
                        j.dependency.dependents.append(h.index)
                        j.dependency.lefthead = h.dependency.lefthead
                        openTransitions.remove(h.index)
                        openTransitions.append(j.index)
                        continuesTransition = True
                        # Remove intervening open heads.
                        deletedHeads = []
                        for oh in reversed(openHeads):
                            if h.index < oh < j.index:
                                deletedHeads.append(oh)
                        openHeads[:] = [head for head in openHeads
                                        if head not in deletedHeads]
                        break
                # B. If not, see whether j connects to a head that
                # precedes the open transitions
                if continuesTransition:
                    return
                else:
                    # Get those open heads that are later
                    # than the earliest open transition.
                    interveningHeads = [idx for idx in openHeads
                                        if idx > openTransitions[0]]
                    connectsToHead = False
                    for h in reversed(interveningHeads):
                        if h != 0 and not isDiatonicStep(self.notes[h], j):
                            if h in interveningHeads:
                                interveningHeads.remove(h)
                        elif isDiatonicStep(self.notes[h], j):
                            self.notes[h].dependency.dependents.append(j.index)
                            j.dependency.lefthead = h
                            openTransitions.append(j.index)
                            connectsToHead = True
                            break
                    if not connectsToHead:
                        # C. If neither of these works, return an error.
                        if self.part.species in ['third', 'fifth']:
                            # can't just add j to open transitions without knowing its lefthead
                            pass
                        else:
                            error = ('The non-tonic-triad pitch '
                                     + j.nameWithOctave + ' in measure '
                                     + str(j.measureNumber)
                                     + ' cannot be generated.')
                            self.errors.append(error)
            elif openHeads:
                skippedHeads = []
                for h in reversed(openHeads):
                    # A. Look for an open head to attach to.
                    if h != 0 and not isDiatonicStep(self.notes[h], j):
                        skippedHeads.append(h)
                    elif isDiatonicStep(self.notes[h], j):
                        logger.debug(f'Case marker 139')
                        self.notes[h].dependency.dependents.append(j.index)
                        j.dependency.lefthead = h
                        openTransitions.append(j.index)
                        # Remove skipped heads from open heads.
                        openHeads[:] = [head for head in openHeads
                                        if head not in skippedHeads]
                        break  # Stop now that a lefthead was found.
                    # B. If A was not successful, search for possible
                    # step-related antecedent (head or trans)
                    # that was previously deleted from the stack.
                    # TODO May need to turn off in third species.
                    elif (h == 0
                          and i.dependency.lefthead is None
                          and i.index != h):
                        # Test cases: Westergaard100k, soprano; Primary05.
                        # (Search 1) Look in reverse at the terminals of current
                        # arcs and select the most recent that is step-related;
                        # return the note of that terminal to the
                        # open heads; remove any existing arcs that cross over
                        # the new lefthead candidate;
                        # return their internal elements to open transitions;
                        # remove righthand terminal from open heads.
                        arcHeadsPrior = []
                        for arc in arcs:
                            if arc[0] in arcHeadsPrior:
                                pass
                            else:
                                arcHeadsPrior.append(arc[0])
                            if arc[-1] in arcHeadsPrior:
                                pass
                            else:
                                arcHeadsPrior.append(arc[-1])
                        arcHeadsPrior = sorted(arcHeadsPrior)
                        leftheadCandidates = []
                        for term in arcHeadsPrior:
                            rules = [term < j.index,
                                     isDiatonicStep(j, self.notes[term])]
                            if all(rules):
                                leftheadCandidates.append(term)
                        if leftheadCandidates:
                            # TODO Why look only at the first candidate?
                            # TODO It is not safe to assume that the new
                            # lefthead will be valid: test before
                            # reinterpreting
                            newLefthead = leftheadCandidates[0]
                            j.dependency.lefthead = newLefthead
                            openHeads.append(newLefthead)
                            openTransitions.append(j.index)
                            self.notes[
                                newLefthead].dependency.dependents.append(
                                j.index)
                            # Look for arcs that cross over the new lefthead
                            # and remove from arc list;
                            # remove the righthead and reset its dependencies;
                            # and return transitional elements to list
                            # of open transitions.
                            for arc in arcs:
                                if isEmbeddedInArc(newLefthead, arc):
                                    arcs.remove(arc)
                                    # append the final transitional element
                                    # in the new arc and resort
                                    openTransitions.append(arc[-2])
                                    openTransitions = sorted(openTransitions)
                                    # revise old dependencies
                                    for idx in arc[1:-1]:
                                        # 2024-10-04 revised to append only
                                        # the penultimate idx
                                        # openTransitions.append(idx)
                                        self.notes[
                                            idx].dependency.righthead = None
                                        self.notes[arc[
                                            -1]].dependency.dependents.remove(
                                            idx)
                                    if arc[-1] in openHeads:
                                        openHeads.remove(arc[-1])
                            # TODO making sure openTransitions is properly sorted
                            #   this may no longer be necessary; see 10 lines up
                            openTransitions = sorted(openTransitions)
                            for t in openTransitions:
                                if j.dependency.lefthead < t < j.index:
                                    error = ('The non-tonic-triad pitch '
                                             + j.nameWithOctave + ' in measure '
                                             + str(j.measureNumber)
                                             + ' cannot be generated.')
                                    self.errors.append(error)
                                else:
                                    return
                        # (Search 2) Look for possible step-related transition
                        # that was previously integrated into a neighbor arc;
                        # look for sd7 as lower neighbor or sd6 as upper
                        # neighbor, bidirectional, prior to j.index;
                        # make sure there are no open transitions between
                        # that neighbor and j.index.
                        if (j.csd.value % 7 == 6 or j.csd.value % 7 == 5
                                and j.csd.direction == 'bidirectional'):
                            for arc in arcs:
                                # Look for 8-7-8 if j is 6, or 5-6-5 if j is 7.
                                rules1 = [
                                    isNeighboringArc(arc, self.notes),
                                    isDiatonicStep(self.notes[arc[1]], j),
                                    self.notes[arc[0]].csd.value % 7 == 0,
                                    j.csd.value % 7 == 5
                                ]
                                rules2 = [
                                    isNeighboringArc(arc, self.notes),
                                    isDiatonicStep(self.notes[arc[1]], j),
                                    self.notes[arc[0]].csd.value % 7 == 4,
                                    j.csd.value % 7 == 6
                                ]
                                openTransBetween = [idx for idx
                                                    in openTransitions
                                                    if arc[1] < idx < j.index]
                                rules3 = [not openTransBetween]
                                rules4 = [
                                    self.notes[arc[1]].csd.value % 7 == 6,
                                    self.notes[arc[1]].csd.direction
                                    == 'ascending'
                                ]
                                rules5 = [
                                    self.notes[arc[1]].csd.value % 7 == 6,
                                    self.notes[arc[1]].csd.direction
                                    == 'bidirectional'
                                ]
                                if (all(rules1) or all(rules2)) and all(
                                        rules3):
                                    if all(rules4):
                                        arcs.remove(arc)
                                        openTransitions.append(j.index)
                                        openTransitions.append(arc[1])
                                        self.notes[
                                            arc[1]].dependency.righthead = None
                                        self.notes[arc[
                                            -1]].dependency.dependents.remove(
                                            arc[1])
                                        j.dependency.lefthead = arc[1]
                                        return
                                    elif all(rules5):
                                        arcs.remove(arc)
                                        openTransitions.append(j.index)
                                        self.notes[
                                            arc[1]].dependency.righthead = None
                                        self.notes[arc[
                                            -1]].dependency.dependents.remove(
                                            arc[1])
                                        j.dependency.dependents.append(arc[1])
                                        j.dependency.lefthead = self.notes[
                                            arc[1]].dependency.lefthead
                                        return

                        # (Search 3) Look for possible step-related insertion
                        # that was embedded in another arc'
                        # gather independent notes prior to i.
                        # This will work out only if the demoted insertion
                        # occurs as an insertion between a transition
                        # and its righthead: arc[-2] < h < arc[-1];
                        # the righthead will have to be removed,
                        # pending search for a suitable righthead,
                        # so arc[-2] will have to be restored
                        # to the open transitions.
                        # Case: WP013
                        demotedHeads = [note.index for note in self.notes
                                        if note.index < i.index
                                        and isIndependent(note)]
                        if demotedHeads:
                            for dh in reversed(demotedHeads):
                                if isDiatonicStep(self.notes[dh], j):
                                    # Look for arcs that cross over dh.
                                    for arc in arcs:
                                        if arc[-2] < dh < arc[-1]:
                                            # Restore arc[-2] to open
                                            # transitions and
                                            # remove old righthead
                                            openTransitions.append(arc[-2])
                                            for t in arc[1:-1]:
                                                self.notes[
                                                    t].dependency.righthead = None
                                            clearDependencies(
                                                self.notes[arc[-1]])
                                            arcs.remove(arc)
                                            self.notes[
                                                dh].dependency.dependents.append(
                                                j.index)
                                            j.dependency.lefthead = dh
                                            openTransitions.append(j.index)
                                            openHeads.append(dh)
                                            newhead = True
                                            # Remove any open heads that
                                            # intervene between the new lefhead
                                            # and j
                                            for oh in openHeads:
                                                if h < oh < j.index:
                                                    openHeads.remove(oh)
                                            return

                        else:
                            error = ('The non-tonic-triad pitch '
                                     + j.nameWithOctave + ' in measure '
                                     + str(j.measureNumber)
                                     + ' cannot be generated.')
                            self.errors.append(error)

                    # C. If neither of these works, return an error.
                    elif self.part.species not in ['third', 'fifth']:
                        logger.debug(f'Case marker 170')
                        error = ('The non-tonic-triad pitch '
                                 + j.nameWithOctave + ' in measure '
                                 + str(j.measureNumber)
                                 + ' cannot be generated.')
                        self.errors.append(error)

                # If no lefthead is found, return an error.
                if (self.part.species not in ['third', 'fifth']
                        and j.dependency.lefthead is None):  # is None, in case
                    # lefthead is 0
                    error = ('The non-tonic-triad pitch '
                             + j.nameWithOctave + ' in measure '
                             + str(j.measureNumber)
                             + ' cannot be generated.')
                    # in some cases (all?), this duplicates an error reported
                    # in case C directly above and perhaps elsewhere, so do not
                    # duplicate
                    if error not in self.errors:
                        self.errors.append(error)

        # CASE EIGHT: Skip from nonharmonic to nonharmonic.
        elif all(case8):
            logger.debug(f'Parse transition {i.index}-{j.index}: case 8')
            openLocals = []
            if self.part.species not in ['third', 'fifth']:
                logger.debug(f'Case marker 173')
                if i.index == j.index - 1:
                    logger.debug(f'Case marker 174')
                    error = ('Nongenerable succession between '
                             + i.nameWithOctave + ' and '
                             + j.nameWithOctave + ' in the line.')
                    self.errors.append(error)
                else:
                    logger.debug(f'Case marker 175')
                    error = ('The line contains an ungenerable intertwining '
                             'of secondary structures involving '
                             + j.nameWithOctave + ' in measure ' +
                             str(j.measureNumber) + '.')
                    self.errors.append(error)
            elif self.part.species in ['third', 'fifth']:
                # TODO Interpret local non-tonic insertions.
                if i.index not in openLocals:
                    openLocals.append(i.index)
                openLocals.append(j.index)
                if openHeads:
                    # TODO Figure out how to connect at least one of
                    # these open nttps to a global head.
                    for t in openHeads:
                        h = self.notes[t]
                        if isDiatonicStep(h, i):
                            pass
                pass

        # CASE NINE: Linear unison between nonharmonic pitches.
        elif all(case9):
            logger.debug(f'Parse transition {i.index}-{j.index}: case 9')
            # TODO: Double check this error, might be too simple.
            if i.index == j.index - 1 or i.measureNumber != j.measureNumber:
                error = ('Repetition of a non-tonic-triad pitch: '
                         + i.nameWithOctave + '.')
                self.errors.append(error)
            else:
                logger.debug(f'Case marker 183')
                pass

        # CASE TEN: Dissonant skip.
        elif all(case10):
            logger.debug(f'Parse transition {i.index}-{j.index}: case 11')
            error = ('Nongenerable leap between ' + i.nameWithOctave +
                     ' and ' + j.nameWithOctave + ' in the line.')
            self.errors.append(error)

        # CASE ELEVEN: Leap larger than an octave.
        elif all(case11):
            logger.debug('Parse transition: case 12')
            logger.debug(f'Case marker 185')
            error = ('Leap larger than an octave between '
                     + i.nameWithOctave +
                     ' and ' + j.nameWithOctave + ' in the line.')
            self.errors.append(error)

    def prepareMonotriadicParses(self):
        """
        After preliminary parsing is completed, determines possibilities
        for basic structures in a monotriadic line based on available
        line types and parses the
        line using each candidate for basic structure. The results are
        collected in self.parses.

        If the line type is :literal:`bass`, the function verifies that
        the line begins and ends on a tonic degree (rules S1 and S2)
        and then assembles a list of notes that could complete the
        basic arpeggiation (rule S3) and builds a
        :py:class:`~Parser.Parse` for each S3 candidate.
        (See :py:func:`~Parser.Parse.parseBass`.)

        If the line type is :literal:`primary`, the function verifies that
        the line ends on a tonic degree (rule S1) and then assembles
        a list of notes that could initiate a basic step motion (rule S2).
        The function uses eight different methods to determine
        whether a valid basic step motion exists for each S2 candidate
        (see :py:func:`~Parser.Parse.parsePrimary`)
        and attempts to build a :py:class:`~Parser.Parse` using each
        method; not every method yields a result.

        If the line type is :literal:`generic`,
        the function verifies that the line begins and ends
        on triad pitches (rules S1 and S2) and then looks for
        a possible step connection between these terminal pitches
        (see :py:func:`~Parser.Parse.parseGeneric`).
        """

        # The line may still have some underinterpreted open heads.
        # If so, the remnant of open heads will be placed in the Parse's
        # buffer and re-parsed.
        for lineType in self.part.lineTypes:
            # Restock the buffer and initialize the empty stack.
            buffer = [self.notes[head] for head in self.openHeads]
            stack = []

            # Look for S2 or S3 candidate notes in the given line type
            # and build parse objects for each candidate.
            # Assign a label and counter to each parse object.
            parsecounter = 0

            if lineType == 'bass':
                buildErrors = []
                if self.notes[0].csd.value % 7 != 0:
                    buildError = ('Bass structure error: The line '
                                  'does not begin on the tonic degree (S2).')
                    buildErrors.append(buildError)
                if self.notes[-1].csd.value % 7 != 0:
                    buildError = ('Bass structure error: The line '
                                  'does not end on the tonic degree (S1).')
                    buildErrors.append(buildError)
                s3cands = []
                n = len(buffer)
                while n > 1:
                    shiftBuffer(stack, buffer)
                    n = len(buffer)
                    i = stack[-1]
                    if i.csd.value % 7 != 4:
                        continue
                    elif i.csd.value % 7 == 4:
                        s3cands.append(i)
                # add sd5s near the end of a third-species line
                # TODO make this a less brute force method
                # for finding a structural dominant bass pitch
                if self.part.species in ['third', 'fifth']:
                    meas = len(self.part.getElementsByClass('Measure'))
                    for n in self.notes:
                        cond = [n.csd.value % 7 == 4,
                                meas - 3 < n.measureNumber < meas]
                        if all(cond):
                            # do not duplicate cands already on list
                            s3indexes = [c.index for c in s3cands]
                            if n.index not in s3indexes:
                                s3cands.append(n)
                if not s3cands:
                    buildError = ('Bass structure error: '
                                  'No candidate for S3 detected.')
                    buildErrors.append(buildError)
                logger.debug(f'List of bass S3 candidates: '
                             f'{[s.index for s in s3cands]}')

                if not buildErrors:
                    for cand in s3cands:
                        logger.debug(f'Building parses for S3 candidate: '
                                     f'{cand.index}, scale degree '
                                     f'{cand.csd.degree}')
                        self.buildParse(cand, lineType,
                                        parsecounter, buildErrors=[])
                        parsecounter += 1
                # If the build as type fails, collect errors in dictionary.
                else:
                    self.typeErrorsDict[lineType] = buildErrors

            elif lineType == 'primary':
                buildErrors = []
                if self.notes[-1].csd.value % 7 != 0:
                    buildError = ('Primary structure error: The line '
                                  'does not end on the tonic degree (S1).')
                    buildErrors.append(buildError)
                s2cands = []  # holder for Notes that might become S2
                n = len(buffer)
                while n > 0:
                    shiftBuffer(stack, buffer)
                    n = len(buffer)
                    i = stack[-1]
                    # look for 3, 5, or 8 above final tonic
                    t = self.notes[-1].csd.value
                    if i.csd.value in {2 + t, 4 + t, 7 + t}:
                        s2cands.append(i)
                if not s2cands:
                    buildError = ('Primary structure error: '
                                  'No candidate for S2 detected.')
                    buildErrors.append(buildError)
                logger.debug(f'List of primary S2 candidates: '
                             f'{[s.index for s in s2cands]}')

                # Create a Parse object for each S2cand
                # and then turn over further processes to each Parse object,
                # using a series of methods to infer a basic step motion.
                methods = 8
                if not buildErrors:
                    for cand in s2cands:
                        logger.debug(f'Building parses for S2 candidate: '
                                     f'{cand.index}, scale degree '
                                     f'{cand.csd.degree}')
                        for m in range(0, methods):
                            self.buildParse(cand, lineType, parsecounter,
                                            buildErrors=[], method=m)
                            parsecounter += 1  # update numbering of parses
                # If the build as type fails, collect errors in dictionary.
                else:
                    self.typeErrorsDict[lineType] = buildErrors

            elif lineType == 'generic':  # for generic lines, first note is S2
                s2cand = self.notes[0]
                stack = buffer
                logger.debug(f'Building parses for generic line')
                self.buildParse(s2cand, lineType, parsecounter,
                                buildErrors=[])

    def prepareHarmonicParses(self):
        """After preliminary parsing is completed, determine possibiities
        for basic structures in a harmonically progressive line using
        each structural head candidate. The results are
        collected in self.parses."""
        for lineType in self.part.lineTypes:
            # Look for S2 or S3 candidate notes in the given line type
            # and build parse objects for each candidate.
            # Assign a label and counter to each parse object.
            parsecounter = 0
            if lineType == 'bass':
                buildErrors = []
                if self.notes[0].csd.value % 7 != 0:
                    buildError = ('Bass structure error: The line '
                                  'does not begin on the tonic degree (S2).')
                    buildErrors.append(buildError)
                if self.notes[-1].csd.value % 7 != 0:
                    buildError = ('Bass structure error: The line '
                                  'does not end on the tonic degree (S1).')
                    buildErrors.append(buildError)
                buffer = [self.notes[head] for head in self.D_openHeads]
                stack = []
                s3cands = [self.notes[head] for head in self.D_openHeads
                           if self.notes[head].csd.value % 7 == 4]
                if not s3cands:
                    buildError = ('Bass structure error: '
                                  'No candidate for S3 detected.')
                    buildErrors.append(buildError)
                logger.debug(f'List of bass S3 candidates: '
                             f'{[s.index for s in s3cands]}')
                # create list of S4 candidates
                s4cands = []
                if (self.context.harmonicSpanDict['offsetPredominant']
                        is not None):
                    s4cands = [self.notes[head] for head in self.P_openHeads
                               if (self.notes[head].csd.value % 7 in {1, 3, 5}
                                   and self.notes[head].offset
                                   < self.context.harmonicSpanDict[
                                       'offsetDominant'])
                               and not isEmbeddedInArcs(head, self.arcs)]

                s3s4Pairs = []
                S1 = self.notes[-1]
                for S3 in s3cands:
                    if s4cands:
                        for S4 in s4cands:
                            rules = [
                                isDiatonicStep(S4, S1) or isDiatonicStep(S4,
                                                                         S3)]
                            if all(rules):
                                s3s4Pairs.append((S3, S4))
                    else:
                        s3s4Pairs.append((S3, None))

                if buildErrors == []:
                    for candPair in s3s4Pairs:
                        logger.debug(f'Building parses for S3 candidate: '
                                     f'{candPair[0].index}, scale degree '
                                     f'{candPair[0].csd.degree}')
                        self.buildParse(candPair[0], lineType,
                                        parsecounter, buildErrors=[],
                                        s4cand=candPair[1])
                        parsecounter += 1
                # If the build as type fails, collect errors in dictionary.
                else:
                    self.typeErrorsDict[lineType] = buildErrors

            elif lineType == 'primary':
                buildErrors = []
                if self.notes[-1].csd.value % 7 != 0:
                    buildError = ('Primary structure error: The line '
                                  'does not end on the tonic degree (S1).')
                    buildErrors.append(buildError)
                t = self.notes[-1].csd.value
                s2cands = [self.notes[head] for head in self.T_openHeads
                           if
                           self.notes[head].csd.value in {2 + t, 4 + t, 7 + t}]
                if not s2cands:
                    buildError = ('Primary structure error: '
                                  'No candidate for S2 detected.')
                    buildErrors.append(buildError)
                logger.debug(f'List of primary S2 candidates: '
                             f'{[s.index for s in s2cands]}')

                # create list of S3 candidates in the predominant span
                # TODO Remove this since not used in building the parse ??
                if (self.context.harmonicSpanDict['offsetPredominant']
                        is not None):
                    s3Pcands = [self.notes[head] for head in self.P_openHeads
                                if (self.notes[head].csd.value in {1 + t,
                                                                   3 + t,
                                                                   5 + t}
                                    and self.notes[head].offset
                                    < self.context.harmonicSpanDict[
                                        'offsetDominant'])]
                    # TODO continue with method

                # Create a Parse object for each S2cand
                # and then turn over further processes to each Parse object,
                # using a series of methods to infer a basic step motion.
                methods = 20
                if not buildErrors:
                    for cand in s2cands:
                        logger.debug(f'Building parses for S2 candidate: '
                                     f'{cand.index}, scale degree '
                                     f'{cand.csd.degree}')
                        for m in range(8, methods):
                            self.buildParse(cand, lineType, parsecounter,
                                            buildErrors=[], method=m)
                            parsecounter += 1  # update numbering of parses
                # If the build as type fails, collect errors in dictionary.
                else:
                    self.typeErrorsDict[lineType] = buildErrors
                # TODO test for compliance with rules after generating a
                #   a complete parse, since the rules involve interaction
                #   with the global structure of the bass line

    def buildParse(self, cand, lineType, parsecounter,
                   buildErrors, method=None, s4cand=None):
        """Sets up the basic features of the parse object
        and then executes the parsing process.
        Uses deep copies of the arcs and notes, as the list of arcs and the
        properties of notes will be altered during the process.
        """
        # create the Parse object
        newParse = Parser.Parse()
        # copy information, deepcopy objects that may undergo alteration
        # during the parse
        newParse.S1Index = self.notes[-1].index
        newParse.arcs = copy.deepcopy(self.arcs)
        newParse.lineType = lineType
        newParse.species = self.part.species
        newParse.tonic = self.part.tonic
        newParse.mode = self.part.mode
        newParse.partNum = self.part.partNum
        # newParse.notes = self.notes
        newParse.notes = copy.copy(self.notes.stream())
        newParse.errors = buildErrors
        newParse.notes[newParse.S1Index].rule.name = 'S1'
        newParse.method = method
        newParse.harmonicSpecies = self.context.harmonicSpecies
        if self.context.harmonicSpecies:
            newParse.harmonicSpanDict = self.context.harmonicSpanDict
        # Prepare the basic structure information.
        if parsecounter < 10:
            parsenumber = '0' + str(parsecounter)
        else:
            parsenumber = str(parsecounter)
        if lineType == 'bass':
            newParse.label = 'parse' + parsenumber + '_BL'
            newParse.S2Index = 0
            newParse.S3Index = cand.index
            newParse.S3Degree = cand.csd.degree
            newParse.S3Value = cand.csd.value
            newParse.notes[newParse.S2Index].rule.name = 'S2'
            newParse.notes[newParse.S3Index].rule.name = 'S3'
            if s4cand is not None:
                newParse.S4Index = s4cand.index
                newParse.S4Degree = s4cand.csd.degree
                newParse.S4Value = s4cand.csd.value
                newParse.notes[newParse.S4Index].rule.name = 'S4'
        elif lineType == 'primary':
            newParse.label = 'parse' + parsenumber + '_PL'
            newParse.S2Index = cand.index
            newParse.S2Degree = cand.csd.degree
            newParse.S2Value = cand.csd.value
            newParse.notes[newParse.S2Index].rule.name = 'S2'
        elif lineType == 'generic':
            newParse.label = 'parse' + parsenumber + '_GL'
            newParse.S2Index = cand.index  # always 0
            newParse.S2Degree = cand.csd.degree
            newParse.S2Value = cand.csd.value
            newParse.notes[newParse.S2Index].rule.name = 'S2'
        newParse.openHeads = [self.notes[idx] for idx in self.openHeads]

        # Now parse the line.
        newParse.performLineParse()
        # And return the results to the Parser.
        self.parses.append(newParse)
        self.parseErrorsDict.update({newParse.label: newParse.errors})

    class Parse:
        """An object for holding one interpretation of
        a line's syntactic structure.

        The object's attributes include `S1Index`, `S2Degree`, `S2Index`,
        `S2Value`, `S3Degree`, `S3Final`, `S3Index`, `S3Indexes`,
        `S3Initial`, `S3PenultCands`, `S3Value`, `label`, `arcs`, `tonic`,
        `mode`, and `arcBasic`.
        """

        def __init__(self):
            self.ruleLabels = []
            self.parentheses = []
            self.openHeads = []
            self.buffer = []
            self.stack = []
            self.errors = []

            self.label = None
            self.notes = None
            self.lineType = None
            self.arcs = []
            self.arcDict = {}
            self.method = None
            self.S1Index = None
            self.S2Index = None
            self.S2Degree = None
            self.S2Value = None
            self.S3Index = None
            self.S3Indexes = None
            self.S3Final = None
            self.S3Initial = None
            self.S3PenultCands = None
            self.arcbasic = None
            self.species = None
            self.harmonicSpecies = False
            self.harmonicSpanDict = {}

        def __repr__(self):
            return self.label

        def performLineParse(self):
            """
            Create a complete interpretation of the line,
            using the following procedure:

            * Construct an arc for the basic structure,
              given the line type and
              a specific option for the basic structure.
            * Assign rules to notes in secondary structures.
            * Test for resolution of local insertions in third species.
            * Consolidate arcs into longer passing motions, if possible
            * Assemble lists for rule labels and parentheses, to be used
              when generating representations of the interpretation.
            * Set the dependency level of each note [if function enabled].
            """
            # log message
            logger.debug('Beginning parse: ' + str(self.label))

            if self.lineType == 'primary':
                self.parsePrimary()
            elif self.lineType == 'bass':
                self.parseBass()
            elif self.lineType == 'generic':
                self.parseGeneric()
            else:
                pass
            # Exit parse if no basic arc is found.
            if self.arcBasic is None:
                return self.errors
            else:
                pass

            # Assign rules to notes in secondary structures.
            self.assignSecondaryRules()
            # Test for resolution of local insertions in third species.
            self.testLocalResolutions()
            # Consolidate arcs into longer passing motions if possible.
            self.pruneArcs()
            # Calculate the structural level of each note and arc.
            if getStructuralLevels:
                self.setDependencyLevels()

            # Now that all arcs for the parse have been settled,
            # create an Arc object for each and populate the
            # parse's arc dictionary.
            self.gatherArcs()
            # Make lists for rule labels and parentheses.
            # Make tuples of note indices and labels/parentheses,
            # for running with musicxml input/output.
            self.gatherRuleLabels()
            self.gatherParentheses()
            # Calculate the hierarchical levels of the arcs
            self.setArcLevels()
            # log result
            parseData = ('Label: ' + self.label
                         + '\n\tBasic: ' + str(self.arcBasic)
                         + '\n\tArcs:  ' + str(self.arcs)
                         + '\n\tRules:\t'
                         + ''.join(['{:4d}'.format(lbl[0])
                                    for lbl in self.ruleLabels])
                         + '\n\t      \t'
                         + ''.join(['{:>4}'.format(lbl[1])
                                    for lbl in self.ruleLabels])
                         )
            if getStructuralLevels:
                parseData = (parseData
                             + '\n\t      \t'
                             + ''.join(['{:4d}'.format(lbl[2])
                                        for lbl in self.ruleLabels])
                             )
            logger.debug(parseData)
            if showWestergaardInterpretations:
                self.displayWestergaardParse()

        def arcMerge(self, arc1, arc2):
            """Combine two passing motions that share an inner
            node and direction."""
            # Merge elements into first arc and empty the second.
            # Revise dependencies.
            leftouter = self.notes[arc1[0]]
            rightinner = self.notes[arc1[-1]]
            leftinner = self.notes[arc2[0]]
            rightouter = self.notes[arc2[-1]]

            rules1 = [rightinner.csd.value == leftinner.csd.value]
            rules2 = [leftouter.csd.value
                      > rightinner.csd.value
                      > rightouter.csd.value,
                      leftouter.csd.value
                      < rightinner.csd.value
                      < rightouter.csd.value]
            if all(rules1) and any(rules2):
                # Merge arc2 elements into arc1
                removeDependenciesFromArc(self.notes, arc1)
                removeDependenciesFromArc(self.notes, arc2)
                # If arcs do not share node, make end of arc1 lefthead
                # of start of arc2.
                # Make a repetition arc.
                if arc1[-1] != arc2[0]:
                    self.notes[arc2[0]].dependency.lefthead = arc1[-1]
                    self.notes[arc1[-1]].dependency.dependents.append(arc2[0])
                    self.arcs.append([arc1[-1], arc2[0]])
                self.arcs.remove(arc2)
                arc2.pop(0)
                for n in arc2:
                    arc1.append(n)
                # Revise dependencies.
                addDependenciesFromArc(self.notes, arc1)

        def arcEmbed(self, arc1, arc2):
            """Embed a repetition inside a passing motion."""
            # In either order:
            # Start with repetition linked to passing, then embed.
            leftouter = self.notes[arc1[0]]
            rightinner = self.notes[arc1[-1]]
            leftinner = self.notes[arc2[0]]
            rightouter = self.notes[arc2[-1]]
            # The arcs share a node.
            rules1 = [rightinner.csd.value == leftinner.csd.value,
                      rightinner.index == leftinner.index]
            # Arc1 is a simple repetition and they share the same pitch
            # on the lefthead
            rules2 = [len(arc1) == 2,
                      leftouter.csd.value == leftinner.csd.value]
            # Arc2 is a simple repetition and they share the same pitch
            # on the lefthead
            rules3 = [len(arc2) == 2,
                      rightinner.csd.value == rightouter.csd.value]
            if all(rules1) and any(rules2):
                removeDependenciesFromArc(self.notes, arc2)
                arc2[0] = arc1[0]
                addDependenciesFromArc(self.notes, arc2)
            elif all(rules1) and any(rules3):
                removeDependenciesFromArc(self.notes, arc1)
                arc1[-1] = arc2[-1]
                addDependenciesFromArc(self.notes, arc1)

        def arcExtend(self, arc, extension):
            """Lengthen an arc by adding a note at extension index to
            the right or left."""
            removeDependenciesFromArc(self.notes, arc)
            if extension < arc[0]:
                arc.insert(0, extension)
            elif extension > arc[-1]:
                arc.append(extension)
            addDependenciesFromArc(self.notes, arc)

        def parsePrimary(self):
            """
            For monotriadic lines, use one of eight methods to
            find a basic step motion
            from a potential S2 (Kopfton):

            #. Look for one existing basic step motion arc that starts
               from S2.
            #. Look for an existing basic step motion arc that can be
               attached to S2 (repetition + passing)
            #. Look for two arcs that can be merged into a basic step
               motion (passing + passing).
            #. Look for three arcs that can be merged into a basic step
               motion (passing + passing + passing).
            #. Take an existing 5-4-3 arc (the longest spanned, if more
               than one) and try to find a connection -2-1 to complete
               a basic arc.
            #. Look for a nonfinal arc from S2 whose terminus ==
               S1.csd.value, and extend the arc to end on S1Index
               if possible.
            #. Reinterpret the line, looking for a descending step motion
               from S2 and then parsing the remaining notes.
               The least reliable method.

            For harmonic lines, use one of a dozen methods to merge a
            series of arcs into a basic step motion that connects with
            the final tonic.

            """
            # Once all preliminary parsing is done,
            # prepare for assigning basic structure
            self.arcs.sort()  # = sorted(self.arcList)
            self.arcBasic = None

            # If present, merge a final neighbor with a descending passing
            # motion if they share an internal node.
            # TODO probably doesnt work for third species
            if self.species not in ['third', 'fifth'] and integrateFinalNeighbor:
                if isNeighboringArc(self.arcs[-1], self.notes):
                    n_arc = self.arcs[-1]
                    p_arc = None
                    n_arc_dir = getNeighborType(n_arc, self.notes)
                    for arc in self.arcs:
                        if (arc[-1] == n_arc[0] and
                                getPassingType(arc,
                                               self.notes) == 'falling'):
                            p_arc = arc
                            break
                    # print(p_arc, n_arc)
                    if p_arc and n_arc_dir == 'lower':
                        self.arcEmbed(p_arc, n_arc)
                    elif p_arc and n_arc_dir == 'upper':
                        removeDependenciesFromArc(self.notes, n_arc)
                        self.arcs.remove(n_arc)
                        new_arc = [p_arc[0], n_arc[1], n_arc[2]]
                        self.arcs.append(new_arc)
                        addDependenciesFromArc(self.notes, new_arc)
                    # print(self.arcs)

            # METHOD 0
            # From any S2 candidate, look for one existing basic step motion
            # arc that starts from S2.
            if self.method == 0:
                for counter, arc1 in enumerate(self.arcs):
                    rules = [arc1[0] == self.S2Index,
                             arc1[-1] == self.S1Index]
                    if all(rules):
                        self.arcBasic = arc1

            # METHOD 1
            # From any S2 candidate look for an existing basic step motion arc
            # that can be attached to S2: repetition + passing.
            elif self.method == 1:
                for counter, arc1 in enumerate(self.arcs):
                    a = self.notes[arc1[0]]
                    b = self.notes[arc1[-1]]
                    rules = [a.index != self.S2Index,
                             a.csd.value == self.S2Value,
                             b.index == self.S1Index]
                    if all(rules):
                        a.dependency.lefthead = self.S2Index
                        arcGenerateRepetition(a.index, self.notes,
                                              self.arcs)
                        a.rule.name = 'E1'
                        for n in arc1[1:-1]:
                            self.notes[n].dependency.lefthead = self.S2Index
                            self.notes[
                                self.S2Index].dependency.dependents.append(n)
                            self.arcBasic = arc1[1:]
                            self.arcBasic.insert(0, self.S2Index)

            # 2020-05-30 Deleted old Method 2 because it is replaced by
            # the preparatory routine above

            # # METHOD 2
            # # May only work if S2 is sd3.  Look for two arcs that can fused
            # # into a basic step motion: passing + neighbor/repetition.
            # elif self.method == 2:
            #     for counter, arc1 in enumerate(self.arcs):
            #         rules1 = [arc1[0] == self.S2Index,
            #                   not arc1[-1] == self.S1Index]
            #         if all(rules1):
            #             for arc2 in self.arcs[counter + 1:]:
            #                 # Look for a passing plus neighboring to fuse.
            #                 rules2 = [
            #                     arc1[-1] == arc2[0],
            #                     arc2[-1] == self.S1Index,
            #                     (self.notes[arc1[0]].csd.value
            #                      > self.notes[arc1[-1]].csd.value),
            #                     (self.notes[arc2[0]].csd.value
            #                      == self.notes[arc2[-1]].csd.value)
            #                 ]
            #                 if all(rules2):
            #                     self.arcEmbed(arc1, arc2)
            #                     self.arcBasic = arc1

            # METHOD 2
            # If S2 = sd5, look for two arcs that can be merged into a basic
            # step motion: passing + passing.
            elif self.method == 2:
                for counter, arc1 in enumerate(self.arcs):
                    rules1 = [arc1[0] == self.S2Index,
                              self.notes[arc1[0]].csd.value == 4,
                              not arc1[-1] == self.S1Index]
                    if all(rules1):
                        # Look rightward for another arc from same degree.
                        for arc2 in self.arcs[counter + 1:]:
                            # Look for two passing motions to merge.
                            # TODO Write rules to handle cases where
                            # there are several possibilities.
                            rules2a = [
                                arc1[-1] == arc2[0],
                                arc2[-1] == self.S1Index,
                                (self.notes[arc1[0]].csd.value
                                 > self.notes[arc1[-1]].csd.value),
                                (self.notes[arc2[0]].csd.value
                                 > self.notes[arc2[-1]].csd.value)
                            ]
                            rules2b = [
                                arc1[-1] < arc2[0],
                                arc2[-1] == self.S1Index,
                                (self.notes[arc1[0]].csd.value
                                 > self.notes[arc1[-1]].csd.value),
                                (self.notes[arc2[0]].csd.value
                                 > self.notes[arc2[-1]].csd.value),
                                not isEmbeddedInOtherArc(arc2, self.arcs,
                                                         startIndex=arc1[-1])
                            ]
                            if all(rules2a) or all(rules2b):
                                self.arcMerge(arc1, arc2)
                                self.arcBasic = arc1

            # METHOD 3
            # If S2 = sd8, look for three arcs that can be merged into
            # a basic step motion: passing + passing + passing.
            elif self.method == 3:
                arcSegments = []
                for counter1, arc1 in enumerate(self.arcs):
                    rules1 = [arc1[0] == self.S2Index,
                              self.notes[arc1[0]].csd.value == 7,
                              (self.notes[arc1[0]].csd.value
                               > self.notes[arc1[-1]].csd.value),
                              not arc1[-1] == self.S1Index]
                    if all(rules1):
                        arcSegments.append(arc1)
                        # Look rightward for another arc from same degree
                        # that is also nonfinal
                        for counter2, arc2 in enumerate(
                                self.arcs[counter1 + 1:]):
                            # Look for two passing motions to merge.
                            # TODO Write rules to handle cases where there
                            # are several possibilities.
                            rules2 = [
                                # arc2 attaches to or is later than arc1
                                arc1[-1] <= arc2[0],
                                arc2[-1] != self.S1Index,
                                # arc1 is descending
                                (self.notes[arc1[0]].csd.value
                                 > self.notes[arc1[-1]].csd.value),
                                # arc2 is descending
                                (self.notes[arc2[0]].csd.value
                                 > self.notes[arc2[-1]].csd.value),
                                # arc1 is higher than arc2
                                (self.notes[arc1[-1]].csd.value
                                 >= self.notes[arc2[0]].csd.value),
                                # arc2 is non final
                                (self.notes[arc2[-1]].csd.value
                                 > self.notes[-1].csd.value),
                                # arc2 is not embedded in another arc
                                not isEmbeddedInOtherArc(arc2, self.arcs,
                                                         startIndex=arc1[-1])
                            ]
                            if all(rules2):
                                arcSegments.append(arc2)
                                for arc3 in self.arcs[counter2 + 1:]:
                                    # Look for two passing motions to merge.
                                    # TODO Write rules to handle cases
                                    # where there are several possibilities.
                                    rules3 = [
                                        arc2[-1] <= arc3[0],
                                        arc3[-1] == self.S1Index,
                                        (self.notes[arc2[0]].csd.value
                                         > self.notes[arc2[-1]].csd.value),
                                        (self.notes[arc3[0]].csd.value
                                         > self.notes[arc3[-1]].csd.value),
                                        not isEmbeddedInOtherArc(
                                            arc3,
                                            self.arcs,
                                            startIndex=arc2[-1])
                                    ]
                                    if all(rules3):
                                        arcSegments.append(arc3)
                                # if no third arc is found,
                                # break off the search
                                if len(arcSegments) < 3:
                                    break
                        if len(arcSegments) == 3:
                            arc1 = arcSegments[0]
                            arc2 = arcSegments[1]
                            arc3 = arcSegments[2]
                            self.arcMerge(arc1, arc2)
                            self.arcMerge(arc1, arc3)
                            self.arcBasic = arc1

            # METHOD 4
            # Take an existing 5-4-3 arc
            # (the longest spanned, if more than one)
            # and try to find a connection -2-1 to complete a basic arc.
            elif self.method == 4 and self.S2Value % 7 == 4:
                fiveThreeArcs = []
                for arc in self.arcs:
                    rules = [arc[0] == self.S2Index,
                             self.notes[arc[0]].csd.value == 4,
                             self.notes[arc[-1]].csd.value == 2]
                    if all(rules):
                        fiveThreeArcs.append(arc)
                arcSpan = 0
                for arc in fiveThreeArcs:
                    if arcLength(arc) > arcSpan:
                        arcSpan = arcLength(arc)
                selectedArcs = [arc for arc in fiveThreeArcs
                                if arcLength(arc) == arcSpan]
                if not selectedArcs:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return
                selectedArc = selectedArcs[0]
                sd3Index = selectedArc[-1]
                self.buffer = [n for n in self.notes[sd3Index:]
                               if not n.tie or n.tie.type == 'start']
                # Reverse the buffer and build basic step motion
                # from the end of the line.
                self.buffer.reverse()
                n = len(self.buffer)
                # Create an arc in reverse.
                basicArcCand = []
                basicArcNodeCand = None
                # Append S1 to basic arc.
                basicArcCand.append(self.S1Index)
                while n > 1:
                    shiftBuffer(self.stack, self.buffer)
                    n = len(self.buffer)
                    i = self.stack[-1]
                    j = self.buffer[0]
                    h = self.notes[basicArcCand[-1]]
                    # Look for descending step to S1.
                    if isStepDown(j, h) and j.csd.value < self.S2Value:
                        # Skip the pitch if it is a local repetition
                        # (prefer the lefthead).
                        if not isLocalRepetition(j.index, self.notes,
                                                 self.arcs):
                            basicArcCand.append(j.index)
                            break
                # Check for success.
                if len(basicArcCand) != 2:
                    error = ('No composite step motion found from this '
                             'S2 candidate: ' + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return
                else:
                    self.arcs.remove(selectedArc)
                    for x in basicArcCand:
                        selectedArc.append(x)
                    self.arcBasic = sorted(selectedArc)

            # METHOD 5
            # Look for a nonfinal arc from S2 whose terminus == S1.csd.value
            # and extend the arc to end on S1Index if possible.
            elif self.method == 5:
                for arc in self.arcs:
                    a = self.notes[arc[0]]
                    b = self.notes[arc[-1]]
                    rules = [a.index == self.S2Index,
                             b.csd.value == self.notes[self.S1Index].csd.value,
                             isEmbeddedInOtherArc(arc, self.arcs,
                                                  startIndex=arc[-1]) is False]
                    if all(rules):
                        clearDependencies(b)
                        arc[-1] = self.S1Index
                        self.arcBasic = arc

            # METHOD 6
            # If S2Value == 2, look for a nonfinal lower neighbor arc
            # that could be transformed into a passing to S1, and
            # extend the arc to end on S1Index if possible.
            elif self.method == 6:
                for arc in self.arcs:
                    a = self.notes[arc[0]]
                    b = self.notes[arc[-1]]
                    t = self.notes[arc[1]]
                    rules = [a.index == self.S2Index,
                             self.S2Value == 2,
                             len(arc) == 3,
                             b.csd.value == a.csd.value,
                             isStepDown(a, t),
                             isEmbeddedInOtherArc(arc, self.arcs) is False]
                    if all(rules):
                        clearDependencies(b)
                        arc[-1] = self.S1Index
                        self.arcBasic = arc

            # METHOD 7
            # Reinterpret the line, starting with the S2 candidate.
            # This is a radical solution that does not work well
            # and shouldn't really ignore all the preparse work.
            # Test cases: Westergaard070g.musicxml
            #             WP000
            #             WP309
            #             WP311
            # TODO Prefer S2 on beat in third species,
            # if there are two candidates in the same bar.
            # TODO currently turned off for harmonic species
            elif self.method == 7 and not self.harmonicSpecies:
                # Refill buffer with context from S2 to end of line.
                self.buffer = [n for n in self.notes[self.S2Index:]
                               if not n.tie or n.tie.type == 'start']
                # Reverse the buffer and build basic step motion
                # from the end of the line.
                self.buffer.reverse()
                n = len(self.buffer)
                # Create an arc in reverse.
                basicArcCand = []
                basicArcNodeCand = None
                # Append S1 to basic arc.
                basicArcCand.append(self.S1Index)
                while n > 1:
                    shiftBuffer(self.stack, self.buffer)
                    n = len(self.buffer)
                    i = self.stack[-1]
                    j = self.buffer[0]
                    h = self.notes[basicArcCand[-1]]
                    # Look for descending steps to S1.
                    if isStepDown(j, h) and j.csd.value < self.S2Value:
                        # If third species, determine whether the candidate
                        # is the righthead of a local repetition.
                        isLocalRighthead = False
                        if self.species == 'third' and not isTriadMember(j, stufe=0):
                            for arc in self.arcs:
                                if arc[-1] == j.index and self.notes[arc[0]].csd.value == self.notes[arc[-1]].csd.value:
                                    isLocalRighthead = True
                        # Skip righthead of local repetition.
                        if isLocalRighthead:
                            pass
                        # Otherwise add note index to basic arc
                        else:
                            basicArcCand.append(j.index)
                    elif isStepDown(j, h) and j.csd.value == self.S2Value:
                        # Skip the pitch if it is a repetition of S2
                        # (prefer the lefthead).
                        if not isRepetition(j.index, self.notes, self.arcs):
                            basicArcCand.append(self.S2Index)
                            break
                # The following procedure prefers to locate tonic triad S3
                # nodes earlier rather than later.  May have to be overriden
                # when harmonizing counterpoint with bass line.
                # If looking for a step motion from 5 or 8:
                if self.S2Value > 2:
                    # Refill the buffer from S2 to end of line.
                    self.buffer = [n for n in self.notes[self.S2Index:]
                                   if not n.tie or n.tie.type == 'start']
                    # Reverse the buffer and look for tonic triad nodes.
                    self.buffer.reverse()
                    n = len(self.buffer)
                    while n > 1:
                        shiftBuffer(self.stack, self.buffer)
                        n = len(self.buffer)
                        i = self.stack[-1]
                        j = self.buffer[0]
                        if (isTriadMember(j, stufe=0)
                                and j.index in basicArcCand):
                            # Get the index of the preceding element
                            # in the basic step motion.
                            x = basicArcCand.index(j.index) - 1
                            prevS = basicArcCand[x]
                            for arc in self.arcs:
                                a = self.notes[arc[0]]
                                b = self.notes[arc[-1]]
                                if (prevS < a.index < j.index
                                        and prevS < b.index < j.index):
                                    # Grab the a head if possible.
                                    if a.csd.value == j.csd.value:
                                        j.dependency.lefthead = a.index
                                        arcGenerateRepetition(j.index,
                                                              self.notes,
                                                              self.arcs)
                                        j.rule.name = 'E1'
                                        self.arcEmbed(arc, [a.index, j.index])
                                        basicArcCand[prevS + 1] = a.index
                                    # Settle for the b head if possible.
                                    elif b.csd.value == j.csd.value:
                                        j.dependency.lefthead = b.index
                                        arcGenerateRepetition(j.index,
                                                              self.notes,
                                                              self.arcs)
                                        j.rule.name = 'E1'
                                        basicArcCand[x + 1] = b.index
                # Check to make sure the basic step motion is complete.
                if len(basicArcCand) != (self.S2Value + 1):
                    error = ('No basic step motion found from this S2 '
                             'candidate: ' + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return
                else:
                    self.arcBasic = list(reversed(basicArcCand))
                self.purgeCrossedArcs()

            # METHOD 8
            # 8-6, 6-4, 4-2, 1
            # TODO what if offPre is None???
            elif self.method == 8 and self.S2Value == 7:
                eightSixArcs = []
                sixFourArcs = []
                fourTwoArcs = []
                offPre = self.harmonicSpanDict['offsetPredominant']
                offDom = self.harmonicSpanDict['offsetDominant']
                if offPre is None:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return
                for arc in self.arcs:
                    rules1 = [arc[0] == self.S2Index,
                              self.notes[arc[0]].csd.value == 7,
                              self.notes[arc[-1]].csd.value == 5]
                    rules2 = [self.notes[arc[0]].csd.value == 5,
                              self.notes[arc[-1]].csd.value == 3,
                              offPre <= self.notes[arc[0]].offset < offDom]
                    rules3 = [self.notes[arc[0]].csd.value == 3,
                              self.notes[arc[-1]].csd.value == 1]
                    if all(rules1):
                        eightSixArcs.append(arc)
                    if all(rules2):
                        sixFourArcs.append(arc)
                    if all(rules3):
                        fourTwoArcs.append(arc)
                arcBasicCandidates = []
                if eightSixArcs and sixFourArcs and fourTwoArcs:
                    for arc1 in eightSixArcs:
                        for arc2 in sixFourArcs:
                            if arc2[0] >= arc1[-1]:
                                for arc3 in fourTwoArcs:
                                    if arc3[0] >= arc2[-1]:
                                        self.arcMerge(arc1, arc2)
                                        self.arcMerge(arc1, arc3)
                                        self.arcExtend(arc1, self.S1Index)
                                        arcBasicCandidates.append(arc1)
                if arcBasicCandidates:
                    # TODO for now, return just the first basic arc found
                    self.arcBasic = arcBasicCandidates[0]
                else:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return

            # METHOD 9: 8-4, 4-2, 1
            # 2 occurs in the dominant
            elif self.method == 9 and self.S2Value == 7:
                eightFourArcs = []
                fourTwoArcs = []
                offPre = self.harmonicSpanDict['offsetPredominant']
                offDom = self.harmonicSpanDict['offsetDominant']
                if offPre is None:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return
                for arc in self.arcs:
                    rules1 = [arc[0] == self.S2Index,
                              self.notes[arc[0]].csd.value == 7,
                              self.notes[arc[-1]].csd.value == 3,
                              offPre <= self.notes[arc[0]].offset < offDom]
                    rules3 = [self.notes[arc[0]].csd.value == 3,
                              self.notes[arc[-1]].csd.value == 1,
                              offDom <= self.notes[arc[0]].offset]
                    if all(rules1):
                        eightFourArcs.append(arc)
                    if all(rules3):
                        fourTwoArcs.append(arc)
                arcBasicCandidates = []
                if eightFourArcs and fourTwoArcs:
                    for arc1 in eightFourArcs:
                        for arc2 in fourTwoArcs:
                            if arc2[0] >= arc1[-1]:
                                self.arcMerge(arc1, arc2)
                                self.arcExtend(arc1, self.S1Index)
                                arcBasicCandidates.append(arc1)
                if arcBasicCandidates:
                    # TODO for now, return just the first basic arc found
                    self.arcBasic = arcBasicCandidates[0]
                else:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return

            # METHOD 10: 8-4, 4-2, 1
            # 2 occurs in the predominant
            elif self.method == 10 and self.S2Value == 7:
                eightFourArcs = []
                fourTwoArcs = []
                offPre = self.harmonicSpanDict['offsetPredominant']
                offDom = self.harmonicSpanDict['offsetDominant']
                if offPre is None:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return
                for arc in self.arcs:
                    rules1 = [arc[0] == self.S2Index,
                              self.notes[arc[0]].csd.value == 7,
                              self.notes[arc[-1]].csd.value == 3,
                              offPre <= self.notes[arc[0]].offset < offDom]
                    rules3 = [self.notes[arc[0]].csd.value == 3,
                              self.notes[arc[-1]].csd.value == 1,
                              offPre <= self.notes[arc[0]].offset < offDom]
                    if all(rules1):
                        eightFourArcs.append(arc)
                    if all(rules3):
                        fourTwoArcs.append(arc)
                arcBasicCandidates = []
                if eightFourArcs and fourTwoArcs:
                    for arc1 in eightFourArcs:
                        for arc2 in fourTwoArcs:
                            if arc2[0] >= arc1[-1]:
                                self.arcMerge(arc1, arc2)
                                self.arcExtend(arc1, self.S1Index)
                                arcBasicCandidates.append(arc1)
                if arcBasicCandidates:
                    # TODO for now, return just the first basic arc found
                    self.arcBasic = arcBasicCandidates[0]
                else:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return

            # METHOD 11: 8-5,--, 5-2, 1
            elif self.method == 11 and self.S2Value == 7:
                eightFiveArcs = []
                fiveTwoArcs = []
                offDom = self.harmonicSpanDict['offsetDominant']
                for arc in self.arcs:
                    rules1 = [arc[0] == self.S2Index,
                              self.notes[arc[0]].csd.value == 7,
                              self.notes[arc[-1]].csd.value == 4]
                    rules3 = [self.notes[arc[0]].csd.value == 4,
                              self.notes[arc[-1]].csd.value == 1,
                              offDom <= self.notes[arc[-1]].offset]
                    if all(rules1):
                        eightFiveArcs.append(arc)
                    if all(rules3):
                        fiveTwoArcs.append(arc)
                arcBasicCandidates = []
                if eightFiveArcs and fiveTwoArcs:
                    for arc1 in eightFiveArcs:
                        for arc2 in fiveTwoArcs:
                            if arc2[0] >= arc1[-1]:
                                self.arcMerge(arc1, arc2)
                                self.arcExtend(arc1, self.S1Index)
                                arcBasicCandidates.append(arc1)
                if arcBasicCandidates:
                    # TODO for now, return just the first basic arc found
                    self.arcBasic = arcBasicCandidates[0]
                else:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return

            # METHOD 12: 8-5,4-2, 1
            # 2 occurs in the dominant
            elif self.method == 12 and self.S2Value == 7:
                eightFiveArcs = []
                fourTwoArcs = []
                offPre = self.harmonicSpanDict['offsetPredominant']
                offDom = self.harmonicSpanDict['offsetDominant']
                if offPre is None:
                    return
                for arc in self.arcs:
                    rules1 = [arc[0] == self.S2Index,
                              self.notes[arc[0]].csd.value == 7,
                              self.notes[arc[-1]].csd.value == 4]
                    rules3 = [self.notes[arc[0]].csd.value == 3,
                              self.notes[arc[-1]].csd.value == 1,
                              offPre <= self.notes[arc[0]].offset,
                              offDom <= self.notes[arc[-1]].offset]
                    if all(rules1):
                        eightFiveArcs.append(arc)
                    if all(rules3):
                        fourTwoArcs.append(arc)
                arcBasicCandidates = []
                if eightFiveArcs and fourTwoArcs:
                    for arc1 in eightFiveArcs:
                        for arc2 in fourTwoArcs:
                            if arc2[0] >= arc1[-1]:
                                self.arcExtend(arc1, arc2[0])
                                self.arcMerge(arc1, arc2)
                                self.arcExtend(arc1, self.S1Index)
                                arcBasicCandidates.append(arc1)
                if arcBasicCandidates:
                    # TODO for now, return just the first basic arc found
                    self.arcBasic = arcBasicCandidates[0]
                else:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return

            # METHOD 13: 8-5,4-2, 1
            # 2 occurs in the predominant
            elif self.method == 13 and self.S2Value == 7:
                eightFiveArcs = []
                fourTwoArcs = []
                offPre = self.harmonicSpanDict['offsetPredominant']
                offDom = self.harmonicSpanDict['offsetDominant']
                if offPre is None:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return
                for arc in self.arcs:
                    rules1 = [arc[0] == self.S2Index,
                              self.notes[arc[0]].csd.value == 7,
                              self.notes[arc[-1]].csd.value == 4]
                    rules3 = [self.notes[arc[0]].csd.value == 3,
                              self.notes[arc[-1]].csd.value == 1,
                              offPre <= self.notes[arc[0]].offset,
                              self.notes[arc[-1]].offset < offDom]
                    if all(rules1):
                        eightFiveArcs.append(arc)
                    if all(rules3):
                        fourTwoArcs.append(arc)
                arcBasicCandidates = []
                if eightFiveArcs and fourTwoArcs:
                    for arc1 in eightFiveArcs:
                        for arc2 in fourTwoArcs:
                            if arc2[0] >= arc1[-1]:
                                self.arcExtend(arc1, arc2[0])
                                self.arcMerge(arc1, arc2)
                                self.arcExtend(arc1, self.S1Index)
                                arcBasicCandidates.append(arc1)
                if arcBasicCandidates:
                    # TODO for now, return just the first basic arc found
                    self.arcBasic = arcBasicCandidates[0]
                else:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return

            # METHOD 14: 5-2, 1
            # 2 occurs in the preDom
            elif self.method == 14 and self.S2Value % 7 == 4:
                fiveTwoArcs = []
                offPre = self.harmonicSpanDict['offsetPredominant']
                offDom = self.harmonicSpanDict['offsetDominant']
                if offPre is None:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return
                for arc in self.arcs:
                    rules = [arc[0] == self.S2Index,
                             self.notes[arc[0]].csd.value == 4,
                             self.notes[arc[-1]].csd.value == 1,
                             offPre <= self.notes[arc[0]].offset < offDom]
                    if all(rules):
                        fiveTwoArcs.append(arc)
                arcBasicCandidates = []
                if fiveTwoArcs:
                    for arc1 in fiveTwoArcs:
                        self.arcExtend(arc1, self.S1Index)
                        arcBasicCandidates.append(arc1)
                if arcBasicCandidates:
                    # TODO for now, return just the first basic arc found
                    self.arcBasic = arcBasicCandidates[0]
                else:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return

            # METHOD 15: 5-2, 1
            # 2 occurs in the dominant
            elif self.method == 15 and self.S2Value % 7 == 4:
                fiveTwoArcs = []
                offDom = self.harmonicSpanDict['offsetDominant']
                for arc in self.arcs:
                    rules = [arc[0] == self.S2Index,
                             self.notes[arc[0]].csd.value == 4,
                             self.notes[arc[-1]].csd.value == 1,
                             offDom <= self.notes[arc[0]].offset]
                    if all(rules):
                        fiveTwoArcs.append(arc)
                arcBasicCandidates = []
                if fiveTwoArcs:
                    for arc1 in fiveTwoArcs:
                        self.arcExtend(arc1, self.S1Index)
                        arcBasicCandidates.append(arc1)
                if arcBasicCandidates:
                    # TODO for now, return just the first basic arc found
                    self.arcBasic = arcBasicCandidates[0]
                else:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return

            # METHOD 16: 5, 4-2, 1
            # 2 occurs in the predominant
            elif self.method == 16 and self.S2Value % 7 == 4:
                fourTwoArcs = []
                offPre = self.harmonicSpanDict['offsetPredominant']
                offDom = self.harmonicSpanDict['offsetDominant']
                if offPre is None:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return
                for arc in self.arcs:
                    rules = [self.notes[arc[0]].csd.value == 3,
                             self.notes[arc[-1]].csd.value == 1,
                             offPre <= self.notes[arc[0]].offset < offDom]
                    if all(rules):
                        fourTwoArcs.append(arc)
                arcBasicCandidates = []
                if self.S2Value == 4 and fourTwoArcs:
                    for arc1 in fourTwoArcs:
                        self.arcExtend(arc1, self.S2Index)
                        self.arcExtend(arc1, self.S1Index)
                        arcBasicCandidates.append(arc1)
                if arcBasicCandidates:
                    # TODO for now, return just the first basic arc found
                    self.arcBasic = arcBasicCandidates[0]
                else:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return

            # METHOD 17: 5, 4-2, 1
            # 2 occurs in the dominant
            elif self.method == 17 and self.S2Value % 7 == 4:
                fourTwoArcs = []
                offDom = self.harmonicSpanDict['offsetDominant']
                for arc in self.arcs:
                    rules = [self.notes[arc[0]].csd.value == 3,
                             self.notes[arc[-1]].csd.value == 1,
                             offDom <= self.notes[arc[0]].offset]
                    if all(rules):
                        fourTwoArcs.append(arc)
                arcBasicCandidates = []
                if self.S2Value == 4 and fourTwoArcs:
                    for arc1 in fourTwoArcs:
                        self.arcExtend(arc1, self.S2Index)
                        self.arcExtend(arc1, self.S1Index)
                        arcBasicCandidates.append(arc1)
                if arcBasicCandidates:
                    # TODO for now, return just the first basic arc found
                    self.arcBasic = arcBasicCandidates[0]
                else:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return

            # METHOD 18: 3, 2, 1
            # 2 occurs in the dominant
            elif self.method == 18 and self.S2Value % 7 == 2:
                offDom = self.harmonicSpanDict['offsetDominant']
                s3cands = [n.index for n in self.notes
                           if (offDom <= n.offset
                               and n.csd.value == self.S2Value - 1)]
                if s3cands:
                    for idx in s3cands:
                        # take the earliest non-embedded sd2
                        if not isEmbeddedInArcs(idx, self.arcs):
                            self.arcBasic = [self.S2Index, idx, self.S1Index]
                            break
                if self.arcBasic is None:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return

            # METHOD 19: 3, 2, 1
            # 2 occurs in the predominant
            elif self.method == 19 and self.S2Value % 7 == 2:
                offPre = self.harmonicSpanDict['offsetPredominant']
                offDom = self.harmonicSpanDict['offsetDominant']
                if offPre is None:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return
                s3cands = [n.index for n in self.notes
                           if (offPre <= n.offset < offDom
                               and n.csd.value == self.S2Value - 1)]
                if s3cands:
                    for idx in s3cands:
                        # take the earliest non-embedded sd2
                        if not isEmbeddedInArcs(idx, self.arcs):
                            self.arcBasic = [self.S2Index, idx, self.S1Index]
                            break
                if self.arcBasic is None:
                    error = ('No composite step motion found from '
                             'this S2 candidate: '
                             + str(self.S2Value + 1) + '.')
                    self.errors.append(error)
                    return

            # report error if no basic arc found after method is applied:
            if self.arcBasic is None:
                error = ('No basic step motion found from this S2 '
                         'candidate: ' + str(self.S2Value + 1) + '.')
                self.errors.append(error)
                return
            # If a basic arc is created, set the rule labels for S3 notes.
            else:
                for n in self.arcBasic[1:-1]:
                    self.notes[n].rule.name = 'S3'
            self.S3Indexes = [note.index for note in self.notes
                              if note.rule.name == 'S3']
            self.S3Initial = min(self.S3Indexes)
            self.S3Final = max(self.S3Indexes)

            # If there are open heads before onset of S3 that have the
            # same pitch as S2, attach them as repetitions of S2
            self.attachOpenheadsToStructuralLefthead(self.S2Index,
                                                     self.S3Initial)

            # If there are open heads after the onset of a tonic-triad S3
            # that have the
            # same pitch as that S3, attach them as repetitions of that S3
            if len(self.arcBasic) == 5:
                self.attachOpenheadsToStructuralLefthead(self.arcBasic[2],
                                                         self.arcBasic[3])
            if len(self.arcBasic) == 8:
                self.attachOpenheadsToStructuralLefthead(self.arcBasic[3],
                                                         self.arcBasic[4])
                self.attachOpenheadsToStructuralLefthead(self.arcBasic[5],
                                                         self.arcBasic[6])
            self.purgeCrossedArcs()

            logger.debug('Method ' + str(self.method)
                         + ' for creating basic step motion.'
                         + '\n\tBasic arc: ' + str(self.arcBasic)
                         + '\n\tArcs:      ' + str(self.arcs))

            # TODO: Reset Note attributes.
            # Look for secondary structures between S nodes.

        def parseBass(self):
            """Test whether a specific dominant pitch can function as S3."""
            # Once all preliminary parsing is done,
            # prepare for assigning basic structure.
            self.arcs.sort()
            self.arcBasic = [0, self.S3Index, self.S1Index]
            # See whether any open heads can be attached as repetitions
            # of S2 or S3.
            self.attachOpenheadsToStructuralLefthead(0, self.S3Index)
            self.attachOpenheadsToStructuralLefthead(self.S3Index,
                                                     self.S1Index)
            self.purgeCrossedArcs()
            # # TODO Figure out and explain why it is necessary
            # #  to look for crossed arcs here. Only affects third species.
            # #  Weird result in WP024, but better results in
            #     # TODO: Reset Note attributes.
            #     # TODO Remove anticipations of S3.


        def parseGeneric(self):
            """The line has already passed the generic test, so all that is to
            be done is: determine whether there is a basic step motion
            connecting the first and last notes.
            """
            # Once preliminary parsing is done, prepare for assigning basic
            # structure and see whether a basic step motion is absent,
            # ascending, or descending.
            self.arcs.sort()
            self.arcBasic = None
            # TODO 2022-05-29 consider removing calculation of direction
            #  since this variable is not used in this function
            basicArcDirection = None
            if self.notes[0].csd.value == self.notes[-1].csd.value:
                self.arcBasic = [self.S2Index, self.S1Index]
            elif self.notes[0].csd.value > self.notes[-1].csd.value:
                basicArcDirection = 'descending'
            elif self.notes[0].csd.value < self.notes[-1].csd.value:
                basicArcDirection = 'ascending'
            # If they are different, search for a basic step motion,
            # and if not there,
            # reinterpret the arcs between start and end of tune.
            if not self.arcBasic:
                for counter, arc1 in enumerate(self.arcs):
                    a = self.notes[arc1[0]]
                    b = self.notes[arc1[-1]]
                    # Look for one existing basic step motion arc
                    # that starts from S2
                    if (arc1[0] == self.S2Index
                            and arc1[-1] == self.S1Index
                            and isPassingArc(arc1, self.notes)):
                        for elem in arc1[1:-1]:
                            self.notes[elem].rule.name = 'S3'
                        self.arcBasic = arc1
                        break
                    # Look for an existing basic step motion arc
                    # that can be attached to S2.
                    elif (a.csd.value == self.S2Value
                          and b.index == self.S1Index
                          and isPassingArc(arc1, self.notes)):
                        arc1[0] = self.S2Index
                        a.dependency.lefthead = self.S2Index
                        arcGenerateRepetition(a.index, self.notes,
                                              self.arcs)
                        a.rule.name = 'E1'
                        for n in arc1[1:-1]:
                            self.notes[n].dependency.lefthead = self.S2Index
                            self.notes[self.S2Index].dependency.dependents.append(
                                n)
                            self.notes[n].rule.name = 'S3'
                            self.arcBasic = arc1
                            break
                        break
                    # Look for two arcs that can be embedded or merged
                    # into a basic step motion.
                    elif arc1[0] == self.S2Index and not arc1[-1] == self.S1Index:
                        # First look rightward for another arc from same degree.
                        for arc2 in self.arcs[counter + 1:]:
                            rules1 = [arc1[-1] == arc2[0],
                                      arc2[-1] == self.S1Index]
                            rules2 = [self.notes[arc1[0]].csd.value
                                      > self.notes[arc1[-1]].csd.value,
                                      self.notes[arc2[0]].csd.value
                                      > self.notes[arc2[-1]].csd.value]
                            rules3 = [self.notes[arc1[0]].csd.value
                                      < self.notes[arc1[-1]].csd.value,
                                      self.notes[arc2[0]].csd.value
                                      < self.notes[arc2[-1]].csd.value]
                            if all(rules1) and (all(rules2) or all(rules3)):
                                self.arcMerge(arc1, arc2)
                                for elem in arc1[1:-1]:
                                    self.notes[elem].rule.name = 'S3'
                                self.arcBasic = arc1
                                break
                            # Merge.
                            elif (self.arcBasic and
                                  (self.notes[arc2[0]
                                              == self.notes[
                                                  self.S1Index].csd.value])):
                                self.arcBasic.pop()
                                self.arcBasic.append(arc2[-1])
                            rules4 = [self.notes[arc1[-1]].csd.value
                                      == self.notes[arc2[0]].csd.value]
                            if all(rules4) and (all(rules2) or all(rules3)):
                                # TODO: Finish this.
                                pass
                                # Attach arc2 to arc1 and then merge.
                                # This may not be needed if earlier
                                # parsing picks up the repetition.
            # Attach repetitions of S2 before onset of S1.
            # TODO Refine generic basic arc and coherence.
            self.attachOpenheadsToStructuralLefthead(self.S2Index,
                                                     self.S1Index)
            # If all else fails, just use first and last notes
            # as the basic arc.
            if self.arcBasic is None:
                self.arcBasic = [self.S2Index, self.S1Index]

        def purgeCrossedArcs(self):
            # Because some methods of inferring a basic arc can contradict
            # arcs in the preliminary arc list, find and remove
            # any secondary arcs that conflict with basic arc.
            if self.arcBasic is None:
                pass
            else:
                # Remove arcs that cross basic arc nodes.
                self.arcs.sort()
                purgeList = []
                # Look for arc that crosses initial node of basic arc
                for arc in self.arcs:
                    if arc[0] < self.arcBasic[0] < arc[-1]:
                        purgeList.append(arc)
                # arc crosses internal nodes of basic arc
                ints = pairwise(self.arcBasic)
                for int in ints:
                    a = int[0]
                    b = int[1]
                    for arc in self.arcs:
                        if a <= arc[0] < b < arc[-1] > b and arc != self.arcBasic:
                            purgeList.append(arc)
                if purgeList:
                    logger.debug(f'Basic arc: {self.arcBasic}')
                    logger.debug(f'Purging crossed arcs: {purgeList}')
                for arc in purgeList:
                    removeDependenciesFromArc(self.notes, arc)
                    self.arcs.remove(arc)
                # Add basic step motion arc if not already in arcs.
                if self.arcBasic not in self.arcs:
                    self.arcs.append(self.arcBasic)
                    addDependenciesFromArc(self.notes, self.arcBasic)

        def attachOpenheadsToStructuralLefthead(self, structuralLefthead,
                                                rightLimit):
            """Examine the span between a structural lefthead and a righthand
            limit, looking for notes that are either head of an arc
            (left or right) or not embedded in an arc,
            and can be taken as a repetition of the structural lefthead.
            This function increases the coherence of a parse.
            """
            self.buffer = [n for n in self.openHeads
                           if structuralLefthead < n.index < rightLimit]
            self.stack = []
            n = len(self.buffer)
            while n > 0:
                shiftBuffer(self.stack, self.buffer)
                n = len(self.buffer)
                i = self.stack[-1]
                # The scale degrees match.
                rules1 = [i.csd.value
                          == self.notes[structuralLefthead].csd.value]
                # It's an arc terminal not already marked as E1.
                rules2 = [isArcTerminal(i.index, self.arcs),
                          i.rule.name != 'E1']
                # It's an independent note.
                rules3 = [not isEmbeddedInArcs(i.index, self.arcs),
                          self.notes[i.index].dependency.lefthead is None,
                          self.notes[i.index].dependency.righthead is None]
                # It's not already in an arc initiated
                # by the structural lefthead.
                rules4 = [not areArcTerminals(structuralLefthead,
                                              i.index, self.arcs)]
                if all(rules1) and (all(rules2)
                                    or all(rules3)) and all(rules4):
                    self.notes[
                        i.index].dependency.lefthead = structuralLefthead
                    self.notes[0].dependency.dependents.append(i.index)
                    self.notes[i.index].rule.name = 'E1'
                    arcGenerateRepetition(i.index, self.notes,
                                          self.arcs)
                    # TODO Consider working on this.
                    if all(rules2):
                        # May also want to transfer dependent neighbors to the
                        # newly created repetition arcs
                        pass

        def integrateSecondaryWithPrimary(self):
            """Revise an intepretation to make it tighter, more efficient,
            more coherent. Connect secondary structures to elements of the
            basic structure where possible. [Not yet implemented.]
            """
            # TODO Implement Westergaard preferences for coherent
            #   interpretations, pp. 63ff.
            pass

        def assignSecondaryRules(self):
            """Find any note that does not yet have a rule assigned and
            determine the appropriate rule based on its dependency.
            """
            # TODO rewrite for harmonic species
            for i in self.notes:
                idl = i.dependency.lefthead
                idr = i.dependency.righthead
                if (i.rule.name is None and
                        ((i.tie and i.tie.type == 'start') or not i.tie)):
                    # CASE ONE: Look for passing and neighboring arcs.
                    if (idl is not None and
                            idr is not None):
                        # For neighboring arcs, determine whether
                        # the heads are tonic-triad pitches or not.
                        if (self.notes[idl].csd.value ==
                                self.notes[idr].csd.value):
                            if isTriadMember(self.notes[idr], 0):
                                i.rule.name = 'E2'
                                if self.notes[idr].rule.name is None:
                                    self.notes[idr].rule.name = 'E1'
                            else:
                                i.rule.name = 'L2'
                                if self.notes[idr].rule.name is None:
                                    self.notes[idr].rule.name = 'L1'
                        # For passing arcs
                        else:
                            i.rule.name = 'E4'
                            if (self.notes[idr].rule.name is None and
                                    isTriadMember(self.notes[idr], 0)):
                                self.notes[idr].rule.name = 'E3'

                    # CASE TWO: Repetitions.
                    elif (idl is not None and
                          idr is None):
                        if (self.notes[idl].csd.value
                                == i.csd.value):
                            if isTriadMember(i, 0):
                                i.rule.name = 'E1'
                            else:
                                i.rule.name = 'L1'

                    # CASE UNKNOWN:
                    elif idl != idr:
                        # What's the function of this section?
                        i.rule.name = 'Ex'

                    # CASE THREE: Independent notes, global and local.
                    if (idl is None
                            and idr is None):
                        if isTriadMember(i, 0):
                            i.rule.name = 'E3'
                            i.noteheadParenthesis = True
                        elif (not isTriadMember(i, 0) and
                              (self.species in ['third', 'fifth']
                               or self.harmonicSpecies)):
                            i.rule.name = 'L3'
                            i.noteheadParenthesis = True
                        else:
                            error = ('The pitch ' + i.nameWithOctave +
                                     ' in measure ' + str(i.measureNumber) +
                                     ' is not generable.')
                            self.errors.append(error)
                    # TODO: the following may be redundant
                    elif i.dependency.dependents is None:
                        if isTriadMember(i, 0):
                            i.rule.name = 'E3'
                            i.noteheadParenthesis = True
                        elif (not isTriadMember(i, 0) and
                              (self.species in ['third', 'fifth']
                               or self.harmonicSpecies)):
                            i.rule.name = 'L3'
                            i.noteheadParenthesis = True
                        else:
                            error = ('The pitch ' + i.nameWithOctave +
                                     'in measure ' + str(i.measureNumber)
                                     + 'is not generable.')
                            self.errors.append(error)

                if i.rule.name == 'E3' and i.dependency.dependents == []:
                    i.noteheadParenthesis = True
                # TODO Figure out why some notes still don't have rules.
                elif i.rule.name is None and i.tie:
                    if i.tie.type != 'stop':
                        i.rule.name = 'X'
                elif i.rule.name is None:
                    i.rule.name = 'x'

        def testLocalResolutions(self):
            """For any note identified as a local insertion (rule L3),
            determine whether it is subsequently displaced stepwise to a
            tonic triad pitch. Record an error if not.
            """
            for i in self.notes:
                if i.rule.name == 'L3':
                    remainder = [n for n in self.notes if n.index > i.index]
                    resolved = False
                    for r in remainder:
                        if isTriadMember(i, 0):
                            resolved = True
                            break
                        elif isDirectedStep(i, r):
                            if isTriadMember(r, 0):
                                resolved = True
                                break
                            else:
                                new_remainder = [n for n in self.notes
                                                 if n.index > r.index]
                                for s in new_remainder:
                                    if (isDirectedStep(r, s)
                                            and isTriadMember(s, 0)):
                                        resolved = True
                                break
                    if not resolved:
                        error = ('The local insertion ' + i.nameWithOctave +
                                 ' in measure ' + str(i.measureNumber) +
                                 ' is not resolved.')
                        self.errors.append(error)
                    if self.lineType == 'bass' and self.harmonicSpecies:
                        if i.index > self.S3Index and i.csd.value % 7 != 5:
                            error = ('Illegal insertion after S3 in harmonic '
                                     'bass line')
                            self.errors.append(error)

        def pruneArcs(self):
            # Find arcs to merge into longer passing motions.
            for arc1 in self.arcs:
                for arc2 in self.arcs:
                    rules1 = [arc1[-1] == arc2[0],
                              self.notes[arc1[-1]].rule.name[0] != 'S',
                              isLinearConsonance(self.notes[arc1[0]],
                                                 self.notes[arc2[-1]])]
                    # TODO Consider changing the conditions
                    # to isPassingArc and in same direction.
                    rules2 = [self.notes[arc1[0]].csd.value
                              > self.notes[arc1[-1]].csd.value,
                              self.notes[arc2[0]].csd.value
                              > self.notes[arc2[-1]].csd.value]
                    rules3 = [self.notes[arc1[0]].csd.value
                              < self.notes[arc1[-1]].csd.value,
                              self.notes[arc2[0]].csd.value
                              < self.notes[arc2[-1]].csd.value]
                    if all(rules1) and (all(rules2) or all(rules3)):
                        mergePairOption = (arc1, arc2)
                        # Make sure that neither arc is embedded
                        # in another arc.
                        for arc in self.arcs:
                            arc1Embedded = False
                            arc2Embedded = False
                            if (mergePairOption[0][-1] == arc[-1] and
                                    arc[0] < mergePairOption[0][0]):
                                arc1Embedded = True
                                break
                            if (mergePairOption[1][0] == arc[0] and
                                    arc[-1] > mergePairOption[1][-1]):
                                arc2Embedded = True
                                break
                        # If neither is embedded, merge the two.
                        if not arc1Embedded and not arc2Embedded:
                            self.arcMerge(mergePairOption[0],
                                          mergePairOption[1])
                            # TODO Is it necessary to set the rules here?
                            # What about the removed node?
                            # Should it also be set to 'E4'?
                            for elem in mergePairOption[0][1:-1]:
                                self.notes[elem].rule.name = 'E4'

        def gatherArcs(self):
            arc_label_counter = 0
            for elem in sorted(self.arcs):
                dict_entry = arc.Arc(elem)
                # set category
                arc_category = None
                if elem == self.arcBasic:
                    arc_category = 'basic'
                else:
                    arc_category = 'secondary'
                dict_entry.category = arc_category
                # set type
                arc_type = None
                if not arc_type:
                    if isRepetitionArc(elem, self.notes):
                        arc_type = 'repetition'
                    elif isNeighboringArc(elem, self.notes):
                        arc_type = 'neighbor'
                    elif isPassingArc(elem, self.notes):
                        arc_type = 'passing'
                    elif self.lineType == 'bass' and arc_category == 'basic':
                        arc_type = 'arpeggiation'
                dict_entry.type = arc_type
                # determine the subtype, if any
                arc_subtype = ''
                if arc_type == 'neighbor':
                    arc_subtype = getNeighborType(elem, self.notes)
                if arc_type == 'passing':
                    arc_subtype = getPassingType(elem, self.notes)
                dict_entry.subtype = arc_subtype
                # find csd content of arc
                arc_content = []
                for idx in elem:
                    arc_content.append(self.notes[idx].csd.value)
                dict_entry.content = arc_content
                # add arc to parse's arc dictionary
                self.arcDict[arc_label_counter] = dict_entry
                arc_label_counter += 1

        def gatherRuleLabels(self):
            for elem in self.notes:
                if not elem.tie or elem.tie.type == 'start':
                    self.ruleLabels.append((elem.index, elem.rule.name,
                                            elem.rule.level))
            return

        def gatherParentheses(self):
            for elem in self.notes:
                if elem.noteheadParenthesis:
                    self.parentheses.append((elem.index, True))
                else:
                    self.parentheses.append((elem.index, False))
            return

        def setDependencyLevels(self):
            """Review a completed parse and determine the
            structural level of each note.

            #. Assign levels to notes in the basic arc.

            #. Set the level of the first note if not in the basic arc.

            #. Collect all the secondary arcs.  Examine each arc and make a
               list of all the spans filled with notes that are not
               components of the arc.

            #. Look at every span in the list, and see whether a dependent
               arc fits into it. This is the core of the function. Give
               priority to an arc that connects both edges of the span,
               then one that is tethered to the left edge, then the
               right edge, and then any that lie independently within
               the span. Give preference to the longer arcs. Once a choice is
               made, assign generative levels to the dependent arc components,
               revise the span list, and continue.

            #. Process any spans that contains only inserted pitches and
               no arcs, testing to ensure compliance with
               the restrictions of rule E3.
            """
            # Assign levels to notes in the basic arc.
            for n in self.notes:
                if n.rule.name == 'S1':
                    n.rule.level = 0
                if n.rule.name == 'S2':
                    n.rule.level = 1
                if n.rule.name == 'S3':
                    n.rule.level = 2
            # Set level of first note if not in basic arc.
            if self.arcBasic[0] != 0:
                self.notes[0].rule.level = 3

            # Collect all the secondary arcs.
            dependentArcs = [arc for arc in self.arcs if arc != self.arcBasic]

            # A span is defined by two notes: initial and final.
            # The rootSpan extends from the first to the last note of a line.
            rootSpan = (self.notes[0].index, self.notes[-1].index)

            # The length of a span = the number of intervening new notes
            # The span between consecutive notes is 0,
            # so only spans of length > 0 are fillable.
            def spanLength(sp):
                spannedNotes = 0
                for n in self.notes:
                    cond = [not n.tie or n.tie.type == 'start',
                            sp[0] < n.index < sp[-1]]
                    if all(cond):
                        spannedNotes += 1
                return spannedNotes

            # Given an arc, divide it into fillable segments (length > 0).
            def addSpansFromArc(arc, spans):
                segments = pairwise(arc)
                for segment in segments:
                    if spanLength(segment) > 0:
                        spans.append(segment)

            # Create a list to hold all the fillable spans.
            spans = []

            # Add spans before and after basic arc, if they exist.
            # (Outer edges will not have been generated yet.)
            # (In the current implementation, there will never be
            # a span after the basic arc, but Westergaard allows it.)
            if self.arcBasic[0] != rootSpan[0]:
                span = (0, self.arcBasic[0])
                if spanLength(span) > 0:
                    spans.append(span)
            if self.arcBasic[-1] != rootSpan[-1]:
                span = (self.arcBasic[-1], rootSpan[1])
                if spanLength(span) > 0:
                    spans.append(span)

            # Add any spans in the basic arc.
            addSpansFromArc(self.arcBasic, spans)

            # For testing whether an insertion conforms
            # to the intervallic constraints:
            def isPermissibleInsertion(x, y, z):
                # Checks the insertion of y between x and z indexes.
                insertion = self.notes[y]
                left = self.notes[x]
                right = self.notes[z]
                rules = [(isLinearConsonance(left, insertion)
                          or isLinearUnison(left, insertion)
                          or isDiatonicStep(left, insertion)),
                         (isLinearConsonance(insertion, right)
                          or isLinearUnison(insertion, right)
                          or isDiatonicStep(insertion, right))]
                if all(rules):
                    return True
                else:
                    return False

            # Look at every span in the list,
            # and see whether a dependent arc fits into it.
            # This is the core of the function.
            def processSpan(span, spans, dependentArcs):
                # The rule levels inside the span are determined
                # by the rule levels of the left and right edges.
                leftEdge = span[0]
                rightEdge = span[1]
                leftEdgeLevel = self.notes[span[0]].rule.level
                rightEdgeLevel = self.notes[span[1]].rule.level

                def getNextLevel(span):
                    leftEdgeLevel = self.notes[span[0]].rule.level
                    rightEdgeLevel = self.notes[span[1]].rule.level
                    if leftEdgeLevel and rightEdgeLevel:
                        nextLevel = max(leftEdgeLevel, rightEdgeLevel) + 1
                    elif leftEdgeLevel and not rightEdgeLevel:
                        nextLevel = leftEdgeLevel + 1
                    elif not leftEdgeLevel and rightEdgeLevel:
                        nextLevel = rightEdgeLevel + 1
                    return nextLevel

                nextLevel = getNextLevel(span)
                # (1) Search for possible branches across or within the span.
                # A dependent arc can fit into a span in one of four ways:
                #     (1) crossBranches connect leftEdge to rightEdge.
                #     (2) rightBranches connect onto the leftEdge
                #         (branch to the right)
                #     (3) leftBranches connect onto the rightEdge
                #         (branch to the left)
                #     (4) interBranches do not connect to either edge
                # Find the best and longest arc available in a span
                #     preferences among categories:
                #          cross > right > left > inter
                #     preferences within category:
                #          longer > shorter
                crossBranch = None
                rightBranch = None
                leftBranch = None
                interBranch = None
                # First look for cross branch connection across span.
                for arc in dependentArcs:
                    if arc[0] == leftEdge and arc[-1] == rightEdge:
                        crossBranch = arc
                # Otherwise look for right or left branches to generated edges.
                # Look for right branches if the left edge
                # has been generated.
                if leftEdgeLevel is not None and crossBranch is None:
                    for arc in dependentArcs:
                        # Look for a right branch.
                        if (arc[0] == leftEdge
                                and rightBranch is None
                                and isPermissibleInsertion(leftEdge, arc[-1],
                                                           rightEdge)):
                            rightBranch = arc
                        # See if there's a longer right branch available.
                        if (arc[0] == leftEdge
                                and rightBranch
                                and arcLength(arc) > arcLength(rightBranch)
                                and isPermissibleInsertion(leftEdge, arc[-1],
                                                           rightEdge)):
                            rightBranch = arc
                # Look for left branches if the right edge has been
                # generated and there is no right branch.
                if (rightEdgeLevel is not None and crossBranch is None
                        and rightBranch is None):
                    for arc in dependentArcs:
                        if (arc[-1] == rightEdge
                                and leftBranch is None
                                and isPermissibleInsertion(leftEdge, arc[0],
                                                           rightEdge)):
                            leftBranch = arc
                        # See if there's a longer left branch available.
                        if (arc[-1] == rightEdge
                                and leftBranch
                                and arcLength(arc) > arcLength(leftBranch)
                                and isPermissibleInsertion(leftEdge, arc[0],
                                                           rightEdge)):
                            leftBranch = arc
                        # TODO if arc[0] is a repetition (E1),
                        #  look for an interbranch that ends with arc[0]...
                # Look for inter branch if no cross branches
                # or left or right branches.
                if (rightBranch is None and leftBranch is None
                        and crossBranch is None):
                    for arc in dependentArcs:
                        if (arc[0] > leftEdge
                                and arc[-1] < rightEdge
                                and interBranch is None):
                            interBranch = arc
                        # See if there's a longer inter branch available.
                        if (arc[0] > leftEdge
                                and arc[-1] < rightEdge
                                and interBranch
                                and arcLength(arc) > arcLength(interBranch)):
                            interBranch = arc
                # (2) Process any branches that have been found in the span:
                #     (a) Remove the branch from the list of dependent arcs.
                #     (b) Calculate rule levels for members of the branch.
                # Termini levels of cross branch are already set,
                # so just set level of inner elements.
                if crossBranch is not None:
                    dependentArcs.remove(crossBranch)
                    for i in crossBranch[1:-1]:
                        self.notes[i].rule.level = nextLevel
                # One terminus level is already set, so set level of the
                # other terminus and the inner elements.
                elif rightBranch is not None:
                    dependentArcs.remove(rightBranch)
                    self.notes[rightBranch[-1]].rule.level = nextLevel
                    for i in rightBranch[1:-1]:
                        self.notes[i].rule.level = nextLevel + 1
                elif leftBranch is not None:
                    dependentArcs.remove(leftBranch)
                    self.notes[leftBranch[0]].rule.level = nextLevel
                    for i in leftBranch[1:-1]:
                        self.notes[i].rule.level = nextLevel + 1
                # No terminus level is already set, so set level of the left
                # terminus, then the right, and then the inner elements.
                elif interBranch is not None:
                    dependentArcs.remove(interBranch)
                    self.notes[interBranch[0]].rule.level = nextLevel
                    self.notes[interBranch[-1]].rule.level = nextLevel + 1
                    for i in interBranch[1:-1]:
                        self.notes[i].rule.level = nextLevel + 2

                # (3) Revise the list of spans.
                if crossBranch or rightBranch or leftBranch or interBranch:
                    spans.remove(span)
                if crossBranch:
                    addSpansFromArc(crossBranch, spans)
                if rightBranch:
                    addSpansFromArc(rightBranch, spans)
                    if spanLength((rightBranch[-1], rightEdge)) > 0:
                        spans.append((rightBranch[-1], rightEdge))
                if leftBranch:
                    if spanLength((leftEdge, leftBranch[0])) > 0:
                        spans.append((leftEdge, leftBranch[0]))
                    addSpansFromArc(leftBranch, spans)
                if interBranch:
                    if spanLength((leftEdge, interBranch[0])) > 0:
                        spans.append((leftEdge, interBranch[0]))
                    addSpansFromArc(interBranch, spans)
                    if spanLength((interBranch[-1], rightEdge)) > 0:
                        spans.append((interBranch[-1], rightEdge))

                # (4) Process a span that contains only inserted
                # pitches and no arcs.
                if (crossBranch is None and rightBranch is None
                        and leftBranch is None and interBranch is None):

                    # initialize the process
                    a = leftEdge
                    b = rightEdge
                    # stack, tree, dictionary
                    segmentStack = [(a, b)]
                    tree = [a, b]
                    insertionDict = {}

                    # other variables: segment, result, i, node

                    def getSegmentFromStack(segmentStack):
                        if len(segmentStack) > 0:
                            return segmentStack.pop()
                        else:
                            return 'finished'

                    def findSegmentInsertions(segment):
                        a = segment[0]
                        b = segment[1]
                        insertionList = []
                        for i in range(a + 1, b):
                            cond = [not self.notes[i].tie
                                    or self.notes[i].tie.type == 'start',
                                    isPermissibleInsertion(a, i, b)]
                            if all(cond):
                                insertionList.insert(0, i)
                        return insertionList

                    def getSegmentInsertion(segment, dict):
                        newInsertion = None
                        if segment in insertionDict:
                            insertionList = dict[segment]
                            if len(insertionList) > 0:
                                newInsertion = insertionList.pop()
                        return newInsertion

                    def segmentContentSize(segment):
                        a = segment[0]
                        b = segment[1]
                        noteCount = 0
                        for i in range(a + 1, b):
                            cond = [not self.notes[i].tie
                                    or self.notes[i].tie.type == 'start']
                            if all(cond):
                                noteCount += 1
                        return noteCount

                    def addSegmentsToStack(segment, i, segmentStack):
                        a = segment[0]
                        b = segment[1]
                        if segmentContentSize((i, b)) > 0:
                            segmentStack.append((i, b))
                        if segmentContentSize((a, i)) > 0:
                            segmentStack.append((a, i))

                    def getSegmentFromTreeTop(tree):
                        segment = None
                        top = tree[-1]
                        for n in reversed(tree):
                            if top > n:
                                segment = (n, top)
                                break
                        return segment

                    def removeSegmentWithNode(node, segmentStack):
                        for segment in segmentStack:
                            if segment[0] == node or segment[-1] == node:
                                segmentStack.remove(segment)
                                break

                    def setLevelsFromTree(tree):
                        paredTree = tree[2:]
                        seg = [tree[0], tree[1]]
                        for i in paredTree:
                            for s in seg:
                                if s > i:
                                    idx = seg.index(s)
                                    seg.insert(idx, i)
                                    nextLevel = getNextLevel((seg[idx - 1],
                                                              seg[idx + 1]))
                                    self.notes[seg[idx]].rule.level = nextLevel
                                    break

                    def processInsertionSegment(segment):
                        i = getSegmentInsertion(segment, insertionDict)
                        if i is not None:
                            tree.append(i)
                            addSegmentsToStack(segment, i, segmentStack)
                            segment = getSegmentFromStack(segmentStack)
                            if segment != 'finished':
                                result = findSegmentInsertions(segment)
                                insertionDict[segment] = result
                        elif i is None:
                            node = tree.pop()
                            removeSegmentWithNode(node, segmentStack)
                            segment = getSegmentFromTreeTop(tree)
                        if segment != 'finished':
                            processInsertionSegment(segment)
                        else:
                            # finish off processing the span then remove
                            setLevelsFromTree(tree)
                            if len(tree) == segmentContentSize((tree[0],
                                                                tree[1])) + 2:
                                spans.remove(span)

                    # start the process
                    segment = getSegmentFromStack(segmentStack)
                    result = findSegmentInsertions(segment)
                    insertionDict[segment] = result
                    # continue with recursive process until finished
                    processInsertionSegment(segment)

            # Run the method's core function
            spancount = len(spans)
            while spancount > 0:
                processSpan(spans[0], spans, dependentArcs)
                spancount = len(spans)
                spans.sort()

            generatedNotes = [(n.index, n.rule.name, n.rule.level)
                              for n in self.notes
                              if n.rule.level is not None]
            generationTable = [n.rule.level for n in self.notes]

        def setArcLevels(self):
            # calculate raw hierarchical level of arc based on generation
            # level of the most deeply embedded component
            # TODO refine how levels are defined
            for key, arc in self.arcDict.items():
                arc_level_raw = 0
                for n in self.notes:
                    if n.index in arc.arc and n.rule.level > arc_level_raw:
                        arc_level_raw = n.rule.level
                arc.level = arc_level_raw
            # re-calculate hierarichical levels of arcs
            arc_levels_raw = []
            for key, arc in self.arcDict.items():
                if arc.level not in arc_levels_raw:
                    arc_levels_raw.append(arc.level)
            arc_levels_raw_sorted = sorted(arc_levels_raw)
            for key, arc in self.arcDict.items():
                arc_level = arc_levels_raw_sorted.index(arc.level)
                arc.level = arc_level

        def displayWestergaardParse(self):
            """Create a multileveled illustration of a parse of the sort
            used in Westergaard's book.  Activate by setting global variable
            showWestergaardInterpretations to True.  Will eventually be added
            as a parse display option.
            """
            # TODO activate as a display option in
            # westerparse.showInterpretations()
            # Given a parsed part, with rule dependencies set:
            illustration = stream.Score()
            notes = self.notes
            # Determine the maximum number of levels in the parse.
            levels = [n.rule.level for n in notes
                      if not n.tie or n.tie.type == 'start']
            maxLevel = max(levels)
            # Create a part in the illustration for each level
            # and assign it a number.
            n = maxLevel + 1
            while n > 0:
                illustration.append(stream.Part())
                n += -1
            for num, part in enumerate(illustration.parts):
                part.partNum = num

            # Add each note to the correct levels.
            def addNoteToIllustration(n, illustration):
                lev = n.rule.level
                for part in illustration.parts:
                    if lev == part.partNum:
                        newNote = note.Note()
                        newNote.pitch = n.pitch
                        newNote.duration = n.duration
                        newNote.lyric = n.rule.name
                        part.insert(n.offset, newNote)
                        if n.tie:
                            if n.tie.type == 'start':
                                newNote.tie = tie.Tie('start')
                                tiedOver = notes[n.index + 1]
                                part.insert(tiedOver.offset, tiedOver)
                    if lev < part.partNum:
                        part.insert(n.offset, n)
                        if n.tie:
                            if n.tie.type == 'start':
                                tiedOver = notes[n.index + 1]
                                part.insert(tiedOver.offset, tiedOver)

            # Populate the illustration parts.
            for n in notes:
                if not n.tie or n.tie.type == 'start':
                    addNoteToIllustration(n, illustration)

            illustration.show()
            # Exit after showing the first parse, for testing.
            # exit()

    def testGenerabilityFromLevels(self):
        """Given a parse in which rule levels have been assigned
        (perhaps by the student), determine whether the line is generable
        in that way. [Under development]
        """
        if self.lineType == 'bass':
            pass
        if self.lineType == 'primary':
            pass
        if self.lineType == 'generic':
            pass
        pass

    def collectParses(self):
        """Collect all the attempted parses of a line in the
        :py:class:`~Parser` and discard any that have errors and thus failed.
        Also removes parses of primary lines if the same basic arc was
        produced by a more reliable method.
        """
        failedParses = []
        for key in self.parseErrorsDict:
            if self.parseErrorsDict[key]:
                failedParses.append(key)

        # Remove parses that have errors.
        self.parses = [parse for parse in self.parses
                       if self.parseErrorsDict[parse.label] == []]

        # remove duplicate parses
        if self.parses:
            unique_parses = [self.parses[0]]
            for parse in self.parses:
                for up in unique_parses:
                    # remove only if rules and linetype are identical
                    rules = [parse.ruleLabels == up.ruleLabels,
                             parse.lineType == up.lineType]
                    if all(rules):
                        unique = False
                    else:
                        unique = True
                if unique == True:
                    unique_parses.append(parse)
            self.parses = unique_parses

        for parse in self.parses:
            if parse.lineType == 'primary':
                self.Pinterps.append(parse)
            elif parse.lineType == 'bass':
                self.Binterps.append(parse)
            elif parse.lineType == 'generic':
                self.Ginterps.append(parse)
        if self.Pinterps:
            self.interpretations['primary'] = self.Pinterps
        if self.Binterps:
            self.interpretations['bass'] = self.Binterps
        if self.Ginterps:
            self.interpretations['generic'] = self.Ginterps

        # Remove parses in primary lines that have the same basic arc
        # as another parse; because of creation order,
        # preference given to inference methods 0-4.
        arcBasicCandidates = []
        prunedParseSet = []
        for prs in self.Pinterps:
            if prs.arcBasic not in arcBasicCandidates:
                arcBasicCandidates.append(prs.arcBasic)
                prunedParseSet.append(prs)
        self.Pinterps = prunedParseSet

        # Set generability properties.
        if self.Pinterps:
            self.isPrimary = True
        else:
            self.isPrimary = False
        if self.Binterps:
            self.isBass = True
        else:
            self.isBass = False
        if self.Ginterps:
            self.isGeneric = True
        else:
            self.isGeneric = False

        # TODO If no parses were successful, return the errors:
        if not self.parses:
            errors = [self.parseErrorsDict[key]
                      for key in self.parseErrorsDict]
            for error in errors:
                if error not in self.errors:
                    self.errors.append(error)
            pass

    def selectPreferredParses(self):
        """Given a list of successful interpretations from :py:class:`~Parser`,
        remove those that do not conform to cognitive preference rules.

        * Primary line preferences

          * For parses that share the same S2 scale degree, prefer the parse
            in which S2 occurs earliest.

        * Bass Lines

          * Prefer parses in which S3 occurs after the midpoint.
          * Prefer parses in which S3 occurs on the beat.
          * If there are two candidates for S3 and the second can be
            interpreted as a direct repetition of the first, prefer the parse
            that interprets the first candidate as S3.
        """
        # Primary upper lines:
        # Find those that have the same scale degree for S2.
        threelines = [interp for interp in self.Pinterps
                      if interp.S2Degree == '3']
        fivelines = [interp for interp in self.Pinterps
                     if interp.S2Degree == '5']
        eightlines = [interp for interp in self.Pinterps
                      if interp.S2Degree == '8']
        # Get the indexes of that degree.
        threelineCands = [interp.arcBasic[0] for interp in threelines]
        fivelineCands = [interp.arcBasic[0] for interp in fivelines]
        eightlineCands = [interp.arcBasic[0] for interp in eightlines]
        # Look for arcs that connect pairs of those indexes (as repetitions).
        ints = pairwise(fivelineCands)
        # Create a list of interpretations that will be purged.
        labelsToPurge = []

        # TODO Westergaard p. 112: prefer S notes onbeat (esp S2).
        # TODO Implement Westergaard cognitive preferences,
        #   sections 4.2, 4.4, and 5.3.
        # Get local offset of each S pitch:
        # Prefer as many offset==0.0 as possible.

        # Just hang onto the earliest S2 candidates.
        if threelines:
            earliestS2 = sorted(threelineCands)[0]
            for interp in threelines:
                if interp.S2Index > earliestS2:
                    labelsToPurge.append(interp.label)
        if fivelines:
            earliestS2 = sorted(fivelineCands)[0]
            for interp in fivelines:
                if interp.S2Index > earliestS2:
                    labelsToPurge.append(interp.label)
        if eightlines:
            earliestS2 = sorted(eightlineCands)[0]
            for interp in eightlines:
                if interp.S2Index > earliestS2:
                    labelsToPurge.append(interp.label)
        # Remove unpreferred interpretations from the set
        # of interpretations.
        self.Pinterps = [interp for interp in self.Pinterps
                         if interp.label not in labelsToPurge]

        # TODO Are there options for the placement of S3?
        #   If so, coordinate with a bass line.
        # Redefine Pinterps after purging.
        # TODO Find the positions of the end of S3 (sd2) in upper lines.
        S3PenultCands = [interp.arcBasic[-2] for interp in self.Pinterps]

        # Bass lines:
        lowfives = [interp for interp in self.Binterps
                    if self.notes[interp.S3Index].csd.value == -3]
        highfives = [interp for interp in self.Binterps
                     if self.notes[interp.S3Index].csd.value == 4]
        # Choose an S3 that's integrated or immediately preceding.
        # Given two options, choose the later if there is a
        # potential repetition of S2 between them.
        # Can this be negotiated earlier in the parse?

        # Currently there is no preference where S3 occurs in a bass line.
        # TODO: Eventually this must be supplemented by a preference for
        #   consonant coordination with an S3 in the upper line:
        #   either simultaneous with or subsequent to sd2.

        # If there are several candidates for high or low five,
        # prefer ones in which S3 occurs past the midway point of the line.
        # TODO define midpoint by offset??
        labelsToPurge = []
        linemidpoint = len(self.notes) / 2
        if len(highfives) > 1:
            for interp in highfives:
                if interp.S3Index < linemidpoint:
                    labelsToPurge.append(interp.label)
        if len(labelsToPurge) == len(highfives):
            pass
        else:
            highfives = [interp for interp in highfives
                         if interp not in labelsToPurge]
        labelsToPurge = []
        if len(lowfives) > 1:
            for interp in lowfives:
                if interp.S3Index < linemidpoint:
                    labelsToPurge.append(interp.label)
        if len(labelsToPurge) == len(lowfives):
            pass
        else:
            lowfives = [interp for interp in lowfives
                        if interp not in labelsToPurge]
        resultantInterps = highfives + lowfives
        self.Binterps = [interp for interp in self.Binterps
                         if interp in resultantInterps]

        # If there are still several candidates for S3,
        # prefer ones in which S3 occurs on the beat.
        allfivesOnbeat = [five for five in self.Binterps
                          if self.notes[five.S3Index].beat == 1.0]
        labelsToPurge = []
        if (len(self.Binterps) > len(allfivesOnbeat)
                and len(allfivesOnbeat) != 0):
            for interp in self.Binterps:
                if self.notes[interp.S3Index].beat != 1.0:
                    labelsToPurge.append(interp.label)
        # don't purge labels if the result is null
        if len(labelsToPurge) == len(self.Binterps):
            pass
        else:
            self.Binterps = [interp for interp in self.Binterps
                             if interp.label not in labelsToPurge]

        # If there are two candidates for S3 and
        # one can be an immediate repetition, prefer that one.
        preferredBassS3 = None
        labelsToPurge = []
        for interp in self.Binterps:
            for arc in interp.arcs:
                if arc == [interp.S3Index, interp.S3Index + 1]:
                    preferredBassS3 = interp.S3Index
        if preferredBassS3 is not None:
            for interp in self.Binterps:
                if interp.S3Index == preferredBassS3 + 1:
                    labelsToPurge.append(interp.label)
        self.Binterps = [interp for interp in self.Binterps
                         if interp.label not in labelsToPurge]

        # Update the list of parses and the dictionary of parses.
        self.parses = self.Pinterps + self.Binterps + self.Ginterps
        self.interpretations['primary'] = self.Pinterps
        self.interpretations['bass'] = self.Binterps
        self.interpretations['generic'] = self.Ginterps

        return self


# -----------------------------------------------------------------------------
# UTILITY SCRIPTS
# -----------------------------------------------------------------------------


# from utilities.py
#   shiftBuffer, shiftStack


def isTriadMember(note, stufe, context=None):
    # Determine whether a note belongs to a triad.
    # Can be used to check membership in a nontonic triad.
    # E.g., using stufe = 4 will look for pitches in the dominant triad.
    # May need to have a context reference (e.g., measure in 3rd species).
    if (note.csd.value - stufe) % 7 in {0, 2, 4}:
        return True
    else:
        return False


def isTriadicSet(pitchList):
    # Test whether a set of notes makes a major, minor or diminished triad.
    isTriadicSet = False
    pairs = itertools.combinations(pitchList, 2)
    for pair in pairs:
        invl = interval.Interval(pair[0], pair[1]).simpleName
        rules = [invl[-1] in ['2', '7'],
                 (invl[-1] == '1' and invl != 'P1'),
                 (invl[-1] == '5' and invl == 'A5'),
                 (invl[-1] == '4' and invl == 'd4')]
        if any(rules):
            isTriadicSet = False
            return isTriadicSet
        else:
            isTriadicSet = True
    # If the pitchList is 0 or 1 pitches, return True.
    if len(pitchList) < 2:
        isTriadicSet = True
    return isTriadicSet


def isHarmonic(pitchTarget, harmonicPitches):
    isHarmonic = False
    testHarm = [elem for elem in harmonicPitches]
    testHarm.append(pitchTarget.pitch)
    if isTriadicSet(testHarm):
        isHarmonic = True
    else:
        isHarmonic = False
        return isHarmonic
    return isHarmonic


def isLinearConsonance(n1, n2):
    # Input two notes with pitch.
    lin_int = interval.Interval(n1, n2)
    if lin_int.name in {'m3', 'M3', 'P4', 'P5', 'm6', 'M6', 'P8'}:
        return True
    else:
        return False


def isSemiSimpleInterval(n1, n2):
    # Input two notes with pitch.
    lin_int = interval.Interval(n1, n2)
    if lin_int.semiSimpleNiceName == lin_int.niceName:
        return True
    else:
        return False


def isLinearUnison(n1, n2):
    # Input two notes with pitch.
    lin_int = interval.Interval(n1, n2)
    if lin_int.name in {'P1'}:
        return True
    else:
        return False


def isDiatonicStep(n1, n2):
    # Input two notes with pitch.
    lin_int = interval.Interval(n1, n2)
    if lin_int.name in {"m2", "M2"}:
        return True
    else:
        return False


def isStepUp(n1, n2):
    # input one note and the next.
    if isDiatonicStep(n1, n2):
        if n2.csd.value > n1.csd.value:
            return True
        else:
            return False


def isStepDown(n1, n2):
    # Input one note and the next.
    if isDiatonicStep(n1, n2):
        if n2.csd.value < n1.csd.value:
            return True
        else:
            return False


def isDirectedStep(n1, n2):
    # Input two notes with pitch.
    rules1 = [n1.csd.direction in {'ascending', 'bidirectional'},
              isStepUp(n1, n2)]
    rules2 = [n1.csd.direction in {'descending', 'bidirectional'},
              isStepDown(n1, n2)]
    if all(rules1) or all(rules2):
        return True
    else:
        return False


def getStepDirection(n1, n2):
    if isStepDown(n1, n2):
        return 'descending'
    if isStepUp(n1, n2):
        return 'ascending'
    else:
        return None


def isNeighboringArc(arc, notes):
    if len(arc) != 3:
        return False
    # Accept an arcList of line indices
    # and determine whether a valid N structure.
    i = notes[arc[0]]
    j = notes[arc[1]]
    k = notes[arc[2]]
    rules1 = [len(arc) == 3,
              isDiatonicStep(i, j),
              isDiatonicStep(j, k),
              k.csd.value == i.csd.value]
    rules2 = [k.csd.direction == 'bidirectional',
              j.csd.value > k.csd.value and k.csd.direction == 'descending',
              j.csd.value < k.csd.value and k.csd.direction == 'ascending']
    if all(rules1) and any(rules2):
        # TODO Could add conditions to add label modifier: upper, lower.
        return True
    else:
        return False


def getNeighborType(arc, notes):
    i = notes[arc[0]]
    j = notes[arc[1]]
    if isNeighboringArc(arc, notes):
        if isStepUp(i, j):
            return 'upper'
        else:
            return 'lower'


def isPassingArc(arc, notes):
    # Accept an arcList of line indices and determine whether
    # a valid P structure; can probably assume that
    # first and last pitches are in tonic triad, but ...
    i = notes[arc[0]]
    k = notes[arc[-1]]
    if i.csd.value > k.csd.value:
        passdir = 'falling'
    elif i.csd.value < k.csd.value:
        passdir = 'rising'
    else:
        return False
    ints = pairwise(arc)
    for int in ints:
        n1 = notes[int[0]]
        n2 = notes[int[1]]
        rules1 = [isDiatonicStep(n1, n2) is True]
        rules2 = [passdir == 'falling'
                  and n1.csd.direction in ('bidirectional', 'descending'),
                  passdir == 'rising'
                  and n1.csd.direction in ('bidirectional', 'ascending')]
        rules3 = [passdir == 'falling' and n1.csd.value > n2.csd.value,
                  passdir == 'rising' and n1.csd.value < n2.csd.value]
        if all(rules1) and any(rules2) and any(rules3):
            continue
        else:
            return False
    return True


def getPassingType(arc, notes):
    i = notes[arc[0]]
    j = notes[arc[1]]
    if isPassingArc(arc, notes):
        if isStepUp(i, j):
            return 'rising'
        else:
            return 'falling'


def isRepetitionArc(arc, notes):
    # Accept an arcList of line indices and determine
    # whether a valid R structure;
    # can probably assume that first and last pitches
    # are in tonic triad, but ...
    i = notes[arc[0]]
    j = notes[arc[1]]
    rules1 = [j.csd.value == i.csd.value]
    if all(rules1):
        return True
    else:
        return False


def isRepetition(noteIndex, notes, arcs):
    # Check whether a note at noteIndex in notes
    # is a global repetition in an arc.
    isGlobalRepetition = False
    for arc in arcs:
        i = notes[arc[0]]
        j = notes[arc[-1]]
        rules1 = [noteIndex == j.index,
                  j.csd.value == i.csd.value]
        if all(rules1):
            isGlobalRepetition = True
            break
    return isGlobalRepetition


def isLocalRepetition(noteIndex, notes, arcs):
    # Check whether a note at noteIndex in notes
    # is a local repetition in an arc.
    isLocalRepetition = False
    for arc in arcs:
        i = notes[arc[0]]
        j = notes[arc[-1]]
        rules1 = [noteIndex == j.index,
                  j.csd.value == i.csd.value,
                  i.measureNumber == j.measureNumber]
        if all(rules1):
            isLocalRepetition = True
            break
    return isLocalRepetition


def arcGenerateTransition(i, part, arcs):
    # Assemble an arc after a righthead is detected.
    # Variable i is a note.index, the last transitional element before
    # a righthead.  Test for arc type in self.line.notes.
    # Also assigns a label.
    # After getting the elements, find the interval directions.
    elements = []
    for elem in (part.flatten().notes[i].dependency.lefthead,
                 i, part.flatten().notes[i].dependency.righthead):
        elements.append(elem)
    for d in part.flatten().notes[i].dependency.dependents:
        if (d < i and
                part.flatten().notes[d].dependency.lefthead ==
                part.flatten().notes[i].dependency.lefthead):
            elements.append(d)
    thisArc = sorted(elements)
    arcs.append(thisArc)
    # See if it's a neighbor or passing.
    if part.flatten().notes[thisArc[-1]] == part.flatten().notes[thisArc[0]]:
        arcType = 'neighbor'
    else:
        arcType = 'passing'


def arcGenerateRepetition(j, part, arcs):
    # Assemble an arc after a repetition is detected.
    # Variable j is a note.index of the repetition.
    # Tests for arc type in self.line.notes.
    elements = [elem for elem in (part.flatten().notes[j].dependency.lefthead, j)]
    thisArc = elements
    arcs.append(thisArc)
    arcType = 'repetition'


def arcExtendTransition(notes, arc, extensions):
    # Extend an arc, usually into the next timespan.
    # Extensions is a list of notes.
    # Clean out the old arc.
    removeDependenciesFromArc(notes, arc)
    # Add the extensions and put in ascending order.
    arc = sorted(arc + extensions)
    # Reset the dependencies in the extended arc.
    addDependenciesFromArc(notes, arc)


def pruneOpenHeads(notes, openheads):
    # Prune direct repetitions from end of the list of open head indices.
    if len(openheads) > 1:
        latesthead = openheads[-1]
        predecessor = openheads[-2]
        if notes[latesthead] == notes[predecessor]:
            openheads.pop()
    return openheads


def clearDependencies(note):
    # Reset a note's dependency attributes.
    note.dependency.lefthead = None
    note.dependency.righthead = None
    note.dependency.dependents = []


def removeDependenciesFromArc(notes, arc):
    for elem in arc:
        i = notes[elem]
        j = notes[arc[0]]
        k = notes[arc[-1]]
        if elem in j.dependency.dependents:
            j.dependency.dependents.remove(elem)
        if elem in k.dependency.dependents:
            k.dependency.dependents.remove(elem)
        if i.dependency.lefthead == j.index:
            i.dependency.lefthead = None
        if i.dependency.righthead == k.index:
            i.dependency.righthead = None


def addDependenciesFromArc(notes, arc):
    for elem in arc[1:-1]:
        notes[elem].dependency.lefthead = arc[0]
        notes[elem].dependency.righthead = arc[-1]
        notes[arc[0]].dependency.dependents.append(elem)
        notes[arc[-1]].dependency.dependents.append(elem)
        # TODO: Also set codependents.
        arcLen = len(arc[1:-1])


def isArcTerminal(i, arcs):
    # Check whether a note at index i is the terminal of any nonbasic arc.
    isTerminal = False
    for arc in arcs:
        if i == arc[0] or i == arc[-1]:
            isTerminal = True
    return isTerminal


def isEmbeddedInArcs(i, arcs):
    # Check whether a note at index i is embedded within any nonbasic arc.
    isEmbedded = False
    for arc in arcs:
        if arc[0] < i < arc[-1]:
            isEmbedded = True
    return isEmbedded


def isEmbeddedInArc(i, arc):
    # Check whether a note at index i is embedded within a given arc.
    isEmbedded = False
    if arc[0] < i < arc[-1]:
        isEmbedded = True
    return isEmbedded


def isEmbeddedInOtherArc(arc, arcs, startIndex=0, stopIndex=-1):
    """
    Check whether an arc is embedded within another arc between two indices.
    """
    isEmbedded = False
    testArcs = []
    for testArc in arcs:
        if (testArc[0] >= startIndex
                and testArc[-1] <= stopIndex
                and testArc != arc):
            testArcs.append(testArc)
    for testArc in testArcs:
        if arc[0] >= testArc[0] and arc[-1] <= testArc[-1]:
            isEmbedded = True
    return isEmbedded


def conflictsWithOtherArc(arc, arcs):
    """
    Check whether an arc is in conflict with any existing arc.
    Five types of relationship:
        1. overlap, always illegal
        2. congruence, always illegal
        3. containment, requires nesting test
        4. co-iniation, requires nesting test
        5. co-termination, requires nesting test
    """
    conflict = False
    for extArc in arcs:
        # new arc overlaps later arc
        cond1a = (arc[0] < extArc[0] < arc[-1] < extArc[-1])
        # new arc overlaps earlier arc
        cond1b = (extArc[0] < arc[0] < extArc[-1] < arc[-1])
        # new arc is congruent with existing arc
        cond2 = (extArc[0] == arc[0] and extArc[-1] == arc[-1])
        # new arc contains an existing arc
        cond3a = (arc[0] < extArc[0]
                 and arc[-1] > extArc[-1])
        # new arc is contained by an existing arc
        cond3b = (extArc[0] < arc[0]
                 and extArc[-1] > arc[-1])
        # new arc is co-initiated with an existing arc and ends earlier
        cond4a  = (extArc[0] == arc[0] and extArc[-1] > arc[-1])
        # new arc is co-initiated with an existing arc and ends later
        cond4b  = (extArc[0] == arc[0] and extArc[-1] < arc[-1])
        # new arc is co-terminated with an existing arc and starts earlier
        cond5a  = (extArc[0] > arc[0] and extArc[-1] == arc[-1])
        # new arc is co-terminated with an existing arc and starts later
        cond5b = (extArc[0] < arc[0] and extArc[-1] == arc[-1])

        if cond1a or cond1b or cond2:
            conflict = True
        # conflicts if internal elements of containing arc
        # found in contained arc
        elif cond3a:
            if len(arc) > 2:
                for d in arc[1:-1]:
                    if extArc[0] < d < extArc[-1]:
                        conflict = True
                        break
        elif cond4a:
            if len(extArc) > 2:
                for d in extArc[1:-1]:
                    if d < arc[-1]:
                        conflict = True
                        break
        elif cond5a:
             if len(arc) > 2:
                for d in arc[1:-1]:
                    if d > extArc[0]:
                        conflict = True
                        break
        elif cond3b:
            if len(extArc) > 2:
                for d in extArc[1:-1]:
                    if arc[0] < d < arc[-1]:
                        conflict = True
                        break
        elif cond4b:
            if len(arc) > 2:
                for d in arc[1:-1]:
                   if d < extArc[-1]:
                        conflict = True
                        break

        elif cond5a:
            if len(extArc) > 2:
                for d in extArc[1:-1]:
                    if d > arc[0]:
                        conflict = True
                        break
    return conflict


def isIndependent(note):
    rules = [note.dependency.dependents == [],
             note.dependency.lefthead is None,
             note.dependency.righthead is None]
    if all(rules):
        return True
    else:
        return False


def areArcTerminals(h, i, arcs):
    # Check whether a head at index h and a note at index i
    # are the terminals of any nonbasic arc.
    areTerminals = False
    for arc in arcs:
        if h == arc[0] and i == arc[-1]:
            areTerminals = True
    return areTerminals


def arcLength(arc):
    # Returns the length of an arc measured as number of consecutions spanned.
    length = arc[-1] - arc[0]
    return length


# -----------------------------------------------------------------------------


class Test(unittest.TestCase):

    def runTest(self):
        pass

    def test_inferLineTypes(self):
        pass

    def test_preParseLine(self):
        pass

    def test_showPartialParse(self):
        pass

    def test_parseTransition(self):
        pass

    def test_prepareParses(self):
        pass

    def test_buildParse(self):
        pass

    def test_performLineParse(self):
        pass

    def test_arcMerge(self):
        pass

    def test_arcEmbed(self):
        pass

    def test_parsePrimary(self):
        pass

    def test_parseBass(self):
        pass

    def test_parseGeneric(self):
        pass

    def test_attachOpenheadsToStructuralLefthead(self):
        pass

    def test_integrateSecondaryWithPrimary(self):
        pass

    def test_assignSecondaryRules(self):
        pass

    def test_testLocalResolutions(self):
        pass

    def test_pruneArcs(self):
        pass

    def test_gatherRuleLabels(self):
        pass

    def test_gatherParentheses(self):
        pass

    def test_setDependencyLevels(self):
        pass

    def test_displayWestergaardParse(self):
        pass

    def test_testGenerabilityFromLevels(self):
        pass

    def test_collectParses(self):
        pass

    def test_selectPreferredParses(self):
        pass

    def test_shiftBuffer(self):
        pass

    def test_shiftStack(self):
        pass

    def test_isTriadMember(self):
        pass

    def test_isTriadicSet(self):
        pass

    def test_isHarmonic(self):
        pass

    def test_isLinearConsonance(self):
        pass

    def test_isSemiSimpleInterval(self):
        pass

    def test_isLinearUnison(self):
        pass

    def test_isDiatonicStep(self):
        pass

    def test_isStepUp(self):
        pass

    def test_isStepDown(self):
        pass

    def test_isDirectedStep(self):
        pass

    def test_isNeighboringArc(self):
        pass

    def test_isPassingArc(self):
        pass

    def test_isRepetitionArc(self):
        pass

    def test_isRepetition(self):
        pass

    def test_isLocalRepetition(self):
        pass

    def test_arcGenerateTransition(self):
        pass

    def test_arcGenerateRepetition(self):
        pass

    def test_arcExtendTransition(self):
        pass

    def test_pruneOpenHeads(self):
        pass

    def test_clearDependencies(self):
        pass

    def test_removeDependenciesFromArc(self):
        pass

    def test_addDependenciesFromArc(self):
        pass

    def test_isArcTerminal(self):
        i = 5
        arcs = [[0, 1, 2], [0, 3, 4], [6, 7, 8]]
        self.assertFalse(isArcTerminal(i, arcs))
        arcs = [[0, 1, 2], [0, 3, 4, 5], [6, 7, 8]]
        self.assertTrue(isArcTerminal(i, arcs))

    def test_isEmbeddedInArcs(self):
        i = 5
        arcs = [[0, 1, 2], [0, 3, 4], [6, 7, 8]]
        self.assertFalse(isEmbeddedInArcs(i, arcs))

    def test_isEmbeddedInArc(self):
        i = 5
        arc = [4, 7, 8]
        self.assertTrue(isEmbeddedInArc(i, arc))

    def test_isEmbeddedInOtherArc(self):
        arc = [4, 8, 20]
        arcs = [[0, 1, 2], [4, 14, 20]]
        self.assertTrue(isEmbeddedInOtherArc(arc, arcs,
                                             startIndex=0, stopIndex=20))

    def test_conflictsWithOtherArc(self):
        cond1 = ([0, 6], [[4, 8]])
        cond2 = ([4, 8], [[0, 6]])
        cond3 = ([4, 7, 9], [[6, 9]])
        cond4 = ([6, 7, 9], [[6, 8, 10]])
        self.assertTrue(conflictsWithOtherArc(cond1[0], cond1[1]))
        self.assertTrue(conflictsWithOtherArc(cond2[0], cond2[1]))
        self.assertTrue(conflictsWithOtherArc(cond3[0], cond3[1]))
        self.assertTrue(conflictsWithOtherArc(cond4[0], cond4[1]))

        a = ([0, 9, 10], [[4, 8]])
        b = ([4, 7, 9], [[4, 5, 6]])
        self.assertFalse(conflictsWithOtherArc(a[0], a[1]))
        self.assertFalse(conflictsWithOtherArc(b[0], b[1]))

    def test_isIndependent(self):
        n = note.Note('C4')
        n.dependency = dependency.Dependency()
        n.dependency.lefthead = None
        n.dependency.righthead = None
        n.dependency.dependents = []
        self.assertTrue(isIndependent(n))

    def test_areArcTerminals(self):
        h = 4
        i = 7
        arcs = [[0, 1, 4], [5, 6, 7]]
        self.assertFalse(areArcTerminals(h, i, arcs))
        arcs = [[0, 1, 4], [4, 5, 6, 7]]
        self.assertTrue(areArcTerminals(h, i, arcs))

    def test_arcLength(self):
        arc = [4, 5, 7, 10]
        self.assertTrue((arcLength(arc) == 6))


# -----------------------------------------------------------------------------


if __name__ == '__main__':
    unittest.main()

# -----------------------------------------------------------------------------
# eof
