#-------------------------------------------------------------------------------
# Name:         context.py
# Purpose:      Framework for analyzing species counterpoint
#
# Author:      Robert Snarrenberg
#-------------------------------------------------------------------------------
'''Contextualizer converts a musicxml source file, 
segments into tonal contexts, and runs the KeyFinder, Parser, and VLChecker machines'''

from music21 import *
import itertools
from csd import *
from rule import *
from dependency import *
from consecutions import *
import parser
import time
import vlChecker
import keyFinder

 
def evaluateLines(source, show, partSelection=None, partLineType=None, **kwargs):
    
    cxt = makeGlobalContext(source, **kwargs)
    parseContext(cxt, show, partSelection, partLineType)
        
def evaluateCounterpoint(source, report=True, **kwargs):
    cxt = makeGlobalContext(source, **kwargs)
    if len(cxt.parts) == 1:
        print('The composition is only a single line. There is no voice-leading to check.')
        return False
    else:
        vlReport = vlChecker.checkCounterpoint(cxt, report=True)
        if vlReport = []:       

def makeGlobalContext(source, **kwargs):
    # import a musicxml file and convert to music21 Stream
    cxt = converter.parse(source)
    gxt = GlobalContext(cxt, **kwargs)
    return gxt

def makeLocalContext(cxt, cxtOn, cxtOff, cxtHarmony):
    # create a context given a start and stop offset in an enclosing Context
    locCxt = cxt.getElementsByOffset(cxtOn, cxtOff, includeEndBoundary=True, 
        mustFinishInSpan=False, mustBeginInSpan=True, includeElementsThatEndAtStart=False, 
        classList=None)
    locCxt.harmony = cxtHarmony
    return locCxt


# TODO: figure out how to accommodate tonal ambiguity: make a global context for each option?

class Context():
    '''An object for representing a span of a composition 
    and for storing objects that represent local spans, thus
    permitting recursive interpretive assessment'''

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
    '''An object for representing a significant span of a composition 
    and for storing objects that represent significant spans, thus
    permitting recursive interpretive assessment'''

    def __init__(self, score, **kwargs):
        self.score = score
        self.parts = self.score.parts
        self.score.measures = len(self.parts[0].getElementsByClass('Measure'))
        self.errors = []
        self.score.errors = []
        
        # to parts: assign numbers, rhythmic species, error lists to part
        # to notes: assign consecutions, rules, dependencies, and indexes
        self.setupPartsGeneral()
        
        # accept key from user if provided, else infer one from the parts
        self.setupTonalityGeneral(**kwargs)
        # to parts: assign tonic, mode, scale
        # to notes: assign csds
        self.setupPartsTonality()

        # prepare local contexts for harmonic analysis
        self.localContexts = {}

# TODO move harmonic species span stuff to a different place
        if kwargs.get('harmonicSpecies'):
            self.harmonicSpecies = kwargs['harmonicSpecies']
        else:
            self.harmonicSpecies = False
        if kwargs.get('harmonicSpecies') == True:
            offPre = kwargs['offsetPredominant']
            offDom = kwargs['offsetDominant']
            offClosTon = kwargs['offsetClosingTonic']
            if offPre == None:
                initialTonicSpan = makeLocalContext(cxt.score, 0.0, offPre, 'initial tonic')
                predominantSpan = makeLocalContext(cxt.score, offPre, offDom, 'predominant')
            else:
                initialTonicSpan = makeLocalContext(cxt.score, 0.0, offDom, 'initial tonic')
                predominantSpan = None
            dominantSpan = makeLocalContext(cxt.score, offDom, offClosTon, 'dominant')
            closingTonicSpan = makeLocalContext(cxt.score, offClosTon, offClosTon+4.0, 'closing tonic')


        # collect dictionary of local harmonies for use in parsing third species 
        self.getLocalOnbeatHarmonies()
        
        # TODO local contexts aren't yet used by the parser
