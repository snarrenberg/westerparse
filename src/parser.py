# -----------------------------------------------------------------------------
# Name:         parser.py
# Purpose:      Framework for analyzing the Westergaardian structure
#               of simple tonal lines
#
# Author:       Robert Snarrenberg
# Copyright:    (c) 2020 by Robert Snarrenberg
# License:      BSD, see license.txt
# -----------------------------------------------------------------------------
'''
Parser
======

Designed as a transition-based dependency parser, the WesterParse parser
analyzes the syntax of a rhythmically simple melodic line
and produces a set of valid interpretations.

Procedure:

#. Accept a part from a context.
#. Infer the possible line type(s) if not given in advance.
#. Parse the part for each possible line type.
#. Return a set of parses and errors.

The machinery consists of a buffer, a stack, and a scanner.
At initialization, the notes of the line are read into the buffer.
The scanner then shifts notes onto the stack one by one. With each shift,
the transition is evaluated in light of the previously analyzed line.
As the scanning proceeds, the parser maintains lists of
open heads, open transitions, and syntactic units (arcs). These lists
shrink and grow as the interpretive process unfolds. When an arc is formed
(e.g., a passing or neighboring motion), a tuple of note positions is placed
in the list of arcs. Meanwhile, dependent elements within the arc are removed
from both the stack and the list of open transitions,
leaving structural heads in place for subsequent attachment.
The parser has a limited ability to
backtrack and reinterpret segments of a line.

The first stage of parsing ends when the buffer is exhausted.
Interpretation then continues by line type.

The parser gathers all of the valid interpretations into lists.
The parser also records errors that arise.
'''
from music21 import *
from utilities import pairwise
import itertools
import copy

# -----------------------------------------------------------------------------
# MODULE VARIABLES
# -----------------------------------------------------------------------------

# variables set by user
selectPreferredParses = True

# for third species
# localNeighborsOnly=False
# extendLocalArcs = True
# addLocalRepetitions = True


# -----------------------------------------------------------------------------
# MAIN CLASSES
# -----------------------------------------------------------------------------

class Parser():
    '''
    The Parser class is the engine of the parser. The bulk of the work is done
    by :py:func:`~parseTransition`.  After a preliminary parse of the line,
    the parser decides on a set of possible structural interpretations and
    creates a :py:class:`~Parser.Parse` object to store each interpretation.

    Upon initialization, the Parser automatically parses the line,
    using the following procedure:

    * Prepare placeholders for parses and errors.
    * Accept a line type if provided, otherwise infer the set
      of possible types.
    * Operate the preliminary parser: :py:func:`~preParseLine`.
    * Interrupt the parser if preliminary parsing is unsuccessful
      and report errors.
    * Determine the set of possible basic structures and parses
      for each possibility: :py:func:`~prepareParses`.
    * Gather all the valid interpretations of the part by line type:
      :py:func:`~collectParses`.
    * Reduce the set of interpretations using preference rules:
      :py:func:`~selectPreferredParses`.

    The individual parses are contained in a :py:class:`~Parser.Parse`.
    These are created by :py:func:`~prepareParses`.
    '''
    def __init__(self, part, context, **keywords):
        # Set up base content.
        self.part = part
        self.context = context
        self.notes = self.part.flat.notes

        # Collect errors by part, line type, and individual parse.
        # Raise exceptions in context.py: parseContext.
        self.errors = []  # syntax errors arising during pre-parse,
        #      by part
        #      results are collected for further evaluation
        self.typeErrorsDict = {}  # syntax errors arising during prepare parses,
        #      by lineType
        #      results are collected for further evaluation,
        #      only used for 'primary' and 'bass'
        self.parseErrorsDict = {}  # syntax errors arising during final parse,
        #      by parseLabel
        #      used only internally to weed out specific failures

        # The following lists will be returned
        # to the Part at the end of the Parser.
        self.parses = []  # list of parseLabels
        self.interpretations = {}  # syntax interpretations
        #       of the part in the context,
        #       keyed by lineType, dictionary built parseLabels in self.parses

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

        # STEP ONE: Operate the preliminary parser.
        self.preParseLine()

        # Interrupt parser if preliminary parsing is unsuccessful.
        # and report errors
        if self.errors:
            return

        # STEP TWO: Determine the set of possible basic structures,
        # and parse for each possibility.
        self.prepareParses()

        # STEP THREE: Gather all the valid interpretations
        # of the part by line type.
        self.collectParses()

        # STEP FOUR: Reduce the set of interpretations using preference rules.
        self.selectPreferredParses()

    def inferLineTypes(self):
        '''If the line type is not specified, infer a set of possibilities.'''
        cond1 = self.notes[0].csd.value % 7 in [0, 2, 4]
        cond2 = self.notes[-1].csd.value % 7 in [0, 2, 4]
        cond3 = self.notes[0].csd.value % 7 == 0
        cond4 = self.notes[-1].csd.value % 7 == 0
        cond5 = self.notes[-1].csd.value == 0
        if not cond1 and not cond2:
            error = ('Generic structure error: The line is not bounded '
                     'by tonic-triad pitches and hence not a valid tonic line.')
            self.errors.append(error)
            return
        else:
            self.part.lineTypes.append('generic')
        # Make some educated guesses as to whether
        # the line can be a bass line or primary line.
        if cond3 and cond4:
            for n in self.notes[1:-1]:
                if n.csd.value % 7 == 4:
                    self.part.lineTypes.append('bass')
                    break
        if cond1 and cond5:
            for n in self.notes[:-1]:
                if n.csd.value in [2, 4, 7]:
                    self.part.lineTypes.append('primary')
                    break

    def preParseLine(self):
        '''
        Conduct a preliminary parse of the line.
        Initialize the buffer, stack, and arcs.
        Initialize the lists of open heads and transitions.
        Set the global harmonic referents.
        Run the scanner, parsing each transition.
        '''
        # Initialize the buffer, stack, and arcs
        lineBuffer = [n for n in self.notes
                      if not n.tie or n.tie.type == 'start']
        lineStack = []
        arcs = []
        # Initialize the lists of open heads and transitions
        openHeads = [0]
        openTransitions = []
        # Set the global harmonic referents
        harmonyStart = [p for p in self.part.tonicTriad.pitches]
        harmonyEnd = [p for p in self.part.tonicTriad.pitches]

        if (self.part.species in ['first', 'second', 'fourth'] and
           not self.context.harmonicSpecies):
            # Run the line scanner.
            n = len(lineBuffer)
            while n > 1:
                shiftBuffer(lineStack, lineBuffer)
                n = len(lineBuffer)
                i = lineStack[-1]
                j = lineBuffer[0]
                # Parse the transition i-j.
                self.parseTransition(lineStack, lineBuffer, self.part, i, j,
                                     harmonyStart, harmonyEnd, openHeads,
                                     openTransitions, arcs)
                # Break upon finding errors.
                if self.errors:
                    break

        # TODO Figure out how to parse harmonic species.
        elif self.context.harmonicSpecies:
            pass

        elif self.part.species in ['third', 'fifth']:
            # Set variable for whether to attempt extending local arcs
            # outside local context.
            # Use for testing.
            localNeighborsOnly = False
            extendLocalArcs = True
            addLocalRepetitions = True

            # Scan the global context.
            n = len(lineBuffer)
            while n > 1:
                shiftBuffer(lineStack, lineBuffer)
                n = len(lineBuffer)
                i = lineStack[-1]
                j = lineBuffer[0]

                # Parse the local span whenever i falls
                # at the start of the measure.
                closedLocalPitchIndexes = []
                localStart = lineStack[-1].index
                localEnd = 0
                if i.beat == 1.0 or i.index == 0:  # and i.offset > 0.0:
                    localStack = []
                    localBuffer = []
                    localArcs = []
                    localOpenHeads = []
                    localOpenTransitions = []
                    if i.beat == 1.0 and i.index > 0:
                        localHarmonyStart = self.context.localHarmonyDict[i.offset]
                    else:  # Get tonic harmony for first measure.
                        localHarmonyStart = [p for p in self.part.tonicTriad.pitches]

                    # Fill the local buffer up to and including the next onbeat
                    # note and set localHarmonyEnd by that note.
                    for note in lineBuffer:
                        if note.beat == 1.0:
                            localBuffer.append(note)
                            localHarmonyEnd = self.context.localHarmonyDict[note.offset]
                            localEnd = note.index
                            break
                        else:
                            localBuffer.append(note)
                    # Now put i in the local buffer so i--j can be parsed.
                    localBuffer.insert(0, i)

                    # Add onbeat note to local heads.
                    localOpenHeads = [i.index]

                    # Scan local context.
                    ln = len(localBuffer)
                    while ln > 1:
                        shiftBuffer(localStack, localBuffer)
                        ln = len(localBuffer)
                        x = localStack[-1]
                        y = localBuffer[0]
                        self.parseTransition(localStack, localBuffer, self.part,
                                             x, y,
                                             localHarmonyStart, localHarmonyEnd,
                                             localOpenHeads,
                                             localOpenTransitions, localArcs)
                    # Break upon finding errors.
                        if self.errors:
                            break

                    # Look for local repetitions.
                    if addLocalRepetitions:
                        firstLocalHead = localOpenHeads[0]
                        for h in localOpenHeads[1:]:
                            if self.notes[h] == self.notes[firstLocalHead]:
                                self.notes[h].dependency.lefthead = firstLocalHead
                                self.notes[firstLocalHead].dependency.dependents.append(h)
                                arcGenerateRepetition(h, self.part, localArcs, localStack)
                                # Remove any intervening local heads.
                                revisedHeads = [head for head in localOpenHeads[1:]
                                                if head < h]
                                localOpenHeads = [firstLocalHead] + revisedHeads
                                # Transfer dependencies to new lefthead.
