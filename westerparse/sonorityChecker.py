#!/Users/snarrenberg/opt/anaconda3/envs/westerparse/bin/python
# -----------------------------------------------------------------------------
# Name:         sonorityChecker.py
# Purpose:      Checks sonority for compliance with preference rules
#
# Authors:      Robert Snarrenberg, Tony Li
# Copyright:    (c) 2021 by Robert Snarrenberg
# License:      BSD, see license.txt
# -----------------------------------------------------------------------------
"""
Sonority Checker
================

Take a counterpoint exercies with two or more parts and examine the
sonorities for conformity with the preference rules of species
counterpoint.
"""
# NB: vlq parts and score Parts are numbered top to bottom
# NB: vPair parts are numbered bottom to top

from music21 import *

import westerparse.vlChecker as vl
# from westerparse import context
# from westerparse import consecutions
# from westerparse import theoryAnalyzerWP
# from westerparse import theoryResultWP

# -----------------------------------------------------------------------------
# MODULE VARIABLES
# -----------------------------------------------------------------------------

sonorityReport = ''

sonorityErrors = []

# set preferences for sonorities
onBeatImperfectMin = .75  # percentage
onBeatUnisonMax = .05  # percentage
onBeatPerfectMax = .20  # percentage
tiedOverDissonanceMin = .50  # percentage
offbeatDissonanceMin = .50  # percentage
# downbeatHarmonyDensity =

# preferences errors
# pferrors = []
# preferences for consecutive imperfect intervals
imperfectStreakLimit = 4
imperfectSeriesLimit = 3

# implement interest rules
    # look for narrow ambitus
    # look for monotony of various types
        # linear: repeated pitches
            # consecutive (limit in outer voices)
        # linear: lack of steps
        # linear: lack of skips
        # sonority: lack of intervallic variety
        # etc.
        # repeated sonority: consecutive, nonconsecutive

# sonority features:
    # pcDensity: number of distinct pcs divided by number of pitches
    # pitchDensity: number of distinct pitches divided by number of notes

# implement preference rules for sonority
    # run independently or in conjunction with voice-leading check
    # need to be able to access measure number for each sonority/interval
    # for reporting to user
    # perhaps modify theoryAnalyzer's getVerticalPairs
    # or get from elements of vPair
        # add attributes to vPair
            # .measure (integer) for time of onset??
            # .onDownbeat (true, false)
        # see fourthSpeciesForbiddenMotions for assembly
            # of onbeat and offbeat vPairs
    # count non-terminal measures
# prefer imperfect on beat (first, second, third)
    # count non-terminal perfect and imperfect
    # prefer, say, 75% imperfect
# on-beat unisons, non-terminal (first, second, third, fourth?)
# fifths and octaves, on-beat
    # report if at least one note's rule is an S rule
# adjacent register of lines
    # weight terminal intervals more than internal intervals
    # look for preponderance of simple intervals, not compound
    # report if too many intervals larger than 12th?
    # report if any intervals equal to or greater than 15th
# first species:
    # DONE consecutive imperfect consonances, with or without
    # DONE change of direction
# second species: dissonance off beat
    # count offbeat dissonances, prefer, say, percentage greater than 50%
# third species: dissonance off beat
    # count offbeat dissonances, prefer, say, percentage greater than 50%
    # count final off-beat dissonances, prefer, say, percentage
    # greater than 50%
# fourth species
    # if tied over, prefer dissonance
    # say, at least 50%
# first species, three parts
    # count pitch-class content of each non-terminal sonority (1, 2, 3)
        # prefer most with 3
    # if pc count = 2
        # prefer octave(double octave) to unison
        # prefer imperfect to perfect
    # if all intervals above bass = perfect
        # report if sonority is non-terminal
    # test adjacency of upper parts, rarely more than octave
    # test adjacency of lower parts, rarely more than twelfth

# def firstSpeciesSonorities(score, analyzer, partNum1=None, partNum2=None):
#    pass

