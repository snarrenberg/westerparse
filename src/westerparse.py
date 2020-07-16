# ------------------------------------------------------------------------------
# Name:        westerparse.py
# Purpose:     Evaluating Westergaardian species counterpoint
#
# Author:      Robert Snarrenberg
# Copyright:   (c) 2020 by Robert Snarrenberg
# License:     BSD, see license.txt
# ------------------------------------------------------------------------------
'''
WesterParse
===========

This is the main program script.

WesterParse allows a user to test a species counterpoint exercise
for conformity with the rules of line construction and voice leading
laid out in Peter Westergaard's book, *An Introduction to Tonal Theory*
(New York, 1975).

WesterParse imports a musicxml file, converts it to a music21 stream,
determines a key (unless specified by the user), and then evaluates
the linear syntax or the counterpoint.

The main scripts are:

>>> evaluateLines(source)
>>> evaluateCounterpoint(source)

For more information on how to use these scripts, see the User's Guide.
'''

from music21 import *
import parser
import vlChecker
from context import *
from utilities import pairwise
import time

# -----------------------------------------------------------------------------
# EXCEPTION HANDLERS
# -----------------------------------------------------------------------------


# -----------------------------------------------------------------------------
# MAIN SCRIPTS
# -----------------------------------------------------------------------------

def evaluateLines(source,
                  show=None,
                  partSelection=None,
                  partLineType=None,
                  report=False,
                  **keywords):
    '''
    Determines whether a line is generable using Westergaard's rules.
    '''
    clearLogfile('logfile.txt')
    if partLineType == 'any' or '':
        partLineType = None
    try:
        cxt = makeGlobalContext(source, **keywords)
    except EvaluationException as fce:
        fce.show()
        return
    try:
        parseContext(cxt, show, partSelection, partLineType)
        if show is None or report is True:
            print(cxt.parseReport)
    except EvaluationException as fce:
        fce.show()


def evaluateCounterpoint(source,
                         report=True,
                         sonorityCheck=False,
                         **keywords):
    '''
    Determines whether the voice leading conforms to Westergaard's rules.
    '''
    clearLogfile('logfile.txt')
    try:
        cxt = makeGlobalContext(source, **keywords)
    except EvaluationException as fce:
        fce.show()
        return
    try:
        if len(cxt.parts) == 1:
            raise ContextError(
                  'Context Error: The composition is only a single line. '
                  'There is no voice-leading to check.')
    except ContextError as ce:
        ce.logerror()
    try:
        if len(cxt.parts) == 1:
            raise EvaluationException
    except EvaluationException as ee:
        ee.show()
    else:
        vlChecker.vlErrors = []
        vlChecker.checkCounterpoint(cxt, report=True)

# -----------------------------------------------------------------------------
# HELPER SCRIPTS
# -----------------------------------------------------------------------------


def makeGlobalContext(source, **keywords):
    '''
    Import a musicxml file and convert to music21 Stream.
    Then create a :py:class:`~context.GlobalContext`.
    '''
    s = converter.parse(source)
    # create a global context object and prep for evaluation
    # if errors encountered, script will exit and report
    gxt = GlobalContext(s, **keywords)
    return gxt


def makeLocalContext(cxt, cxtOn, cxtOff, cxtHarmony):
    '''
    Create a local context given a start and stop offset
    in an enclosing Context.
    [Not functional.]
    '''
    locCxt = cxt.getElementsByOffset(cxtOn,
                                     cxtOff,
                                     includeEndBoundary=True,
                                     mustFinishInSpan=False,
                                     mustBeginInSpan=True,
                                     includeElementsThatEndAtStart=False,
                                     classList=None)
    locCxt.harmony = cxtHarmony
    return locCxt


def displaySourceAsPng(source):
    '''
    Use MuseScore to create a .png image of a musicxml source file.
    '''
    cxt = converter.parse(source)
    timestamp = str(time.time())
    filename = 'tempimages/' + 'display_output_' + timestamp + '.xml'
    cxt.write('musicxml.png', fp=filename)