#        self.setupLocalContexts()
    def __repr__(self):
        return('Global context')

    def setupPartsGeneral(self):
        # set part properties: part number, rhythmic species
        for num,part in enumerate(self.parts):
            # part number
            part.partNum = num
            part.name = 'Part ' + str(num+1)
            part.errors = []
            
            # part rhythmic species
            part.species = assignSpecies(part)
            
            # set up note consecution relations, from consecutions.py
            getConsecutions(part)

            # set up note properties used in parsing
            for indx, note in enumerate(part.recurse().notes):
                # assigns a Rule object to each Note
                note.rule = Rule()
                # assigns a Dependency object to each Note
                note.dependency = Dependency()
                # fix the order position of the note in the line
                note.index = indx

            # if creation of the context fails, report and exit
            if self.errors:
                print('Global Context Error Report')
                for error in self.errors: print('\t', error)

    def setupTonalityGeneral(self, **kwargs):
        # setup key, using information provided by user or inferred from parts
        knote = kwargs.get('keynote')
        kmode = kwargs.get('mode')
        kvalidate = kwargs.get('validateKey')
        if not kvalidate: 
            kvalidate == True
        if knote and kmode: # need to add a data validity check
            if knote != None and kmode != None:
                self.key = key.Key(tonic=knote, mode=kmode)
                self.keyFromUser = True
        else:
            self.key = keyFinder.findKey(self.score)
            self.keyFromUser = False
        # report errors is user-defined key is problematic
        if knote and kmode and kvalidate==True:
            e = keyFinder.reportKeyFinderLineErrorsGivenKey(self.parts[0], knote, kmode)
            if e != []:
                print('Key finder errors. Given key =', knote, kmode)
                for error in e:
                    print('\t', error)
# TODO replace exit()
                exit()
        else:
            pass

        if self.score.errors:
            print('Global Context Error Report')
            for error in self.score.errors: print('\t', error)
# TODO find a solution that does not require the exit() command
            exit()    
        # create name string for key
        if self.key.getTonic().accidental != None:
            keyAccidental = '-' + self.key.getTonic().accidental.name
        else: keyAccidental = ''
        self.key.nameString = self.key.getTonic().step + keyAccidental + ' ' + self.key.mode
                
    def setupPartsTonality(self):
        # set part properties: part number, tonic degree, rhythmic species, scale degrees
        for num,part in enumerate(self.parts):
            # part tonic = lowest tonic degree in the line's register
            # find tonic pitch class
            ton = self.key.getTonic()
            ton.octave = 0
            partAmb = analysis.discrete.Ambitus()
            pitchMin, pitchMax = partAmb.getPitchSpan(part)
            # and search for the lowest representative within the line
            part.tonic = None
            while ton.octave < 8:
                if pitchMin <= ton <= pitchMax:
                    part.tonic = ton
                    break
                ton.octave += 1
            if part.tonic == None:                
                ton.octave = 8
                while ton.octave > 0:
                    if pitchMin > ton:
                        part.tonic = ton
                        break
                    ton.octave -= 1

            # assign scale to part based on register of tonic degree
            if self.key.mode == 'major':
                part.mode = self.key.mode
                part.scale = scale.MajorScale(part.tonic)
            elif self.key.mode == 'minor':
                part.mode = self.key.mode
                part.scale = scale.MelodicMinorScale(part.tonic)

            # infer principal harmonic triads
            part.tonicTriad = chord.Chord([part.scale.pitchFromDegree(1), 
                            part.scale.pitchFromDegree(3), 
                            part.scale.pitchFromDegree(5)])
            part.dominantTriad = chord.Chord([part.scale.pitchFromDegree(5), 
                            part.scale.pitchFromDegree(7, direction='ascending'), 
                            part.scale.pitchFromDegree(2)])
            part.predominantTriad = chord.Chord([part.scale.pitchFromDegree(2), 
                            part.scale.pitchFromDegree(4), 
                            part.scale.pitchFromDegree(6, direction='descending')])

            # assign scale degrees to notes
            for indx, note in enumerate(part.recurse().notes):
                # create a ConcreteScaleDegree object for each note
                note.csd = ConcreteScaleDegree(note.pitch, part.scale)
                if note.csd.errors:
                    self.errors.append(note.csd.errors)

            # if creation of the context fails, report and exit
            if self.errors:
                print('Global Context Error Report')
                for error in self.errors: print('\t', error)

    # for parsing third or fifth species and for counterpoint analysis, collect dictionary of onbeat harmonies
    def getLocalOnbeatHarmonies(self):
        # for third and fifth species counterpoint, use the measures to define the local context timespans
        self.localHarmonyDict = {}
        # use context.measureOffsetMap
        measureOffsets = self.score.measureOffsetMap() # get the offset for each downbeat
        offsetSpans = pairwise(measureOffsets) # get the start/stop offsets for each measure
        # include the span of the final bar
        measureSpan = offsetSpans[0][1] - offsetSpans[0][0]
        finalSpanOnset = offsetSpans[-1][1]
        finalSpan = (finalSpanOnset, finalSpanOnset+measureSpan)
        offsetSpans.append(finalSpan)
        # gather the content of each local context 
        for span in offsetSpans:
            offsetStart = span[0]
            offsetEnd = span[1]
            harmonicEssentials = []