#                                for d in self.notes[h].dependency.dependents:
#                                    if self.notes[d].dependency.lefthead == h:
#                                        self.notes[d].dependency.lefthead = firstLocalHead

                    # If local insertions are not allowed, limit local arcs
                    # to neighbors and repetitions.
                    if localNeighborsOnly:
                        localArcs = [arc for arc in localArcs if
                                     (isNeighboring(arc, self.notes) or
                                      isRepetition(arc, self.notes))]

                    # Collect indexes of pitches that are
                    # embedded in local arcs.
                    for arc in localArcs:
                        if arc in localArcs:
                            cond1 = len(arc) == 3
                            cond2 = len(arc) == 2
                            cond3 = isNeighboring(arc, self.notes)
                            cond4 = isRepetition(arc, self.notes)
                            if (cond1 and cond3) or (cond2 and cond4):
                                for idx in range(arc[0]+1, arc[-1]+1):
                                    if self.notes[idx].beat != 1.0:
                                        closedLocalPitchIndexes.append(idx)
                            else:
                                for idx in range(arc[1], arc[-1]):
                                    closedLocalPitchIndexes.append(idx)
                        clp = []
                        closedLocalPitchIndexes = list(set(closedLocalPitchIndexes))
                        # Copy local arcs to global arcs.
                        arcs.append(arc)

                    # Try to extend local passing motions from
                    # or into bordering context
                    if extendLocalArcs:
                        # Try to extend local arcs leftward
                        # if lefthead in open transitions.
                        for arc in localArcs:
                            if arc[0] in openTransitions:
                                lh = self.notes[arc[0]].dependency.lefthead
                                # Get all of the global notes connected to
                                # the open transition.
                                globalElems = [idx for idx in
                                               self.notes[arc[0]].dependency.dependents
                                               if self.notes[arc[0]].dependency.lefthead < idx < arc[0]]
                                extensions = [lh] + globalElems

                                # See whether the global lefthead
                                # is just a step away
                                if isPassing(arc, self.notes):
                                    tempArc = extensions + arc
                                    # See whether new arc passes through
                                    # a consonant interval
                                    rules = [isPassing(tempArc, self.notes),
                                             isLinearConsonance(self.notes[tempArc[0]],
                                             self.notes[tempArc[-1]])]
                                    if all(rules):
                                        arcExtendTransition(self.notes, arc, extensions)
                                        openTransitions.remove(arc[0])
                                        localOpenHeads.remove(arc[0])
                                        closedLocalPitchIndexes.append(arc[0])
                                        arcs.remove(arc)
                                        localArcs.remove(arc)
                                        arcs.append(tempArc)
                                        localArcs.append(tempArc)

                        # Try to extend local arcs rightward if ...
                        for arc in localArcs:
                            if arc[-1] == localEnd-1:
                                tempArc = arc + [localEnd]
                                rules = [isPassing(tempArc, self.notes),
                                         isLinearConsonance(self.notes[arc[0]],
                                         self.notes[localEnd])]
                                if all(rules):
                                    arcExtendTransition(self.notes, arc, extensions=[localEnd])
                                    localOpenHeads.remove(arc[-1])
                                    closedLocalPitchIndexes.append(arc[-1])
                                    arcs.remove(arc)
                                    localArcs.remove(arc)
                                    arcs.append(tempArc)
                                    localArcs.append(tempArc)

                        # TODO: Try to extend leftward and rightward
                        # simultaneously?

                        # And now see whether any local neighbors
                        # remain available
                        if len(localOpenHeads) > 1:
                            pairs = itertools.combinations(localOpenHeads, 2)
                            for pair in pairs:
                                i = self.notes[pair[0]]
                                j = self.notes[pair[1]]
                                rules = [i.csd.value == j.csd.value,
                                         i.measureNumber == j.measureNumber,
                                         not isEmbeddedInArcs(pair[0], localArcs),
                                         not isEmbeddedInArcs(pair[1], localArcs)]
                                if all(rules):
                                    j.dependency.lefthead = i.index
                                    i.dependency.dependents.append(j.index)
                                    arcGenerateRepetition(j.index, self.notes,
                                                          localArcs, localStack)
                                    localOpenHeads.remove(j.index)
                                    closedLocalPitchIndexes.append(j.index)
                                    j.rule.name = 'L1'
                                    # remove embedded local heads
                                    for h in localOpenHeads:
                                        if i.index < h < j.index:
                                            localOpenHeads.remove(h)
                                            closedLocalPitchIndexes.append(h)

                # Shift locals into line stack if not locally closed.
                # Start with the top of the stack, which is
                # first in the local context.
                # Remove top of stack if it is now closed.
                if lineStack[-1].index in closedLocalPitchIndexes:
                    lineStack.pop(-1)
                # Then proceed through the rest of the local context.
                while lineBuffer[0].index < localEnd:
                    shiftBuffer(lineStack, lineBuffer)
                    if lineStack[-1].index in closedLocalPitchIndexes:
                        lineStack.pop(-1)

                # Restore the open locals to the buffer.
                while lineStack[-1].index > localStart:
                    shiftStack(lineStack, lineBuffer)

                # Reparse the open locals in the global context.
                # TODO This is problematical when there are several open locals.
                harmonyStart = [p for p in self.part.tonicTriad.pitches]
                harmonyEnd = [p for p in self.part.tonicTriad.pitches]
                while lineBuffer[0].index < localEnd:
                    i = lineStack[-1]
                    j = lineBuffer[0]
                    self.parseTransition(lineStack, lineBuffer, self.part, i, j,
                                         harmonyStart, harmonyEnd, openHeads,
                                         openTransitions, arcs)
                    shiftBuffer(lineStack, lineBuffer)

                # Parse the transition into the next span.
                if lineBuffer[0].index == localEnd:
                    i = lineStack[-1]
                    j = lineBuffer[0]
                    self.parseTransition(lineStack, lineBuffer, self.part, i, j,
                                         harmonyStart, harmonyEnd, openHeads,
                                         openTransitions, arcs)
                n = len(lineBuffer)

        if self.part.species in ['third', 'fifth'] and openTransitions:
            for idx in openTransitions:
                # TODO First look for 'resolution'.
                self.notes[idx].rule.name = 'L0'
        elif openTransitions:
            # TODO Convert to measures, note that indexes in fourth species
            # are for each individual half note, not each tied combination.
            error = ('There are unclosed transitions in the line at '
                     'the following positions: ' + str(openTransitions))
            self.errors.append(error)
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
        context.gatherArcs(self.part, arcs)
        self.part.show()
        for n in self.notes:
            n.style.color = 'black'

    def parseTransition(self, stack, buffer, part, i, j, harmonyStart,
                        harmonyEnd, openHeads, openTransitions, arcs):
        '''
        Asks a series of questions at the transition from note *i* to note *j*.

        * Do *i* and *j* belong to the harmony of the context
          (tonic, in the case of global contexts)?
        * What is the intervallic relation between *i* and *j* (step or skip)?
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

           * If *i* is an open transition, end the transition at *j*.

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

        #. *Consonant skip from nonharmonic to nonharmonic*

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

        '''
        case1 = [(isHarmonic(i, harmonyStart) and isHarmonic(j, harmonyStart)),
                 (isHarmonic(i, harmonyStart) and isHarmonic(j, harmonyStart))]
        case2 = [self.part.species in ['third', 'fifth'],
                 not isHarmonic(i, harmonyStart),
                 isHarmonic(j, harmonyEnd),
                 isDiatonicStep(i, j),
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
        case10 = [not isHarmonic(i, harmonyStart),
                  not isHarmonic(j, harmonyStart),
                  not isLinearConsonance(i, j),
                  not isLinearUnison(i, j)]
        case11 = [not isLinearConsonance(i, j),
                  not isLinearUnison(i, j),
                  not isDiatonicStep(i, j)]
        case12 = [not isSemiSimpleInterval(i, j)]

        # CASE ONE: Both pitches are harmonic.
        if all(case1):
            if self.part.species in ['third', 'fifth']:
                if j.pitch not in harmonyStart:
                    harmonyStart.append(j.pitch)
            if i.csd.value == j.csd.value:
                j.dependency.lefthead = i.index
                i.dependency.dependents.append(j.index)
                arcGenerateRepetition(j.index, part, arcs, stack)
            elif openTransitions:
                # See if j resolves the most recent open transition.
                t = openTransitions[-1]
                for t in reversed(openTransitions):
                    h = self.notes[t]
                    if isDiatonicStep(h, j):
                        h.dependency.righthead = j.index
                        if h.dependency.dependents:
                            for d in h.dependency.dependents:
                                self.notes[d].dependency.righthead = j.index
                        j.dependency.dependents.append(h.index)
                        openTransitions.remove(h.index)
                        arcGenerateTransition(h.index, part, arcs, stack)
                        pruneHeads = []
                        for x in openHeads:
                            if h.index < x < j.index:
                                pruneHeads.append(x)
                        openHeads[:] = [head for head in openHeads
                                        if head not in pruneHeads]
                        openHeads.append(j.index)
                        return
                else:
                    if i.index not in openHeads:
                        openHeads.append(i.index)
                    openHeads.append(j.index)
            else:
                if i.index not in openHeads:
                    openHeads.append(i.index)
                openHeads.append(j.index)

        # CASE TWO: Transition from the harmony of this bar
        # to the harmony of the next.
        elif all(case2):
            if i.index in openTransitions:
                i.dependency.righthead = j.index
                j.dependency.dependents.append(i.index)
                openTransitions.remove(i.index)
                for d in i.dependency.dependents:
                    if i.dependency.lefthead is None:
                        i.dependency.lefthead = self.notes[d].dependency.lefthead
                    # Add righthead to codependents if they share lefthead.
                    if self.notes[d].dependency.lefthead == i.dependency.lefthead:
                        self.notes[d].dependency.righthead = j.index
                arcGenerateTransition(i.index, part, arcs, stack)

        # CASE THREE: Step from harmonic to nonharmonic pitch.
        elif all(case3):
            if openTransitions:
                for t in reversed(openTransitions):
                    h = self.notes[t]
                    rules1 = [isStepUp(h, j),
                              h.csd.direction in ['ascending', 'bidirectional'],
                              j.csd.direction in ['ascending', 'bidirectional']]
                    rules2 = [isStepDown(h, j),
                              h.csd.direction in ['descending', 'bidirectional'],
                              j.csd.direction in ['descending', 'bidirectional']]
                    if all(rules1) or all(rules2):
                        j.dependency.lefthead = h.dependency.lefthead
                        j.dependency.dependents.append(h.index)  # YES?
                        h.dependency.dependents.append(j.index)
                        self.notes[h.dependency.lefthead].dependency.dependents.append(j.index)
                        openTransitions.remove(h.index)
                        openTransitions.append(j.index)
                        # TODO could/should i.index instead be added to openHeads???
                        if i.index in openHeads:
                            openHeads.remove(i.index)
                        break
                    if openHeads:
                        for t in reversed(openHeads):
                            h = self.notes[t]
                            # If i is the only open head, ...
                            if i.index == h.index:
                                j.dependency.lefthead = i.index
                                i.dependency.dependents.append(j.index)
                                openTransitions.append(j.index)
                                break
                            elif h != i:
                                # TODO rethink why we remove t from
                                # open heads during local parse
                                openHeads.remove(t)
                            elif h == i:
                                j.dependency.lefthead = h.index
                                h.dependency.dependents.append(j.index)
                                openTransitions.append(j.index)
                                break
                        else:
                            j.dependency.lefthead = i.index
                            i.dependency.dependents.append(j.index)
                            openTransitions.append(j.index)
                            break
                    else:
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
                        elif h != i:
                            # TODO rethink why we remove t from open heads
                            # during local parse
                            openHeads.remove(t)
                        elif h == i:
                            j.dependency.lefthead = h.index
                            h.dependency.dependents.append(j.index)
                            break
                    else:
                        j.dependency.lefthead = i.index
                        i.dependency.dependents.append(j.index)
                        openTransitions.append(j.index)
                else:
                    j.dependency.lefthead = i.index
                    i.dependency.dependents.append(j.index)
                # TODO 2020-06-09 should this be indented?
                openTransitions.append(j.index)

        # CASE FOUR: Step from nonharmonic to harmonic pitch.
        elif all(case4):
            # Complete the local harmony if possible
            if self.part.species in ['third', 'fifth']:
                if j.pitch not in harmonyStart:
                    harmonyStart.append(j.pitch)
            # TODO 2020-07-08: isn't i already on the list of open transitions?
            if not openTransitions:
                # if step up or down, i.csd.direction must match direction of step
                if isStepUp(i, j) and i.csd.direction not in ['ascending', 'bidirectional']:
                    openTransitions.append(i.index)
                elif isStepDown(i, j) and i.csd.direction not in ['descending', 'bidirectional']:
                    openTransitions.append(i.index)
                else:
                    i.dependency.righthead = j.index
                    j.dependency.dependents.append(i.index)
                    # TODO: when is the arc created for this??
            elif openTransitions:
                for t in reversed(openTransitions):
                    h = self.notes[t]
                    if t == i.index:
                        if isStepUp(i, j) and i.csd.direction in ['ascending', 'bidirectional']:
                            i.dependency.righthead = j.index
                            j.dependency.dependents.append(i.index)
                            for d in i.dependency.dependents:
                                self.notes[d].dependency.righthead = j.index
                            openTransitions.remove(i.index)
                            if self.notes[i.dependency.lefthead] != self.notes[i.dependency.righthead]:
                                openHeads.append(j.index)
                            arcGenerateTransition(i.index, part, arcs, stack)
                            # If lefthead of transition is not in triad,
                            # remove from open heads.
                            if not(isHarmonic(self.notes[i.dependency.lefthead], harmonyStart)):
                                openHeads.remove(i.dependency.lefthead)
                        elif isStepDown(i, j) and i.csd.direction in ['descending', 'bidirectional']:
                            i.dependency.righthead = j.index
                            j.dependency.dependents.append(i.index)
# REMOVED 2020-05-26: add dependents to j
#     I removed the following three lines, because they added dependents that shouldn't really to j
# REINSTATED 2020-05-26: add dependents to j, because otherwise longer passing motions don't get parsed correctly
# TODO: figure out how to add only those dependents that share the lefthead
                            for d in i.dependency.dependents:
                                self.notes[d].dependency.righthead = j.index
                                j.dependency.dependents.append(d)
                            openTransitions.remove(i.index)
                            if self.notes[i.dependency.lefthead] != self.notes[i.dependency.righthead]:
                                openHeads.append(j.index)
                            arcGenerateTransition(i.index, part, arcs, stack)
                        elif isStepUp(i, j) and i.csd.direction == 'descending' and isStepUp(self.notes[i.dependency.lefthead], i):
                            i.dependency.righthead = j.index
                            j.dependency.dependents.append(i.index)
                            openTransitions.remove(i.index)
                            arcGenerateTransition(i.index, part, arcs, stack)
# 2020-06-10 not sure why we are checking relation between open trans and nonharmonic i
# TODO rethink this if problem cases are discovered
#                     elif isStepDown(h, i) and h.csd.direction == i.csd.direction:
#                         if i.csd.direction in ['descending', 'bidirectional']:
#                             h.dependency.righthead = j.index
#                             i.dependency.righthead = j.index
#                             self.notes[h.dependency.lefthead].dependency.dependents.append(i.index)
#                             self.notes[j.index].dependency.dependents.append(h.index)
#                             self.notes[j.index].dependency.dependents.append(i.index)
#                             openTransitions.remove(h.index)
#                             if i.index in openTransitions:
#                                 openTransitions.remove(i.index)
#                             arcGenerateTransition(h.index, part, arcs, stack)
#                     elif isStepUp(h, i) and h.csd.direction == i.csd.direction:
#                         print('listening to', j.index, openHeads, arcs, openTransitions)
#                         if i.csd.direction in ['ascending', 'bidirectional']:
#                             h.dependency.righthead = j.index
#                             i.dependency.righthead = j.index
#                             self.notes[h.dependency.lefthead].dependency.dependents.append(i.index)
#                             self.notes[j.index].dependency.dependents.append(h.index)
#                             self.notes[j.index].dependency.dependents.append(i.index)
#                             openTransitions.remove(h.index)
#                             # I think this should be the same as with StepDown
#                             if i.index in openTransitions:
#                                 openTransitions.remove(i.index)
#                             arcGenerateTransition(h.index, part, arcs, stack)

                    elif isDiatonicStep(h, j) and t != i.index:
                        if isStepUp(h, j) and h.csd.direction in ['ascending', 'bidirectional']:
                            h.dependency.righthead = j.index
                            j.dependency.dependents.append(h.index)
                            for d in h.dependency.dependents:
                                if d < h.index and isStepUp(self.notes[d], h):
                                    self.notes[d].dependency.righthead = j.index
                                    # TODO Remove condition if there's no reason
                                    # why d is not still in openTransitions
                                    openTransitions[:] = [trans for trans
                                                          in openTransitions
                                                          if trans != d]
                            openTransitions.remove(h.index)
                            arcGenerateTransition(h.index, part, arcs, stack)
                            openHeads[:] = [head for head in openHeads if head <= h.index]
                            if j.index not in openHeads:
                                openHeads.append(j.index)
                        elif isStepDown(h, j) and h.csd.direction in ['descending', 'bidirectional']:
                            h.dependency.righthead = j.index
                            j.dependency.dependents.append(h.index)
                            for d in h.dependency.dependents:
                                if d < h.index and isStepDown(self.notes[d], h):
                                    self.notes[d].dependency.righthead = j.index
                                    # TODO: d was probably removed from open
                                    # transitions somewhere prior to this
                                    # so this may be entirely unnecessary.
                                    openTransitions[:] = [trans for trans
                                                          in openTransitions
                                                          if trans != d]
                            openTransitions.remove(h.index)
                            arcGenerateTransition(h.index, part, arcs, stack)
                            openHeads[:] = [head for head in openHeads
                                            if head <= h.index]
                            if j.index not in openHeads:
                                openHeads.append(j.index)
                    elif i.index in openTransitions:
                        i.dependency.righthead = j.index
                        j.dependency.dependents.append(i.index)
                        openTransitions.remove(i.index)
                        openHeads.append(j.index)
                        for d in i.dependency.dependents:
                            if i.dependency.lefthead is None:
                                i.dependency.lefthead = self.notes[d].dependency.lefthead
                            self.notes[d].dependency.righthead = j.index
                            j.dependency.dependents.append(d.index)
                        arcGenerateTransition(i.index, part, arcs, stack)
                        break
            elif i.dependency.lefthead is None:
                for t in reversed(openHeads):
                    h = self.notes[t]
                    if not isDiatonicStep(h, i):
                        openHeads.remove(t)
                    elif isDiatonicStep(h, i):
                        h.dependency.dependents.append(i.index)
                        j.dependency.dependents.append(i.index)
                        i.dependency.lefthead = h.index
                        if i.index in openTransitions:
                            openTransitions.remove(i.index)
                        openHeads.append(j.index)
                        arcGenerateTransition(i.index, part, arcs, stack)
                    break

        # CASE FIVE: Step from nonharmonic to nonharmonic.
        elif all(case5):
            if (i.csd.direction == j.csd.direction or
               i.csd.direction == 'bidirectional' and
               j.csd.direction == 'ascending'):
                if i.dependency.lefthead is None:
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
                            # been added to openTransitions.
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
# 2020-06-09 added rules to make sure that reversals continue in same direction
# needs to be verified in further tests
                        rules1 = [isStepDown(self.notes[i.dependency.lefthead], i),
                                  isStepDown(i, j)]
                        rules2 = [isStepUp(self.notes[i.dependency.lefthead], i),
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
# TODO verify that this new code handles reversals in passing motions:
# allow for finding preceding as well as subsequent head
# at the change of direction, close off an arc, then look backward for head or add i to openTransitions
                    else:
                        if i.consecutions.leftDirection == j.consecutions.leftDirection:
                            j.dependency.lefthead = i.dependency.lefthead
                            i.dependency.dependents.append(j.index)
                            j.dependency.dependents.append(i.index)
                            openTransitions.remove(i.index)
                            openTransitions.append(j.index)
                        else:
                            earlierHeads = [ind for ind in openHeads if ind < i.dependency.lefthead]
                            connectsToHead = False
                            for h in reversed(earlierHeads):
                                if h != 0 and not isDiatonicStep(self.notes[h], i):
                                    pass
                                elif isDiatonicStep(self.notes[h], i):
                                    # Generate a transition to i and then
                                    # reassign i's lefthead etc.
                                    connectsToHead = True
                                    self.notes[i.dependency.dependents[-1]].dependency.righthead = i.index
                                    arcGenerateTransition(i.dependency.dependents[-1], part, arcs, stack)
                                    i.dependency.lefthead = h
                                    j.dependency.lefthead = h
                                    i.dependency.dependents.append(j.index)
                                    j.dependency.dependents.append(i.index)
                                    self.notes[h].dependency.dependents.append(j.index)
                                    self.notes[h].dependency.dependents.append(i.index)
# 2020-06-10 added line to remove embedded heads between h and j
# need to verify that this is always correct
                                    openHeads[:] = [head for head in openHeads if not h < head < j.index]
                                    openTransitions.remove(i.index)
                                    openTransitions.append(j.index)
                                    break
                            if not connectsToHead:
# 2020-06-10
# now set things up to allow for connection to a later head
                                openHeads.append(i.index)
                                i.dependency.dependents.append(j.index)
                                j.dependency.lefthead = i.index
                                openTransitions.append(j.index)
# close off the transition to i, and add i to j's dependents, remove i from open transitions and add j
#                                error = 'The non-tonic-triad pitch ' + j.nameWithOctave + str(j.index) + ' cannot be generated.'
#                                self.errors.append(error)

            elif i.csd.direction == 'ascending' and j.csd.direction == 'descending':
                i.dependency.righthead = j.index
                j.dependency.dependents.append(i.index)
                openTransitions.remove(i.index)
                openTransitions.append(j.index)
                arcGenerateTransition(i.index, part, arcs, stack)
            elif i.csd.direction == 'ascending' and j.csd.direction == 'bidirectional':
                # Added this if trap on 2020-06-05 to capture 8-#7-#6-5 in minor
                if i.csd.value % 7 == 6 and j.csd.value % 7 == 5:
                    j.dependency.lefthead = i.index
                    i.dependency.dependents.append(j.index)
                    openTransitions.append(j.index)
                else:
                    j.dependency.lefthead = i.dependency.lefthead
                    i.dependency.dependents.append(j.index)
                    j.dependency.dependents.append(i.index)
                    self.notes[j.dependency.lefthead].dependency.dependents.append(j.index)
                    openTransitions.append(j.index)
            elif i.csd.direction == 'bidirectional' and j.csd.direction == 'descending':
                # For catching 5-#6-b7 in minor, revised 2020-06-05
                i.dependency.righthead = j.index
                j.dependency.dependents.append(i.index)
                openTransitions.append(j.index)
                openTransitions.remove(i.index)
                arcGenerateTransition(i.index, part, arcs, stack)
                openHeads.remove(i.dependency.lefthead)
                # Take lefthead off the stack, too.
                stack = [n for n in stack if n.index != i.dependency.lefthead]
#            elif i.csd.direction == 'bidirectional' and j.csd.direction == 'bidirectional':
#                print('listening to', j.index, j.dependency.lefthead)
            else:
                # I think this is okay, for catching things in third species
                j.dependency.lefthead = i.dependency.lefthead
                i.dependency.dependents.append(j.index)
                j.dependency.dependents.append(i.index)
                openTransitions.remove(i.index)
                openTransitions.append(j.index)

        # CASE SIX: Skip from nonharmonic to harmonic.
        elif all(case6):
            if i.dependency.lefthead is None:
                for t in reversed(openHeads):
                    h = self.notes[t]
                    if isDiatonicStep(h, i):
                        i.dependency.lefthead = h.index
                        h.dependency.dependents.append(i.index)
                        if i.index not in openTransitions:
                            openTransitions.append(i.index)
                        openHeads.append(j.index)
                        break
            else:
                openHeads.append(j.index)

        # CASE SEVEN: Skip from harmonic to nonharmonic.
        elif all(case7):
            if openTransitions:
                # A. See whether j continues a transition in progress
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
# 2020-06-09 I don't think two unrelated transitions can be in progress at the
# same time, except when the lefthead of the second is later than
# (not earlier than!) the first open transition, so I rewrote the earlierHeads
# to get heads that intervene between the first and second transition
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
                # C. If neither of these works, return an error.
                    if not connectsToHead:
                        error = ('The non-tonic-triad pitch '
                                 + j.nameWithOctave + ' in measure '
                                 + str(j.measureNumber) + ' cannot be generated.')
                        self.errors.append(error)
            elif openHeads:
                skippedHeads = []
                for h in reversed(openHeads):
                    # A. Look for an open head to attach to.
                    if h != 0 and not isDiatonicStep(self.notes[h], j):
                        skippedHeads.append(h)
                    elif isDiatonicStep(self.notes[h], j):
                        self.notes[h].dependency.dependents.append(j.index)
                        j.dependency.lefthead = h
                        openTransitions.append(j.index)
                        # Remove skipped heads from open heads and stack.
                        openHeads[:] = [head for head in openHeads
                                        if head not in skippedHeads]
                        for s in reversed(stack):
                            if s.index in skippedHeads:
                                stack.remove(s)
                        break  # Stop now that a lefthead was found.
                    # B. If A was not successful, search for possible
                    # step-related antecedent (head or trans)
                    # that was previously deleted from the stack.
                    # TODO May need to turn off in third species.
                    elif h == 0 and i.dependency.lefthead is None and i.index != h:
                        # Test cases: Westergaard100k, soprano; Primary05.
                        # (Search 1) Look in reverse at the terminals of current
                        # arcs and select the most recent that is step-related;
                        # return the note of that terminal to the stack and
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
                            newLefthead = leftheadCandidates[0]
                            j.dependency.lefthead = newLefthead
                            openTransitions.append(j.index)
                            self.notes[newLefthead].dependency.dependents.append(j.index)
                            # Look for arcs that cross over the new lefthead
                            # and remove from arc list;
                            # remove the righthead and reset its dependencies;
                            # and return transitional elements to list
                            # of open transitions.
                            for arc in arcs:
                                if isEmbeddedInArc(newLefthead, arc):
                                    arcs.remove(arc)
                                    for idx in arc[1:-1]:
                                        openTransitions.append(idx)
                                        self.notes[idx].dependency.righthead = None
                                        self.notes[arc[-1]].dependency.dependents.remove(idx)
                                    openHeads.remove(arc[-1])
                            openTransitions = sorted(openTransitions)
                            break
                        # (Search 2) Look for possible step-related transition
                        # that was previously integrated into a neighbor arc;
                        # look for sd7 as lower neighbor or sd6 as upper
                        # neighbor, bidirectional, prior to j.index;
                        # make sure there are no open transitions between
                        # that neighbor and j.index.
                        if (j.csd.value % 7 == 6 or j.csd.value % 7 == 5 and
                           j.csd.direction == 'bidirectional'):
# 2020-06-22 remove lefthead_found trap
#                            lefthead_found = False
                            for arc in arcs:
                                # Look for 8-7-8 if j is 6, or 5-6-5 if j is 7.
                                rules1 = [isNeighboring(arc, self.notes),
                                          isDiatonicStep(self.notes[arc[1]], j),
                                          self.notes[arc[0]].csd.value % 7 == 0,
                                          j.csd.value % 7 == 5]
                                rules2 = [isNeighboring(arc, self.notes),
                                          isDiatonicStep(self.notes[arc[1]], j),
                                          self.notes[arc[0]].csd.value % 7 == 4,
                                          j.csd.value % 7 == 6]
                                openTransBetween = [idx for idx in openTransitions if arc[1] < idx < j.index]
                                rules3 = [not openTransBetween]
                                rules4 = [self.notes[arc[1]].csd.value % 7 == 6,
                                          self.notes[arc[1]].csd.direction == 'ascending']
                                rules5 = [self.notes[arc[1]].csd.value % 7 == 6,
                                          self.notes[arc[1]].csd.direction == 'bidirectional']
                                if (all(rules1) or all(rules2)) and all(rules3):
                                    if all(rules4):
                                        arcs.remove(arc)
                                        openTransitions.append(j.index)
                                        openTransitions.append(arc[1])
                                        self.notes[arc[1]].dependency.righthead = None
                                        self.notes[arc[-1]].dependency.dependents.remove(arc[1])
                                        j.dependency.lefthead = arc[1]
                                        return
                                    elif all(rules5):
                                        arcs.remove(arc)
                                        openTransitions.append(j.index)
                                        self.notes[arc[1]].dependency.righthead = None
                                        self.notes[arc[-1]].dependency.dependents.remove(arc[1])
                                        j.dependency.dependents.append(arc[1])
                                        j.dependency.lefthead = self.notes[arc[1]].dependency.lefthead
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
                        demotedHeads = [note.index for note in self.notes
                                        if note.index < i.index and isIndependent(note)]
                        if demotedHeads:
                            for h in reversed(demotedHeads):
                                if isDiatonicStep(self.notes[h], j):
                                    # Look for arcs that cross over h.
                                    for arc in arcs:
                                        if arc[-2] < h < arc[-1]:
                                            # Restore arc[-2] to open
                                            # transitions and
                                            # remove old righthead
                                            openTransitions.append(arc[-2])
                                            for t in arc[1:-1]:
                                                self.notes[t].dependency.righthead = None
                                            clearDependencies(self.notes[arc[-1]])
                                            arcs.remove(arc)
                                            self.notes[h].dependency.dependents.append(j.index)
                                            j.dependency.lefthead = h
                                            openTransitions.append(j.index)
                                            openHeads.append(h)
                                            newhead = True
                                            # Remove any open heads that
                                            # intervene between the new lefhead
                                            # and j
                                            for oh in openHeads:
                                                if h < oh < j.index:
                                                    openHeads.remove(oh)
                                            return

#  (4) if either of these fails, take the radical approach ?
#
#                         stack = self.notes[0:j.index]
#                         for s in reversed(stack):
#                             clearDependencies(s)
#                             for arc in arcs:
#                                 if arc[-1] == s.index:
#                                     arcs.remove(arc)
#                         stack.pop()  # remove i from consideration
#                         for x in reversed(stack):
#                             buffer.insert(0,x)
#                             stack.pop()
#
                        else:
                            error = ('The non-tonic-triad pitch '
                                     + j.nameWithOctave + ' in measure '
                                     + str(j.measureNumber) + ' cannot be generated.')
                            self.errors.append(error)

                    # C. If neither of these works, return an error.
                    else:
                        error = ('The non-tonic-triad pitch '
                                 + j.nameWithOctave + ' in measure '
                                 + str(j.measureNumber) + ' cannot be generated.')
                        self.errors.append(error)

        # CASE EIGHT: Skip from nonharmonic to nonharmonic.
        elif all(case8):
            openNonTonicTriadPitches = []
            if self.part.species not in ['third', 'fifth']:
                if i.index == j.index-1:
                    error = ('Nongenerable succession between '
                             + i.nameWithOctave + ' and '
                             + j.nameWithOctave + ' in the line.')
                    self.errors.append(error)
                else:
                    error = ('The line contains an ungenerable intertwining '
                             'of secondary structures involving '
                             + j.nameWithOctave + ' in measure ' +
                             str(j.measureNumber) + '.')
                    self.errors.append(error)
            elif self.part.species in ['third', 'fifth']:
                # TODO Interpret local non-tonic insertions.
                if i.index not in openNonTonicTriadPitches:
                    openNonTonicTriadPitches.append(i.index)
                openNonTonicTriadPitches.append(j.index)
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
            # TODO: Double check this error, might be too simple.
            if i.index == j.index - 1 or i.measureNumber != j.measureNumber:
                error = ('Repetition of a non-tonic-triad pitch: '
                         + i.nameWithOctave + '.')
                self.errors.append(error)
            else:
                pass

        # CASE TEN: Dissonant skip between nonharmonic pitches.
        elif all(case10):
            if i.index == j.index-1:
                error = ('Nongenerable dissonant leap between '
                         + i.nameWithOctave + ' and '
                         + j.nameWithOctave + ' in the line.')
                self.errors.append(error)
            else:
                error = ('The line contains an ungenerable intertwining of '
                         'secondary structures involving '
                         + j.nameWithOctave + ' in measure ' +
                         str(j.measureNumber) + '.')
                self.errors.append(error)

        # CASE ELEVEN: Nongenerable skip.
        elif all(case11):
            error = ('Nongenerable leap between ' + i.nameWithOctave +
                     ' and ' + j.nameWithOctave + ' in the line.')
            self.errors.append(error)

        # CASE TWELVE: Leap larger than an octave.
        elif all(case12):
            error = ('Leap larger than an octave between ' + i.nameWithOctave +
                     ' and ' + j.nameWithOctave + ' in the line.')
            self.errors.append(error)

        # TODO Prune the list open heads if a repetition has been added.
        # TODO Figure out the optimal time to prune direct repetitions from
        # the list of open heads.

    def prepareParses(self):
        '''
        After preliminary parsing is completed, determines possibiities
        for basic structures based on available line types and parse the line
        using each candidate for basic structure. The results are collected
        in self.parses.

        If the line type is :literal:`bass`, the function verifies that the
        line begins and ends on a tonic degree (rules S1 and S2) and then
        assembles a list of notes that could complete the basic arpeggiation
        (rule S3) and builds a :py:class:`~Parser.Parse`
        for each S3 candidate. (See :py:func:`~Parser.Parse.parseBass`.)

        If the line type is :literal:`primary`, the function verifies that
        the line ends on a tonic degree (rule S1) and then assembles
        a list of notes that could initiate a basic step motion (rule S2).
        The function uses eight different methods to determine
        whether a valid basic step motion exists for each S2 candidate
        (see :py:func:`~Parser.Parse.parsePrimary`)
        and attempts to build a :py:class:`~Parser.Parse` using each method;
        not every method yields a result.

        If the line type is :literal:`generic`,
        the function verifies that the line begins and ends
        on triad pitches (rules S1 and S2) and then looks for
        a possible step connection between these terminal pitches
        (see :py:func:`~Parser.Parse.parseGeneric`).
        '''

        # The stack may still have some underinterpreted open heads.
        # If so, the remnant of open heads will be placed in the Parse's
        # buffer and re-parsed.
        for lineType in self.part.lineTypes:
            # Restock the buffer and initialize the empty stack.
            buffer = [self.notes[head] for head in self.openHeads]
            stack = []

            # Look for S2 or S3 candidate notes in the given line type
            # and build parse objects for each candidate.
            # Assign a label and counter to each parse object.
            parsecounter = 1

            if lineType == 'bass':
                buildErrors = []
                if self.notes[0].csd.value % 7 != 0:
                    buildError = ('Bass structure error: The line '
                                  'does not begin on the tonic degree.')
                    buildErrors.append(buildError)
                if self.notes[-1].csd.value % 7 != 0:
                    buildError = ('Bass structure error: The line '
                                  'does not end on the tonic degree.')
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
                if not s3cands:
                    buildError = ('Bass structure error: '
                                  'No candidate for S3 detected.')
                    buildErrors.append(buildError)

                if buildErrors == []:
                    for cand in s3cands:
                        self.buildParse(cand, lineType,
                                        parsecounter, stack, buildErrors=[])
                        parsecounter += 1
                # If the build as type fails, collect errors in dictionary.
                else:
                    self.typeErrorsDict[lineType] = buildErrors

            elif lineType == 'primary':
                buildErrors = []
                if self.notes[-1].csd.value % 7 != 0:
                    buildError = ('Primary structure error: The line '
                                  'does not end on the tonic degree.')
                    buildErrors.append(buildError)
                s2cands = []  # holder for Notes that might become S2
                n = len(buffer)
                while n > 0:
                    shiftBuffer(stack, buffer)
                    n = len(buffer)
                    i = stack[-1]
                    if i.csd.value in {2, 4, 7}:
                        s2cands.append(i)
                if not s2cands:
                    buildError = ('Primary structure error: '
                                  'No candidate for S2 detected.')
                    buildErrors.append(buildError)

                # Create a Parse object for each S2cand
                # and then turn over further processes to each Parse object,
                # using a series of methods to infer a basic step motion.
                methods = 9
                if buildErrors == []:
                    for cand in s2cands:
                        for m in range(0, methods):
                            self.buildParse(cand, lineType, parsecounter,
                                            stack, buildErrors=[], method=m)
                            parsecounter += 1  # update numbering of parses
                # If the build as type fails, collect errors in dictionary.
                else:
                    self.typeErrorsDict[lineType] = buildErrors

            elif lineType == 'generic':  # for generic lines, first note is S2
                s2cand = buffer[0]
                stack = buffer
                self.buildParse(s2cand, lineType, parsecounter, stack, buildErrors=[])

    def buildParse(self, cand, lineType, parsecounter,
                   stack, buildErrors, method=None):
        '''Sets up the basic features of the parse object
        and then executes the parsing process.
        Uses deep copies of the arcs and notes, as the list of arcs and the
        properties of notes will be altered during the process.
        '''
        # create the Parse object
        newParse = Parser.Parse()
        # copy information
        newParse.S1Index = self.notes[-1].index
        newParse.arcs = copy.deepcopy(self.arcs)
        newParse.lineType = lineType
        newParse.species = self.part.species
        newParse.tonic = self.part.tonic
        newParse.mode = self.part.mode
        newParse.partNum = self.part.partNum
        newParse.notes = copy.deepcopy(self.notes)
        newParse.errors = buildErrors
        newParse.notes[newParse.S1Index].rule.name = 'S1'
        newParse.method = method
        # Prepare the basic structure information.
        if lineType == 'bass':
            newParse.label = 'parse' + str(parsecounter) + '_BL'
            newParse.S2Index = 0
            newParse.S3Index = cand.index
            newParse.S3Degree = cand.csd.degree
            newParse.S3Value = cand.csd.value
            newParse.notes[newParse.S2Index].rule.name = 'S2'
            newParse.notes[newParse.S3Index].rule.name = 'S3'
        elif lineType == 'primary':
            newParse.label = 'parse' + str(parsecounter) + '_PL'
            newParse.S2Index = cand.index
            newParse.S2Degree = cand.csd.degree
            newParse.S2Value = cand.csd.value
            newParse.notes[newParse.S2Index].rule.name = 'S2'
        elif lineType == 'generic':
            newParse.label = 'parse' + str(parsecounter) + '_GL'
            newParse.S2Index = cand.index  # always 0
            newParse.S2Degree = cand.csd.degree
            newParse.S2Value = cand.csd.value
            newParse.notes[newParse.S2Index].rule.name = 'S2'
        # Copy the remnant of open heads from the stack.
        newParse.stackremnant = stack

        # Now parse the line.
        newParse.performLineParse()
        # And return the results to the Parser.
        self.parses.append(newParse)
        self.parseErrorsDict.update({newParse.label: newParse.errors})

    class Parse():
        '''An object for holding one interpretation of
        a line's syntactic structure.

        The object's attributes include `S1Index`, `S2Degree`, `S2Index`,
        `S2Value`, `S3Degree`, `S3Final`, `S3Index`, `S3Indexes`, `S3Initial`,
        `S3PenultCands`, `S3Value`, `label`, `arcs`, `tonic`, `mode`, and
        `arcBasic`.
        '''
        def __init__(self):
            self.stackremnant = []
            self.buffer = []
            self.stack = []
            self.errors = []


        def __repr__(self):
            return self.label

        def performLineParse(self):
            '''
            Create a complete interpretation of the line,
            using the following procedure:

            * Construct an arc for the basic structure,
              given the line type and
              a specific option for the basic structure.
            * Assign rules to notes in secondary structures.
            * Test for resolution of local insertions in third species.
            * Consolidate arcs into longer passing motions, if possible
            * Assemble lists for rule labels and parentheses, to be used when
              generating representations of the interpretation.
            * Set the dependency level of each note. [This function is
              currently disabled.]
            '''
            if self.lineType == 'primary':
                self.parsePrimary()
            elif self.lineType == 'bass':
                self.parseBass()
            elif self.lineType == 'generic':
                self.parseGeneric()
            else:
                pass
            # exit parse if no basic arc is found
            if self.arcBasic is None:
                return self.errors
            else:
                pass

            # assign rules to notes in secondary structures
            self.assignSecondaryRules()
            # test for resolution of local insertions in third species
            self.testLocalResolutions()
            # consolidate arcs into longer passing motions if possible
            self.pruneArcs()
            # make lists for rule labels and parentheses
            # tuples of note indices and labels/parentheses
            # for running with musicxml input/output
            self.gatherRuleLabels()
            self.gatherParentheses()

            # TODO finish writing function to set dependency levels
#            self.setDependencyLevels()

        def arcMerge(self, arc1, arc2):
            '''A function for combining two passing motions that share an inner node and direction.'''
            # merges elements into first arc and empties the second
            # revises dependencies
            leftouter = self.notes[arc1[0]]
            rightinner = self.notes[arc1[-1]]
            leftinner = self.notes[arc2[0]]
            rightouter = self.notes[arc2[-1]]

            rules1 = [rightinner.csd.value == leftinner.csd.value]
            rules2 = [leftouter.csd.value > rightinner.csd.value > rightouter.csd.value,
                      leftouter.csd.value < rightinner.csd.value < rightouter.csd.value]
            if all(rules1) and any(rules2):
                # merge arc2 elements into arc1
                removeDependenciesFromArc(self.notes, arc1)
                removeDependenciesFromArc(self.notes, arc2)
                # if arcs do not share node, make end of arc1 lefthead of start of arc2
                # make a repetition arc
                if arc1[-1] != arc2[0]:
                    self.notes[arc2[0]].dependency.lefthead = arc1[-1]
                    self.notes[arc1[-1]].dependency.dependents.append(arc2[0])
                    self.arcs.append([arc1[-1], arc2[0]])
                self.arcs.remove(arc2)
                arc2.pop(0)
                for n in arc2:
                    arc1.append(n)
                # revise dependencies
                addDependenciesFromArc(self.notes, arc1)

        def arcEmbed(self, arc1, arc2):
            '''A function for for embedding a repetition inside a passing motion.'''
            # in either order
            # start with repetition linked to passing, then embed
            leftouter = self.notes[arc1[0]]
            rightinner = self.notes[arc1[-1]]
            leftinner = self.notes[arc2[0]]
            rightouter = self.notes[arc2[-1]]
            # the arcs share a node
            rules1 = [rightinner.csd.value == leftinner.csd.value,
                      rightinner.index == leftinner.index]
            # arc1 is a simple repetition and they share the same pitch on the lefthead
            rules2 = [len(arc1) == 2,
                      leftouter.csd.value == leftinner.csd.value]
            # arc2 is a simple repetition and they share the same pitch on the lefthead
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

        def parsePrimary(self):
            '''
            Uses eight different methods to find a basic step motion from a potential S2:

            #. Look for one existing basic step motion arc that starts from S2.
            #. Look for an existing basic step motion arc that can be attached
               to S2 (repetition + passing)
            #. Look for two arcs that can fused into a basic step motion (passing +
               neighbor/repetition).
            #. Look for two arcs that can be merged into a basic step motion
               (passing + passing).
            #. Look for three arcs that can be merged into a basic step motion
               (passing + passing + passing).
            #. Take an existing 5-4-3 arc (the longest spanned, if more than one)
               and try to find a connection -2-1 to complete a basic arc.
            #. Look for a nonfinal arc from S2 whose terminus == S1.csd.value,
               and extend the arc to end on S1Index if possible.
            #. Reinterpret the line, looking for a descending step motion from S2
               and then parsing the remaining notes. The least reliable method.

            '''
            # once all preliminary parsing is done, prepare for assigning basic structure
            self.arcs.sort()  # = sorted(self.arcList)
            self.arcBasic = None

            # METHOD 0: from any S2 candidate
            # look for one existing basic step motion arc that starts from S2
            if self.method == 0:
                for counter, arc1 in enumerate(self.arcs):
                    rules = [arc1[0] == self.S2Index,
                             arc1[-1] == self.S1Index]
                    if all(rules):
                        self.arcBasic = arc1

            # METHOD 1: from any S2 candidate
            # look for an existing basic step motion arc that can be attached to S2:
            # repetition + passing
            elif self.method == 1:
                for counter, arc1 in enumerate(self.arcs):
                    a = self.notes[arc1[0]]  # the arc's leftmost Note
                    b = self.notes[arc1[-1]]  # the arc's rightmost Note
                    rules = [a.index != self.S2Index,
                             a.csd.value == self.S2Value,
                             b.index == self.S1Index]
                    if all(rules):
                        a.dependency.lefthead = self.S2Index
                        arcGenerateRepetition(a.index, self.notes, self.arcs, self.stack)
                        a.rule.name = 'E1'
                        for n in arc1[1:-1]:
                            self.notes[n].dependency.lefthead = self.S2Index
                            self.notes[self.S2Index].dependency.dependents.append(n)
                            self.arcBasic = arc1[1:]
                            self.arcBasic.insert(0, self.S2Index)

            # METHOD 2: may only work if S2 is sd3
            # look for two arcs that can fused into a basic step motion:
            # passing + neighbor/repetition
            elif self.method == 2:
                for counter, arc1 in enumerate(self.arcs):
                    rules1 = [arc1[0] == self.S2Index,
                              not arc1[-1] == self.S1Index]
                    if all(rules1):
                        for arc2 in self.arcs[counter+1:]:
                            # look for a passing plus neighboring to fuse
                            rules2 = [arc1[-1] == arc2[0],
                                      arc2[-1] == self.S1Index,
                                      self.notes[arc1[0]].csd.value > self.notes[arc1[-1]].csd.value,
                                      self.notes[arc2[0]].csd.value == self.notes[arc2[-1]].csd.value]
                            if all(rules2):
                                self.arcEmbed(arc1, arc2)
                                self.arcBasic = arc1

            # METHOD 3: if S2 = sd5
            # look for two arcs that can be merged into a basic step motion: passing + passing
            elif self.method == 3:
                for counter, arc1 in enumerate(self.arcs):
                    rules1 = [arc1[0] == self.S2Index,
                              self.notes[arc1[0]].csd.value == 4,
                              not arc1[-1] == self.S1Index]
                    if all(rules1):
                        # look rightward for another arc from same degree
                        for arc2 in self.arcs[counter+1:]:
                            # look for two passing motions to merge
                            # TODO write rules to handle cases where
                            # there are several possibilities
                            rules2a = [arc1[-1] == arc2[0],
                                       arc2[-1] == self.S1Index,
                                       self.notes[arc1[0]].csd.value > self.notes[arc1[-1]].csd.value,
                                       self.notes[arc2[0]].csd.value > self.notes[arc2[-1]].csd.value]
                            rules2b = [arc1[-1] < arc2[0],
                                       arc2[-1] == self.S1Index,
                                       self.notes[arc1[0]].csd.value > self.notes[arc1[-1]].csd.value,
                                       self.notes[arc2[0]].csd.value > self.notes[arc2[-1]].csd.value,
                                       not isEmbeddedInOtherArc(arc2, self.arcs, startIndex=arc1[-1])]
                            if all(rules2a) or all(rules2b):
                                self.arcMerge(arc1, arc2)
                                self.arcBasic = arc1

            # METHOD 4: if S2 = sd8
            # look for three arcs that can be merged into a basic step motion:
            # passing + passing + passing
            elif self.method == 4:
                arcSegments = []
                for counter1, arc1 in enumerate(self.arcs):
                    rules1 = [arc1[0] == self.S2Index,
                              self.notes[arc1[0]].csd.value == 7,
                              not arc1[-1] == self.S1Index]
                    if all(rules1):
                        arcSegments.append(arc1)
                        # look rightward for another arc from same degree that is also nonfinal
                        for counter2, arc2 in enumerate(self.arcs[counter1+1:]):
                            # look for two passing motions to merge
                            # TODO write rules to handle cases where there are several possibilities
                            rules2a = [arc1[-1] == arc2[0],
                                       arc2[-1] != self.S1Index,
                                       self.notes[arc1[0]].csd.value > self.notes[arc1[-1]].csd.value,
                                       self.notes[arc2[0]].csd.value > self.notes[arc2[-1]].csd.value,
                                       self.notes[arc2[-1]].csd.value > self.notes[-1].csd.value]
                            rules2b = [arc1[-1] < arc2[0],
                                       arc2[-1] != self.S1Index,
                                       self.notes[arc1[0]].csd.value > self.notes[arc1[-1]].csd.value,
                                       self.notes[arc2[0]].csd.value > self.notes[arc2[-1]].csd.value,
                                       self.notes[arc2[-1]].csd.value > self.notes[-1].csd.value,
                                       not isEmbeddedInOtherArc(arc2, self.arcs, startIndex=arc1[-1])]
                            if all(rules2a) or all(rules2b):
                                arcSegments.append(arc2)
                                for arc3 in self.arcs[counter2+1:]:
                                    # look for two passing motions to merge
                                    # TODO write rules to handle cases
                                    # where there are several possibilities
                                    rules3a = [arc2[-1] == arc3[0],
                                               arc3[-1] == self.S1Index,
                                               self.notes[arc2[0]].csd.value > self.notes[arc2[-1]].csd.value,
                                               self.notes[arc3[0]].csd.value > self.notes[arc3[-1]].csd.value]
                                    rules3b = [arc2[-1] < arc3[0],
                                               arc3[-1] == self.S1Index,
                                               self.notes[arc2[0]].csd.value > self.notes[arc2[-1]].csd.value,
                                               self.notes[arc3[0]].csd.value > self.notes[arc3[-1]].csd.value,
                                               not isEmbeddedInOtherArc(arc3, self.arcs, startIndex=arc2[-1])]
                                    if all(rules3a) or all(rules3b):
                                        arcSegments.append(arc3)
                        if len(arcSegments) == 3:
                            arc1 = arcSegments[0]
                            arc2 = arcSegments[1]
                            arc3 = arcSegments[2]
                            self.arcMerge(arc1, arc2)
                            self.arcMerge(arc1, arc3)
                            self.arcBasic = arc1

            # METHOD 5
            # take an existing 5-4-3 arc (the longest spanned, if more than one)
            # and try to find a connection -2-1 to complete a basic arc
            elif self.method == 5 and self.S2Value == 4:
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
                selectedArcs = [arc for arc in fiveThreeArcs if arcLength(arc) == arcSpan]
                if not selectedArcs:
                    error = ('No composite step motion found from '
                             'this S2 candidate:', self.S2Value+1)
                    self.errors.append(error)
                    return
                selectedArc = selectedArcs[0]
                sd3Index = selectedArc[-1]
                self.buffer = [n for n in self.notes[sd3Index:]
                               if not n.tie or n.tie.type == 'start']
                # reverse the buffer and build basic step motion
                # from the end of the line
                self.buffer.reverse()
                n = len(self.buffer)
                # create an arc in reverse
                basicArcCand = []
                basicArcNodeCand = None
                # append S1 to basic arc
                basicArcCand.append(self.S1Index)
                while n > 1:
                    shiftBuffer(self.stack, self.buffer)
                    n = len(self.buffer)
                    i = self.stack[-1]
                    j = self.buffer[0]
                    h = self.notes[basicArcCand[-1]]
                    # look for descending step to S1
                    if isStepDown(j, h) and j.csd.value < self.S2Value:
                        # skip the pitch if it is a local repetition
                        # (prefer the lefthead)
                        if not isLocalRepetition(j.index, self.notes, self.arcs):
                            basicArcCand.append(j.index)
                            break
                # check for success
                if len(basicArcCand) != 2:
                    error = 'No composite step motion found from this S2 candidate:', self.S2Value+1
                    self.errors.append(error)
                    return
                else:
                    self.arcs.remove(selectedArc)
                    for x in basicArcCand:
                        selectedArc.append(x)
                    self.arcBasic = sorted(selectedArc)

            # METHOD 6
            # look for a nonfinal arc from S2 whose terminus == S1.csd.value
            # extend the arc to end on S1Index if possible
            elif self.method == 6:
                for arc in self.arcs:
                    a = self.notes[arc[0]]  # the arc's leftmost Note
                    b = self.notes[arc[-1]]  # the arc's rightmost Note
                    rules = [a.index == self.S2Index,
                             b.csd.value == self.notes[self.S1Index].csd.value,
                             isEmbeddedInOtherArc(arc, self.arcs, startIndex=arc[-1]) is False]
                    if all(rules):
                        clearDependencies(b)
                        arc[-1] = self.S1Index
                        self.arcBasic = arc

            # METHOD 7
            # if S2Value == 2, look for a nonfinal lower neighbor arc
            # that could be transformed into a passing  to S1
            # extend the arc to end on S1Index if possible
            elif self.method == 7:
                for arc in self.arcs:
                    a = self.notes[arc[0]]  # the arc's leftmost Note
                    b = self.notes[arc[-1]]  # the arc's rightmost Note
                    t = self.notes[arc[1]]  # the arc's rightmost Note
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

            # METHOD 8
            # reinterpret the line
            # TODO this does not work well and shouldn't really ignore all the preparse work
            # see 2020_05_19T16_58_53_914Z.musicxml
            # see Westergaard070g.musicxml
            # TODO prefer S2 on beat in third species, if there are two candidates in the same bar
            elif self.method == 8:
                # refill buffer with context from S2 to end of line
                self.buffer = [n for n in self.notes[self.S2Index:] if not n.tie or n.tie.type == 'start']
                # reverse the buffer and build basic step motion from the end of the line
                self.buffer.reverse()
                n = len(self.buffer)
                # create an arc in reverse
                basicArcCand = []
                basicArcNodeCand = None
                # append S1 to basic arc
                basicArcCand.append(self.S1Index)
                while n > 1:
                    shiftBuffer(self.stack, self.buffer)
                    n = len(self.buffer)
                    i = self.stack[-1]
                    j = self.buffer[0]
                    h = self.notes[basicArcCand[-1]]
                    # look for descending steps to S1
                    if isStepDown(j, h) and j.csd.value < self.S2Value:
                        # skip the pitch if it is a local repetition (prefer the lefthead)
                        if not isLocalRepetition(j.index, self.notes, self.arcs):
                            basicArcCand.append(j.index)
                    elif isStepDown(j, h) and j.csd.value == self.S2Value:
                        # skip the pitch if it is a local repetition (prefer the lefthead)
                        if not isLocalRepetition(j.index, self.notes, self.arcs):
                            basicArcCand.append(self.S2Index)
                            break
                # the following procedure prefers to locate tonic triad S3 nodes
                # earlier rather than later
                # may have to be overriden when harmonizing counterpoint with bass line
                if self.S2Value > 2:  # this only applies to Urlinien from 5 or 8
                    # refill the buffer from S2 to end of line
                    self.buffer = [n for n in self.notes[self.S2Index:]
                                   if not n.tie or n.tie.type == 'start']
                    # reverse the buffer and look for tonic triad nodes
                    self.buffer.reverse()
                    n = len(self.buffer)
                    while n > 1:
                        shiftBuffer(self.stack, self.buffer)
                        n = len(self.buffer)
                        i = self.stack[-1]
                        j = self.buffer[0]
                        if isTriadMember(j, stufe=0) and j.index in basicArcCand:
                            # get the index of the preceding element in the basic step motion
                            x = basicArcCand.index(j.index) - 1
                            prevS = basicArcCand[x]
                            for arc in self.arcs:
                                a = self.notes[arc[0]]
                                b = self.notes[arc[-1]]
                                if prevS < a.index < j.index and prevS < b.index < j.index:
                                    # grab the a head if possible
                                    if a.csd.value == j.csd.value:
                                        j.dependency.lefthead = a.index
                                        arcGenerateRepetition(j.index, notes, arcs, stack)
                                        j.rule.name = 'E1'
                                        self.arcEmbed(arc, [a.index, j.index])
                                        basicArcCand[prevS+1] = a.index
                                    # settle for the b head if possible
                                    elif b.csd.value == j.csd.value:
                                        j.dependency.lefthead = b.index
                                        arcGenerateRepetition(j.index, notes, arcs, stack)
                                        j.rule.name = 'E1'
                                        basicArcCand[x+1] = b.index
                # check to make sure the basic step motion is complete
                if len(basicArcCand) != (self.S2Value+1):
                    # TODO report specific Note/Pitch of failed S2 candidate
                    error = ('No basic step motion found from this S2 candidate:',
                             self.S2Value+1)
                    self.errors.append(error)
                    return
                else:
                    self.arcBasic = list(reversed(basicArcCand))

            if self.arcBasic is None:
                error = ('No basic step motion found from this S2 candidate:',
                         self.S2Value+1)
                self.errors.append(error)
                return
            # if a basic arc is created, set the rule labels for S3 notes
            else:
                for n in self.arcBasic[1:-1]:
                    self.notes[n].rule.name = 'S3'
            S3Indexes = [note.index for note in self.notes
                         if note.rule.name == 'S3']
            self.S3Initial = min(S3Indexes)
            self.S3Final = max(S3Indexes)

            # if there are open heads before onset of S3 that have the
            # same pitch as S2, attach them as repetitions of S2
            self.attachOpenheadsToStructuralLefthead(self.S2Index, self.S3Initial)

            # TODO and explain why it is necessary to look for crossed arcs here
            # ... because this method of inferring basic arc can contradict
            # arcs in the preliminary arc list
            if self.arcBasic is None:
                pass
            else:
                # remove arcs that cross S2-S3, S3-S3 boundaries
                self.arcs.sort()
                ints = pairwise(self.arcBasic)
                purgeList = []
                # find offending arcs
                for int in ints:
                    a = int[0]
                    b = int[1]
                    for arc in self.arcs:
                        if a <= arc[0] < b and arc[-1] > b and arc != self.arcBasic:
                            purgeList.append(arc)
                for arc in purgeList:
                    removeDependenciesFromArc(self.notes, arc)
                    self.arcs.remove(arc)
                # add basic step motion arc
                self.arcs.append(self.arcBasic)
                addDependenciesFromArc(self.notes, self.arcBasic)

                # TODO: reset Note attributes
                # look for secondary structures between Snodes
                # TODO: try to attach repetitions of S3 sd5 or sd3

        def parseBass(self):
            '''Tests whether a specific dominant pitch can function as S3.'''
            # once all preliminary parsing is done,
            # prepare for assigning basic structure
            self.arcs.sort()  # = sorted(self.arcList)
            self.arcBasic = [0, self.S3Index, self.S1Index]
            # see whether any open heads can be attached as repetitions of S2 or S3
            self.attachOpenheadsToStructuralLefthead(0, self.S3Index)
            self.attachOpenheadsToStructuralLefthead(self.S3Index, self.S1Index)

            # TODO figure out and explain why it is necessary
            # to look for crossed arcs here
            self.arcs.sort()  # = sorted(self.arcList)
            if self.arcBasic is None:
                pass
            else:
                # remove arcs that cross S2-S3, S3-S3 boundaries
                # TODO is this necessary for bass lines?
                self.arcs.sort()
                ints = pairwise(self.arcBasic)
                purgeList = []
                # find offending arcs
                for int in ints:
                    a = int[0]
                    b = int[1]
                    for arc in self.arcs:
                        if a <= arc[0] < b and arc[-1] > b and arc != self.arcBasic:
                            purgeList.append(arc)
                for arc in purgeList:
                    removeDependenciesFromArc(self.notes, arc)
                    self.arcs.remove(arc)
                # add basic step motion arc
                self.arcs.append(self.arcBasic)
                addDependenciesFromArc(self.notes, self.arcBasic)
                # TODO: reset Note attributes

                # TODO remove anticipations of S3
                for arc in self.arcs:
                    rules = [len(arc) == 2,
                             arc[1] == self.S3Index]
                    if all(rules):
                        removeDependenciesFromArc(self.notes, arc)
                        self.arcs.remove(arc)

        def parseGeneric(self):
            '''The line has already passed the generic test, so all that is to
            be done is determine whether there is a basic step motion connecting
            the first and last notes.'''
            # once preliminary parsing is done, prepare for assigning basic structure
            # see whether a basic step motion is absent, ascending, or descending
            self.arcs.sort()  # = sorted(self.arcList)
            self.arcBasic = None
            basicArcDirection = None
            if self.notes[0].csd.value == self.notes[-1].csd.value:
                self.arcBasic = [self.S2Index, self.S1Index]
            elif self.notes[0].csd.value > self.notes[-1].csd.value:
                basicArcDirection = 'descending'
            elif self.notes[0].csd.value < self.notes[-1].csd.value:
                basicArcDirection = 'ascending'
            # if so, find a basic step motion, and
            # if not there, reinterpret the arcs between start and end of tune
            for counter, arc1 in enumerate(self.arcs):
                a = self.notes[arc1[0]]  # the arc's leftmost Note
                b = self.notes[arc1[-1]]  # the arc's rightmost Note
                # look for one existing basic step motion arc that starts from S2
                if arc1[0] == self.S2Index and arc1[-1] == self.S1Index:
                    for elem in arc1[1:-1]:
                        self.notes[elem].rule.name = 'S3'
                    self.arcBasic = arc1
                    break
                # look for an existing basic step motion arc that can be attached to S2
                elif a.csd.value == self.S2Value and b.index == self.S1Index:
                    arc1[0] = self.S2Index
                    a.dependency.lefthead = self.S2Index
                    arcGenerateRepetition(a.index, self.notes, self.arcs, self.stack)
                    a.rule.name = 'E1'
                    for n in arc1[1:-1]:
                        self.notes[n].dependency.lefthead = self.S2Index
                        self.notes[self.S2Index].dependency.dependents.append(n)
                        self.notes[n].rule.name = 'S3'
                        self.arcBasic = arc1
                        break
                    break
                # look for two arcs that can be embedded or merged into a basic step motion
                elif arc1[0] == self.S2Index and not arc1[-1] == self.S1Index:
                    # first look rightward for another arc from same degree
                    for arc2 in self.arcs[counter+1:]:
                        rules1 = [arc1[-1] == arc2[0],
                                  arc2[-1] == self.S1Index]
                        rules2 = [self.notes[arc1[0]].csd.value > self.notes[arc1[-1]].csd.value,
                                  self.notes[arc2[0]].csd.value > self.notes[arc2[-1]].csd.value]
                        rules3 = [self.notes[arc1[0]].csd.value < self.notes[arc1[-1]].csd.value,
                                  self.notes[arc2[0]].csd.value < self.notes[arc2[-1]].csd.value]
                        if all(rules1) and (all(rules2) or all(rules3)):
                            self.arcMerge(arc1, arc2)
                            for elem in arc1[1:-1]:
                                self.notes[elem].rule.name = 'S3'
                            self.arcBasic = arc1
                            break
                        # merge
                        elif (self.arcBasic and  # prefinal neighbor
                              self.notes[arc2[0] == self.notes[self.S1Index].csd.value]):
                            self.arcBasic.pop()
                            self.arcBasic.append(arc2[-1])
                        rules4 = [self.notes[arc1[-1]].csd.value ==
                                  self.notes[arc2[0]].csd.value]
                        if all(rules4) and (all(rules2) or all(rules3)):
                            # TODO: finish this
                            pass
                            # attach arc2 to arc1 and then merge
                            # this may not be needed if earlier
                            # parsing picks up the repetition
            # attach repetitions of S2 before onset of S1
            # TODO refine generic basic arc and coherence
            self.attachOpenheadsToStructuralLefthead(self.S2Index, self.S1Index)
            # if all else fails, just use first and last notes as the basic arc
            if self.arcBasic is None:
                self.arcBasic = [self.S2Index, self.S1Index]

        def attachOpenheadsToStructuralLefthead(self, structuralLefthead, rightLimit):
            '''Examines the span between a structural lefthead and a righthand limit,
            looking for notes that are either head of an arc (left or right)
            or not embedded in an arc,
            and can be taken as a repetition of the structural lefthead.
            This function increases the coherence of a parse.'''
            # structuralLefthead = index, rightLimit = index
            self.buffer = [n for n in self.stackremnant
                           if structuralLefthead < n.index < rightLimit]
            self.stack = []
            n = len(self.buffer)
            while n > 0:
                shiftBuffer(self.stack, self.buffer)
                n = len(self.buffer)
                i = self.stack[-1]
                # rules 1: the scale degrees match
                rules1 = [i.csd.value == self.notes[structuralLefthead].csd.value]
                # rules 2: and either it's an arc terminal not already marked as E1
                rules2 = [isArcTerminal(i.index, self.arcs),
                          i.rule.name != 'E1']
                # rules 3: or it's an independent note
                rules3 = [not isEmbeddedInArcs(i.index, self.arcs),
                          self.notes[i.index].dependency.lefthead is None,
                          self.notes[i.index].dependency.righthead is None]
                # rules 4: and it's not already in an arc initiated
                # by the structural lefthead
                rules4 = [not areArcTerminals(structuralLefthead, i.index, self.arcs)]
                if all(rules1) and (all(rules2) or all(rules3)) and all(rules4):
                    self.notes[i.index].dependency.lefthead = structuralLefthead
                    self.notes[0].dependency.dependents.append(i.index)
                    self.notes[i.index].rule.name = 'E1'
                    arcGenerateRepetition(i.index, self.notes, self.arcs, self.stack)
                # TODO consider working on this
                    if all(rules2):
                        # may also want to transfer dependent neighbors to the newly created
                        # repetition arcs
                        pass

        def integrateSecondaryWithPrimary(self):
            '''Revises an intepretation to make it tighter, more efficient,
            more coherent. Connect secondary structures to elements of the
            basic structure where possible.'''
            # TODO Implement Westergaard preferences for coherent interpretations, pp. 63ff.
            pass

        def assignSecondaryRules(self):
            # find any note that does not yet have a rule assigned and is not tied over
            for i in self.notes:
                if (i.rule.name is None and
                   ((i.tie and i.tie.type == 'start') or not i.tie)):
                    # CASE ONE: look for passing and neighboring arcs
                    if (i.dependency.lefthead is not None and
                       i.dependency.righthead is not None):
                        # for neighboring arcs, determine whether
                        # the heads are tonic-triad pitches or not
                        if (self.notes[i.dependency.lefthead].csd.value ==
                           self.notes[i.dependency.righthead].csd.value):
                            if isTriadMember(self.notes[i.dependency.righthead], 0):
                                i.rule.name = 'E2'
                                if self.notes[i.dependency.righthead].rule.name is None:
                                    self.notes[i.dependency.righthead].rule.name = 'E1'
                            else:
                                i.rule.name = 'L2'
                                if self.notes[i.dependency.righthead].rule.name is None:
                                    self.notes[i.dependency.righthead].rule.name = 'L1'
                        # for passing arcs
                        else:
                            i.rule.name = 'E4'
                            if (self.notes[i.dependency.righthead].rule.name is None and
                               isTriadMember(self.notes[i.dependency.righthead], 0)):
                                self.notes[i.dependency.righthead].rule.name = 'E3'
#                            elif self.notes[i.dependency.righthead].rule.name == None and
#                                  not isTriadMember(self.notes[i.dependency.righthead], 0):
#                                self.notes[i.dependency.righthead].rule.name = 'LL3'

                    # CASE TWO: repetitions
                    elif (i.dependency.lefthead is not None and
                          i.dependency.righthead is None):
                        if self.notes[i.dependency.lefthead].csd.value == i.csd.value:
                            if isTriadMember(i, 0):
                                i.rule.name = 'E1'
                            else:
                                i.rule.name = 'L1'

                    # CASE UNKNOWN:
                    elif i.dependency.lefthead != i.dependency.righthead:
                        # what's the function of this section??
                        # This may not function correctly in every case
                        i.rule.name = 'Ex'

                    # CASE THREE: independent notes, global and local
                    if i.dependency.lefthead is None and i.dependency.righthead is None:
                        if isTriadMember(i, 0):
                            i.rule.name = 'E3'
                            i.noteheadParenthesis = True
                        elif (not isTriadMember(i, 0) and
                              self.species in ['third', 'fifth']):
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
                              self.species in ['third', 'fifth']):
                            i.rule.name = 'L3'
                            i.noteheadParenthesis = True
                        else:
                            error = ('The pitch ' + i.nameWithOctave + 'in measure '
                                     + str(i.measureNumber) + 'is not generable.')
                            self.errors.append(error)

                if i.rule.name == 'E3' and i.dependency.dependents == []:
                    i.noteheadParenthesis = True
                # TODO figure out why some notes still don't have rules
                elif i.rule.name is None and i.tie:
                    if i.tie.type != 'stop':
                        i.rule.name = 'X'
                elif i.rule.name is None:
                    i.rule.name = 'x'

        def testLocalResolutions(self):
            for i in self.notes:
                if i.rule.name == 'L3':
                    remainder = [n for n in self.notes if n.index > i.index]
                    resolved = False
                    for r in remainder:
                        # TODO test for directionality
                        if isDirectedStep(i, r):
                            resolved = True
                            break
                    if not resolved:
                        error = ('The local insertion ' + i.nameWithOctave +
                                 'in measure ' + str(i.measureNumber) +
                                 'is not resolved.')
                        self.errors.append(error)

        def pruneArcs(self):
            pass
            # find arcs to merge into longer passing motions
            for arc1 in self.arcs:
                for arc2 in self.arcs:
                    rules1 = [arc1[-1] == arc2[0],
                              self.notes[arc1[-1]].rule.name[0] != 'S']
                    # TODO consider changing the conditions
                    # to isPassing and in same direction
                    rules2 = [self.notes[arc1[0]].csd.value > self.notes[arc1[-1]].csd.value,
                              self.notes[arc2[0]].csd.value > self.notes[arc2[-1]].csd.value]
                    rules3 = [self.notes[arc1[0]].csd.value < self.notes[arc1[-1]].csd.value,
                              self.notes[arc2[0]].csd.value < self.notes[arc2[-1]].csd.value]
                    if all(rules1) and (all(rules2) or all(rules3)):
                        mergePairOption = (arc1, arc2)
                        # make sure that neither arc is embedded in another arc
                        for arc in self.arcs:
                            arc1Embedded = False  # assume that it is independent
                            arc2Embedded = False  # assume that it is independent
                            if (mergePairOption[0][-1] == arc[-1] and
                               arc[0] < mergePairOption[0][0]):
                                arc1Embedded = True
                                break
                            if (mergePairOption[1][0] == arc[0] and
                               arc[-1] > mergePairOption[1][-1]):
                                arc2Embedded = True
                                break
                        # if neither is embedded, merge the two
                        if not arc1Embedded and not arc2Embedded:
                            self.arcMerge(mergePairOption[0],
                                          mergePairOption[1])
                            # TODO is it necessary to set the rules here,
                            # what about the removed node?
                            # should it also be set to 'E4'?
                            for elem in mergePairOption[0][1:-1]:
                                self.notes[elem].rule.name = 'E4'

        def gatherRuleLabels(self):
            self.ruleLabels = []
            for elem in self.notes:
                self.ruleLabels.append((elem.index, elem.rule.name))
            return

        def gatherParentheses(self):
            self.parentheses = []
            for elem in self.notes:
                if elem.noteheadParenthesis:
                    self.parentheses.append((elem.index, True))
                else:
                    self.parentheses.append((elem.index, False))
            return

        def setDependencyLevels(self):
            '''Reviews a completed parse and determine the
            structural level of each note.'''
            # this works for now, but is not optimal
            # does not work for this line: BL in major:
            # 1 5 4 3 1 -7 -5 1 6 5 4 3 2 1
            # arcs = [[0, 1, 13], [1, 2, 3], [1, 8, 9],
            # [1, 10, 11, 12, 13], [4, 5, 7]]
            # there needs to be a more robust way of evaluating insertions,
            # not just left-to-right
            # also may not work for complicated, poorly interpreted
            # third species lines

            # assign levels to notes in the basic arc
            for n in self.notes:
                if n.rule.name == 'S1':
                    n.rule.level = 0
                if n.rule.name == 'S2':
                    n.rule.level = 1
                if n.rule.name == 'S3':
                    n.rule.level = 2
            # set level of first note if not in basic arc
            if self.arcBasic[0] != 0:
                self.notes[0].rule.level = 3

            # collect all the secondary arcs
            dependentArcs = [arc for arc in self.arcs if arc != self.arcBasic]

            # a span is defined by two notes: initial and final
            # the rootSpan extends from the first to the last note of a line
            # TODO consider using some kind of root node pair:
            # leftRoot, rightRoot, or just None
            rootSpan = (self.notes[0].index, self.notes[-1].index)

            # the length of a span = final.index - initial-index
            # the span between consecutive notes is 1
            # so only spans of length > 1 are fillable
            def length(span):
                length = span[-1] - span[0]
                return length

            # given an arc, divide it into fillable segments (length > 1)
            def addSpansFromArc(arc, spans):
                segments = pairwise(arc)
                for segment in segments:
                    if length(segment) > 1:
                        spans.append(segment)

            # create a list to hold all the fillable spans
            spans = []

            # add spans before and after basic arc, if they exist
            # (outer edges will not have been generated yet)
            if self.arcBasic[0] != rootSpan[0]:
                span = (0, self.arcBasic[0])
                if length(span) > 1:
                    spans.append(span)
            if self.arcBasic[-1] != rootSpan[-1]:
                span = (self.arcBasic[-1], rootSpan[1])
                if length(span) > 1:
                    spans.append(span)

            # add any spans in the basic arc
            addSpansFromArc(self.arcBasic, spans)

            # for testing whether an insertion conforms
            # to the intervallic constraints
            def isPermissibleConsonance(x, y, z):
                # checks the insertion of y between x and z indexes
                left = self.notes[x]
                right = self.notes[z]
                insertion = self.notes[y]
                rules = [(isLinearConsonance(left, insertion) or
                          isLinearUnison(left, insertion) or
                          isDiatonicStep(left, insertion)),
                         (isLinearConsonance(insertion, right) or
                          isLinearUnison(insertion, right) or
                          isDiatonicStep(insertion, right))]
                if all(rules):
                    return True
                else:
                    return False

            # look at every span in the list,
            # and see whether a dependent arc fits into it
            # this is the core of the function
            def processSpan(span, spans, dependentArcs):
                # the rule levels inside the span are determined
                # by the rule levels of the left and right edges
                leftEdge = span[0]
                rightEdge = span[1]
                leftEdgeLevel = self.notes[span[0]].rule.level
                rightEdgeLevel = self.notes[span[1]].rule.level

                # infer next level from span edges
                if leftEdgeLevel and rightEdgeLevel:
                    nextLevel = max(leftEdgeLevel, rightEdgeLevel) + 1
                elif leftEdgeLevel and not rightEdgeLevel:
                    nextLevel = leftEdgeLevel + 1
                elif not leftEdgeLevel and rightEdgeLevel:
                    nextLevel = rightEdgeLevel + 1

                # (1) search for possible branches across or within the span
                # a dependent arc can fit into a span in one of four ways:
                #     (1) crossBranches connect leftEdge to rightEdge
                #     (2) leftBranches connect onto the rightEdge
                #         (branch to the left)
                #     (3) rightBranches connect onto the leftEdge
                #         (branch to the right)
                #     (4) interBranches do not connect to either edge
                # find the best and longest arc available in a span
                #     preferences between categories:
                #          cross > right > left > inter
                #     preferences within category:
                #          longer > shorter
                crossBranch = None
                leftBranch = None
                rightBranch = None
                interBranch = None
                # first look for cross branch connection across span
                for arc in dependentArcs:
                    if arc[0] == leftEdge and arc[-1] == rightEdge:
                        crossBranch = arc
                # otherwise look for right or left branches to generated edges
                for arc in dependentArcs:
                    # look for right branches if the left edge has been generated
                    if leftEdgeLevel and not crossBranch:
                        # look for a right branch
                        if arc[0] == leftEdge and rightBranch is None:
                            if isPermissibleConsonance(leftEdge, arc[-1], rightEdge):
                                rightBranch = arc
                        # look to see if there's a longer branch available
                        if arc[0] == leftEdge and rightBranch:
                            if length(arc) > length(rightBranch):
                                if isPermissibleConsonance(leftEdge, arc[-1], rightEdge):
                                    rightBranch = arc
                # look for left branches if the right edge has been
                # generated and there is no right branch
                for arc in dependentArcs:
                    if rightEdgeLevel and not crossBranch and not rightBranch:
                        if arc[-1] == rightEdge and leftBranch is None:
                            if isPermissibleConsonance(leftEdge, arc[0], rightEdge):
                                leftBranch = arc
                            leftBranch = arc
                        # look to see if there's a longer branch available
                        if arc[-1] == rightEdge and leftBranch:
                            if length(arc) > length(leftBranch):
                                if isPermissibleConsonance(leftEdge, arc[0], rightEdge):
                                    leftBranch = arc
                # look for inter branch if no cross branches
                # or left or right branches
                for arc in dependentArcs:
                    if not rightBranch and not leftBranch and not crossBranch:
                        for arc in dependentArcs:
                            if (arc[0] > leftEdge and
                               arc[-1] < rightEdge and
                               interBranch is None):
                                interBranch = arc
                            # look to see if there's a longer branch available
                            if (arc[0] > leftEdge and
                               arc[-1] < rightEdge and
                               interBranch):
                                if length(arc) > length(interBranch):
                                    interBranch = arc

                # (2) process any branches that have been found in the span
                #     (a) remove the branch from the list of dependent arcs
                #     (b) calculate rule levels for members of the branch
                # termini levels of cross branch are already set,
                # so just set level of inner elements
                if crossBranch:
                    dependentArcs.remove(crossBranch)
                    for i in crossBranch[1:-1]:
                        self.notes[i].rule.level = nextLevel
                # one terminus level is already set, so set level of the
                # other terminus and the inner elements
                elif rightBranch:
                    dependentArcs.remove(rightBranch)
                    self.notes[rightBranch[-1]].rule.level = nextLevel
                    for i in rightBranch[1:-1]:
                        self.notes[i].rule.level = nextLevel + 1
                elif leftBranch:
                    dependentArcs.remove(leftBranch)
                    self.notes[leftBranch[0]].rule.level = nextLevel
                    for i in leftBranch[1:-1]:
                        self.notes[i].rule.level = nextLevel + 1
                # no terminus level is already set, so set level of the left
                # terminus, then the right, and then the inner elements
                elif interBranch:
                    dependentArcs.remove(interBranch)
                    self.notes[interBranch[0]].rule.level = nextLevel
                    self.notes[interBranch[-1]].rule.level = nextLevel + 1
                    for i in interBranch[1:-1]:
                        self.notes[i].rule.level = nextLevel + 2

                # (3) revise the list of spans
                if crossBranch or rightBranch or leftBranch or interBranch:
                    spans.remove(span)
                if crossBranch:
                    addSpansFromArc(crossBranch, spans)
                if rightBranch:
                    addSpansFromArc(rightBranch, spans)
                    if rightEdge - rightBranch[-1] > 1:
                        spans.append((rightBranch[-1], rightEdge))
                if leftBranch:
                    if leftBranch[0] - leftEdge > 1:
                        spans.append((leftEdge, leftBranch[0]))
                    addSpansFromArc(leftBranch, spans)
                if interBranch:
                    if interBranch[0] - leftEdge > 1:
                        spans.append((leftEdge, interBranch[0]))
                    addSpansFromArc(interBranch, spans)
                    if rightEdge - interBranch[-1] > 1:
                        spans.append((interBranch[-1], rightEdge))

                # (4) process a span that contains only inserted
                # pitches no arcs
                # TODO this is a temporary solution,
                # need an algorithm that finds the best of
                #  the many possible solutions, not necessarily left to right
                #  e.g., look for repetitions of leftEdge
                if not(crossBranch or rightBranch or leftBranch or interBranch):
                    if isPermissibleConsonance(leftEdge, leftEdge+1, rightEdge):
                        self.notes[leftEdge+1].rule.level = nextLevel
                        spans.remove(span)
                        if rightEdge - (leftEdge+1) > 1:
                            spans.append((leftEdge+1, rightEdge))
                    elif (length(span) > 3 and
                          isPermissibleConsonance(leftEdge, leftEdge+1, leftEdge+2) and
                          isPermissibleConsonance(leftEdge, leftEdge+2, rightEdge)):
                        self.notes[leftEdge+2].rule.level = nextLevel
                        self.notes[leftEdge+1].rule.level = nextLevel + 1
                        spans.remove(span)
                        if rightEdge - (leftEdge+2) > 1:
                            spans.append((leftEdge+2, rightEdge))

            spancount = len(spans)
            while spancount > 0:
                for span in spans:
                    processSpan(span, spans, dependentArcs)
                    spancount = len(spans)

            generatedNotes = [(n.index, n.rule.name, n.rule.level)
                              for n in self.notes
                              if n.rule.level is not None]
            generationTable = [n.rule.level for n in self.notes]

        def displayFullParse(self):
            '''Creates a multileveled illustration of a parse of the sort
            used in Westergaard's book. [Under developement]'''
            # given a parsed part, with rule dependencies set
            illustration = stream.Score()
            notes = self.notes
            # determine the maximum number of levels in the parse
            levels = [n.rule.level for n in notes]
            if None in levels:
                print('Parse incomplete. Some notes not assigned to levels.')
                return
#                exit()
            maxLevel = max(levels)
            # create a part in the illustration for each level
            # and assign it a number
            n = maxLevel+1
            while n > 0:
                illustration.append(stream.Part())
                n += -1
            for num, part in enumerate(illustration.parts):
                # part number
                part.partNum = num
            # create a measure in each part of the illustration
            measures = len(notes)
            n = measures

            # function to add note to the correct levels
            def addNoteToIllustration(note, illustration):
                lev = note.rule.level
                meas = note.index+1
                for part in illustration.parts:
                    if lev == part.partNum:
                        part.insert(note.offset, note)
#                        part.measure(str(meas)).append(note)
# need to figure in the note offset
                    if lev < part.partNum:
                        part.insert(note.offset, note)
#                        part.measure(str(meas)).append(note)
# need to figure in the note offset
            # populate the illustration parts
            for n in notes:
                addNoteToIllustration(n, illustration)

            illustration.show()
            # exit after showing the first parse, for testing
            exit()

    def testGenerabilityFromLevels(parse):
        '''Given a parse in which rule levels have been assigned (perhaps by the student),
        determines whether the line is generable in that way. [Under development]'''
        if parse.lineType == 'bass':
            pass
        if parse.lineType == 'primary':
            pass
        if parse.lineType == 'generic':
            pass
        pass

    def collectParses(self):
        '''Collects all the attempted parses of a line
        in the :py:class:`~Parser`
        and discard any that have errors and thus failed.
        Also removes parses of primary lines if the same basic arc was
        produced by a more reliable method.'''
        failedParses = []
        for key in self.parseErrorsDict:
            if self.parseErrorsDict[key] != []:
                failedParses.append(key)

        # remove parses that have errors:
        self.parses = [parse for parse in self.parses
                       if self.parseErrorsDict[parse.label] == []]

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

        # remove parses in primary lines that have the same basic arc
        # as another parse because of creation order,
        # preference given to inference methods 0-4
        arcBasicCandidates = []
        prunedParseSet = []
        for prs in self.Pinterps:
            if prs.arcBasic not in arcBasicCandidates:
                arcBasicCandidates.append(prs.arcBasic)
                prunedParseSet.append(prs)
        self.Pinterps = prunedParseSet

        # set generability properties
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

    def selectPreferredParses(self):
        '''Given a list of successful interpretations from :py:class:`~Parser`,
        removes those that do not conform to cognitive preference rules.

        * Primary line preferences

           * for parses that share the same S2 scale degree, prefer the parse
             in which S2 occurs earliest

        * Bass Lines

           * prefer parses in which S3 occurs after the midpoint
           * prefer parses in which S3 occurs on the beat
           * if there are two candidates for S3 and the second can be interpreted
             as a direct repetition of the first, prefer the parse that interprets
             the first candidate as S3

        '''

        # primary upper lines
        # find those that have the same scale degree for S2
        threelines = [interp for interp in self.Pinterps
                      if interp.S2Degree == '3']
        fivelines = [interp for interp in self.Pinterps
                     if interp.S2Degree == '5']
        eightlines = [interp for interp in self.Pinterps
                      if interp.S2Degree == '8']
        # get the indexes of that degree
        threelineCands = [interp.arcBasic[0] for interp in threelines]
        fivelineCands = [interp.arcBasic[0] for interp in fivelines]
        eightlineCands = [interp.arcBasic[0] for interp in eightlines]
        # look for arcs that connect pairs of those indexes (as repetitions)
        ints = pairwise(fivelineCands)
        # create a list of interpretations that will be purged
        labelsToPurge = []

        # TODO Westergaard p. 112: prefer S notes onbeat (esp S2)
        # TODO implement Westergaard cognitive preferences,
        # sections 4.2, 4.4, and 5.3
        # get local offset of each S pitch:
        # prefer as many offset==0.0 as possible

        # just hang onto the earliest S2 candidates:
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
        # remove unpreferred interpretations from the set of interpretations
        self.Pinterps = [interp for interp in self.Pinterps
                         if interp.label not in labelsToPurge]

        # TODO are there options for the placement of S3?
        # if so, coordinate with a bass line
        # redefine Pinterps after purging
        # TODO find the positions of the end of S3 (sd2) in upper lines
        S3PenultCands = [interp.arcBasic[-2] for interp in self.Pinterps]

        # bass lines
        labelsToPurge = []
#        bassS3Degree = self.line.notes[interp.S3Index].csd.value
        lowfives = [interp for interp in self.Binterps
                    if self.notes[interp.S3Index].csd.value == -3]
        highfives = [interp for interp in self.Binterps
                     if self.notes[interp.S3Index].csd.value == 4]
        lowfiveCands = [interp.arcBasic[1] for interp in lowfives]
        highfiveCands = [interp.arcBasic[1] for interp in highfives]
        # choose an S3 that's integrated or immediately preceding
        # given two options, choose the later if there is a
        # potential repetition of S2 between them
        # can this be negotiated earlier in the parse?

        # currently there is no preference where S3 occurs in a bass line
        # TODO: eventually this must be replaced by a preference for
        # consonant coordination with an S3 in the upper line:
        # either simultaneous with or subsequent to sd2
        # TODO: using the reversed buffer is too radical,
        # since it would prefer the second note of a repetition as S3
        # What about removing a candidate if it has the same
        # sole dependent as an earlier candidate? NO

        # if there are several candidates for high or low five,
        # prefer ones in which S3 occurs past the midway point of the line
        linemidpoint = len(self.notes)/2
        if len(highfives) > 1:
            for interp in highfives:
                if interp.S3Index < linemidpoint:
                    labelsToPurge.append(interp.label)
        if len(lowfives) > 1:
            for interp in lowfives:
                if interp.S3Index < linemidpoint:
                    labelsToPurge.append(interp.label)
        self.Binterps = [interp for interp in self.Binterps
                         if interp.label not in labelsToPurge]

        # if there are still several candidates for S3,
        # prefer ones in which S3 occurs on the beat
        allfivesOnbeat = [five for five in self.Binterps
                          if self.notes[five.S3Index].beat == 1.0]
        if (len(self.Binterps) > len(allfivesOnbeat)
           and len(allfivesOnbeat) != 0):
            for interp in self.Binterps:
                if self.notes[interp.S3Index].beat != 1.0:
                    labelsToPurge.append(interp.label)
        self.Binterps = [interp for interp in self.Binterps
                         if interp.label not in labelsToPurge]

        # if there are two candidates for S3 and
        # one can be an immediate repetition, prefer that one
        preferredBassS3 = None
        labelsToPurge = []
        for interp in self.Binterps:
            for arc in interp.arcs:
                if arc == [interp.S3Index, interp.S3Index+1]:
                    preferredBassS3 = interp.S3Index
        if preferredBassS3 is not None:
            for interp in self.Binterps:
                if interp.S3Index == preferredBassS3+1:
                    labelsToPurge.append(interp.label)
        self.Binterps = [interp for interp in self.Binterps
                         if interp.label not in labelsToPurge]

        # update the list of parses and the dictionary of parses
        self.parses = self.Pinterps + self.Binterps + self.Ginterps
        self.interpretations['primary'] = self.Pinterps
        self.interpretations['bass'] = self.Binterps
        self.interpretations['generic'] = self.Ginterps

        return self

# -----------------------------------------------------------------------------
# UTILITY SCRIPTS
# -----------------------------------------------------------------------------


def shiftBuffer(stack, buffer):
    nextnote = buffer[0]
    buffer.pop(0)
    stack.append(nextnote)


def shiftStack(stack, buffer):
    lastnote = stack[-1]
    stack.pop(-1)
    buffer.insert(0, lastnote)


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
    # tests whether a set of notes makes a major, minor or diminished triad
    isTriadicSet = False
    pairs = itertools.combinations(pitchList, 2)
    for pair in pairs:
        int = interval.Interval(pair[0], pair[1]).simpleName
        rules = [int[-1] in ['2', '7'],
                 (int[-1] == '1' and int != 'P1'),
                 (int[-1] == '5' and int == 'A5'),
                 (int[-1] == '4' and int == 'd4')]
        if any(rules):
            isTriadicSet = False
            return isTriadicSet
        else:
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
    harmonicPitches = testHarm
    return isHarmonic


def isLinearConsonance(n1, n2):
    # input two notes with pitch
    lin_int = interval.Interval(n1, n2)
    if lin_int.name in {"m3", "M3", "P4", "P5", "m6", "M6", "P8"}:
        return True
    else:
        return False


def isSemiSimpleInterval(n1, n2):
    # input two notes with pitch
    lin_int = interval.Interval(n1, n2)
    if lin_int.semiSimpleNiceName == lin_int.niceName:
        return True
    else:
        return False


def isLinearUnison(n1, n2):
    # input two notes with pitch
    lin_int = interval.Interval(n1, n2)
    if lin_int.name in {'P1'}:
        return True
    else:
        return False


def isDiatonicStep(n1, n2):
    # input two notes with pitch
    lin_int = interval.Interval(n1, n2)
    if lin_int.name in {"m2", "M2"}:
        return True
    else:
        return False


def isStepUp(n1, n2):
    # input one note and the next
    if isDiatonicStep(n1, n2):
        if n2.csd.value > n1.csd.value:
            return True
        else:
            return False


def isStepDown(n1, n2):
    # input one note and the next
    if isDiatonicStep(n1, n2):
        if n2.csd.value < n1.csd.value:
            return True
        else:
            return False


def isDirectedStep(n1, n2):
    # input two notes with pitch
    rules1 = [n1.csd.direction in {'ascending', 'bidirectional'},
              isStepUp(n1, n2)]
    rules2 = [n1.csd.direction in {'descending', 'bidirectional'},
              isStepDown(n1, n2)]
    if all(rules1) or all(rules2):
        return True
    else:
        return False


def isNeighboring(arc, notes):
    if len(arc) != 3:
        return False
    # accepts an arcList of line indices and determines whether a valid N structure
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
        # could add conditions to add label modifier: upper, lower
        return True
    else:
        return False


def isPassing(arc, notes):
    # accepts an arcList of line indices and determines whether
    # a valid Pstructure can probably assume that
    # first and last pitches are in tonic triad, but
    span = len(arc)
    i = notes[arc[0]]
    k = notes[arc[-1]]
    if i.csd.value > k.csd.value:
        passdir = 'falling'
    if i.csd.value < k.csd.value:
        passdir = 'rising'
    else:
        return False
    ints = pairwise(arc)
    for int in ints:
        n1 = notes[int[0]]
        n2 = notes[int[1]]
        rules1 = [isDiatonicStep(n1, n2) is True]
        rules2 = [passdir == 'falling' and n1.csd.direction in ('bidirectional', 'descending'),
                  passdir == 'rising' and n1.csd.direction in ('bidirectional', 'ascending')]
        rules3 = [passdir == 'falling' and n1.csd.value > n2.csd.value,
                  passdir == 'rising' and n1.csd.value < n2.csd.value]
        if all(rules1) and any(rules2) and any(rules3):
            continue
        else:
            return False
    return True


def isRepetition(arc, notes):
    # accepts an arcList of line indices and determines
    # whether a valid R structure
    # can probably assume that first and last pitches
    # are in tonic triad, but
    i = notes[arc[0]]
    j = notes[arc[1]]
    rules1 = [j.csd.value == i.csd.value]
    if all(rules1):
        return True
    else:
        return False


def isLocalRepetition(noteIndex, notes, arcs):
    # check whether a note at noteIndex in notes
    # is a local repetition in an arc
    isLocalRepetition = False
    for arc in arcs:
        i = notes[arc[0]]
        j = notes[arc[-1]]
        rules1 = [noteIndex == j,
                  j.csd.value == i.csd.value,
                  i.measureNumber == j.measureNumber]
        if all(rules1):
            isLocalRepetition = True
            break
    return isLocalRepetition


def arcGenerateTransition(i, part, arcs, stack):
    # i is a note.index, the last transitional element before a righthead
    # assembles an arc after a righthead is detected
    # tests for arc type in self.line.notes
    # also assigns a label
    # after getting the elements, find the interval directions
    elements = []
    for elem in (part.flat.notes[i].dependency.lefthead,
                 i, part.flat.notes[i].dependency.righthead):
        elements.append(elem)
    for d in part.flat.notes[i].dependency.dependents:  # codependents
        if (d < i and
           part.flat.notes[d].dependency.lefthead ==
           part.flat.notes[i].dependency.lefthead):
            elements.append(d)
    thisArc = sorted(elements)
    arcs.append(thisArc)
    # remove dependents from the stack
    # see if it's a neighbor or passing
    if part.flat.notes[thisArc[-1]] == part.flat.notes[thisArc[0]]:
        arcType = 'neighbor'
    else:
        arcType = 'passing'
    arcPurge(thisArc, stack, arcType)


def arcGenerateRepetition(j, part, arcs, stack):
    # j is a note.index of the repetition
    # assembles an arc after a repetition is detected
    # tests for arc type in self.line.notes
    elements = [elem for elem in (part.flat.notes[j].dependency.lefthead, j)]
    thisArc = elements
    arcs.append(thisArc)
    # remove dependents from the stack
    arcType = 'repetition'
    arcPurge(thisArc, stack, arcType)


def arcExtendTransition(notes, arc, extensions):
    # extentions is a list of notes
    # extends an arc, usually into the next timespan
    # clean out the old arc
    removeDependenciesFromArc(notes, arc)
    # add the extensions and put in ascending order
    arc = sorted(arc + extensions)
    # reset the dependencies in the extended arc
    addDependenciesFromArc(notes, arc)


def arcPurge(arc, stack, arcType):
    # purge stack elements in arc that have
    # (a) lefthead and righthead or
    # (b) are a repetition
    # TODO figure out how to remove the righthand element
    # of a neighboring motion (because it's a repetition)
    if arcType == 'passing':
        for elem in arc[1:-1]:
            for pos, note in enumerate(stack):
                if note.index == elem:
                    stack.pop(pos)
    elif arcType == 'neighbor':
        for elem in arc[1:]:
            for pos, note in enumerate(stack):
                if note.index == elem:
                    stack.pop(pos)
    elif arcType == 'repetition':
        elem = arc[1]
        for pos, note in enumerate(stack):
            if note.index == elem:
                stack.pop(pos)


def pruneOpenHeads(notes, openheads):
    # Prune direct repetitions from end of the list of open head indices
    if len(openheads) > 1:
        latesthead = openheads[-1]
        predecessor = openheads[-2]
        if notes[latesthead] == notes[predecessor]:
            openheads.pop()
    return openheads


def clearDependencies(note):
    # reset a note's dependency attributes
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
        # TODO also set codependents
        arcLen = len(arc[1:-1])


def isArcTerminal(i, arcs):
    # checks to see whether a note at index i
    # is the terminal of any nonbasic arc
    isTerminal = False
    for arc in arcs:
        if i == arc[0] or i == arc[-1]:
            isTerminal = True
    return isTerminal


def isEmbeddedInArcs(i, arcs):
    # checks to see whether a note at index i
    # is embedded within any nonbasic arc
    isEmbedded = False
    for arc in arcs:
        if arc[0] < i < arc[-1]:
            isEmbedded = True
    return isEmbedded


def isEmbeddedInArc(i, arc):
    # checks to see whether a note at index i
    # is embedded within an arc
    isEmbedded = False
    if arc[0] < i < arc[-1]:
        isEmbedded = True
    return isEmbedded


def isEmbeddedInOtherArc(arc, arcs, startIndex=0, stopIndex=-1):
    # checks to see whether an arc is embedded within
    # another arc between two indices
    isEmbedded = False
    testArcs = []
    for testArc in arcs:
        if testArc[0] >= startIndex and testArc[-1] <= stopIndex and testArc != arc:
            testArcs.append(testArc)
    for testArc in testArcs:
        if arc[0] >= testArc[0] and arc[-1] <= testArc[-1]:
            isEmbedded = True
    return isEmbedded


def isIndependent(note):
    rules = [note.dependency.dependents == [],
             note.dependency.lefthead is None,
             note.dependency.righthead is None]
    if all(rules):
        return True
    else:
        return False


def areArcTerminals(h, i, arcs):
    # checks to see whether a head at index h and a note at index i
    # are the terminals of any nonbasic arc
    areTerminals = False
    for arc in arcs:
        if h == arc[0] and i == arc[-1]:
            areTerminals = True
    return areTerminals


def arcLength(arc):
    # returns the length of an arc measured as number of consecutions spanned
    length = arc[-1] - arc[0]
    return length

# -----------------------------------------------------------------------------


if __name__ == "__main__":
    pass
# -----------------------------------------------------------------------------
# eof