def parseContext(context,
                 show=None,
                 partSelection=None,
                 partLineType=None,
                 report=False):
    '''
    This function runs the parse on each line of a
    context using :py:func:`parsePart`.
    A dictionary is used to collect error reports from the parser;
    this is used to produce an error report.
    A separate report is created for successful parses.
    If the user has elected to display the results, the function selects
    the preferred interpretations and displays them.
    '''
    # dictionary for collecting error reports
    # primary keys: part names
    # secondary keys: 'parser errors', 'primary', 'bass'
    context.errorsDict = {}
    for part in context.parts:
        context.errorsDict[part.name] = {}

    # determine which parts to parse
    # and return a slice of context.parts
    def validatePartSelection(context, partSelection):
        if partSelection is not None:
            try:
               context.parts[partSelection]
            except IndexError:
                if len(context.parts) == 1:
                    pts = ' part'
                else:
                    pts = ' parts'
                raise ContextError(
                    'Context Error: The composition has only '
                    + str(len(context.parts)) + pts
                    + ', so the part selection must fall in the range of 0-'
                    + str(len(context.parts)-1) + '. Hence the selection of part '
                    + str(partSelection) + ' is invalid.')
            else:
                if partSelection >= 0:
                    partsSelected = context.parts[partSelection:partSelection+1]
                else:
                    partsSelected = context.parts[partSelection::partSelection-1]
        elif len(context.parts) == 1:
            partsSelected = context.parts[0:1]
        elif partSelection is None:
            partsSelected = context.parts
        return partsSelected
        
    try:
        partsForParsing = validatePartSelection(context, partSelection) 
    except ContextError as ce:
        ce.logerror()
        raise EvaluationException
    # run the parser and collect errors
    for part in partsForParsing:
        # set the part's lineType if given by the user
        if partLineType:
            part.lineType = partLineType
        else:
            part.lineType = None
        # parse the selected part
        parsePart(part, context)
        # collect errors
        if part.errors:
            context.errorsDict[part.name]['parser errors'] = part.errors
        if part.typeErrorsDict:
            for key, value in part.typeErrorsDict.items():
                context.errorsDict[part.name][key] = value
    # continue and report/show results
    generableParts = 0
    generableContext = False
    if partSelection is None:
        for part in context.parts:
            if part.isPrimary or part.isBass or part.isGeneric:
                generableParts += 1
        if generableParts == len(context.parts):
            generableContext = True
    elif partSelection is not None:
        rules = [context.parts[partSelection].isPrimary,
                 context.parts[partSelection].isBass,
                 context.parts[partSelection].isGeneric]
        if any(rules):
            generableContext = True

    # create optional parse report for user
    # and required error report if errors arise
    def createParseReport():
        # base string for reporting parse results
        context.parseReport = 'PARSE REPORT'

        # gather information on the key to report to the user
        if context.keyFromUser == True:
            result = ('Key supplied by user: ' + context.key.nameString)
            context.parseReport = context.parseReport + '\n' + result
        else:
            result = ('Key inferred by program: ' + context.key.nameString)
            context.parseReport = context.parseReport + '\n' + result

        if generableContext is True:
            if partSelection is not None or len(context.parts) == 1:
                if partSelection is not None:
                    part = context.parts[partSelection]
                else:
                    part = context.parts[0]
                if partLineType is None:
                    if part.isPrimary and part.isBass:
                        result = ('The line is generable as both '
                                  'a primary line and a bass line.')
                    elif not part.isPrimary and part.isBass:
                        result = ('The line is generable as a bass '
                                  'line but not as a primary line.')
                    elif part.isPrimary and not part.isBass:
                        result = ('The line is generable as a primary '
                                  'line but not as a bass line.')
                    if not part.isPrimary and not part.isBass and part.isGeneric:
                        result = ('The line is generable only as a generic line.')
                elif partLineType is not None:
                    if partLineType == 'primary' and part.isPrimary:
                        result = ('The line is generable as a primary line.')
                    elif partLineType == 'bass' and part.isBass:
                        result = ('The line is generable as a bass line.')
                    elif partLineType == 'generic' and part.isGeneric:
                        result = ('The line is generable as a generic line.')
                    # ERRORS
                    else:
                        error = ('The line is not generable as the '
                                 'selected type: ' + partLineType)
                        error = (error + '\nThe following linear '
                                 'errors were found:')
                        if context.errorsDict[part.name][partLineType]:
                            for err in context.errorsDict[part.name][partLineType]:
                                error = error + '\n\t\t' + str(err)
                        raise ContextError(error)
                # update parse report if no errors found
                context.parseReport = context.parseReport + '\n' + result

            elif partSelection is None and len(context.parts) > 1:
                upperPrimary = False
                subsidiaryUpperLines = []  # by part name
                lowerBass = False
                for part in context.parts[0:-1]:
                    if part.isPrimary:
                        upperPrimary = True
                    else:
                        subsidiaryUpperLines.append(part.name)
                if context.parts[-1].isBass:
                    lowerBass = True
                if upperPrimary and lowerBass:
                    if len(context.parts) == 2:
                        result = ('The upper line is generable as a '
                                  'primary line. \nThe lower line '
                                  'is generable as a bass line.')
                    else:
                        result = ('At least one upper line is generable '
                                  'as a primary line. \nThe lower line '
                                  'is generable as a bass line.')
                # ERRORS
                elif not upperPrimary and lowerBass:
                    if len(context.parts) == 2:
                        error = ('\tThe upper line is not generable '
                                 'as a primary line. \nBut the lower '
                                 'line is generable as a bass line.')
                    else:
                        error = ('\tNo upper line is generable as a '
                                 'primary line. \nBut the lower line '
                                 'is generable as a bass line.')
                    for sul in subsidiaryUpperLines:
                        if context.errorsDict[sul]:
                            error = (error + '\n\tThe following linear '
                                     'errors were found in ' + sul + ':')
                            for err in context.errorsDict[sul]['primary']:
                                error = error + '\n\t\t\t' + str(err)
                    raise ContextError(error)
                elif upperPrimary and not lowerBass:
                    if len(context.parts) == 2:
                        error = ('\tThe upper line is generable as a '
                                 'primary line. \nBut the lower line '
                                 'is not generable as a bass line.')
                    else:
                        error = ('\tAt least one upper line is generable '
                                 'as a primary line. \nBut the lower line '
                                 'is not generable as a bass line.')
                    bln = context.parts[-1].name
                    if context.errorsDict[bln]:
                        error = (error + '\n\tThe following linear '
                                 'errors were found in the bass line:')
                        for err in context.errorsDict[bln]['bass']:
                            error = error + '\n\t\t\t' + str(err)
                    raise ContextError(error)
                elif not upperPrimary and not lowerBass:
                    if len(context.parts) == 2:
                        error = ('\tThe upper line is not generable as a '
                                 'primary line. \nNor is the lower line '
                                 'generable as a bass line.')
                    else:
                        error = ('\tNo upper line is generable as '
                                 'a primary line. \nNor is the lower '
                                 'line generable as a bass line.')
                    for part in context.parts[:-1]:
                        if context.errorsDict[part.name]:
                            error = (error + '\n\tThe following linear '
                                     'errors were found in ' + part.name + ':')
                            for err in context.errorsDict[sul]['primary']:
                                error = error + '\n\t\t\t' + str(err)
                    bln = context.parts[-1].name
                    if context.errorsDict[bln]:
                        error = (error + '\n\tThe following linear errors '
                                 'were found in the bass line:')
                        for err in context.errorsDict[bln]['bass']:
                            error = error + '\n\t\t\t' + str(err)
                    raise ContextError(error)
                # update parse report if no errors found
                context.parseReport = context.parseReport + '\n' + result

        elif generableContext is False:
            # get header and key information from parse report
            error = context.parseReport + '\n' + 'Line Parsing Errors'
            if len(partsForParsing) == 1:
                part = partsForParsing[0]
                error = (error + '\n\tThe following linear errors were '
                         'found when attempting to interpret the line:')
                try:
                    context.errorsDict[part.name]['parser errors']
                except KeyError:
                    pass
                else:
                    for err in context.errorsDict[part.name]['parser errors']:
                        error = error + '\n\t\t\t' + str(err)
                try:
                    context.errorsDict[part.name]['primary']
                except KeyError:
                    pass
                else:
                    for err in context.errorsDict[part.name]['primary']:
                        error = error + '\n\t\t\t' + str(err)
                try:
                    context.errorsDict[part.name]['bass']
                except KeyError:
                    pass
                else:
                    for err in context.errorsDict[part.name]['bass']:
                        error = error + '\n\t\t\t' + str(err)
                raise ContextError(error)
            else:
                for part in context.parts[:-1]:
                    if context.errorsDict[part.name] == {} and part.isPrimary:
                        error = (error + '\n\t' + part.name +
                                 ' is generable as a primary line.')
                    elif (context.errorsDict[part.name] == {}
                          and not part.isPrimary and part.isGeneric):
                        error = (error + '\n\t' + part.name +
                                 ' is generable as a generic line.')
                    else:
                        error = (error + '\n\t' + part.name +
                                 ' is not generable. '
                                 'The following errors were found:')
                    try:
                        context.errorsDict[part.name]['parser errors']
                    except KeyError:
                        pass
                    else:
                        for err in context.errorsDict[part.name]['parser errors']:
                            error = error + '\n\t\t\t' + str(err)
                    try:
                        context.errorsDict[part.name]['primary']
                    except KeyError:
                        pass
                    else:
                        for err in context.errorsDict[part.name]['primary']:
                            error = error + '\n\t\t\t' + str(err)
                for part in context.parts[-1:]:
                    if context.errorsDict[part.name] == {} and part.isBass:
                        error = (error + '\n\t' + part.name +
                                 ' is generable as a bass line.')
                    else:
                        error = (error + '\n\t' + part.name +
                                 ' is not generable. '
                                 'The following errors were found:')
                    try:
                        context.errorsDict[part.name]['parser errors']
                    except KeyError:
                        pass
                    else:
                        for err in context.errorsDict[part.name]['parser errors']:
                            error = error + '\n\t\t\t' + str(err)
                    try:
                        context.errorsDict[part.name]['bass']
                    except KeyError:
                        pass
                    else:
                        for err in context.errorsDict[part.name]['bass']:
                            error = error + '\n\t\t\t' + str(err)

            raise ContextError(error)

    try:
        createParseReport()
    except ContextError as ce:
        ce.logerror()
        raise EvaluationException
    else:
        pass

        if show is not None:
            # preferences currently only work for two-part counterpoint
            if 1 < len(context.parts) < 3 and partSelection is None:
                selectedPreferredParseSets(context, show)
            else:
                showInterpretations(context, show, partSelection, partLineType)


