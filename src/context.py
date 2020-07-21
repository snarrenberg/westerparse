# -----------------------------------------------------------------------------
# Name:         context.py
# Purpose:      Framework for analyzing species counterpoint
#
# Author:       Robert Snarrenberg
# Copyright:    (c) 2020 by Robert Snarrenberg
# License:      BSD, see license.txt
# -----------------------------------------------------------------------------
"""
Context
=======

The Context module includes classes to represent both global
and local contexts.
"""

from music21 import *
import itertools

import vlChecker
import parser
import keyFinder
import csd
import rule
import dependency
import consecutions
from utilities import pairwise

# -----------------------------------------------------------------------------
# EXCEPTION HANDLERS
# -----------------------------------------------------------------------------

logfile = 'logfile.txt'


def clearLogfile(logfile):
    file = open(logfile, 'w+')
#    file.truncate(0)
    file.close()


def printLogfile(logfile):
    with open(logfile) as file:
        print(file.read())


class ContextError(Exception):
    def __init__(self, desc):
        self.desc = desc
        self.logfile = logfile

    def logerror(self):
        log = open(self.logfile, 'a')
        print(self.desc, file=log)


class EvaluationException(Exception):
    def __init__(self):
        self.logfile = logfile

    def show(self):
        printLogfile(self.logfile)

# TODO: Figure out how to accommodate tonal ambiguity:
# Make a global context for each option?

# -----------------------------------------------------------------------------
# MAIN CLASSES
# -----------------------------------------------------------------------------


class Context():
    """An object for representing a span of a composition
    and for storing objects that represent smaller spans.
    """

    def __init__(self, music21Stream):
        self.scale
        self.triad
        self.harmonyStart = None
        self.harmonyEnd = None
        self.offset = None
        # dictionaries, by part, of parse-related data
        self.openHeads = {}
        self.openTransitions = {}
        self.arcs = {}


class LocalContext(Context):

    def __init__(self):
        self.score = None
        self.harmonyStart = None
        self.harmonyEnd = None
        self.offset = None
        # dictionaries, by part, of parse-related data
        self.openHeads = {}
        self.openTransitions = {}
        self.arcs = {}
        pass

    def __repr__(self):
        return str('Local context starting at ' + str(self.offset))


class GlobalContext(Context):
    """An object for representing a tonally unified span of a composition
    and for storing objects that represent local spans
    within the global context.

    A global context consists of a music21 Score and its constituent Parts.

    When a global context is created, several things happen automatically
    to prepare the score for evaluation.

    #. A key for the context is automatically validated or inferred
       using the Key Finder (:py:mod:`~keyFinder`).
    #. For each part:

       * A part number is assigned.
       * The rhythmic species is identified.
       * A referential tonic scale degree (csd.value = 0) is selected.
       * A list is created to collect errors.

    #. For each note in the part:

       * A position index is assigned. The is the primary note
         reference used during parsing.
       * A concrete scale degree (:py:class:`~csd.ConcreteScaleDegree`)
         is determined.
       * A :py:class:`~rule.Rule` object is attached.
       * A :py:class:`~dependency.Dependency` object is attached.
       * The manner or approach and departure
         (:py:class:`~consecutions.Consecutions`) for the note are determined.

    #. Measure-long local harmonic contexts are created,
       for use in parsing events in third species.
    """
    def __init__(self, score, **kwargs):
        self.score = score
        self.parts = self.score.parts
        self.score.measures = len(self.parts[0].getElementsByClass('Measure'))
        self.score.errors = []
        self.errors = []

        # (1) Verify that there are parts populated with notes.
        try:
            validateParts(self.score)
        except ContextError as ce:
            ce.logerror()
            raise EvaluationException
            return
        # (2) General set up for notes and parts.
        # To parts: assign numbers, rhythmic species, error list.
        # To notes: assign consecutions, rules, dependencies, and indexes.
        self.setupPartsGeneral()

        # (3) Accept key from user if provided, else infer one from the parts.
        # Exit if errors are encountered.
        self.setupTonalityGeneral(**kwargs)

        # (4) Specific set up for notes and parts.
        # To parts: assign tonic, mode, scale.
        # To notes: assign csds.
        self.setupPartsTonality()

        # (5) Prepare local contexts for harmonic analysis.
        self.localContexts = {}

        # TODO Move harmonic species span stuff to a different place.
        if kwargs.get('harmonicSpecies'):
            self.harmonicSpecies = kwargs['harmonicSpecies']
        else:
            self.harmonicSpecies = False
        if kwargs.get('harmonicSpecies'):
            offPre = kwargs['offsetPredominant']
            offDom = kwargs['offsetDominant']
            offClosTon = kwargs['offsetClosingTonic']
            if offPre is None:
                initialTonicSpan = makeLocalContext(cxt.score, 0.0, offPre, 'initial tonic')
                predominantSpan = makeLocalContext(cxt.score, offPre, offDom, 'predominant')
            else:
                initialTonicSpan = makeLocalContext(cxt.score, 0.0, offDom, 'initial tonic')
                predominantSpan = None
            dominantSpan = makeLocalContext(cxt.score, offDom, offClosTon, 'dominant')
            closingTonicSpan = makeLocalContext(cxt.score, offClosTon, offClosTon+4.0, 'closing tonic')

        # Collect dictionary of local harmonies for use
        # in parsing third species.
        thirdSpeciesPart = False
        for part in self.parts:
            if part.species == 'third':
                thirdSpeciesPart = True
                break
        if thirdSpeciesPart:
            try:
                self.getLocalOnbeatHarmonies()
            except ContextError as ce:    
                ce.logerror()
                raise EvaluationException()
                return

        # TODO Local contexts aren't yet used by the parser.
