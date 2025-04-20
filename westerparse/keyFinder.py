# -----------------------------------------------------------------------------
# Name:         keyFinder.py
# Purpose:      Framework for determining the key of simple tonal lines
#
# Author:       Robert Snarrenberg
# Copyright:    (c) 2025 by Robert Snarrenberg
# License:      BSD, see license.txt
# -----------------------------------------------------------------------------
"""
Key Finder
==========

The Key Finder examines a music21 Stream and either validates
a key provided by the user or infers an appropriate key.

Key inference begins by examining each part in the context to
determine the scales in which the following criteria are met:
first and last pitches are tonic-triad pitches,
all pitches in the line belong to the scale, and at least
one pitch in any leap is a triad pitch.
The list of possibilities is collected in part.keyCandidatesFromScale.
Then each part is examined to determine the keys in which
only tonic-triad pitches are left hanging.
The list of possibilities is collected in
part.keyCandidatesFromHanging.
The lists resulting from the first two steps are sifted
see what possibilities are common to all parts.
The results are collected in scoreKeyCandidates.
If there are still multiple options for key,
the list is winnowed using two preference
rules: (a) prefer most lines to end on tonic degree,
and (b) prefer major rather than minor
if ambiguously mixed.  If winnowed to one option,
the appropriate major or melodic minor scale and key are
assigned to the context, otherwise an exception is raised
and the failure to find a single
key is reported to the user.

Validation of a user-provided key involves two steps:
the name of the key is tested for validity
('Q# diminished' is not a valid option)
and the validated name is then
tested using the same criteria as in key inference.
"""
import unittest

from music21 import *

MINORMODE = {'triad': [0, 3, 7], 'scale': [0, 2, 3, 5, 7, 8, 9, 10, 11]}
MAJORMODE = {'triad': [0, 4, 7], 'scale': [0, 2, 4, 5, 7, 9, 11]}

# -----------------------------------------------------------------------------
# TODO LISTS
# -----------------------------------------------------------------------------

#    TO DO, ADD OPTION: Test each key using parser.preParseLine

#    TODO: create selectable options for the tests and
#    TODO: allow ambiguous results to pass through
#        terminals=True
#        leaps=True
#        finalTonic=True
#        preferMajor=True
#        preferences=True
#        ambiguityAllowed=False

# -----------------------------------------------------------------------------
# EXCEPTION HANDLERS
# -----------------------------------------------------------------------------


class KeyFinderError(Exception):

    def __init__(self, desc):
        self.desc = desc
        self.report = ''

    def logerror(self):
        self.report += f'KEY FINDER ERROR\n{self.desc}'
        return self.report

# -----------------------------------------------------------------------------
# MAIN SCRIPTS
# -----------------------------------------------------------------------------


def testKey(score, knote=None, kmode=None, kharm=False):
    """Validate and test a key provided by the user."""
    # (1) Validate the user selected key.
    try:
        userKey = validateKeySelection(knote, kmode)
    except KeyFinderError as kfe:
        kfe.logerror()
        return (False, kfe.report)
    # (2) Test each part for generic errors.
    try:
        testValidatedKey(score, knote, kmode, kharm)
    except KeyFinderError as kfe:
        kfe.logerror()
        return (False, kfe.report)
    else:
        return (True, userKey)


def inferKey(score):
    """Infer a key from the parts."""
    # (1) Find the keys of each part.
    try:
        allPartKeys = findPartKeys(score)
    except KeyFinderError as kfe:
        kfe.logerror()
        return (False, kfe.report)
    # (2) And then find the keys of the score.
    try:
        key = findScoreKeys(score)
    except KeyFinderError as kfe:
        kfe.logerror()
        return (False, kfe.report)
    else:
        return (True, key)

# -----------------------------------------------------------------------------
# HELPER SCRIPTS
# -----------------------------------------------------------------------------


def validateKeySelection(knote, kmode):
    # Validate the name of the key provided by the user.
    validKeys = ['A- minor', 'A- major',
                 'A minor', 'A major',
                 'A# minor',
                 'B- minor', 'B- major',
                 'B minor', 'B major',
                 'C- major',
                 'C minor', 'C major',
                 'C# minor', 'C# major',
                 'D- major',
                 'D minor', 'D major',
                 'D# minor'
                 'E- minor', 'E- major',
                 'E minor', 'E major',
                 'F minor', 'F major',
                 'F# minor', 'F# major',
                 'G- major',
                 'G minor', 'G major',
                 'G# minor']
    # Three possibilities: no key info provided,
    # invalid key info, valid key info.
    if knote is None or kmode is None:
        # Pass to next step if key not provided by user.
        return None
    elif str(knote + ' ' + kmode) not in validKeys:
        error = ('The user-selected key (' + knote
                 + ' ' + kmode + ') is not a valid key.')
        raise KeyFinderError(error)
    else:
        userKey = key.Key(tonic=knote, mode=kmode)
        return userKey