# -----------------------------------------------------------------------------
# Sonority Class
# -----------------------------------------------------------------------------

class Sonority:

    def __init__(self, offset, objects):
        # input is a list of objects (notes or rests), derived
        #   from a vertical slice, ordered from top to bottom
        # also get the offset, for use in filtering onbeat and offbeat
        #   sonorities
        self.offset = offset
        self.objects = objects
        if objects[-1].isNote:
            self._bass = objects[-1]
        else:
            self._bass = None
        if objects[0].isNote:
            self._soprano = objects[0]
        else:
            self._soprano = None
        self._upper = [p for p in objects[:-1] if p.isNote]

    def bass(self):
        return self._bass

    def uppertones(self):
        return self._upper

    def soprano(self):
        return self._soprano

    def pitches(self):
        pitches = [p.pitch for p in self.objects if p.isNote]
        return pitches

    def intervals(self):
        intervals = []
        if self.bass():
            bass = self.bass()
        else:
            bass = self.uppertones()[-1]
        for p in self.uppertones():
            if p.isNote:
                if p >= bass:
                    intervals.append(interval.Interval(bass, p))
                else:
                    intervals.append(interval.Interval(bass, p).complement)
        return intervals

    def intervalsGeneric(self):
        intervalsGeneric = []
        for ivl in self.intervals():
            intervalsGeneric.append(ivl.generic.directed)
        return intervalsGeneric

    def intervalsReduced(self):
        intervalsReduced = []
        nonzeroresidues = []
        for ivl in self.intervalsGeneric():
            if (ivl - 1) % 7 == 0:
                nonzeroresidues.append(8)
            elif ((ivl - 1) % 7) + 1 not in nonzeroresidues:
                nonzeroresidues.append(((ivl - 1) % 7) + 1)
        intervalsReduced = sorted(nonzeroresidues, reverse=True)
        return intervalsReduced

    @property
    def isOpen(self):
        outerIntv = interval.notesToGeneric(self.bass(),
                                            self.soprano()).undirected
        if outerIntv % 7 in {3, 6}:
            return True
        else:
            return False

    def pitchDensity(self):
        pitches = []
        for note in self.pitches():
            if note.nameWithOctave not in pitches:
                pitches.append(note.nameWithOctave)
        density = len(pitches) / len(self.pitches())
        return round(density, 2)

    def pitchClassDensity(self):
        pcs = []
        for note in self.pitches():
            if note.name not in pcs:
                pcs.append(note.name)
        density = len(pcs) / len(self.pitches())
        return round(density, 2)


# -----------------------------------------------------------------------------
# MAIN SCRIPTS
# -----------------------------------------------------------------------------


def getAllVerticalities(score):
    # make a list of verticalities that have notes and rests
    # the keys are part numbers in the duet
    #     and the values are notes (rests)
    return vl.getAllVerticalContentDictionariesList(score)


def getBassDuetPartNumbers(score):
    # assumes that the lowest part in the score is also the bass
    allPartNums = vl.getAllPartNumPairs(score)
    bassPartNum = len(score.parts) -1
    bassDuetPartNums = [pair for pair in allPartNums if bassPartNum in pair]
    return bassDuetPartNums


def getAdjacentPartPairs(score):
    adjacentPairs = []
    n = 0
    while n < len(score.parts)-1:
        adjacentPairs.append((n, n+1))
        n += 1
    return adjacentPairs


def getSonorityList(score):
    vertDict = getAllVerticalities(score)
    sonorityList = []
    for vert in vertDict.items():
        offset = vert[0]
        vertContent = vert[1]
        objectList = []
        for obj in vertContent.values():
            objectList.append(obj)
        son = Sonority(offset, objectList)
        sonorityList.append(son)
    return sonorityList


def getOnbeatSonorities(score):
    onbeats = vl.getOnbeatOffsetList(score)
    sons = getSonorityList(score)
    onbeatSons = [s for s in sons if s.offset in onbeats]
    return onbeatSons