def parsePart(part, context):
    '''
    Given a part, create a parser (:py:class:`~parser.Parser`) for it and
    collect the results. Determine whether the line is generable as a primary,
    bass, or generic line. Compile a list of ways the line can be generated
    for each line type, if at all. Collect a list of parsing errors.
    '''
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
    part.typeErrorsDict = partParser.typeErrorsDict


def selectedPreferredParseSets(context, show):
    '''After parsing the individual parts, select sets of parses
    based on Westergaard preference rules, trying to negotiate best match
    between global structures in the parts. [This currently works
    only for two-part counterpoint.]'''

    # TODO currently only works for two-part counterpoint

    # TODO need to refine the preferences substantially
    if len(context.parts) > 1:
        # select uppermost part that isPrimary as the primaryPart
        # this is arbitrary
        primPart = None
        for part in context.parts[:-1]:
            if part.isPrimary:
                primPart = part
                break
        # select lowest part as the bassPart
        bassPart = context.parts[-1]

        primaryS3Finals = [i.S3Final for i in primPart.interpretations['primary']]
        bassS3s = [i.S3Index for i in bassPart.interpretations['bass']]
        preferredGlobals = []
        domOffsetDiffList = []  # structural Dominant Offset Differences List
        lowestDifference = 100
        for interpPrimary in primPart.interpretations['primary']:
            for interpBass in bassPart.interpretations['bass']:
                domOffsetDiff = (primPart.recurse().flat.notes[interpPrimary.S3Final].offset - bassPart.recurse().flat.notes[interpBass.S3Index].offset)
                if abs(domOffsetDiff) < lowestDifference:
                    lowestDifference = domOffsetDiff
                domOffsetDiffList.append((domOffsetDiff, (interpPrimary, interpBass)))