def testValidatedKey(score, keynote, mode, kharm):
    # Test whether the user-selected key is fits the context.
    userKeyErrors = ''
    for part in score.parts:
        partErrorStr = ''
        partErrors = ''
        thisKey = key.Key(tonic=keynote, mode=mode)
        if mode == 'minor':
            thisScale = scale.MelodicMinorScale(keynote)
            thisPitches = (scale.MelodicMinorScale(keynote).pitches
                           + scale.MinorScale(keynote).pitches)
            thisCollection = [p.name for p in thisPitches]
        elif mode == 'major':
            thisScale = scale.MajorScale(keynote)
            thisPitches = scale.MajorScale(keynote).pitches
            thisCollection = [p.name for p in thisPitches]
        thisTriad = [thisScale.pitchFromDegree(1).name,
                     thisScale.pitchFromDegree(3).name,
                     thisScale.pitchFromDegree(5).name]
        # (1) Test first and last notes.
        if part.flatten().notes[0].pitch.name not in thisTriad:
            error = ('The first note is not a triad pitch.')
            partErrors += '\n\t' + error
        if part.flatten().notes[-1].pitch.name not in thisTriad:
            error = ('The last note is not a triad pitch.')
            partErrors += '\n\t' + error
        # (2) Test for scale pitches.
        nonscalars = 0
        for n in part.flatten().notes:
            if n.pitch.name not in thisCollection:
                nonscalars += 1
        if nonscalars == 1:
            error = ('One note in the line does not belong to the scale.')
            partErrors += '\n\t' + error
        if nonscalars > 1:
            error = (str(nonscalars)
                     + ' notes in the line do not belong to the scale.')
            partErrors += '\n\t' + error
        # (3) Test leaps in monotriadic first, second and fourth species.
        leapPairs = {(note.pitch.name, note.next('Note').pitch.name)
                     for note in part.flatten().notes
                     if note.consecutions.rightType == 'skip'}
        if (not kharm
                and part.species in ['first', 'second', 'fourth'] and
                leapTestWeak(leapPairs, thisTriad) is False):
            error = ('At least one leap fails to include a triad pitch.')
            partErrors += '\n\t' + error
        if partErrors:
            partErrorStr = ('Problems found in ' + part.name
                            + '. Given key = ' + keynote + ' '
                            + mode + partErrors)
        userKeyErrors += partErrorStr

    if len(userKeyErrors) > 0:
        raise KeyFinderError(userKeyErrors)
    else:
        return True


def findPartKeys(score):
    for part in score.parts:
        getPartKeysUsingScale(part)
        getPartKeyUsingHangingNotes(part)

        if part.keyCandidatesFromScale == []:
            error = 'Unable to derive a key from one or more of the parts.'
            raise KeyFinderError(error)


def findScoreKeys(score):
    error = ''
    partKeyListsFromScale = [part.keyCandidatesFromScale
                             for part in score.parts]
    # Exempt third-species lines from the hanging notes test.
    partKeyListsFromHanging = [part.keyCandidatesFromHanging
                               for part in score.parts]

    # Get only those keys that are shared among all parts.
    scoreKeyCandidatesFromScale = set(
        partKeyListsFromScale[0]
        ).intersection(*partKeyListsFromScale)

    # Get those keys shared among all parts not in third species.
    if partKeyListsFromHanging:
        scoreKeyCandidatesFromHanging = set(
            partKeyListsFromHanging[0]
            ).intersection(*partKeyListsFromHanging)
    # Narrow the list to those that agree with both forms of derivation.
    scoreKeyCandidates = set(
        scoreKeyCandidatesFromScale
        ).intersection(scoreKeyCandidatesFromHanging)

    # If there is still more than one plausible key,
    # prefer keys in which most lines end on the tonic degree.
    if len(scoreKeyCandidates) > 1:
        for part in score.parts:
            part.finalpitch = part.flatten().notes[-1].pitch.name
        ks = list(scoreKeyCandidates)
        ksweighted = []
        for k in ks:
            kw = 0
            for part in score.parts:
                if part.finalpitch == k[0]:
                    kw += 1
            ksweighted.append((k, kw))
        strongkeys = [k for k in ksweighted if k[1] > 0]
        if len(strongkeys) == 1:
            scoreKeyCandidates = {strongkeys[0][0]}
    # If there is still more than one plausible key,
    # prefer keys in which some lines begin on the tonic degree.
    if len(scoreKeyCandidates) > 1:
        for part in score.parts:
            part.initialpitch = part.flatten().notes[0].pitch.name
        ks = list(scoreKeyCandidates)
        ksweighted = []
        for k in ks:
            kw = 0
            for part in score.parts:
                if part.initialpitch == k[0]:
                    kw += 1
            ksweighted.append((k, kw))
        strongkeys = [k for k in ksweighted if k[1] > 0]
        if len(strongkeys) == 1:
            scoreKeyCandidates = {strongkeys[0][0]}
    if len(scoreKeyCandidates) == 2:
        k = list(scoreKeyCandidates)
        # If ambiguous between mode only, prefer major.
        if k[0][0] == k[1][0]:
            thisKey = key.Key(tonic=k[0][0], mode='major')
            return thisKey
        # Prefer line in which both notes in at least one leap
        # belong to the triad.
