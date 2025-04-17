# -----------------------------------------------------------------------------
# Name:         context.py
# Purpose:      Framework for analyzing species counterpoint.
#
# Author:       Robert Snarrenberg
# Copyright:    (c) 2025 by Robert Snarrenberg
# License:      BSD, see license.txt
# -----------------------------------------------------------------------------
"""
Context
=======

The Context module includes classes to represent both global
and local contexts.
"""

from music21 import *
import logging

from westerparse import vlChecker
from westerparse import parser
from westerparse import keyFinder
from westerparse import csd
from westerparse import rule
from westerparse import dependency
from westerparse import consecutions
from westerparse.utilities import pairwise

# -----------------------------------------------------------------------------
# LOGGER
# -----------------------------------------------------------------------------

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
# logger.setLevel(logging.DEBUG)
# logging handlers
f_handler = logging.FileHandler('parser.txt', mode='w')
f_handler.setLevel(logging.DEBUG)
# logging formatters
f_formatter = logging.Formatter('%(message)s')
f_handler.setFormatter(f_formatter)
# add handlers to logger
logger.addHandler(f_handler)

# -----------------------------------------------------------------------------
# EXCEPTION HANDLERS
# -----------------------------------------------------------------------------


class ContextError(Exception):
    def __init__(self, desc):
        self.desc = desc
        self.report = ''

    def logerror(self):
        self.report += f'CONTEXT ERROR\n{self.desc}'
        return self.report


class EvaluationException(Exception):
    def __init__(self, desc):
        self.desc = desc
        pass

    def report(self):
        pass
        # print(self.desc)

# TODO: Figure out how to accommodate tonal ambiguity:
#   Make a global context for each option?

# -----------------------------------------------------------------------------
# MAIN CLASSES
# -----------------------------------------------------------------------------


class Context:
    """An object for representing a span of a composition
    and for storing objects that represent smaller spans.
    """

    def __init__(self):
        self.scale = None
        self.triad = None
        self.harmonyStart = None
        self.harmonyEnd = None
        self.offset = None
        # dictionaries, by part, of parse-related data
        self.openHeads = []
        self.openTransitions = []
        self.arcs = []