#                    if interpBass.S3Index == interpPrimary.S3Final:
#                        preferredGlobals.append((interpPrimary, interpBass))
        for pair in domOffsetDiffList:
            if abs(pair[0]) == abs(lowestDifference):
                preferredGlobals.append(pair[1])
        for pair in preferredGlobals:
            primPart.Pinterps = [pair[0]]
            bassPart.Binterps = [pair[1]]
            showInterpretations(context, show)
    elif len(context.parts) == 1:
        showInterpretations(context, show)


def showInterpretations(context, show, partSelection=None, partLineType=None):
    '''
    Build interpretations for the context, gathering information from
    the parses of each line.
    '''

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
            filename = ('/home/spenteco/1/snarrenberg/parses_from_context/'
                        + 'parser_output_' + timestamp + '.musicxml')
            content.write('musicxml', filename)
            print(filename)
        elif show == 'writeToLocal':
            timestamp = str(time.time())
            filename = ('parses_from_context/'
                        + 'parser_output_' + timestamp + '.musicxml')
            content.write('musicxml', filename)
            print(filename)
        elif show == 'writeToPng':
            timestamp = str(time.time())
            filename = ('tempimages/'
                        + 'parser_output_' + timestamp + '.xml')
            content.write('musicxml.png', fp=filename)
        elif show == 'showWestergaardParse':
            pass
            # create a function for displaying layered representation of
            # a parsed line, for one line only

    if partSelection is not None:
        part = context.parts[partSelection]
        if partLineType == 'primary' and part.isPrimary:
            for P in part.Pinterps:
                buildInterpretation(P)
                selectOutput(part, show)
        elif partLineType == 'bass' and part.isBass:
            for B in part.Binterps:
                buildInterpretation(B)
                selectOutput(part, show)
        elif partLineType == 'generic' and part.isGeneric:
            for G in part.Ginterps:
                buildInterpretation(G)
                selectOutput(part, show)

    elif len(context.parts) == 1 and partLineType is None:
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

    elif len(context.parts) == 1 and partLineType:
        part = context.parts[0]
        if partLineType == 'primary' and part.Pinterps:
            for P in part.Pinterps:
                buildInterpretation(P)
                selectOutput(part, show)
        elif partLineType == 'bass' and part.Binterps:
            for B in part.Binterps:
                buildInterpretation(B)
                selectOutput(part, show)
        elif partLineType == 'generic' and part.Ginterps:
            for G in part.Ginterps:
                buildInterpretation(G)
                selectOutput(part, show)

    elif len(context.parts) == 2 and partSelection is None:
        # TODO transfer this testing to the verify function
        upperPart = context.parts[0]
        lowerPart = context.parts[1]
        for P in upperPart.Pinterps:
            buildInterpretation(P)
            for B in lowerPart.Binterps:
                buildInterpretation(B)
                selectOutput(context.score, show)
                time.sleep(2)

    elif len(context.parts) == 3 and partSelection is None:
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

        for U in upperPartPreferredInterps:
            buildInterpretation(U)
            for I in innerPartPreferredInterps:
                buildInterpretation(I)
                for B in lowerPart.Binterps:
                    buildInterpretation(B)
                    selectOutput(context.score, show)
                    time.sleep(2)

    elif len(context.parts) > 3:
        error = 'Not yet able to display counterpoint in four or more parts.'
        raise ContextError(error)
    return