def getOffbeatSonorities(score):
    offbeats = vl.getOffbeatOffsetList(score)
    sons = getSonorityList(score)
    offbeatSons = [s for s in sons if s.offset in offbeats]
    return offbeatSons


def printSonorityList(score):
    """
    For each sonority, the intervals above the bass are listed
    from lowest to highest.
    """
    sonorities = getSonorityList(score)
    sonorityList = [s.intervalsGeneric() for s in sonorities]
    # get the number of parts in the texture
    texture = len(sonorityList[0])
    # start with the highest part
    t = 0
    print('figured bass progression')
    while t < texture:
        fb = ''
        for son in sonorityList:
            s = son[t]
            if len(str(s)) == 1:
                fb = fb + ' ' + str(s) + '  '
            else:
                fb = fb + str(s) + '  '
        print(fb)
        t += 1


def getDensityList(score, densityType=None):
    densityList = []
    if densityType not in ['pitch', 'pitch class']:
        print('User must select a density type to report: '
              'use \'pitch\' or \'pitch class\'.')
        return
    n = 0
    sonorityList = getSonorityList(score)
    for s in sonorityList:
        if densityType == 'pitch':
            density = s.pitchDensity()
        elif densityType == 'pitch class':
            density = s.pitchClassDensity()
        densityList.append(density)
        n += 1
    return(densityList)


def getAdjacencyRatingsReport(score):
    vertDict = getAllVerticalities(score)
    adjPairs = getAdjacentPartPairs(score)
    adjacencyReport = ''
    for pair in adjPairs:
        # Initialize counter for intervals an octave or smaller.
        # Initialize counter for all intervals.
        pairReport = (f'Adjacency rating for parts {pair[0]} and {pair[1]}: ')
        simpleCount = 0
        fullCount = 0
        for vert in vertDict.items():
            vertContent = vert[1]
            if (vertContent[pair[0]] and vertContent[pair[1]]):
                n1 = vertContent[pair[0]]
                n2 = vertContent[pair[1]]
                if (interval.Interval(n1, n2).name
                   == interval.Interval(n1, n2).semiSimpleName):
                    simpleCount += 1
                fullCount += 1
        pairReport = pairReport + '{:.1%}'.format(simpleCount/fullCount)
        adjacencyReport = adjacencyReport + '\n' + pairReport
    return adjacencyReport