#            partIdx = 0
            for part in self.score.parts:
                # get all the notes in the local span
                localPartElements = part.flat.recurse().getElementsByOffset(offsetStart, offsetEnd, 
                                includeEndBoundary=False, mustFinishInSpan=False, mustBeginInSpan=True, 
                                includeElementsThatEndAtStart=False).notesAndRests
                localPartNotes = [elem for elem in localPartElements if elem.isNote]
                # get onbeat consonances or resolutions of tied-over dissonances
                for elem in localPartElements:
                    if elem.isNote and elem.offset == offsetStart:
                        if elem.tie == None:
                            harmonicEssentials.append(elem.pitch)
                for elem in localPartElements:
                    isHarmonic = True
                    if elem.isNote and elem.offset == offsetStart and elem.tie:
                        for n in harmonicEssentials:
                            if not vlChecker.isTriadicConsonance(elem, note.Note(n)):
                                isHarmonic = False
                                break
                        if elem.isNote and isHarmonic == True:
                            harmonicEssentials.append(elem.pitch)
                        else:
                            # TODO can't just look at scale in minor because music21 uses natural minor 
                            # TODO look for actual resolution pitch that is down a step in the context
                            for resolution in localPartElements:
                                if resolution.isNote and resolution.offset > offsetStart and parser.isStepDown(elem, resolution):
    #                                resolution = part.scale.next(elem, 'descending')
                                    harmonicEssentials.append(resolution.pitch)
                self.localHarmonyDict[offsetStart] = harmonicEssentials

    def setupLocalContexts(self):
        # TODO this currently sets up measure-length contexts
        # but would also like to set up harmonic spans for harmonic species
######### TODO create a custom offset map for harmonic species and use the measure map for third species
#        offsetspans = []
#        if harmonicSpecies == True:
#            offsetSpans = []
#        else:

        measureOffsets = self.score.measureOffsetMap() # get the offset for each downbeat
        offsetSpans = pairwise(measureOffsets) # get the start/stop offsets for each measure
        # include the span of the final bar
        #measureSpan = offsetSpans[0][1] - offsetSpans[0][0]
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
            # create a new stream for each context
            cxt.score = stream.Score()
            # go through the parts of the global and add notes to corresponding local parts
            for num, part in enumerate(self.score.parts):
                newpart = stream.Part()
                newpart.species = part.species
                cxt.score.append(newpart)
                for note in part.flat.notes:
                    if offsetStart <= note.offset <= offsetEnd:
                        newpart.append(note)
                # part-related parsing initialization
#                newpart.buffer = [n for n in part.flat.notes if not n.tie or n.tie.type == 'start'] # and n.tie.type != 'stop'
#                newpart.stack = []
#                newpart.arcs = []
#                newpart.openHeads = []
#                newpart.openTransitions = []
            self.localContexts[cxt.offset] = cxt

def parseContext(context, show=None, partSelection=None, partLineType=None):
    
    # dictionary for collecting error reports
    context.errorsDict = {}

    # parse the selected part, if given and extant
    if partSelection != None and partSelection < len(context.parts):
        # set the part's lyneType if given by the user
        part = context.parts[partSelection]
        if partLineType:
            part.lineType = partLineType
        else: part.lineType = None
        # parse the selected part
        parsePart(part, context)
        if part.errors:
            context.errorsDict.update({part.name: part.errors})
            
    # otherwise generate interpretations of all the parts
    elif partSelection == None:
        texture = len(context.parts) # just need a line here to keep from doing an extra loop???
        for part in context.parts:
            part.lineType = None
            parsePart(part, context)
            if part.errors:
                context.errorsDict.update({part.name: part.errors})

    # report the information on the key to the user
    if show == None:
        if context.keyFromUser == True:
            print('Key supplied by user:', context.key.nameString)
        else:
            print('Key inferred by program:', context.key.nameString)      

# REMOVED 2020-05-27 if at least one part fails to be generable: 9 lines
# I think this is taken care of by trap below, when generableContext == False
# these lines didn't always work if partSelection != None
    # if at least one part fails to be generable, report and exit