#        elif k[0][0] != k[1][0]:
#            leapTestsResults = []
            # TODO Perhaps relocate this test to the two getPartKeys functions.
        else:
            keystring = (k[0][0] + ' ' + k[0][1]
                         + ' and ' + k[1][0] + ' ' + k[1][1])
            error = ('Two keys are possible for this score: '
                     + keystring)
    elif len(scoreKeyCandidates) == 1:
        k = list(scoreKeyCandidates)
        thisKey = key.Key(tonic=k[0][0], mode=k[0][1])
    elif len(scoreKeyCandidates) == 0:
        error = 'No viable key inferrable from this score.'
    else:
        error = 'More than two keys are possible for this score.'
    if error:
        raise KeyFinderError(error)
    else:
        return thisKey


def terminalsTest(initial, final, triad):
    if {initial, final} <= triad:
        return True
    else:
        return False


def scaleTest(residues, scale):
    if residues <= scale:
        return True
    else:
        return False


def leapTestWeak(leapPairs, triad):
    # TODO Not sure how to construct this test.
    # Test whether at least one note in a leap belongs to the triad.
    # Assume it's true, but return false if an interval fails the test.
    if len(leapPairs) == 0:
        result = True
    else:
        result = False
        for pair in leapPairs:
            if pair[0] in triad or pair[1] in triad:
                result = True
            else:
                result = False
            if not result:
                break
    return result


def leapTestStrong(leapPairs, triad):
    # Test whether both notes in at least one leap belong to the triad.
    # Assume it's true, but return false if all intervals fail the test.
    if len(leapPairs) == 0:
        result = True
    else:
        result = False
        for pair in leapPairs:
            if pair[0] in triad and pair[1] in triad:
                result = True
            else:
                result = False
            if result is True:
                break
    return result


def getPartKeysUsingScale(part):
    chromaResidues = {note.pitch.ps % 12 for note in part.flatten().notes}
    residueInit = part.flatten().notes[0].pitch.ps % 12
    residueFin = part.flatten().notes[-1].pitch.ps % 12
    leapPairResidues = {(note.pitch.ps % 12, note.next('Note').pitch.ps % 12)
                        for note in part.flatten().notes
                        if note.consecutions.rightType == 'skip'}

    # Run tests for all chromatic-enharmonic minor and major keys.
    # Store t for minor/major scales/triads that pass tests.
    tFactorsMinor = []
    tFactorsMajor = []
    
    x = range(12)
    for n in x:
        thisMinorScale = {(deg+n) % 12 for deg in MINORMODE.get('scale')}
        thisMinorTriad = {(deg+n) % 12 for deg in MINORMODE.get('triad')}
        thisMajorScale = {(deg+n) % 12 for deg in MAJORMODE.get('scale')}
        thisMajorTriad = {(deg+n) % 12 for deg in MAJORMODE.get('triad')}

        terminals = terminalsTest(residueInit, residueFin, thisMinorTriad)
        scalars = scaleTest(chromaResidues, thisMinorScale)
        # EXEMPT THIRD SPECIES LINES AND HARMONIC SPECIES FROM LEAPS TEST.
        if (part.harmonicSpecies
                or part.species not in ['first', 'second', 'fourth']):
            leaps = True
        else:
            leaps = leapTestWeak(leapPairResidues, thisMinorTriad)
        if terminals and scalars and leaps:
            tFactorsMinor.append(n)

        terminals = terminalsTest(residueInit, residueFin, thisMajorTriad)
        scalars = scaleTest(chromaResidues, thisMajorScale)
        if (part.harmonicSpecies or part.species not in ['first', 'second', 'fourth']):
            leaps = True
        else:
            leaps = leapTestWeak(leapPairResidues, thisMajorTriad)
        if terminals and scalars and leaps:
            tFactorsMajor.append(n)

    # TODO Apply leaps test only if key is ambiguous by other measures.
    #        if len(tFactorsMinor) + len(tFactorsMajor) > 1:

    keyCandidates = []

    # Find the right diatonic spelling for the scale,
    # using first pitch of the line.
    for t in tFactorsMinor:
        mode = 'minor'
        if residueInit == t:
            keynote = part.flatten().notes[0].pitch.name
            keyCandidates.append((keynote, mode))
        elif residueInit == (t+3) % 12:
            keynote = part.flatten().notes[0].pitch.transpose('-m3').name
            keyCandidates.append((keynote, mode))
        elif residueInit == (t+7) % 12:
            keynote = part.flatten().notes[0].pitch.transpose('-P5').name
            keyCandidates.append((keynote, mode))
    for t in tFactorsMajor:
        mode = 'major'
        if residueInit == t:
            keynote = part.flatten().notes[0].pitch.name
            keyCandidates.append((keynote, mode))
        elif residueInit == (t+4) % 12:
            keynote = part.flatten().notes[0].pitch.transpose('-M3').name
            keyCandidates.append((keynote, mode))
        elif residueInit == (t+7) % 12:
            keynote = part.flatten().notes[0].pitch.transpose('-P5').name
            keyCandidates.append((keynote, mode))

    part.keyCandidatesFromScale = keyCandidates