def checkImperfectSequences(duet):
    # original written by Tony Li
    # use for first species in two parts
    # ? use for any duet where parts are in the same species
    vps = vl.getVerticalPairs(duet)
    maxThirdsStreak = 0
    maxThirdsSeries = 0
    maxSixthsStreak = 0
    maxSixthsSeries = 0
    pferrors = []
    # Find maximum number of consecutive imperfect intervals:
    #     streak = with change of direction
    #     series = without a change of direction
    n = 0
    while n < len(vps):
        if vps[n] is not None:
            itvl = interval.Interval(vps[n][0], vps[n][1])
            if itvl.simpleName in {'m3', 'M3', 'm6', 'M6'}:
                streak = 1
                series = 1
                done = False
                intSize = itvl.generic.directed  # 3 or 6
                while not done:
                    if n < len(vps) - 1:
                        n += 1
                        newInt = interval.Interval(vps[n][0],
                                                   vps[n][1])
                        if (newInt.simpleName in {'m3', 'M3', 'm6', 'M6'}
                           and newInt.generic.directed == intSize):
                            streak += 1
                            series += 1
                            if streak >= 3:
                                #Check for a change of direction
                                rules = [
                                    (vps[n][0] > vps[n-1][0]
                                     and vps[n-1][0] < vps[n-2][0]),
                                    (vps[n][0] < vps[n-1][0]
                                     and vps[n-1][0] > vps[n-2][0])
                                     ]
                                if any(rules):
                                    series = streak - 1
                                    # record series if longer than previous
                                    if (series > maxThirdsSeries
                                       and intSize % 7 == 3):
                                        maxThirdsSeries = series
                                    elif (series > maxSixthsSeries
                                       and intSize % 7 == 6):
                                        maxSixthsSeries = series
                                    # reset series variables
                                    series = 1
                                else:
                                    continue
                        else:
                            # record streak if longer than previous
                            if streak == series:
                                if (series > maxThirdsSeries
                                   and intSize % 7 == 3):
                                    maxThirdsSeries = series
                                elif (series > maxSixthsSeries
                                      and intSize % 7 == 6):
                                    maxSixthsSeries = series
                            elif streak > series:
                                if (streak > maxThirdsStreak
                                   and intSize % 7 == 3):
                                    maxThirdsStreak = streak
                                elif (streak > maxSixthsStreak
                                      and intSize % 7 == 6):
                                    maxSixthsStreak = streak
                            done = True
                    else:
                        done = True
                        n += 1
            else:
                n += 1
        else:
            n += 1
    if maxThirdsSeries > imperfectSeriesLimit:
        error = ('The maximum number of parallel thirds in the same '
                 'direction is ' + str(maxThirdsSeries)
                 + ', \nwhich exceeds the recommended limit of '
                 + str(imperfectSeriesLimit) + '.')
        pferrors.append(error)
    if maxThirdsStreak > imperfectStreakLimit:
        error = ('The maximum number of parallel thirds with a change '
                 'of direction is ' + str(maxThirdsStreak)
                 + ', \nwhich exceeds the recommended limit of '
                 + str(imperfectStreakLimit) + '.')
        pferrors.append(error)
    if maxSixthsSeries > imperfectSeriesLimit:
        error = ('The maximum number of parallel sixths in the same '
                 'direction is ' + str(maxSixthsSeries)
                 + ', \nwhich exceeds the recommended limit of '
                 + str(imperfectSeriesLimit) + '.')
        pferrors.append(error)
    if maxSixthsStreak > imperfectStreakLimit:
        error = ('The maximum number of parallel sixths with a change '
                 'of direction is ' + str(maxSixthsStreak)
                 + ', \nwhich exceeds the recommended limit of '
                 + str(imperfectStreakLimit) + '.')
        pferrors.append(error)
    if pferrors:
        return pferrors
    else:
        return 'There are no monotonous streaks or series of thirds or sixths.'






def getOnbeatIntervals(duet):
    # TODO limit to onbeat verticals
    onbeatDyads = vl.getVerticalPairs(duet)
    # return lists of measure numbers
    onbeatConsonances = []
    onbeatDissonances = []
    onbeatUnisons = []
    onbeatOctaves = []
    onbeatPerfect = []
    onbeatImperfect = []
    # or, create an object for every vPair and give it attributes:
    # consonance=True, unison=True, perfect=True,
    # dissonance=False, simple=True, onbeat=True
    # measure, interval,
    for vPair in onbeatDyads:
        if vl.isConsonanceAboveBass(vPair[1], vPair[0]):
            onbeatConsonances.append(vPair[0].measureNumber)
        if vl.isVerticalDissonance(vPair[0], vPair[1]):
            onbeatDissonances.append(vPair[0].measureNumber)
        if vl.isUnison(vPair[0], vPair[1]):
            onbeatUnisons.append(vPair[0].measureNumber)
        elif vl.isOctave(vPair[0], vPair[1]):
            onbeatOctaves.append(vPair[0].measureNumber)
        if vl.isPerfectVerticalConsonance(vPair[0], vPair[1]):
            onbeatPerfect.append(vPair[0].measureNumber)
        elif vl.isImperfectVerticalConsonance(vPair[0], vPair[1]):
            onbeatImperfect.append(vPair[0].measureNumber)
    print('on-beat consonance count:', len(onbeatConsonances))
    print('on-beat dissonance count:', len(onbeatDissonances))
    print('on-beat unison count:', len(onbeatUnisons))
    print('on-beat octave count:', len(onbeatOctaves))
    print('on-beat perfect intervals count:', len(onbeatPerfect))
    print('on-beat imperfect intervals count:', len(onbeatImperfect))