#    partErrorsTrue = False
#    for part in context.parts:
#        if part.errors:
#            partErrorsTrue = True
#            break
#    if partErrorsTrue == True:
#        reportErrors(context)
#        exit()

    # else continue and report/show results
    generableParts = 0
    generableContext = False
    if partSelection == None:
        for part in context.parts:
            if part.interpretations:
                generableParts += 1
        if generableParts == len(context.parts):
            generableContext = True
    elif partSelection != None:
        if context.parts[partSelection].interpretations:
            generableContext = True

    # report to user if all parts are generable 
    # TODO improve reporting on generability as a specific lineType 
    if generableContext == True and partSelection == None:
        if show == None: 
            if len(context.parts) == 1:
                # TODO report on the types of valid line 
                if part.isPrimary == True and part.isBass == True:
                    print('The line is generable as both a primary line and a bass line.')
                elif part.isPrimary == False and part.isBass == True:
                    print('The line is generable as a bass line but not as a primary line.')
                elif part.isPrimary == True and part.isBass == False:
                    print('The line is generable as a primary line but not as a bass line.')
                if part.isPrimary == False and part.isBass == False and part.isGeneric == True:
                    print('The line is generable only as a generic line.')
            elif len(context.parts) == 2:
                print('Both lines are generable.')
                if context.parts[0].isPrimary == False:
                    print('But the upper line is not a primary line.')
                else:
                    print('The upper line is a primary line.')
                if context.parts[1].isBass == False:
                    print('But the lower line is not a bass line.')
                else:
                    print('The lower line is a bass line.')
#                selectedPreferredParseSets(context)
            else:
                print('All lines are generable.')
        elif show != None:
            selectedPreferredParseSets(context, show)
#            showInterpretations(context, show)
    elif generableContext == True and partSelection != None:
        if show == None and partLineType in context.parts[partSelection].interpretations.keys():
            print('The line is generable as a', partLineType, 'line.')
#        elif show != None and partLineType in context.parts[partSelection].interpretations.keys():
#            showInterpretations(context, show)
        elif show == None and partLineType == None:
            part = context.parts[partSelection]
            if part.isPrimary == True and part.isBass == True:
                print('The line is generable as both a primary line and a bass line.')
            elif part.isPrimary == False and part.isBass == True:
                print('The line is generable as a bass line but not as a primary line.')
            elif part.isPrimary == True and part.isBass == False:
                print('The line is generable as a primary line but not as a bass line.')
            if part.isPrimary == False and part.isBass == False and part.isGeneric == True:
                print('The line is generable only as a generic line.')
        elif show != None:# and partLineType == None:
            showInterpretations(context, show, partSelection, partLineType)
        else:
            print('The line is not generable as a', partLineType, 'line.')
    elif generableContext == False:
        reportErrors(context, partSelection)        

def parsePart(part, context):
    # run the Parser
    partParser = parser.Parser(part, context)
    # sort out the interpretations of the part
    part.isPrimary = partParser.isPrimary
    part.isGeneric = partParser.isGeneric
    part.isBass = partParser.isBass
    part.Pinterps = partParser.Pinterps
    part.Ginterps = partParser.Ginterps
    part.Binterps = partParser.Binterps
    part.interpretations = partParser.interpretations
    # gather errors, if any
    part.errors = partParser.errors

def selectedPreferredParseSets(context, show):
    '''After parsing the individual parses, select contrapuntal sets of parses 
    based on Westergaard preference rules'''
    
    # TODO currently only works for two-part counterpoint
    
    # negotiate best match between global structures in two parts
        
    # TODO need to refine the preferences substantially
    if len(context.parts) > 1:
        # select uppermost part that isPrimary as the primaryPart
        primaryPart = None
        for part in context.parts[:-1]:
            if part.isPrimary:
                primaryPart = part
                break
        if primaryPart == None:
            print('Failed to find a primary upper line.')
            exit
        # select lowest part as the bassPart
        bassPart = context.parts[-1]
        if not bassPart.isBass:
            print('The lowest line is not a bass line.')
            exit
        primaryS3Finals = [interp.S3Final for interp in primaryPart.interpretations['primary']]
        bassS3s = [interp.S3Index for interp in bassPart.interpretations['bass']]
        preferredGlobals = []
        structuralDominantOffsetDifferencesList = []
        lowestDifference = 100
        for interpPrimary in primaryPart.interpretations['primary']:
            for interpBass in bassPart.interpretations['bass']:
                structuralDominantOffsetDifference = (primaryPart.recurse().flat.notes[interpPrimary.S3Final].offset - bassPart.recurse().flat.notes[interpBass.S3Index].offset)
                if abs(structuralDominantOffsetDifference) < lowestDifference:
                    lowestDifference = structuralDominantOffsetDifference
                structuralDominantOffsetDifferencesList.append((structuralDominantOffsetDifference,(interpPrimary, interpBass)))