class LocalContext(Context):

    def __init__(self):
        super().__init__()
        self.score = None
        self.harmonyStart = None
        self.harmonyEnd = None
        self.offset = None
        # dictionaries, by part, of parse-related data
        self.openHeads = []
        self.openTransitions = []
        self.arcs = []

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

       * A position index is assigned. This is the primary note
         reference used during parsing.
       * A concrete scale degree (:py:class:`~csd.ConcreteScaleDegree`)
         is determined.
       * A :py:class:`~rule.Rule` object is attached.
       * A :py:class:`~dependency.Dependency` object is attached.
       * The manner of approach and departure
         (:py:class:`~consecutions.Consecutions`) for the note are determined.

    #. Measure-long local harmonic contexts are created,
       for use in parsing events in third species.
    """
    def __init__(self, score, **kwargs):
        super().__init__()
        self.score = score
        self.parts = self.score.parts
        self.score.measures = len(self.parts[0].getElementsByClass('Measure'))
        self.barDuration = self.parts[0].getElementsByClass('Measure')[0].barDuration.quarterLength
        self.score.errors = []
        self.errors = []
        self.errorsDict = {}
        self.parseReport = ''
        if kwargs.get('harmonicSpecies'):
            self.harmonicSpecies = kwargs['harmonicSpecies']
        else:
            self.harmonicSpecies = False
        if kwargs.get('filename'):
            self.filename = kwargs['filename']
        # (1) Verify that there are parts populated with notes.
        # TODO: only check selected parts
        try:
            validateParts(self.score)
        except ContextError as ce:
            ce.logerror()
            raise EvaluationException(ce.report)
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

        # def makeLocalContext(cxt, cxtOn, cxtOff, cxtHarmony):
        #     """
        #     Create a local context given a start and stop offset
        #     in an enclosing Context.
        #     """
        #     locCxt = cxt.flatten().getElementsByOffset(cxtOn,
        #                                      cxtOff,
        #                                      includeEndBoundary=True,
        #                                      mustFinishInSpan=False,
        #                                      mustBeginInSpan=True,
        #                                      includeElementsThatEndAtStart=False,
        #                                      classList=None).stream()
        #     locCxt.harmony = cxtHarmony
        #     return locCxt

        # TODO Move harmonic species span stuff to a different place.
        if self.harmonicSpecies:
            if kwargs.get('startPredominant'):
                offPre = (kwargs['startPredominant'] - 1) * self.barDuration
            else:
                offPre = None
            if kwargs.get('startDominant'):
                offDom = (kwargs['startDominant'] - 1) * self.barDuration
            offClosTon = (self.score.measures - 1) * self.barDuration
            try:
                validateHarmonicSegmentation(offPre,
                                             offDom,
                                             offClosTon,
                                             self.barDuration)
            except ContextError as ce:
                ce.logerror()
                raise EvaluationException(ce.report)
                return
            else:
                self.harmonicSpanDict = {
                    'offsetInitialTonic': 0.0,
                    'offsetPredominant': offPre,
                    'offsetDominant': offDom,
                    'offsetClosingTonic': offClosTon,
                }
            # TODO Local harmonies and timespans aren't yet
            #   used by the parser for all species.
            self.setupHarmonicTimespans()

        # Collect dictionary of local harmonies for use
        # in parsing third species.
        thirdSpeciesPart = False
        for part in self.parts:
            if part.species in {'third', 'fifth'}:
                thirdSpeciesPart = True
                break
        if thirdSpeciesPart:
            try:
                self.getLocalOnbeatHarmonies()
            except ContextError as ce:
                ce.logerror()
                raise EvaluationException(ce.report)
                return

    def __repr__(self):
        return 'Global context'

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
            consecutions.setConsecutions(part)
            # Set up note properties used in parsing.
            for idx, note in enumerate(part.recurse().notes):
                # Get the order position of the note in the line.
                note.index = idx
                # Assign a Rule object to each Note.
                note.rule = rule.Rule()
                # Assign a Dependency object to each Note.
                note.dependency = dependency.Dependency()
            # Set up harmonic species property
            part.harmonicSpecies = self.harmonicSpecies

    def setupTonalityGeneral(self, **kwargs):
        # Setup key, using information provided by user or inferred from parts.
        knote = kwargs.get('keynote')
        kmode = kwargs.get('mode')
        kharm = self.harmonicSpecies
        # (1a) If user provides key, validate and test.
        if knote and kmode:
            user_key_test_result = keyFinder.testKey(self.score, knote, kmode, kharm)
            logger.debug(f'user_key_test_result = {user_key_test_result}')
            if not user_key_test_result[0]:
                raise EvaluationException(user_key_test_result[1])
                return
            else:
                self.key = user_key_test_result[1]
                self.keyFromUser = True
        # (1b) Else attempt to derive a key from the score.
        else:
            infer_key_test_result = keyFinder.inferKey(self.score)
            logger.debug(f'infer_key_test_result = {infer_key_test_result}')
            if not infer_key_test_result[0]:
                raise EvaluationException(infer_key_test_result[1])
                return
            else:
                self.keyFromUser = False
                self.key = infer_key_test_result[1]
        # (2) If successful, create a pretty name for the key.
        if self.key.getTonic().accidental is not None:
            keyAccidental = '-' + self.key.getTonic().accidental.name
        else:
            keyAccidental = ''
        self.key.nameString = (self.key.getTonic().step
                               + keyAccidental + ' ' + self.key.mode)

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
            part.tonicTriad = chord.Chord(
                [part.scale.pitchFromDegree(1),
                 part.scale.pitchFromDegree(3),
                 part.scale.pitchFromDegree(5)])
            part.dominantTriad = chord.Chord(
                [part.scale.pitchFromDegree(5),
                 part.scale.pitchFromDegree(7, direction=scale.Direction.ASCENDING),
                 part.scale.pitchFromDegree(2)])
            part.predominantTriad = chord.Chord(
                [part.scale.pitchFromDegree(2),
                 part.scale.pitchFromDegree(4),
                 part.scale.pitchFromDegree(6, direction=scale.Direction.DESCENDING)])

            # Assign scale degrees to notes.
            for indx, note in enumerate(part.recurse().notes):
                note.csd = csd.ConcreteScaleDegree(note.pitch, part.scale)
                # 2020-06-29 By this point, it's probably already been
                # established that all of the pitches belong to the scale,
                # so this exception is probably not necessary:
                if not note.csd:
                    raise EvaluationException('temp text for csd exception, contact sysadmin')
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
                localPartElements = part.flatten().recurse().getElementsByOffset(
                    offsetStart,
                    offsetEnd,
                    includeEndBoundary=False,
                    mustFinishInSpan=False,
                    mustBeginInSpan=True,
                    includeElementsThatEndAtStart=False).notesAndRests
                localPartNotes = [elem for elem in localPartElements
                                  if elem.isNote]
                # Get onbeat consonances or resolutions
                # of tied-over dissonances.
                for elem in localPartElements:
                    if elem.isNote and elem.offset == offsetStart:
                        if elem.tie is None:
                            harmonicEssentials.append(elem.pitch)
                for elem in localPartElements:
                    isHarmonic = True
                    if elem.isNote and elem.offset == offsetStart and elem.tie:
                        for n in harmonicEssentials:
                            if not vlChecker.isTriadicConsonance(elem,
                                                                 note.Note(n)):
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
                                    harmonicEssentials.append(resolution.pitch)
                self.localHarmonyDict[offsetStart] = harmonicEssentials

        # Test the local harmonies for triadicity. Collect measure numbers
        # of non-triadic collections.
        harmErrorList = []
        for harm in self.localHarmonyDict.items():
            logging.debug(f'local harmony = {harm[1]}')
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

    def setupHarmonicTimespans(self):
        # TODO This currently sets up measure-length contexts,
        # but would also like to set up harmonic spans for harmonic species.
        # TODO Perhaps create a custom offset map for harmonic species
        #        and use the measure map for third species
        #        offsetspans = []
        #        if harmonicSpecies == True:
        #            offsetSpans = []
        #        else:

        # Get the offset for each downbeat.
        offsetSpans = []
        if self.harmonicSpanDict['offsetPredominant'] is not None:
            offsetSpans.append((self.harmonicSpanDict['offsetInitialTonic'],
                                self.harmonicSpanDict['offsetPredominant']))
            offsetSpans.append((self.harmonicSpanDict['offsetPredominant'],
                                self.harmonicSpanDict['offsetDominant']))
        else:
            offsetSpans.append((self.harmonicSpanDict['offsetInitialTonic'],
                                self.harmonicSpanDict['offsetDominant']))
        offsetSpans.append((self.harmonicSpanDict['offsetDominant'],
                            self.harmonicSpanDict['offsetClosingTonic']))
        offsetSpans.append((self.harmonicSpanDict['offsetClosingTonic'],
                            self.score.duration.quarterLength))

        # create list in the Context for the timespans
        self.timespans = []
        for span in offsetSpans:
            ts = TimeSpan(self.score)
            ts.start = span[0]
            ts.end = span[1]
            # ts.harmonyStart = self.localHarmonyDict[ts.start]
            # ts.harmonyEnd = self.localHarmonyDict[ts.end]
            self.timespans.append(ts)

        for ts in self.timespans:
            tsNotes = []
            for n in ts.score.parts[0].flatten().notes:
                if ts.start <= n.offset <= ts.end:
                    tsNotes.append(n.index)
            pass
            # print(tsNotes)

    def makeTwoPartContexts(self):
        partNumPairs = vlChecker.getAllPartNumPairs(self.score)
        bassPartNum = self.parts[-1].partNum
        twoPartContexts = []
        if partNumPairs:
            for pair in partNumPairs:
                parts = [self.parts[pair[0]], self.parts[pair[1]]]
                duet = stream.Score(givenElements=parts)
                # copy part number in context to part in duet
                duet.parts[0].parentID = pair[0]
                duet.parts[1].parentID = pair[1]
                duet.key = self.key
                # duetScore.score = duetScore
                duet.filename = f'Parts {pair[0]} and {pair[1]}'
                if bassPartNum in pair:
                    duet.includesBass = True
                else:
                    duet.includesBass = False
                twoPartContexts.append(duet)
                # duetScore.show()
        return twoPartContexts