def getBassUpperPair(noteList):
    # accepts a noteList ordered high to low, bass at end of list
    bassPartNum = len(noteList)-1
    upperPartNums = []
    n = len(noteList) - 2
    while n > -1:
        upperPartNums.append(n)
        n -= 1
    bassUpperPartPair = []
    for partNum in upperPartNums:
        bassUpperPartPair.append((bassPartNum, partNum))
#    bassUpperPartPairs = bassUpperPartPairs.sort(key = lambda x: x[1])
    return sorted(bassUpperPartPair)




# this script not in use
def getSonorityClass(noteList):
    bassUpperPartPair = getBassUpperPair(noteList)
    sonority = []
    for partPair in bassUpperPartPair:
        bassPart = noteList[partPair[0]]
        upperPart = noteList[partPair[1]]
        intv = interval.notesToGeneric(bassPart, upperPart).undirected
        if 1 < intv < 10:
            sonority.append(intv)
        elif intv == 15:
            sonority.append(8)
        else:
            sonority.append(intv % 7)
    return sonority


def getOnbeatDyads(score, analyzer, partNum1, partNum2):
    onbeatDyads = []
    vPairList = analyzer.getVerticalPairs(score, partNum1, partNum2)
    for vPair in vPairList:
        if vPair is not None:
            # use isOnbeat(note) from vlChecker
            if isOnbeat(vPair[0]) and isOnbeat(vPair[1]):
                onbeatDyads.append(vPair)
    return onbeatDyads



def isOnbeatVerticality(verticality):
    """Tests whether a verticality is initiated on the downbeat."""
    # does not work!!!
    vnotes = verticality.getObjectsByClass('Note')
    isOnbeat = True
    print(verticality.offset)
    for note in vnotes:
        print(note)
        if note.beat != 1.0:
            vOnbeat = False
            break
    return isOnbeat


# based on context.assignSpecies(part)
def assignSpeciesToParts(score):
    for part in score.parts:
        if not part.species:
            context.assignSpecies(part)


def getFullSonorities(vertList):
    """Given a list of all the verticalities,
    select only those that have a note in every part
    """
    texture = len(vertList[-1].objects)
    vertList = [vert for vert in vertList
                if len(vert.objects) == texture]
    return vertList


def getSonorityRating(score, beatPosition=None, sonorityType=None,
                      outerVoicesOnly=True, includeTerminals=False):
    """
    Report the percentage of a given sonority type in the
    list of full-voiced verticalities.
    Valid options:
        beatPosition: ['on', 'off', None]
        sonorityType: ['imperfect', 'perfect', 'dissonant',
                       'unison', 'octave', None]
        outerVoicesOnly: [True, False]
        includeTerminals: [True, False]
    """
    vertList = getFullSonorities(getAllVerticalities(score))

    # get verts by beat position
    if beatPosition == 'on':
        vl = getOnbeatVertList(vertList)
    elif beatPosition == 'off':
        vl = getOffbeatVertList(vertList)
    else:
        vl = vertList

    # Trim list if terminals excluded.
    if not includeTerminals:
        vl = vl[1:-1]

    # Count the number of parts in the final verticality,
    # as a reliable measure of the basic texture.
    texture = len(vertList[-1].objects)

    # Select part pairs based on outer voice parameter.
    if not outerVoicesOnly:
        partPairs = getBassUpperPairs(score)
    elif outerVoicesOnly:
        partPairs = [[texture-1, 0]]  # [bass, top]

    # Now count all the relevant sonorities if the match the given type.
    if sonorityType is None:
        print('cannot evaluate for all sonority types at once, '
              'so choose one and try again')
        return
    # Initialize the counter and divisor.
    sonorityCount = 0
    # Set list length to nonzero number.
    totl = len(vl) * len(partPairs)
    if totl == 0:
        totl = 1
    # Count the relevant sonorites.
    for pair in partPairs:
        bassPartNum = pair[0]
        topPartNum = pair[1]
        for vert in vl:
            bassPart = vert.getObjectsByPart(bassPartNum,
                                             classFilterList='Note')
            topPart = vert.getObjectsByPart(topPartNum,
                                            classFilterList='Note')
            if (sonorityType == 'imperfect'
               and isImperfectVerticalConsonance(bassPart, topPart)):
                sonorityCount += 1
            elif (sonorityType == 'perfect'
                  and isPerfectVerticalConsonance(bassPart, topPart)):
                sonorityCount += 1
            elif (sonorityType == 'dissonant'
                  and isVerticalDissonance(bassPart, topPart)):
                sonorityCount += 1
            elif (sonorityType == 'unison'
                  and isUnison(bassPart, topPart)):
                sonorityCount += 1
            elif (sonorityType == 'octave'
                  and isOctave(bassPart, topPart)):
                sonorityCount += 1
    return sonorityCount/totl