def getPartKeyUsingHangingNotes(part):
    hangingNotes = []
    displacedNotes = []
    line = [n.pitch for n in part.flatten().notes]
    ln = len(line)
    while ln > 0:
        x = line[-1]
        if x.name not in hangingNotes and x.step not in displacedNotes:
            hangingNotes.append(x.name)
            if x.step == 'A':
                displacedNotes.append('G'), displacedNotes.append('B')
            if x.step == 'B':
                displacedNotes.append('A'), displacedNotes.append('C')
            if x.step == 'C':
                displacedNotes.append('B'), displacedNotes.append('D')
            if x.step == 'D':
                displacedNotes.append('C'), displacedNotes.append('E')
            if x.step == 'E':
                displacedNotes.append('D'), displacedNotes.append('F')
            if x.step == 'F':
                displacedNotes.append('E'), displacedNotes.append('G')
            if x.step == 'G':
                displacedNotes.append('F'), displacedNotes.append('A')
        elif x.name in hangingNotes:
            pass
        elif x.step in displacedNotes:
            if x.step == 'A':
                displacedNotes.append('G'), displacedNotes.append('B')
            if x.step == 'B':
                displacedNotes.append('A'), displacedNotes.append('C')
            if x.step == 'C':
                displacedNotes.append('B'), displacedNotes.append('D')
            if x.step == 'D':
                displacedNotes.append('C'), displacedNotes.append('E')
            if x.step == 'E':
                displacedNotes.append('D'), displacedNotes.append('F')
            if x.step == 'F':
                displacedNotes.append('E'), displacedNotes.append('G')
            if x.step == 'G':
                displacedNotes.append('F'), displacedNotes.append('A')
        line.pop()
        ln = len(line)
    keyCandidates = []
    hnchord = chord.Chord(hangingNotes)
    if hnchord.canBeTonic():
        keyCandidates.append((hnchord.root().name, hnchord.quality))
    elif hnchord.isIncompleteMinorTriad():
        keyCandidates.append((hnchord.root().name, hnchord.quality))
        keyCandidates.append((hnchord.root().transpose('m6').name, 'major'))
    elif hnchord.isIncompleteMajorTriad():
        keyCandidates.append((hnchord.root().name, hnchord.quality))
        keyCandidates.append((hnchord.root().transpose('M6').name, 'minor'))
    elif hnchord.commonName in ['Perfect Fifth', 'Perfect Fourth']:
        keyCandidates.append((hnchord.root().name, 'minor'))
        keyCandidates.append((hnchord.root().name, 'major'))
    elif hnchord.commonName in ['unison', 'note', 'Perfect Octave']:
        keyCandidates.append((hnchord.root().name, 'minor'))
        keyCandidates.append((hnchord.root().name, 'major'))
        keyCandidates.append((hnchord.root().transpose('M6').name, 'minor'))
        keyCandidates.append((hnchord.root().transpose('m6').name, 'major'))
        keyCandidates.append((hnchord.root().transpose('P4').name, 'minor'))
        keyCandidates.append((hnchord.root().transpose('P4').name, 'major'))
    else:
        part.keyCandidatesFromHanging = None
    part.keyCandidatesFromHanging = keyCandidates


# -----------------------------------------------------------------------------


class Test(unittest.TestCase):

    def runTest(self):
        pass

    def test_(self):
        pass

# -----------------------------------------------------------------------------


if __name__ == '__main__':
    # self_test code
    unittest.main()

# -----------------------------------------------------------------------------
# eof