#        self.setupLocalContexts()

    def __repr__(self):
        return('Global context')

    def setupPartsGeneral(self):
        # Set part properties: part number, rhythmic species.
        for num, part in enumerate(self.parts):
            # Part number.
            part.partNum = num
            part.name = 'Part ' + str(num+1)
            part.errors = []
            # Part rhythmic species.
            part.species = assignSpecies(part)
            # Set up note consecution relations, from consecutions.py.
            consecutions.getConsecutions(part)
            # Set up note properties used in parsing.
            for idx, note in enumerate(part.recurse().notes):
                # Get the order position of the note in the line.
                note.index = idx
                # Assign a Rule object to each Note.
                note.rule = rule.Rule()
                # Assign a Dependency object to each Note.
                note.dependency = dependency.Dependency()

    def setupTonalityGeneral(self, **kwargs):
        # Setup key, using information provided by user or inferred from parts.
        knote = kwargs.get('keynote')
        kmode = kwargs.get('mode')
        # (1a) If user provides key, validate and test.
        if knote and kmode:
            self.key = keyFinder.testKey(self.score, knote, kmode)
            if not self.key:
                raise EvaluationException
                return
            else:
                self.keyFromUser = True
        # (1b) Else attempt to derive a key from the score.
        else:
            self.key = keyFinder.inferKey(self.score)
            if not self.key:
                raise EvaluationException
                return
            else:
                self.keyFromUser = False
        # (2) If successful, create a pretty name for the key.
        if self.key.getTonic().accidental is not None:
            keyAccidental = '-' + self.key.getTonic().accidental.name
        else:
            keyAccidental = ''
        self.key.nameString = self.key.getTonic().step + keyAccidental + ' ' + self.key.mode

    def setupPartsTonality(self):
        # Set part properties: part number, tonic degree,
        # rhythmic species, scale degrees.
        for num, part in enumerate(self.parts):
            # Part tonic = lowest tonic degree in the line's register.
            # Find tonic pitch class.
            ton = self.key.getTonic()
            ton.octave = 0
            partAmb = analysis.discrete.Ambitus()
            pitchMin, pitchMax = partAmb.getPitchSpan(part)
            # And search for the lowest representative within the line.
            part.tonic = None
            while ton.octave < 8:
                if pitchMin <= ton <= pitchMax:
                    part.tonic = ton
                    break
                ton.octave += 1
            if part.tonic is None:
                ton.octave = 8
                while ton.octave > 0:
                    if pitchMin > ton:
                        part.tonic = ton
                        break
                    ton.octave -= 1

            # Assign scale to part based on register of tonic degree.
            if self.key.mode == 'major':
                part.mode = self.key.mode
                part.scale = scale.MajorScale(part.tonic)
            elif self.key.mode == 'minor':
                part.mode = self.key.mode
                part.scale = scale.MelodicMinorScale(part.tonic)

            # Infer principal harmonic triads.
            part.tonicTriad = chord.Chord([part.scale.pitchFromDegree(1),
                                           part.scale.pitchFromDegree(3),
                                           part.scale.pitchFromDegree(5)])
            part.dominantTriad = chord.Chord([part.scale.pitchFromDegree(5),
                                              part.scale.pitchFromDegree(7, direction='ascending'),
                                              part.scale.pitchFromDegree(2)])
            part.predominantTriad = chord.Chord([part.scale.pitchFromDegree(2),
                                                 part.scale.pitchFromDegree(4),
                                                 part.scale.pitchFromDegree(6, direction='descending')])

            # Assign scale degrees to notes.
            for indx, note in enumerate(part.recurse().notes):
                note.csd = csd.ConcreteScaleDegree(note.pitch, part.scale)
                # 2020-06-29 By this point, it's probably already been
                # established that all of the pitches belong to the scale,
                # so this exception is probably not necessary:
                if not note.csd:
                    raise EvaluationException
                    return

    # For parsing third or fifth species and for counterpoint
    # analysis, collect dictionary of onbeat harmonies.
    def getLocalOnbeatHarmonies(self):
        # For third and fifth species counterpoint,
        # use the measures to define the local context timespans.
        self.localHarmonyDict = {}
        # Use context.measureOffsetMap
        # Get the offset for each downbeat.
        measureOffsets = self.score.measureOffsetMap()
        # Get the start/stop offsets for each measure.
        offsetSpans = pairwise(measureOffsets)
        # Include the span of the final bar.
        measureSpan = offsetSpans[0][1] - offsetSpans[0][0]
        finalSpanOnset = offsetSpans[-1][1]
        finalSpan = (finalSpanOnset, finalSpanOnset+measureSpan)
        offsetSpans.append(finalSpan)
        # Gather the content of each local context.
        for span in offsetSpans:
            offsetStart = span[0]
            offsetEnd = span[1]
            harmonicEssentials = []
            for part in self.score.parts:
                # Get all the notes in the local span.
                localPartElements = part.flat.recurse().getElementsByOffset(offsetStart,
                                                                            offsetEnd,
                                                                            includeEndBoundary=False,
                                                                            mustFinishInSpan=False,
                                                                            mustBeginInSpan=True,
                                                                            includeElementsThatEndAtStart=False).notesAndRests
                localPartNotes = [elem for elem in localPartElements if elem.isNote]
                # Get onbeat consonances or resolutions of tied-over dissonances.
                for elem in localPartElements:
                    if elem.isNote and elem.offset == offsetStart:
                        if elem.tie is None:
                            harmonicEssentials.append(elem.pitch)
                for elem in localPartElements:
                    isHarmonic = True
                    if elem.isNote and elem.offset == offsetStart and elem.tie:
                        for n in harmonicEssentials:
                            if not vlChecker.isTriadicConsonance(elem, note.Note(n)):
                                isHarmonic = False
                                break
                        if elem.isNote and isHarmonic:
                            harmonicEssentials.append(elem.pitch)
                        else:
                            # TODO Can't just look at scale in minor
                            # because music21 uses natural minor.
                            # TODO Look for actual resolution pitch
                            # that is down a step in the context.
                            for resolution in localPartElements:
                                if (resolution.isNote and
                                   resolution.offset > offsetStart and
                                   parser.isStepDown(elem, resolution)):
                                       # resolution = part.scale.next(elem, 'descending')
                                       harmonicEssentials.append(resolution.pitch)
                self.localHarmonyDict[offsetStart] = harmonicEssentials

        # Test the local harmonies for triadicity. Collect measure numbers
        # of non-triadic collections.
        harmErrorList = []
        for harm in self.localHarmonyDict.items():
            if not parser.isTriadicSet(harm[1]):
                mn = (harm[0] + measureSpan) / measureSpan
                harmErrorList.append('{:2.0f}'.format(mn))
        if harmErrorList:
            error = ('Counterpoint Error: The following measures contain '
                     + 'non-triadic sonorities: '
                     + ', '.join(harmErrorList) + '.')
            raise ContextError(error)
        else:
            pass

    def setupLocalContexts(self):
        # TODO This currently sets up measure-length contexts,
        # but would also like to set up harmonic spans for harmonic species.
        # TODO Create a custom offset map for harmonic species
        #        and use the measure map for third species
        #        offsetspans = []
        #        if harmonicSpecies == True:
        #            offsetSpans = []
        #        else:

        # Get the offset for each downbeat.
        measureOffsets = self.score.measureOffsetMap()
        # Get the start/stop offsets for each measure.
        offsetSpans = pairwise(measureOffsets)
        # Include the span of the final bar.
        # measureSpan = offsetSpans[0][1] - offsetSpans[0][0]
        measureSpan = self.parts[0].getElementsByClass('Measure')[-1].barDuration.quarterLength
        finalSpanOnset = offsetSpans[-1][1]
        finalSpan = (finalSpanOnset, finalSpanOnset+measureSpan)
        offsetSpans.append(finalSpan)

        for span in offsetSpans[:-1]:
            offsetStart = span[0]
            offsetEnd = span[1]
            cxt = LocalContext()
            cxt.offset = offsetStart
            cxt.harmonyStart = self.localHarmonyDict[offsetStart]
            cxt.harmonyEnd = self.localHarmonyDict[offsetEnd]
            # Create a new stream for each context.
            cxt.score = stream.Score()
            # Go through the parts of the global context
            # and add notes to corresponding local parts.
            for num, part in enumerate(self.score.parts):
                newpart = stream.Part()
                newpart.species = part.species
                cxt.score.append(newpart)
                for note in part.flat.notes:
                    if offsetStart <= note.offset <= offsetEnd:
                        newpart.append(note)
                # Part-related parsing initialization:
                # newpart.buffer = [n for n in part.flat.notes 
                #                   if not n.tie or n.tie.type == 'start']
                #                   # and n.tie.type != 'stop'
                # newpart.stack = []
                # newpart.arcs = []
                # newpart.openHeads = []
                # newpart.openTransitions = []
            self.localContexts[cxt.offset] = cxt