class TimeSpan:

    def __init__(self, score):
        self.harmonyStart = None
        self.harmonyEnd = None
        self.start = None
        self.end = None
        self.score = score
        # dictionaries, by part, of parse-related data
        self.parts = {}  # references to context parts
        for num, part in enumerate(score.parts):
            partId = f'Part {num}'
            self.parts[partId] = TsPart()
        # list, if TimeSpan has subordinate timespans
        self.timespans = []

    def __repr__(self):
        return str('Timespan starting at ' + str(self.start))


class TsPart:

    def __init__(self):
        self.openHeads = []
        self.openTransitions = []
        self.arcs = [['X'], ['Y']]

# -----------------------------------------------------------------------------
# HELPER SCRIPTS
# -----------------------------------------------------------------------------


def validateParts(score):
    if len(score.parts) < 1:
        error = 'The source does not contain any parts.'
        raise ContextError(error)
    for part in score.parts:
        for measure in part.getElementsByClass('Measure'):
            if len([n for n in measure.notes]) == 0 or measure.barDuration.quarterLength < measure.duration.quarterLength:
                error = ('At least one measure does not contain enough notes.\nPlease complete the exercise and try again.')
                raise ContextError(error)
            elif measure.barDuration.quarterLength > measure.duration.quarterLength:
                error = (
                    'At least one measure contains too many notes.\nPlease revise the exercise and try again.')
                raise ContextError(error)
            elif measure.number > 1 and (len([nr for nr in measure.notesAndRests]) != len([n for n in measure.notes])):
                error = ('At least one measure other than the first contains a rest.\nPlease reivse the exercise and try again.')
                raise ContextError(error)
            elif measure.number == 1:
                initial_pitch = False
                for n in measure.notesAndRests:
                    if n.isNote:
                        initial_pitch = True
                    if n.isRest and initial_pitch:
                        error = ('The first measure has a rest after a note.\nPlease revise the exercise and try again.')
                        raise ContextError(error)
        final_measure = part.measure(-1)
        final_measure_notes = final_measure.notes

        if len(final_measure_notes) != 1:
            error = (
                'The final measure contains too many notes.\nPlease revise the exercise and try again.')
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
    species = None
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
    return species


def validateHarmonicSegmentation(offPre, offDom, offClosTon, barDuration):
    """Use the offsets for the beginnings of harmonic spans and
    calcluate whether the segmentation conforms to the rules for
    harmonic species."""
    # e.g. 32.0, 36.0, 44.0, 4.0
    totalLength = offClosTon + barDuration
    if offPre is not None:
        spanA = offPre
        spanB = totalLength - offPre
    else:
        spanA = offDom
        spanB = totalLength - offDom
    if spanA < spanB:
        error = 'The initial tonic span is too short.'
        raise ContextError(error)


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pass

    source = 'TestScoresXML/ChromaTest.musicxml'

# -----------------------------------------------------------------------------
# eof