#                    if interpBass.S3Index == interpPrimary.S3Final:
#                        preferredGlobals.append((interpPrimary, interpBass))
        for pair in structuralDominantOffsetDifferencesList:
            if abs(pair[0]) == abs(lowestDifference):
                preferredGlobals.append(pair[1])
        for pair in preferredGlobals:
            primaryPart.Pinterps = [pair[0]]
            bassPart.Binterps = [pair[1]]
            showInterpretations(context, show)
    elif len(context.parts) == 1:
        showInterpretations(context, show)
        
def reportErrors(context, partSelection=None):
    print('Line Parsing Report')
    if len(context.parts) == 1 or partSelection !=None:
        if len(context.parts) == 1:
            partNum = 0
        else:
            partNum = partSelection
        part = context.parts[partNum]
        # TODO also report if the line is generable in at least some fashion
        if part.isPrimary == True: 
            print('\tThe line is generable as a primary upper line.')
        elif part.isGeneric == True: 
            print('\tThe line is generable as a generic line.')
        elif part.isBass == True: 
            print('\tThe line is generable as a bass line.')
        elif part.errors:
            for type in part.lineTypes:
                print('\tThe following linear errors were found when attempting to interpret the ' \
                    'part as a', type, 'line:')
                for error in context.errorsDict[part.name]:
                    print('\t\t', error)
    if len(context.parts) > 1 and partSelection==None:
        for part in context.parts[:-1]:
            if part.isPrimary == True: 
                print('\tPart number', part.partNum+1, 'is generable as a primary upper line.')
            elif part.isGeneric == True: 
                print('\tPart number', part.partNum+1, 'is generable as a generic line.')
            elif part.errors:
                print('\tThe following linear errors were found when attempting to interpret ' \
                     'part number', part.partNum+1, 'as an upper line:')
                for error in context.errorsDict[part.name]:
                    print('\t\t', error)
        for part in context.parts[-1:]:
            if part.isBass == True:
                print('\tPart number', part.partNum+1, 'is generable as a bass line.')
            elif part.errors:
                print('\tThe following linear errors were found when attempting to interpret ' \
                     'part number', part.partNum+1, 'as a bass line:')
                for error in context.errorsDict[part.name]:
                    print('\t\t', error)
        