# -----------------------------------------------------------------------------
# OPERATIONAL SCRIPTS FOR PARSING DISPLAY
# -----------------------------------------------------------------------------


def gatherArcs(source, arcs):
    '''
    Given a fully parsed line (an interpretation), sort through the arcs and
    create a music21 spanner (tie/slur) to represent each arc.
    '''
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
    '''
    The function that actually converts an arc into a slur.
    '''
    # source is a Part in the input Score
    if len(arc) == 2:
        slurStyle = 'dashed'
    else:
        slurStyle = 'solid'
    thisSlur = spanner.Slur()
    thisSlur.lineType = slurStyle
    source.insert(0, thisSlur)
    for ind in arc:
        obj = source.recurse().notes[ind]
        thisSlur.addSpannedElements(obj)


def assignRules(source, rules):
    '''
    Given a fully parsed line (an interpretation), add a lyric to each
    note to show the syntactic rule that generates the note.
    Also assigns the color
    blue to notes generated by a rule of basic structure.
    '''
    # source is a Part in the input Score
    ruleLabels = rules
    for index, elem in enumerate(source.recurse().notes):
        for rule in ruleLabels:
            if index == rule[0]:
                elem.lyric = rule[1]
                if elem.lyric is not None and elem.lyric[0] == 'S':
                    elem.style.color = 'blue'
                else:
                    elem.style.color = 'black'
            else:
                pass


def assignParentheses(source, parentheses):
    '''
    Adds parentheses around notes generated as insertions. [This aspect
    of syntax representation cannot be fully implemented at this time,
    because musicxml only allows parentheses to be assigned in pairs,
    whereas syntax coding requires
    the ability to assign left and right parentheses separately.]
    '''
    # source is a Part in the input Score
    parentheses = parentheses
    for index, elem in enumerate(source.recurse().notes):
        for parens in parentheses:
            if index == parens[0]:
                elem.noteheadParenthesis = parens[1]
            else:
                pass


# -----------------------------------------------------------------------------

if __name__ == "__main__":
    pass

    source = '../TestScoresXML/Primary06.musicxml'
    evaluateLines(source)

# -----------------------------------------------------------------------------
# eof