# -----------------------------------------------------------------------------
# HELPER SCRIPTS
# -----------------------------------------------------------------------------


def validateParts(score):
    if len(score.parts) < 1:
        error = ('The source does not contain any parts.')
        raise ContextError(error)
    else:
        for num, part in enumerate(score.parts):
            if len(part.recurse().notes) < 1:
                error = ('Part ' + str(num+1) + ' contains no notes.')
                raise ContextError(error)


def assignSpecies(part):
    # TODO Examine input measure by measure and build up the Context.
    # Fifth species must be a series of contexts, each with its own species.
    # Fourth species may include breaking into second species.
    # Species assignment has to be input into the parser as well as vlChecker.
    # For the parser: third-species contexts have to permit local elaborations.
    # For the parser: fifth-species contexts have to permit local decorations.
    meas = len(part.getElementsByClass('Measure'))
    notecount = 0
    if meas < 3:
        species = 'fifth'
        return species
    for m in range(2, meas):
        npm = len(part.measure(m).notes)
        notecount += npm
    if notecount/(meas-2) == 1:
        species = 'first'
    elif notecount/(meas-2) == 2:
        if part.measure(2).notes[1].tie:
            species = 'fourth'
        else:
            species = 'second'
    elif notecount/(meas-2) == 3:
        species = 'third'
    elif notecount/(meas-2) == 4:
        species = 'third'
    else:
        species = 'fifth'
    if species:
        return species
    else:
        return None

# -----------------------------------------------------------------------------


if __name__ == "__main__":
    pass

    source = 'TestScoresXML/ChromaTest.musicxml'

# -----------------------------------------------------------------------------
# eof