def showInterpretations(context, show, partSelection=None, partLineType=None):


    def buildInterpretation(parse):
        # clean out slurs that might have been left behind by a previous parse
        slurs = context.parts[parse.partNum].recurse().getElementsByClass(spanner.Slur)
        for slur in slurs:
            context.parts[parse.partNum].remove(slur)
        # TODO remove not only slurs but also parentheses and colors

        # BUILD the interpretation 
        # arcs, rules, and parens are tied to note indexes in the line 
        # and these are then attached to notes in the source part
        gatherArcs(context.parts[parse.partNum], parse.arcs)
        assignRules(context.parts[parse.partNum], parse.ruleLabels)
        assignParentheses(context.parts[parse.partNum], parse.parentheses)    


    def selectOutput(content, show):
        if show == 'show':
            content.show()
        elif show == 'writeToServer':
            timestamp = str(time.time())
            filename = '/home/spenteco/1/snarrenberg/parses_from_context/' + 'parser_output_' + timestamp + '.musicxml'
            content.write('musicxml', filename)
            print(filename)
        elif show == 'writeToLocal':
            timestamp = str(time.time())
            filename = 'parses_from_context/' + 'parser_output_' + timestamp + '.musicxml'
            content.write('musicxml', filename)
            print(filename)
        elif show == 'showWestergaardParse':
            pass
            # create a function for displaying layered representation of a parsed line, for one line only
            
    if partSelection != None:
        part = context.parts[partSelection]
        if partLineType == 'primary' and context.parts[partSelection].isPrimary:
            for P in part.Pinterps:
                buildInterpretation(P)
                selectOutput(part, show)
        elif partLineType == 'bass' and context.parts[partSelection].isBass:
            for B in part.Binterps:
                buildInterpretation(B)
                selectOutput(part, show)
        elif partLineType == 'generic' and context.parts[partSelection].isGeneric:
            for G in part.Ginterps:
                buildInterpretation(G)
                selectOutput(part, show)
         

    elif len(context.parts) == 1 and partSelection==None:
        part = context.parts[0]
        if part.Pinterps: 
            for P in part.Pinterps:
                buildInterpretation(P)
                selectOutput(part, show)
        if part.Binterps:
            for B in part.Binterps: 
                buildInterpretation(B)
                selectOutput(part, show)
        if part.Ginterps:
            for G in part.Ginterps: 
                buildInterpretation(G)
                selectOutput(part, show)

    elif len(context.parts) == 2 and partSelection==None:
        # TODO transfer this testing to the verify function
        upperPart = context.parts[0]
        lowerPart = context.parts[1]
        if not upperPart.isPrimary or not lowerPart.isBass:
            print('Either the upper line is not a primary line or the lower line is not a bass line.')
            return
        else:
            for P in upperPart.Pinterps:
                buildInterpretation(P)
                for B in lowerPart.Binterps: 
                    buildInterpretation(B)
                    selectOutput(context.score, show)
                    time.sleep(2)        

    elif len(context.parts) == 3 and partSelection==None:
        # TODO transfer this testing to the verify function
        upperPart = context.parts[0]
        innerPart = context.parts[1]
        lowerPart = context.parts[2]

        if upperPart.isPrimary:
            upperPartPreferredInterps = upperPart.Pinterps
        else: 
            upperPartPreferredInterps = upperPart.Ginterps
        if innerPart.isPrimary:
            innerPartPreferredInterps = innerPart.Pinterps
        else: 
            innerPartPreferredInterps = innerPart.Ginterps

        if not upperPart.isPrimary and not innerPart.isPrimary:
            print('Neither of the upper lines is a primary line.')
        if not lowerPart.isBass:
            print('The lower line is not a bass line.')
            return
        else:
            for U in upperPartPreferredInterps:
                buildInterpretation(U)
                for I in innerPartPreferredInterps:
                    buildInterpretation(I)
                    for B in lowerPart.Binterps: 
                        buildInterpretation(B)
                        selectOutput(context.score, show)
                        time.sleep(2)
    elif len(context.parts) > 3:
            print('Not yet able to display counterpoint in four or more parts.')
    return

def assignSpecies(part):
    # TODO examine input measure by measure and build up the Context
    #        fifth species must be a series of contexts, each with its own species
    #        fourth species may include breaking into second species
    #        species assignment has to be input into the parser as well as vlChecker
    #            for the parser: third-species contexts have to permit local elaborations
    #            for the parser: fifth-species contexts have to permit local decorations
    meas = len(part.getElementsByClass('Measure'))
    notecount = 0
    if meas < 3:
        species = 'fifth'
        return species
    for m in range(2,meas):
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

def pairwise(span):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(span)
    next(b, None)
    zipped = zip(a, b)
    return list(zipped)

# OPERATIONAL SCRIPTS
def gatherArcs(source, arcs):
    # source is a Part in the input Score
    # sort through the arcs and create a spanner(tie/slur) for each
    tempArcs = []
    # skip duplicate arcs
    for elem in arcs:
        if elem not in tempArcs:
            tempArcs.append(elem)
    arcs = tempArcs
    # build arcs
    for arc in arcs:
        arcBuild(source, arc)
    # TODO set up separate function for the basic arc 

def arcBuild(source, arc):
    # source is a Part in the input Score
    if len(arc) == 2:
        slurStyle = 'dashed'
    else: slurStyle = 'solid'
    thisSlur = spanner.Slur()
    thisSlur.lineType = slurStyle
    source.insert(0, thisSlur)
    for ind in arc:
        obj = source.recurse().notes[ind]
        thisSlur.addSpannedElements(obj)
          
def assignRules(source, rules):
    # source is a Part in the input Score
    ruleLabels = rules
    for index,elem in enumerate(source.recurse().notes):
        for rule in ruleLabels:
            if index == rule[0]:
                elem.lyric = rule[1]
                if elem.lyric !=None and elem.lyric[0] == 'S':
                    elem.style.color = 'blue'
                else: elem.style.color = 'black'
            else:
                pass

def assignParentheses(source, parentheses):
    # source is a Part in the input Score
    parentheses = parentheses
    for index,elem in enumerate(source.recurse().notes):
        for parens in parentheses:
            if index == parens[0]:
                elem.noteheadParenthesis = parens[1]
            else:
                pass

##########################################################################################
if __name__ == "__main__":
    pass