#    return '{:.1%}'.format(sonorityCount/totl)


def getDensityRating(score, beatPosition=None,
                     densityType=None, includeTerminals=False):
    """
    Report the percentage of a given density type in the list of
    full-voiced verticalities.
    Valid options:
        beatPosition: ['on', 'off', None]
        densityType: ['pitch', 'pitch class', None]
        includeTerminals: [True, False]
    """
    vertList = getFullSonorities(getAllVerticalities(score))

    # get verts by beat position
    if beatPosition == 'on':
        vl = getOnbeatVertList(vertList)
    elif beatPosition == 'off':
        vl = getOffbeatVertList(vertList)
    else:
        vl = vertList

    # trim list if terminals excluded
    if not includeTerminals:
        vl = vl[1:-1]

    # get the appropriate density list
    dl = getDensityList(vl, densityType=densityType)
    totl = len(dl)
    if totl == 0:
        totl = 1
    density = 0
    for d in dl:
        density = density + d
    return '{:.1%}'.format(density/totl)

#     for vPair in vPairList:
#         if vPair != None:
#             if isUnison(vPair[0],vPair[1]):
#                 uCount += 1
#     if uCount > unisonLimit:
#         error='The number of unisons is '+ str(uCount)
#                + ', which exceeds the limit of ' +\
#                 str(unisonLimit) + '.'
#         prefErrors.append(error)



# -----------------------------------------------------------------------------


if __name__ == '__main__':
    pass
#    source='../tests/TestScoresXML/FirstSpecies01.musicxml'
#    source='../tests/TestScoresXML/FirstSpecies02.musicxml'
#    source='../tests/TestScoresXML/FirstSpecies03.musicxml'
#    source='../tests/TestScoresXML/FirstSpecies04.musicxml'
#    source='../tests/TestScoresXML/FirstSpecies10.musicxml'
#    source='../tests/TestScoresXML/SecondSpecies10.musicxml'
#    source='../tests/TestScoresXML/SecondSpecies20.musicxml'
#    source='../tests/TestScoresXML/SecondSpecies21.musicxml'
#    source='../tests/TestScoresXML/SecondSpecies22.musicxml'
#    source = '../tests/TestScoresXML/ThirdSpecies01.musicxml'
#    source='../tests/TestScoresXML/FourthSpecies01.musicxml'
#    source='../tests/TestScoresXML/FourthSpecies20.musicxml'
#    source='../tests/TestScoresXML/FourthSpecies21.musicxml'
#    source='../tests/TestScoresXML/FourthSpecies22.musicxml'
#    source='../examples/corpus/Westergaard075f.musicxml'
#    source='../examples/corpus/Westergaard075g.musicxml'
#    source='../examples/corpus/Westergaard121a.musicxml'
#     source='../tests/TestScoresXML/2020_07_24T20_59_43_778Z.musicxml'
#     print('\n'.join(pferrors))
# -----------------------------------------------------------------------------
# eof
