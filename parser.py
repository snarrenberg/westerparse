from music21 import *
from rule import *
from dependency import *

import itertools
import copy
import context

class Parser():
    '''
    A parsing tool using a Buffer and a Stack to assemble a list of syntactic units.
    The Notes of a line are read into the Buffer and then shifted onto the Stack
    where they are collected until a secondary structure (Arc) is formed.
    
    Lists of openHeads and openTransitions are maintained and cleared as secondary 
    structures are formed.
    
    A representation of the secondary structure is placed in the Arcs list as a tuple, 
    along with structural information for each element and a key for the structure
    Meanwhile, interior dependent elements are removed from the Stack, leaving structural 
    heads for subsequent attachment.
    
    TODO: If the parse fails, the location is marked 
    (with relevant elements marked "NG"? = nongenerable, color=Red) 
    and the most recent Arc is popped into a failed list 
    and its elements replaced on the Stack;
    the parser then must skip assigning a structure that matches the failed Arc 
    and instead shift more elements onto the Stack
    Parsing ends with the Buffer is empty and the Stack is cleared
        
    Procedure:
    (1) accept a part from the Contextualizer
    (2) infer the possible lineTypes if not given in advance 
    (3) parse the part for each possible lineType 
    (4) return a set of parses and errors
    '''

    def __init__(self, part, context, **kwargs):
        # set up base content
        self.part = part
        self.context = context
        self.notes = self.part.flat.notes
        # the following lists will be returned to the Part at the end of the Parser
        self.parses = [] # list of parses 
        self.interpretations = {} # syntax interpretations of the part in the context, 
            # keyed by lineType, dictionary built from self.parses
        self.parseErrorsDict = {} # syntax errors of the part in the context, 
            # currently keyed by parseLabel
            # TODO keyed by lineType? depends on how the dictionary is to be used
        self.errors = [] # syntax errors of the part in the context, identified during pre-parse
            # TODO perhaps also use if no parse is successful
        self.Pinterps = []
        self.Binterps = []
        self.Ginterps = []
        self.isPrimary = False
        self.isGeneric = False
        self.isBass = False

        
        # accept line type if already selected, otherwise infer the set of possible types
        if self.part.lineType != None:
            self.part.lineTypes = [self.part.lineType]
        else:
            self.part.lineTypes = []
            self.inferLineTypes()

        # operate the parser
        self.preParseLine()

        # TODO interrupt parser if preparsing is unsuccessful and report errors
        if self.errors:
#            print('preparse errors:', self.errors)
            return
            
        self.prepareParses()

        # TODO interrupt parser if no parses are successful and report errors
#        for key in self.parseErrorsDict:
#            print(key)

        # gather the valid interpretations of the part by lineType
        self.collectParses()
        # reduce the set of interpretations
        self.selectPreferredParses()
        
    def inferLineTypes(self):
        if self.notes[0].csd.value % 7 not in [0, 2, 4] and self.notes[-1].csd.value % 7 not in [0, 2, 4]:
            error = 'Generic structure error: The line is not bounded by tonic-triad pitches and hence not a valid tonic line.'
            return(error)
        if self.notes[0].csd.value % 7 == 0 and self.notes[-1].csd.value % 7 == 0:
            for n in self.notes[1:-1]: 
                if n.csd.value % 7 == 4 and 'bass' not in self.part.lineTypes:
                    self.part.lineTypes.append('bass') 
                if n.csd.value in [2, 4, 7] and 'primary' not in self.part.lineTypes:
                    self.part.lineTypes.append('primary')
        if self.notes[0].csd.value != 0 and self.notes[-1].csd.value == 0:
            for n in self.notes[:-1]: 
                if n.csd.value in [2, 4, 7] and 'primary' not in self.part.lineTypes:
                    self.part.lineTypes.append('primary')
        if 'primary' not in self.part.lineTypes or 'bass' not in self.part.lineTypes:
            # only use generic if the others fail
            self.part.lineTypes.append('generic')
                      
    def preParseLine(self, localNeighborsOnly=False):
        # initiate the buffer, stack, and arcs
        lineBuffer = [n for n in self.notes if not n.tie or n.tie.type == 'start'] 
        lineStack = []
        arcs = []
        # initiate the lists of heads and transitions
        openHeads = [0]
        openTransitions = []
        # set the global harmonic referents
        harmonyStart = [p for p in self.part.tonicTriad.pitches]
        harmonyEnd = [p for p in self.part.tonicTriad.pitches]
        
        if self.part.species in ['first', 'second', 'fourth'] and self.context.harmonicSpecies == False:
            # run the line scanner
            n = len(lineBuffer)
            while n > 1:
                shiftBuffer(lineStack, lineBuffer)
                n = len(lineBuffer)
                i = lineStack[-1]
                j = lineBuffer[0]
                # parse the transition i-j
                self.parseTransition(lineStack, lineBuffer, self.part, i, j, harmonyStart, 
                        harmonyEnd, openHeads, openTransitions, arcs)
## TODO reconsider whether to break upon finding first error                        
                if self.errors: break
#                print('open heads', openHeads)
#                self.showPartialParse(i, j, arcs, openHeads, openTransitions)


# TODO figure out how to parse harmonic species
        elif self.context.harmonicSpecies == True:
#            print('evaluating harmonic species')
            pass

        elif self.part.species in ['third', 'fifth']:
            # scan the global context        
            n = len(lineBuffer)
            while n > 1:
                shiftBuffer(lineStack, lineBuffer)
                n = len(lineBuffer)
                i = lineStack[-1]
                j = lineBuffer[0]
                # parse the local span
                closedLocalPitchIndexes = []
                localStart = lineStack[-1].index
                localEnd = 0
                
                if i.beat == 1.0 or i.index == 0: # and i.offset > 0.0:
                    localStack = []
                    localBuffer = []
                    localArcs = []
                    localOpenHeads = []
                    localOpenTransitions = []
                    if i.beat == 1.0 and i.index > 0: 
                        localHarmonyStart = self.context.localHarmonyDict[i.offset]
                    else: # get tonic harmony for first measure
                        localHarmonyStart = [p for p in self.part.tonicTriad.pitches]

                    # fill the local buffer up to and including the next onbeat note
                    # and set localHarmonyEnd by that note
                    for note in lineBuffer:
                        if note.beat == 1.0:
                            localBuffer.append(note)
                            localHarmonyEnd = self.context.localHarmonyDict[note.offset]
                            localEnd = note.index
                            break
                        else: localBuffer.append(note)
                    # now put i in the local buffer so i--j can be parsed
                    localBuffer.insert(0, i)
                    
                    # add onbeat note to local heads
                    localOpenHeads = [i.index]

                    # scan local context
                    ln = len(localBuffer)
                    while ln > 1:
                        shiftBuffer(localStack, localBuffer)
                        ln = len(localBuffer)
                        x = localStack[-1]
                        y = localBuffer[0]
                        self.parseTransition(localStack, localBuffer, self.part, x, y, 
                                localHarmonyStart, localHarmonyEnd, localOpenHeads, 
                                localOpenTransitions, localArcs)
## TODO reconsider whether to break upon finding first error                        
                        if self.errors: break
#                        if 14 < n < 26: self.showPartialParse(x, y, localArcs, localOpenHeads, 
#                            localOpenTransitions)
                    # collect indexes of pitches that belong to local arcs
                    if localNeighborsOnly == True:
                        localArcs = [arc for arc in localArcs if 
                            (isNeighboring(arc, self.notes) or 
                            isRepetition(arc, self.notes))]
                            
#############
#############

#                    print('local arcs before revision', localArcs)

                    # TODO rewrite, remove all pitches embedded in local arcs, 
                    # not just their inner constituents
                    # use index numbers of arc heads to find embedded pitches 
                    #         if arc[0] < n.index < arc[-1]: remove(n)
                    #         if isNeighbor or is Repetition: remove(arc[-1])
                    # shouldn't the pruning happen after extensions are attempted?
                    for arc in localArcs:
                        if arc in localArcs:
                            if ((len(arc) == 3 and isNeighboring(arc, self.notes)) or
                                    (len(arc) == 2 and isRepetition(arc, self.notes))):
                                for idx in arc[1:]:
                                    if self.notes[idx].beat != 1.0:
                                        closedLocalPitchIndexes.append(idx)
                            else: 
                                for idx in arc[1:-1]:
                                    closedLocalPitchIndexes.append(idx)    
                        # copy local arcs to global arcs
                        arcs.append(arc)                    

                    # try to extend local arcs leftward if lefthead in openTransitions
                    for arc in localArcs:
                        if arc[0] in openTransitions:
                            lh = self.notes[arc[0]].dependency.lefthead
                            # get all of the global notes connected to the open transition
                            globalElems = [idx for idx in 
                                self.notes[arc[0]].dependency.dependents if idx not in arc]
                            extensions = [lh] + globalElems

                            # see whether the global lefthead is just a step away
                            if isPassing(arc, self.notes):
                                tempArc = extensions + arc
                                # see whether new arc passes through a consonant interval
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
#                                    if lineStack[-1] == self.notes[arc[0]]:
#                                        lineStack.pop(-1)
#                                    print('here', localOpenHeads, closedLocalPitchIndexes)
                    # try to extend local arcs rightward if ...
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
                                
                    # TODO: try to extend leftward and rightward simultaneously?
                    
                    # and now look whether any local neighbors remain available
                    if len(localOpenHeads) > 1:
                        pairs = itertools.combinations(localOpenHeads, 2)
                        for pair in pairs:
                            i = self.notes[pair[0]]
                            j = self.notes[pair[1]]
                            rules = [i.csd.value == j.csd.value, 
                                    i.measureNumber == j.measureNumber,
                                    not isEmbeddedInArc(pair[0], localArcs),
                                    not isEmbeddedInArc(pair[1], localArcs)]
                            if all(rules):
                                j.dependency.lefthead = i.index
                                i.dependency.dependents.append(j.index)
                                arcGenerateRepetition(j.index, self.notes, localArcs, localStack)
                                localOpenHeads.remove(j.index)
                                closedLocalPitchIndexes.append(j.index)    
                                j.rule.name = 'L1'                        
                                # remove embedded local heads
                                for h in localOpenHeads:
                                    if i.index < h < j.index:
                                        localOpenHeads.remove(h)
                                        closedLocalPitchIndexes.append(h)
                                
#                    print('local arcs after revision', localArcs)
                # shift locals into lineStack if not locally closed
                # ... start with the top of the stack, which is first in the local context
                # remove top of stack if it is now closed
                if lineStack[-1].index in closedLocalPitchIndexes:
                   lineStack.pop(-1)
                # ... then proceed through the rest of the local context
                while lineBuffer[0].index < localEnd:
                    shiftBuffer(lineStack, lineBuffer)
                    if lineStack[-1].index in closedLocalPitchIndexes:
#                        print('popped pitch', lineStack[-1].index)
                        lineStack.pop(-1)
#                print('closed locals', closedLocalPitchIndexes)
#                print('open local trans', localOpenTransitions)
#                print('open local heads', localOpenHeads)
#                print('global stack', lineStack, lineBuffer[0])
                        
                # restore the open locals to the buffer
                while lineStack[-1].index > localStart:
                    shiftStack(lineStack, lineBuffer)

#                print('global stack', lineStack, lineBuffer[0])
#                print('global open heads', openHeads)
#                print('global open transitions', openTransitions)
#                print('global arcs', arcs)
#                print('global stack', [x.index for x in lineStack])

#                self.showPartialParse(i, j, arcs, openHeads, openTransitions)

                # reparse the open locals in the global context
                harmonyStart = [p for p in self.part.tonicTriad.pitches]
                harmonyEnd = [p for p in self.part.tonicTriad.pitches]
                while lineBuffer[0].index < localEnd:
                    i = lineStack[-1]
                    j = lineBuffer[0]
#                    print([n.index for n in lineStack], [n.index for n in lineBuffer])
#                    print('buffer head', j.index)
#                    self.showPartialParse(i, j, arcs, openHeads, openTransitions)                    
                    self.parseTransition(lineStack, lineBuffer, self.part, i, j, 
                            harmonyStart, harmonyEnd, openHeads, openTransitions, arcs)
#                    self.showPartialParse(i, j, arcs, openHeads, openTransitions)
                    shiftBuffer(lineStack, lineBuffer)
                    n = len(lineBuffer)
                # parse the transition into the next span
                if lineBuffer[0].index == localEnd:
                    i = lineStack[-1]
                    j = lineBuffer[0]
#                    self.showPartialParse(i, j, arcs, openHeads, openTransitions)
                    self.parseTransition(lineStack, lineBuffer, self.part, i, j, 
                            harmonyStart, harmonyEnd, openHeads, openTransitions, arcs)
#                    self.showPartialParse(i, j, arcs, openHeads, openTransitions)
                n = len(lineBuffer)
#                if n < 3: self.showPartialParse(i, j, arcs, openHeads, openTransitions)
#        self.showPartialParse(i, j, arcs, openHeads, openTransitions)
#                print('arcs', arcs)
                
        if self.part.species in ['third', 'fifth'] and openTransitions:
            for idx in openTransitions:
                # TODO first look for 'resolution'
                self.notes[idx].rule.name = 'L0'
        elif openTransitions:
            error = 'There are unclosed transitions in the line:', openTransitions, 'The line is not generable'
            self.errors.append(error)
#                print('stack', [note.index for note in lineStack], 'buffer', [note.index for note in lineBuffer])                
        self.arcs = arcs
        self.openHeads = openHeads

    def showPartialParse(self, stackTop, bufferBottom, arcs, openHeads, openTransitions):
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

    def parseTransition(self, stack, buffer, part, i, j, harmonyStart, harmonyEnd, openHeads, openTransitions, arcs):
            ### CASE ONE
            if (isHarmonic(i, harmonyStart) and isHarmonic(j, harmonyStart)) and (isLinearConsonance(i, j) or isLinearUnison(i, j)):
# TODO doesn't linear unision have to be disallowed for all but first species, or is that checked in voice leading?
#                if part.species == 'third': print('listening to', i, 'then', j)
                if openTransitions:
                    # see if j resolves the most recent open transition
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
                            for x in pruneHeads: openHeads.remove(x)
                            openHeads.append(j.index)
                elif i.csd.value == j.csd.value:
                    j.dependency.lefthead = i.index
                    i.dependency.dependents.append(j.index)
                    arcGenerateRepetition(j.index, part, arcs, stack)
                else:
#                    if part.species == 'third': print('listening to jkjkk', i, 'then', j)
                    if i.index not in openHeads:
                        openHeads.append(i.index)
                    openHeads.append(j.index)

            ### CASE TWO
            elif (self.part.species in ['third', 'fifth'] and not isHarmonic(i, harmonyStart) and 
                    isHarmonic(j, harmonyEnd) and isDiatonicStep(i, j) and buffer[-1].index == j.index):
#                if part.species == 'third': 
#                print('listening to', j.index)
#                    print(stack, buffer)
#                print('stepping from dissonance into the next span')
                if i.index in openTransitions:
                    i.dependency.righthead = j.index
                    j.dependency.dependents.append(i.index)
                    openTransitions.remove(i.index)
    #                openHeads.append(j.index)
                    for d in i.dependency.dependents:
                        if i.dependency.lefthead == None:
                            i.dependency.lefthead = self.notes[d].dependency.lefthead
                        self.notes[d].dependency.righthead = j.index
                        j.dependency.dependents.append(d)
                    arcGenerateTransition(i.index, part, arcs, stack)
    #                if part.species == 'third': print('resolves in next span', arcs)
                # see whether an arc can be extended across the span boundary

            ### CASE THREE
            elif (isHarmonic(i, harmonyStart) and not isHarmonic(j, harmonyStart) and 
                    isDiatonicStep(i, j) and buffer[-1].index != j.index):
#                print('listening to', j, harmonyStart, harmonyEnd)
    #            if part.species == 'third': print('listening to', j) 
#                if part.species == 'third': print('step to nonharmonic', i,j, openHeads)
#                if part.species == 'third': print('listening to', j, openTransitions) 
                if openTransitions:
                    for t in reversed(openTransitions):
                        h = self.notes[t]
                        rules1 = [isStepUp(h, j),
                            h.csd.direction in ['ascending', 'bidirectional'],
                            j.csd.direction in ['ascending', 'bidirectional']]
    #                        j.csd.direction == h.csd.direction]
                        rules2 = [isStepDown(h, j),
                            h.csd.direction in ['descending', 'bidirectional'],
                            j.csd.direction in ['descending', 'bidirectional']]
    ##                        j.csd.direction == h.csd.direction]
                        if all(rules1) or all(rules2):
                            j.dependency.lefthead = h.dependency.lefthead
                            j.dependency.dependents.append(h.index) # YES?
                            h.dependency.dependents.append(j.index)
                            self.notes[h.dependency.lefthead].dependency.dependents.append(j.index)
                            openTransitions.remove(h.index)
                            openTransitions.append(j.index)
                            # TODO could/should i.index instead be added to openHeads???
                            if i.index in openHeads:
                                openHeads.remove(i.index)
                            break
                        else:
                            j.dependency.lefthead = i.index
                            i.dependency.dependents.append(j.index)
                            openTransitions.append(j.index)
                            break                        
                elif not openTransitions:
#                    if part.species == 'third': print(i.index, j.index, 'openHeads', openHeads)
                    # connect to an earlier head with the same pitch as i, if available
                    if openHeads:
                        for t in reversed(openHeads):
                            h = self.notes[t]
                            # if i is the only open head
                            if i.index == h.index:
                                j.dependency.lefthead = i.index
                                i.dependency.dependents.append(j.index)
                                break
                            elif h != i:
                                # TODO rethink why we remove t from open heads during local parse 
#                                pass
#                                print('here', i, j, t)
                                openHeads.remove(t)
                            elif h == i:
                                j.dependency.lefthead = h.index
                                h.dependency.dependents.append(j.index)
                                break
                    else:
                        j.dependency.lefthead = i.index
                        i.dependency.dependents.append(j.index)
                    openTransitions.append(j.index)
#                    print(j, j.dependency.lefthead, j.index, openTransitions)

            ### CASE FOUR
            elif (not isHarmonic(i, harmonyStart) and isHarmonic(j, harmonyStart) and 
                    isDiatonicStep(i, j)):
                # complete the local harmony if possible
                if self.part.species in ['third', 'fifth']: 
                    if j not in harmonyStart: 
                        harmonyStart.append(j.pitch)
#                if part.species == 'third': print('listening to', j) 
    #            if part.species == 'third': print('resolves here', i, j, openTransitions, 'heads:', openHeads, i.dependency.lefthead)
                if not openTransitions:
                    #if step up or down, i.csd.direction must match    direction of step
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
    #                        if part.species == 'third': print('resolves here', i, j, openTransitions)
                            if isStepUp(i, j) and i.csd.direction in ['ascending', 'bidirectional']:
                                i.dependency.righthead = j.index
                                j.dependency.dependents.append(i.index)
                                for d in i.dependency.dependents:
                                    self.notes[d].dependency.righthead = j.index
                                openTransitions.remove(i.index)
                                if self.notes[i.dependency.lefthead] != self.notes[i.dependency.righthead]:
                                    openHeads.append(j.index)
                                arcGenerateTransition(i.index, part, arcs, stack)
#                                break
    #                            if part.species == 'third': 
    #                                print('resolves here', arcs)
    #                                print(stack, openHeads)
                            elif isStepDown(i, j) and i.csd.direction in ['descending', 'bidirectional']:
#                                if part.species == 'third': print(i, j, i.csd.direction, j.csd.direction)
#                                if part.species == 'third': print(i.index, i.dependency.lefthead)
#                                if part.species == 'third': print('open heads', openHeads)
#                                if part.species == 'third': print('open trans', openTransitions)
#                                if part.species == 'third': print(harmonyStart, harmonyEnd)
                                i.dependency.righthead = j.index
                                j.dependency.dependents.append(i.index)
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
                        elif isStepDown(h, i) and h.csd.direction == i.csd.direction:
                            if i.csd.direction in ['descending', 'bidirectional']:
                                h.dependency.righthead = j.index
                                i.dependency.righthead = j.index
                                self.notes[h.dependency.lefthead].dependency.dependents.append(i.index)
                                self.notes[j.index].dependency.dependents.append(h.index)
                                self.notes[j.index].dependency.dependents.append(i.index)
                                openTransitions.remove(h.index)
                                if i.index in openTransitions:
                                    openTransitions.remove(i.index)
                                arcGenerateTransition(h.index, part, arcs, stack)
                        elif isStepUp(h, i) and h.csd.direction == i.csd.direction:
                            if i.csd.direction in ['ascending', 'bidirectional']:
                                h.dependency.righthead = j.index
                                i.dependency.righthead = j.index
                                self.notes[h.dependency.lefthead].dependency.dependents.append(i.index)
                                self.notes[j.index].dependency.dependents.append(h.index)
                                self.notes[j.index].dependency.dependents.append(i.index)
                                openTransitions.remove(h.index)
                                # I think this should be the same as with StepDown
                                if i.index in openTransitions:
                                    openTransitions.remove(i.index)
                                arcGenerateTransition(h.index, part, arcs, stack)
                        elif isDiatonicStep(h, j) and t != i.index:
                            if isStepUp(h, j) and h.csd.direction in ['ascending', 'bidirectional']:
                                h.dependency.righthead = j.index
                                j.dependency.dependents.append(h.index)
                                for d in h.dependency.dependents:
                                    if d < h.index and isStepUp(self.notes[d], h):
                                        self.notes[d].dependency.righthead = j.index
                                        # remove condition if there's no reason why d is not still in openTransitions
                                        if d in openTransitions:
                                            openTransitions.remove(d)
                                openTransitions.remove(h.index)
                                arcGenerateTransition(h.index, part, arcs, stack)
                                for head in openHeads:
                                    if head > h.index:
                                        openHeads.remove(head)
                                if j.index not in openHeads:
                                    openHeads.append(j.index)
                            elif isStepDown(h, j) and h.csd.direction in ['descending', 'bidirectional']:
                                h.dependency.righthead = j.index
                                j.dependency.dependents.append(h.index)
                                for d in h.dependency.dependents:
                                    if d < h.index and isStepDown(self.notes[d], h):
                                        self.notes[d].dependency.righthead = j.index
                                        # TODO: d was probably removed from openTransitions somewhere prior to this 
                                        # so this may be entirely unnecessary
                                        if d in openTransitions: 
                                            openTransitions.remove(d)
                                openTransitions.remove(h.index)
                                arcGenerateTransition(h.index, part, arcs, stack)
                                for head in openHeads:
                                    if head > h.index:
                                        openHeads.remove(head)
                                if j.index not in openHeads:
                                    openHeads.append(j.index)
                        elif i.index in openTransitions:
                            i.dependency.righthead = j.index
                            j.dependency.dependents.append(i.index)
                            openTransitions.remove(i.index)
                            openHeads.append(j.index)
                            for d in i.dependency.dependents:
                                if i.dependency.lefthead == None:
                                    i.dependency.lefthead = self.notes[d].dependency.lefthead
                                self.notes[d].dependency.righthead = j.index
                                j.dependency.dependents.append(d.index)
                            arcGenerateTransition(i.index, part, arcs, stack)
                            break
                elif i.dependency.lefthead == None:
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

            ### CASE FIVE
            elif (not isHarmonic(i, harmonyStart) and not isHarmonic(j, harmonyStart) and 
                    isDiatonicStep(i, j)):# and buffer[-1] != j:
                if (i.csd.direction == j.csd.direction or 
                        i.csd.direction == 'bidirectional' and j.csd.direction == 'ascending'):
# the following lines produced the wrong results in minor keys
#                        (i.csd.direction == 'bidirectional' and j.csd.direction == 'ascending') or
#                        (i.csd.direction == 'ascending' and j.csd.direction == 'bidirectional')):
                    if i.dependency.lefthead == None:
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
                                # TODO: I don't think i.index has even been added to openTransitions 
    #                            openTransitions.remove(i.index)
                                openTransitions.append(j.index)
                                break
                    elif i.csd.value == 5 and j.csd.value == 6 and i.csd.direction == 'descending':
                        openTransitions.append(j.index)
                        i.dependency.dependents.append(j.index)
                        j.dependency.lefthead = i.index
                    else:
                        if not i.dependency.dependents:
                            j.dependency.lefthead = i.dependency.lefthead
                            i.dependency.dependents.append(j.index)
                            j.dependency.dependents.append(i.index)
                            openTransitions.remove(i.index)
                            openTransitions.append(j.index)
# TODO verify that this new code handles reversals in passing motions
# allow for finding preceding as well as subsequent head
# at the change of direction, close off an arc, then look backward for head or add i to openTransitions
# consider making consecutions a get method rather than an attribute lookup
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
                                    if h !=0 and not isDiatonicStep(self.notes[h], i):
                                        pass
                                    elif isDiatonicStep(self.notes[h], i):
                                        # generate a transition to i and then reassign i's lefthead etc
                                        connectsToHead = True
                                        self.notes[i.dependency.dependents[-1]].dependency.righthead = i.index
                                        arcGenerateTransition(i.dependency.dependents[-1], part, arcs, stack)
                                        i.dependency.lefthead = h
                                        j.dependency.lefthead = h
                                        i.dependency.dependents.append(j.index)
                                        j.dependency.dependents.append(i.index)
                                        self.notes[h].dependency.dependents.append(j.index)
                                        self.notes[h].dependency.dependents.append(i.index)
#                                        self.notes[h].dependency.dependents.append(j.index)
#                                        j.dependency.lefthead = h
#                                        openTransitions.append(j.index)
#                                        connectsToHead = True
                                        break
                                if connectsToHead == False:
                                    openHeads.append(i.index)
                                    i.dependency.dependents.append(j.index)
                                    j.dependency.lefthead = i.index
                                    openTransitions.append(j.index)
# now set things up to allow for connection to a later head 
# close off the transition to i, and add i to j's dependents, remove i from open transitions and add j
#                                    error = 'The non-tonic-triad pitch ' + j.nameWithOctave + str(j.index) + ' cannot be generated.'
#                                   self.errors.append(error)
                                
                elif i.csd.direction == 'ascending' and j.csd.direction == 'descending':
                    i.dependency.righthead = j.index
                    j.dependency.dependents.append(i.index)
                    openTransitions.remove(i.index)
                    openTransitions.append(j.index)
                    arcGenerateTransition(i.index, part, arcs, stack)
                elif i.csd.direction == 'ascending' and j.csd.direction == 'bidirectional':
                    j.dependency.lefthead = i.index
                    i.dependency.dependents.append(j.index)
                    openTransitions.append(j.index)
                else:
                    # I think this is okay, for catching things in third species
                    j.dependency.lefthead = i.dependency.lefthead
                    i.dependency.dependents.append(j.index)
                    j.dependency.dependents.append(i.index)
                    openTransitions.remove(i.index)
                    openTransitions.append(j.index)

            ### CASE SIX
            elif (not isHarmonic(i, harmonyStart) and isHarmonic(j, harmonyStart) and 
                    isLinearConsonance(i, j)):
    #            if part.species == 'third': print('listening to', j)         
                if i.dependency.lefthead == None:
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

            ### CASE SEVEN
            elif (isHarmonic(i, harmonyStart) and not isHarmonic(j, harmonyStart) and 
                    isLinearConsonance(i, j) and buffer[-1].index != j.index):
    #            if part.species == 'third': print('listening to', j)         
                if openTransitions:
                    # see whether j continues a transition in progress
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
                            # remove intervening open heads
                            for oh in reversed(openHeads):
                                if h.index < oh < j.index:
                                    openHeads.remove(oh)
                            break
                    # if not, see whether j connects to a head that precedes the open transitions
                    if continuesTransition == True:
                        return
                    else:
                        # get those open heads that are earlier than the earliest open transition:
                        earlierHeads = [i for i in openHeads if i < openTransitions[0]]
                        connectsToHead = False
                        for h in reversed(earlierHeads):
                            if h !=0 and not isDiatonicStep(self.notes[h], j):
                                if h in earlierHeads:
                                    earlierHeads.remove(h)
                            elif isDiatonicStep(self.notes[h], j):
                                self.notes[h].dependency.dependents.append(j.index)
                                j.dependency.lefthead = h
                                openTransitions.append(j.index)
                                connectsToHead = True
                                break
                    # if neither of these works, return an error: j appears out of the blue and cannot be generated
                        if connectsToHead == False:
                            error = 'The non-tonic-triad pitch ' + j.nameWithOctave + str(j.index) + ' cannot be generated.'
                            self.errors.append(error)
                elif openHeads:
                    for h in reversed(openHeads): # only open heads are currently on the stack
                        if h !=0 and not isDiatonicStep(self.notes[h], j):
                            if h in openHeads:
                                openHeads.remove(h)
                        elif isDiatonicStep(self.notes[h], j):
                            self.notes[h].dependency.dependents.append(j.index)
                            j.dependency.lefthead = h
                            openTransitions.append(j.index)
                            break # stop once a lefthead is found
                        # TODO may need to turn off in third species
                        elif h == 0 and i.dependency.lefthead == None and i.index != h:# and self.part.species not in ['third', 'fifth']:
#                            print('reinterpeting', self.notes[h], i, j)
                            # CASE: allows for reinterpretation on the fly
                            # Example: PL, 3 8 7 8 6 5 6 5 2 1, listening to 6
                            #     first pass interp takes 8 7 8 as arc, but cannot attach either 6
                            #     this routine 'forgets' the second 8 and then reinterprets,
                            #     this routine 'finds' 8 7 6 5 as arc
                            # if j cannot be connected to i or h, then the parse should fail
                            # restock stack and search backwards for connection
                            # TODO double check to see whether it's okay to restock starting with
                            #        the second note of the line
                            #        this keeps the parser from duplicating line[0] in the open heads
                            # TODO will really fail if substructures are intertwined
                            # Example: GL, minor: 1 5 7 1 2 3 6 5 8 7 6 5 4 3
                            #    will not be able to handle the first 6, so removes 3, leaving
                           	#    a dissonant nontriad leap between 2 and 6
                            stack = self.notes[0:j.index]
                            for s in reversed(stack):
                                clearDependencies(s)
                                for arc in arcs:
                                    if arc[-1] == s.index:
                                        arcs.remove(arc)
                            stack.pop()  # remove i from consideration
                            for x in reversed(stack):
                                buffer.insert(0,x)
                                stack.pop()
                        else:
                            error = 'The non-tonic-triad pitch ' + j.nameWithOctave + str(j.index) + ' cannot be generated.'
                            self.errors.append(error)
                else:
                    i.dependency.righthead = j.index
                    j.dependency.dependents.append(i.index)
    #                openTransitions.remove(t)
                    arcGenerateTransition(i.index, part, arcs, stack)

            ### CASE EIGHT
            elif (not isHarmonic(i, harmonyStart) and not isHarmonic(j, harmonyStart) and 
                    isLinearConsonance(i, j)):
    #            if part.species == 'third': print('listening to', j) 
                openNonTonicTriadPitches = []
                if self.part.species not in ['third', 'fifth']:
                    if i.index == j.index-1:
                        error = 'Nongenerable succession between ' +  i.nameWithOctave + ' and ' + j.nameWithOctave + ' in the line.'
                        self.errors.append(error)
                    else:
                        error = 'The line contains an ungenerable intertwining of secondary structures involving ' \
                                + j.nameWithOctave + ' in measure ' + str(j.measureNumber) + '.'
                        self.errors.append(error)
                elif self.part.species in ['third', 'fifth']:
                    # TODO interpret local non-tonic insertions
                    if i.index not in openNonTonicTriadPitches:
                        openNonTonicTriadPitches.append(i.index)
                    openNonTonicTriadPitches.append(j.index)
                    if openHeads:
                        # TODO figure out how to connect at least one of these open nttps to a global head
#                        print(i.index, j.index)
#                        print('open nontonic pitches', openNonTonicTriadPitches)
#                        print('open heads', openHeads)
#                        print('open transitions', openTransitions)
                        for t in openHeads:
                            h = self.notes[t]
                            if isDiatonicStep(h, i):
                                pass
#                                print('here', h, i)
#                    j.rule.name = 'L3'
#                    print(j, j.rule.name)
#                    buffer.pop(0)

    #                 if isHarmonic(i, harmonyStart): print('chord RN', stufe+1)                
                    pass
    #            if i.dependency.righthead and i.dependency.lefthead:
    #                arcGenerateTransition(i.index, part, arcs, stack)

            ### CASE NINE
            elif (not isHarmonic(i, harmonyStart) and not isHarmonic(j, harmonyStart) and 
                    isLinearUnison(i, j)):
    #            if part.species == 'third': print('listening to', j) 
                # TODO: double check this error, might be too simple
                if i.index == j.index - 1 or i.measureNumber != j.measureNumber:
                    error = 'Repetition of a non-tonic-triad pitch: ' +  i.nameWithOctave
                    self.errors.append(error)
                else: pass

            ### CASE TEN
            elif (not isHarmonic(i, harmonyStart) and not isHarmonic(j, harmonyStart) and 
                    not isLinearConsonance(i, j)) and not isLinearUnison(i, j):
                if i.index == j.index-1:
                    error = 'Nongenerable dissonant leap between ' +  i.nameWithOctave + ' and ' + j.nameWithOctave + ' in the line.'
                    self.errors.append(error)
                else:
                    error = 'The line contains an ungenerable intertwining of secondary structures involving ' \
                        + j.nameWithOctave + ' in measure ' + str(j.measureNumber) + '.'
                    self.errors.append(error)
            
            ### CASE ELEVEN
            elif not isLinearConsonance(i, j) and not isLinearUnison(i, j) and not isDiatonicStep(i, j):
                error = 'Nongenerable leap between ' +  i.nameWithOctave + ' and ' + j.nameWithOctave + ' in the line.'
                self.errors.append(error)

            ### CASE TWELVE
            elif not isSemiSimpleInterval(i, j):
                error = 'Leap larger than an octave between ' +  i.nameWithOctave + ' and ' + j.nameWithOctave + ' in the line.'
                self.errors.append(error)

            ### TODO prune the list open heads if a repetition has been added
            ### figure out the optimal time to prune direct repetitions from the list of open heads
#            openHeads = pruneOpenHeads(self.notes, openHeads)

    def prepareParses(self):
        # run the line parser for every type of line if the context is only one part
        if self.part.lineTypes and len(self.context.parts) == 1:
            pass
        # otherwise delete generic type if another type is present
###########################
###########################
# TODO only delete generic if another type is actually valid (generable)
# postpone this till later, in collectParses
# think carefully before actually revising this
###########################
###########################
        # and only use bass for bottom line if possible
        elif self.part.lineTypes and len(self.context.parts) > 1:
            if len(self.part.lineTypes) > 1:
                self.part.lineTypes = [type for type in self.part.lineTypes if type != 'generic']
            if len(self.part.lineTypes) > 1 and self.part == self.context.parts[-1]:
                self.part.lineTypes = [type for type in self.part.lineTypes if type != 'primary']
        # outputs will eventually be collected in self.parses
        # the uninterpreted stack of openHeads will be moved into the Parse buffer
        for lineType in self.part.lineTypes:
            # restock the buffer ...
            buffer = [self.notes[head] for head in self.openHeads]
            stack= []
            # ... create holder for all interpretations that pass through during a parse
    #        self.interpretations = []
            # ... and look for S2 or S3 candidate notes in the given lineType
            # and build parse objects for each candidate
###########################
###########################
# TODO create all of the possible basic arcs here rather than in the Parse object
# Revise buildParse accordingly
###########################
###########################
            parsecounter = 1
            if lineType == 'bass':
                if self.notes[0].csd.value % 7 != 0:
                    error = 'Bass structure error: The line does not begin on the tonic degree.'
                    self.errors.append(error)
                if self.notes[-1].csd.value % 7 != 0:
                    error = 'Bass structure error: The line does not end on the tonic degree.'
                    self.errors.append(error)
                s3cands = []
                n = len(buffer)
                shiftBuffer(stack, buffer)
                while n > 1:
                    shiftBuffer(stack, buffer)
                    n = len(buffer)
                    i = stack[-1]
                    if i.csd.value % 7 != 4: 
                        continue
                    elif i.csd.value % 7 == 4:
                        s3cands.append(i)
                if not s3cands:
                    error = 'Bass structure error: No candidate for S3 detected.'
                    self.errors.append(error)
                if self.errors:
                    pass # break
                else:
                    for cand in s3cands: 
                        self.buildParse(cand, lineType, parsecounter, stack)
                        parsecounter += 1 # update numbering of parses
            elif lineType == 'primary':
                if self.notes[-1].csd.value % 7 != 0:
                    error = 'Primary structure error: The line does not end on the tonic degree.'
                    self.errors.append(error)
                s2cands = [] # holder for Notes that might become S2
                n = len(buffer)
                while n > 0:
                    shiftBuffer(stack, buffer)
                    n = len(buffer)
                    i = stack[-1]
                    if i.csd.value in {2, 4, 7}: # add this to get S2 as early as possible: and i not in s2cands:
                        s2cands.append(i)
                if not s2cands:
                    error = 'Primary structure error: No candidate for S2 detected.'
                    self.errors.append(error)

                # generate a Parse object for each S2cand
                # and then turn over further processes to each Parse object, 
                # using a series of methods to infer a basic step motion
                methods = 7
                if self.errors:
                    break
                else:
                    for cand in s2cands:
                        for m in range(0, methods):
#                            print('parse using method', m, 'for s2 cand', cand.index)
                            self.buildParse(cand, lineType, parsecounter, stack, method=m)
                            parsecounter += 1 # update numbering of parses
            elif lineType == 'generic': # for all other types of line, first note is S2
                s2cand = buffer[0]
                stack = buffer
                self.buildParse(s2cand, lineType, parsecounter, stack)
            
    def buildParse(self, cand, lineType, parsecounter, stack, method=None):
        newParse = Parser.Parse()
        newParse.S1Index = self.notes[-1].index
        newParse.arcs = copy.deepcopy(self.arcs)
        newParse.lineType = lineType
        newParse.species = self.part.species
        newParse.tonic = self.part.tonic
        newParse.mode = self.part.mode
        newParse.partNum = self.part.partNum
        newParse.notes = copy.deepcopy(self.notes)
        newParse.notes[newParse.S1Index].rule.name = 'S1'
        newParse.method = method
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
            newParse.S2Index = cand.index # always 0
            newParse.S2Degree = cand.csd.degree
            newParse.S2Value = cand.csd.value
            newParse.notes[newParse.S2Index].rule.name = 'S2'
        newParse.stackremnant = stack
        newParse.performLineParse()
        self.parses.append(newParse)
#        print('parse errors', newParse.label, newParse.errors)
        self.parseErrorsDict.update({newParse.label: newParse.errors})
#########################
#########################
#########################
#########################
#########################
#        newParse.displayFullParse()

    class Parse():
        '''An object for holding a parsed interpretation'''
        def __init__(self):
            self.stackremnant = []
            self.buffer = []
            self.stack = []
            self.errors = []
        
        # attributes: 
            # S1Index
            # S2Degree, S2Index, S2Value, 
            # S3Degree, S3Final, S3Index, S3Indexes, S3Initial, S3PenultCands, S3Value
            # label
            # arcs
            # tonic
            # mode
            # arcBasic
            

        def __repr__(self):
            return self.label

        def performLineParse(self):
            if self.lineType == 'primary':
                self.parsePrimary()
            elif self.lineType == 'bass':
                self.parseBass()
            elif self.lineType == 'generic':
                self.parseGeneric()
            else:
                pass
            # exit parse if no basic arc is found
            if self.arcBasic == None:
#                print(self.errors)
                return self.errors
            else:
                pass
            self.parseSecondaries()
            self.testLocalResolutions()
            self.pruneArcs()
            # remove empty arcs
            for arc in self.arcs:
                if arc == []:
                    pass # write code to delete empty arc
            # for running with music xml input/output
            self.gatherRuleLabels()
            self.gatherParentheses()
            # TODO finish writing function to set dependency levels
#            self.setDependencyLevels()

        def arcMerge(self, arc1, arc2):
            # a function for combining two passings that share an inner node and direction 
            # merges elements into first arc and empties the second
            # revises dependencies
            leftouter = self.notes[arc1[0]]
            rightinner = self.notes[arc1[-1]]
            leftinner = self.notes[arc2[0]]
            rightouter = self.notes[arc2[-1]]
            #        
            rules1 = [rightinner.csd.value == leftinner.csd.value]
            rules2 = [leftouter.csd.value > rightinner.csd.value > rightouter.csd.value,
                    leftouter.csd.value < rightinner.csd.value < rightouter.csd.value]
            #
            if all(rules1) and any (rules2):
            # merge arc2 elements into arc1
                removeDependenciesFromArc(self.notes, arc1)
                removeDependenciesFromArc(self.notes, arc2)
                self.arcs.remove(arc2)
                arc2.pop(0)
                for n in arc2:
                    arc1.append(n)
                # revise dependencies
                addDependenciesFromArc(self.notes, arc1)

        def arcEmbed(self, arc1, arc2):
            # a function for embedding a repetition inside a passing
            # in either order
            # start with repetition linked to passing, then embed
            leftouter = self.notes[arc1[0]]
            rightinner = self.notes[arc1[-1]]
            leftinner = self.notes[arc2[0]]
            rightouter = self.notes[arc2[-1]]
            rules1 = [rightinner.csd.value == leftinner.csd.value, # the arcs share a node
                        rightinner.index == leftinner.index]
            rules2 = [len(arc1) == 2, # arc1 is a simple repetition
                        leftouter.csd.value == leftinner.csd.value] # they share the same pitch on the lefthead
            rules3 = [len(arc2) == 2, # arc2 is a simple repetition
                        rightinner.csd.value == rightouter.csd.value] # they share the same pitch on the lefthead
            if all(rules1) and any(rules2):
                removeDependenciesFromArc(self.notes, arc2)
                arc2[0] = arc1[0]
                addDependenciesFromArc(self.notes, arc2)
            elif all(rules1) and any(rules3):
                removeDependenciesFromArc(self.notes, arc1)
                arc1[-1] = arc2[-1]
                addDependenciesFromArc(self.notes, arc1)
                    
        def parsePrimary(self):
            # once all lower-level parsing is done, prepare for assigning basic structure
            self.arcs.sort()# = sorted(self.arcList)
            self.arcBasic = None

            # find a basic step motion, and
                # if not there, reinterpret the arcs between S2Index and end of tune
            # METHOD 0: from any S2 candidate
            # look for one existing basic step motion arc that starts from S2
            if self.method == 0:
                for counter,arc1 in enumerate(self.arcs):
                    rules = [arc1[0] == self.S2Index,
                            arc1[-1] == self.S1Index]
                    if all(rules):
                        self.arcBasic = arc1

            # METHOD 1: from any S2 candidate
            # look for an existing basic step motion arc that can be attached to S2: repetition + passing
            elif self.method == 1:
                for counter,arc1 in enumerate(self.arcs):
                    a = self.notes[arc1[0]] # the arc's leftmost Note
                    b = self.notes[arc1[-1]] # the arc's rightmost Note
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
            # look for two arcs that can fused into a basic step motion: passing + neighbor/repetition
            elif self.method == 2:
                for counter,arc1 in enumerate(self.arcs):
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
            # look for two arcs that can be merged into a basic step motion
            elif self.method == 3:
                for counter,arc1 in enumerate(self.arcs):
                    rules1 = [arc1[0] == self.S2Index, 
                            not arc1[-1] == self.S1Index]
                    if all(rules1):
                        # look rightward for another arc from same degree
                        for arc2 in self.arcs[counter+1:]:
                            # look for two passing motions to merge
                            # TODO write rules to handle cases where there are several possibilities
                            rules2 = [arc1[-1] == arc2[0],
                                     arc2[-1] == self.S1Index,
                                     self.notes[arc1[0]].csd.value > self.notes[arc1[-1]].csd.value,
                                     self.notes[arc2[0]].csd.value > self.notes[arc2[-1]].csd.value]
                            if all(rules2):
                                self.arcMerge(arc1, arc2)
                                self.arcBasic = arc1

            # METHOD 4: if S2 = sd8
            # look for three arcs that can be merged into a basic step motion
            elif self.method == 4:
                for counter1,arc1 in enumerate(self.arcs):
                    rules1 = [arc1[0] == self.S2Index, 
                            not arc1[-1] == self.S1Index]
                    if all(rules1):
                        # look rightward for another arc from same degree that is also nonfinal
                        for counter2,arc2 in enumerate(self.arcs[counter1+1:]):
                            # look for two passing motions to merge
                            # TODO write rules to handle cases where there are several possibilities
                            rules2 = [arc1[-1] == arc2[0],
                                     arc2[-1] != self.S1Index,
                                     self.notes[arc1[0]].csd.value > self.notes[arc1[-1]].csd.value,
                                     self.notes[arc2[0]].csd.value > self.notes[arc2[-1]].csd.value,
                                     self.notes[arc2[-1]].csd.value > self.notes[-1].csd.value]
                            if all(rules2):
                                for arc3 in self.arcs[counter2+1:]:
                                    # look for two passing motions to merge
                                    # TODO write rules to handle cases where there are several possibilities
                                    rules3 = [arc2[-1] == arc3[0],
                                             arc3[-1] == self.S1Index,
                                             self.notes[arc2[0]].csd.value > self.notes[arc2[-1]].csd.value,
                                             self.notes[arc3[0]].csd.value > self.notes[arc3[-1]].csd.value]
                                    if all(rules3):
                                        self.arcMerge(arc1, arc2)
                                        self.arcMerge(arc1, arc3)
                                        self.arcBasic = arc1

            # METHOD 5
            # TODO devise method that takes an existing 5-4-3 arc (the longest spanned, if more than one)
            # and tries to find a connection -2-1 to complete a basic arc
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
                    error = 'No composite step motion found from this S2 candidate:', self.S2Value+1
                    self.errors.append(error)
                    return
                selectedArc = selectedArcs[0]
                sd3Index = selectedArc[-1]
                self.buffer = [n for n in self.notes[sd3Index:] if not n.tie or n.tie.type == 'start']
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
                    # look for descending step to S1
                    if isStepDown(j, h):
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
            # reinterpret the line
            # TODO this does not work well and shouldn't really ignore all the preparse work
            # see 2020_05_19T16_58_53_914Z.musicxml
            elif self.method == 6:
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
                        basicArcCand.append(j.index)
                    elif isStepDown(j, h) and j.csd.value == self.S2Value:
                        basicArcCand.append(self.S2Index)
                        break                    
                # the following procedure prefers to locate tonic triad S3 nodes earlier rather than later
                # may have to be overriden when harmonizing counterpoint with bass line
                if self.S2Value > 2: # this only applies to Urlinien from 5 or 8
                # refill the buffer from S2 to end of line
                    self.buffer = [n for n in self.notes[self.S2Index:] if not n.tie or n.tie.type == 'start']
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
                                        a.rule.name = 'S3'
                                        self.arcEmbed(arc, [a.index, j.index])
                                        basicArcCand[prevS+1] = a.index
                                    # settle for the b head if possible
                                    elif b.csd.value == j.csd.value:
                                        j.dependency.lefthead = b.index
                                        arcGenerateRepetition(j.index, notes, arcs, stack)
                                        j.rule.name = 'E1'
                                        b.rule.name = 'S3'
                                        basicArcCand[x+1] = b.index
                # check to make sure the basic step motion is complete
                if len(basicArcCand) != (self.S2Value+1):
                    #TODO report specific Note/Pitch of failed S2 candidate
                    error = 'No basic step motion found from this S2 candidate:', self.S2Value+1
                    self.errors.append(error)
                    return        
               #
                else:
                    self.arcBasic = list(reversed(basicArcCand))

#            if self.arcBasic:
#                print('finding basic arc using method', self.method, self.arcBasic)
#                print([arc for arc in self.arcs if arc != self.arcBasic])     

            if self.arcBasic == None:
                error = 'No basic step motion found from this S2 candidate:', self.S2Value+1
                self.errors.append(error)
                return
            # set the rule labels for S3 notes  
            else:
                for n in self.arcBasic[1:-1]:
                    self.notes[n].rule.name = 'S3'
                  
            S3Indexes = [note.index for note in self.notes if note.rule.name == 'S3']            
            self.S3Initial = min(S3Indexes)
            self.S3Final = max(S3Indexes)
        
            # attach repetitions of S2 before onset of S3        
            self.attachOpenheadsToStructuralLefthead(self.S2Index, self.S3Initial)

 
            # TODO figure out and explain why it is necessary to look for crossed arcs here
            #    use of method 5 for inferring basic arc can leave junk behind in the arc list
            if self.arcBasic == None:
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
#                print('basic arc', self.arcBasic)
#                print('purge list', purgeList)
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
            self.arcs.sort()# = sorted(self.arcList)
            self.arcBasic = [0, self.S3Index, self.S1Index]        
            self.attachOpenheadsToStructuralLefthead(0, self.S3Index)
            self.attachOpenheadsToStructuralLefthead(self.S3Index, self.S1Index)
            self.arcs.sort()# = sorted(self.arcList)
            if self.arcBasic == None:
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
#                print('basic arc', self.arcBasic)
#                print('purge list', purgeList)
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
            # once all lower-level parsing is done, prepare for assigning basic structure
            # see if a basic step motion is absent, ascending, or descending
            self.arcs.sort()# = sorted(self.arcList)
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
            for counter,arc1 in enumerate(self.arcs):
                a = self.notes[arc1[0]] # the arc's leftmost Note
                b = self.notes[arc1[-1]] # the arc's rightmost Note
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
                        elif self.arcBasic and self.notes[arc2[0] == self.notes[self.S1Index].csd.value]: # prefinal neighbor
                            self.arcBasic.pop()
                            self.arcBasic.append(arc2[-1])
                        rules4 = [self.notes[arc1[-1]].csd.value == self.notes[arc2[0]].csd.value]
                        if all(rules4) and (all(rules2) or all(rules3)):
                            # TODO: finish this
                            pass
                            # print('here')
                            # attach arc2 to arc1 and then merge
                            # this may not be needed if earlier parsing picks up the repetition
            # attach repetitions of S2 before onset of S1
            # TODO refine generic basic arc and coherence    
            self.attachOpenheadsToStructuralLefthead(self.S2Index, self.S1Index)
            # if all else fails, just use first and last notes as the basic arc
            if self.arcBasic == None:
                self.arcBasic = [self.S2Index, self.S1Index]

        def attachOpenheadsToStructuralLefthead(self, structuralLefthead, rightLimit):
            '''examine the span between a structural lefthead and a righthand limit,
            looking for notes that are either head of an arc (left or right) or not embedded in an arc,
            and can be taken as a repetition of the structural lefthead.
            This function increases the coherence of a parse.
            structuralLefthead = index, rightLimit = index'''
            self.buffer = [n for n in self.stackremnant if structuralLefthead < n.index < rightLimit]
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
                rules3 = [not isEmbeddedInArc(i.index, self.arcs), 
                            self.notes[i.index].dependency.lefthead == None, 
                            self.notes[i.index].dependency.righthead == None]
                # rules 4: and it's not already in an arc initiated by the structural lefthead 
                rules4 = [not areArcTerminals(structuralLefthead, i.index, self.arcs)]
                if all(rules1) and (all(rules2) or all(rules3)) and all(rules4):
    #                print('interpret', i.index, 'as repetition')
                    self.notes[i.index].dependency.lefthead = structuralLefthead
                    self.notes[0].dependency.dependents.append(i.index)
                    self.notes[i.index].rule.name = 'E1'
                    arcGenerateRepetition(i.index, self.notes, self.arcs, self.stack)
                # TODO consider working on this
                    if all(rules2):
                        # may also want to transfer dependent neighbors to the newly created
                        # repetition arcs
                        pass
    
        def parseSecondaries(self):
            for i in self.notes:
                if i.rule.name == None and ((i.tie and i.tie.type == 'start') or not i.tie):
                    if i.dependency.lefthead != None and i.dependency.righthead != None:
                        if self.notes[i.dependency.lefthead].csd.value == self.notes[i.dependency.righthead].csd.value:
                            if isTriadMember(self.notes[i.dependency.righthead], 0):
                                i.rule.name = 'E2'
                                if self.notes[i.dependency.righthead].rule.name == None:
                                    self.notes[i.dependency.righthead].rule.name = 'E1'
                            else:
                                i.rule.name = 'L2'
                                if self.notes[i.dependency.righthead].rule.name == None:
                                    self.notes[i.dependency.righthead].rule.name = 'L1'
                        else:
                            i.rule.name = 'E4'
                            if self.notes[i.dependency.righthead].rule.name == None and isTriadMember(self.notes[i.dependency.righthead], 0):
                                self.notes[i.dependency.righthead].rule.name = 'E3'
#                            elif self.notes[i.dependency.righthead].rule.name == None and not isTriadMember(self.notes[i.dependency.righthead], 0):
#                                self.notes[i.dependency.righthead].rule.name = 'LL3'
                    elif i.dependency.lefthead != i.dependency.righthead:
                        # This may not function correctly in every case
#                        print('misidentified E1', i, i.dependency.lefthead, i.dependency.righthead)
                        i.rule.name = 'Ex'
                    elif i.dependency.lefthead == None and i.dependency.righthead == None:
                        # what's the function of this section??    
                        # to seek out coherent connection with S2?
                        # find consecutions in the basic arc 
                        ints = pairwise(self.arcBasic)
                        for int in ints:
                            a = int[0]
                            b = int[1]
                            self.arcs.sort()
                            for arc in self.arcs:
                                # if i and the arc are between two notes of the basic arc 
                                if a < i.index < b and a <= arc[0] < b and a < arc[-1] < b:
                                    # and if i comes after the arc 
                                    if i.index > arc[0] and i.index > arc[-1]:
                                        pass
    #                                     print(i.index, arc)
                                        # see whether i can count as a repetition of an arc terminal
    #                                     if i.csd.value == self.line.notes[arc[0]].csd.value:
    #                                         i.dependency.lefthead = arc[0]
    #                                         i.rule.name = 'E21'
    #                                         arcGenerateRepetition(i)
    #                                     if i.csd.value == self.line.notes[arc[-1]].csd.value:
    #                                         i.dependency.lefthead = arc[-1]
    #                                         i.rule.name = 'E41'                
    #                                         arcGenerateRepetition(i.index)
                    if i.dependency.lefthead == None and i.dependency.righthead == None:                
                        if isTriadMember(i, 0):
                            i.rule.name = 'E3'
                            i.noteheadParenthesis = True
                        elif not isTriadMember(i, 0) and self.species in ['third', 'fifth']:
                            i.rule.name = 'L3'
                            i.noteheadParenthesis = True
                        else:
                            error = 'The pitch ' + i.nameWithOctave + 'in measure ' + str(i.measureNumber) + 'is not generable.'
                            self.errors.append(error)
                    elif i.dependency.dependents == None:
                        if isTriadMember(i, 0):
                            i.rule.name = 'E3'
                            i.noteheadParenthesis = True
                        elif not isTriadMember(i, 0) and self.species in ['third', 'fifth']:
                            i.rule.name = 'L3'
                            i.noteheadParenthesis = True
                        else:
                            error = 'The pitch ' + i.nameWithOctave + 'in measure ' + str(i.measureNumber) + 'is not generable.'
                            self.errors.append(error)
                if i.rule.name == 'E3' and i.dependency.dependents == []:
                    i.noteheadParenthesis = True
                # TODO figure out why some notes still don't have rules
                elif i.rule.name == None and i.tie: 
                    if i.tie.type != 'stop':
                        i.rule.name = 'X'
                elif i.rule.name == None:
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
                    if resolved == False:
                        error = 'The local insertion ' + i.nameWithOctave + 'in measure ' + str(i.measureNumber) + 'is not resolved.'
                        self.errors.append(error)
            
        def pruneArcs(self):
            pass
            # find arcs to merge into longer passing motions
            # TODO check to make sure that neither arc is embedded in another arc
            #        arc1[-1] = arcX[-1] and arcX[0] < arc1[0]
            #        arc2[0] = arcY[0] and arcY[-1] > arc2[-1]            
            for arc1 in self.arcs:
                for arc2 in self.arcs:
                    rules1 = [arc1[-1] == arc2[0],
                            self.notes[arc1[-1]].rule.name[0] != 'S']
                    # TODO consider changing the conditions to isPassing and in same direction
                    rules2 = [self.notes[arc1[0]].csd.value > self.notes[arc1[-1]].csd.value,
                            self.notes[arc2[0]].csd.value > self.notes[arc2[-1]].csd.value]
                    rules3 = [self.notes[arc1[0]].csd.value < self.notes[arc1[-1]].csd.value,
                            self.notes[arc2[0]].csd.value < self.notes[arc2[-1]].csd.value]
                    if all(rules1) and (all(rules2) or all(rules3)):
                        mergePairOption = (arc1, arc2)
                        for arc in self.arcs:
                            arc1Embedded = False # assume that it is independent
                            arc2Embedded = False # assume that it is independent
                            if mergePairOption[0][-1] == arc[-1] and arc[0] < mergePairOption[0][0]:
                                arc1Embedded = True
                                break
                            if mergePairOption[1][0] == arc[0] and arc[-1] > mergePairOption[1][-1]:
                                arc2Embedded = True
                                break
                        if arc1Embedded == False and arc2Embedded == False:
                            self.arcMerge(mergePairOption[0], mergePairOption[1])
                            # TODO is it necessary to set the rules here, 
                            # what about the removed node? should it also be set to 'E4'?
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
                if elem.noteheadParenthesis == True:
                    self.parentheses.append((elem.index, True))
                else:
                    self.parentheses.append((elem.index, False))
            return
        
        def setDependencyLevels(self):
            '''review a completed parse and determine the level for each note'''
            # this works for now, but is not optimal
            # does not work for this line: BL in major: 1 5 4 3 1 -7 -5 1 6 5 4 3 2 1
            # arcs = [[0, 1, 13], [1, 2, 3], [1, 8, 9], [1, 10, 11, 12, 13], [4, 5, 7]]
            # there needs to be a more robust way of evaluating insertions, not just left-to-right
            # also may not work for complicated, poorly interpreted third species lines


            # assign levels to notes in the basic arc
            for n in self.notes:
                if n.rule.name == 'S1': n.rule.level = 0
                if n.rule.name == 'S2': n.rule.level = 1
                if n.rule.name == 'S3': n.rule.level = 2
            # set level of first note if not in basic arc
            if self.arcBasic[0] != 0:
                self.notes[0].rule.level = 3

            # collect all the secondary arcs
            dependentArcs = [arc for arc in self.arcs if arc != self.arcBasic]

            # a span is defined by two notes: initial and final
            # the rootSpan extends from the first to the last note of a line
            # TODO consider using some kind of root node pair: leftRoot, rightRoot, or just None
            rootSpan = (self.notes[0].index, self.notes[-1].index)
#            print('root span', rootSpan)

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


#            print('first-order spans', spans)
#            print('dependent arcs', dependentArcs)                        


            # for testing whether an insertion conforms to the intervallic constraints 
            def isPermissibleConsonance(x, y, z):
                # checks the insertion of y between x and z indexes
                left = self.notes[x]
                right = self.notes[z]
                insertion = self.notes[y]
                rules = [(isLinearConsonance(left, insertion) or isLinearUnison(left, insertion) or
                        isDiatonicStep(left, insertion)),
                        (isLinearConsonance(insertion, right) or isLinearUnison(insertion, right) or
                        isDiatonicStep(insertion, right))]
                if all(rules):
                    return True
                else:
                    return False

            # look at every span in the list, and see whether a dependent arc fits into it 
            # this is the core of the function

            def processSpan(span, spans, dependentArcs):
                # the rule levels inside the span are determined by the rule levels of the left and right edges
                leftEdge = span[0]
                rightEdge = span[1]
                leftEdgeLevel = self.notes[span[0]].rule.level
                rightEdgeLevel = self.notes[span[1]].rule.level
#                print(span, leftEdgeLevel, rightEdgeLevel)

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
                #     (2) leftBranches connect onto the rightEdge (branch to the left)
                #     (3) rightBranches connect onto the leftEdge (branch to the right)
                #     (4) interBranches do not connect to either edge
                # find the best and longest arc available in a span
                #     preferences between categories: cross > right > left > inter
                #     preferences within category: longer > shorter
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
                        if arc[0] == leftEdge and rightBranch == None:
                            if isPermissibleConsonance(leftEdge, arc[-1], rightEdge):
                                rightBranch = arc
                        # look to see if there's a longer branch available
                        if arc[0] == leftEdge and rightBranch:
                            if length(arc) > length(rightBranch):
                                if isPermissibleConsonance(leftEdge, arc[-1], rightEdge):
                                    rightBranch = arc
                # look for left branches if the right edge has been generated and there is no right branch
                for arc in dependentArcs:
                    if rightEdgeLevel and not crossBranch and not rightBranch:
                        if arc[-1] == rightEdge and leftBranch == None:
                            if isPermissibleConsonance(leftEdge, arc[0], rightEdge):
                                leftBranch = arc
                            leftBranch = arc
                        # look to see if there's a longer branch available
                        if arc[-1] == rightEdge and leftBranch:
                            if length(arc) > length(leftBranch):
                                if isPermissibleConsonance(leftEdge, arc[0], rightEdge):
                                    leftBranch = arc
                # look for inter branch if no cross branches or left or right branches
                for arc in dependentArcs:
                    if not rightBranch and not leftBranch and not crossBranch:
                        for arc in dependentArcs:
                            if arc[0] > leftEdge and arc[-1] < rightEdge and interBranch == None:
                                interBranch = arc
                            # look to see if there's a longer branch available
                            if arc[0] > leftEdge and arc[-1] < rightEdge and interBranch:
                                if length(arc) > length(interBranch):
                                    interBranch = arc

#                    print(dependentArcs)
#                    print(span, crossBranch, rightBranch, leftBranch, interBranch)
#                    exit()
#                    print(leftEdgeLevel, rightEdgeLevel, nextLevel)                

                # (2) process any branches that have been found in the span
                #     (a) remove the branch from the list of dependent arcs
                #     (b) calculate rule levels for members of the branch
                # termini levels of cross branch are already set, so just set level of inner elements
                if crossBranch:
                    dependentArcs.remove(crossBranch)
                    for i in crossBranch[1:-1]:
                        self.notes[i].rule.level = nextLevel
                # one terminus level is already set, so set level of the other terminus and the inner elements
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
                # no terminus level is already set, so set level of the left terminus, then the right, and then the inner elements
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

                # (4) process a span that contains only inserted pitches no arcs
                # TODO this is a temporary solution, need an algorithm that finds the best of
                #     the many possible solutions, not necessarily left to right
                #     e.g., look for repetitions of leftEdge
                if not(crossBranch or rightBranch or leftBranch or interBranch):
                    if isPermissibleConsonance(leftEdge, leftEdge+1, rightEdge):
                        self.notes[leftEdge+1].rule.level = nextLevel
                        spans.remove(span)
                        if rightEdge - (leftEdge+1) > 1:
                            spans.append((leftEdge+1, rightEdge))
                    elif length(span) > 3 and isPermissibleConsonance(leftEdge, leftEdge+1, leftEdge+2) and isPermissibleConsonance(leftEdge, leftEdge+2, rightEdge):
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

            generatedNotes = [(n.index, n.rule.name, n.rule.level) for n in self.notes if n.rule.level != None]
#            print('current parse:', generatedNotes)
            generationTable = [n.rule.level for n in self.notes]
#            print('current parse:', generationTable)

        def displayFullParse(self):
            # given a parsed part, with rule dependencies set
            illustration = stream.Score()
            notes = self.notes
            # determine the maximum number of levels in the parse 
            levels = [n.rule.level for n in notes]
            if None in levels:
                print('Parse incomplete. Some notes not assigned to levels.')
                exit()
#            print('levels', levels)
            maxLevel = max(levels)
            # create a part in the illustration for each level and assign it a number
            n = maxLevel+1
            while n > 0:
                illustration.append(stream.Part())
                n += -1
            for num,part in enumerate(illustration.parts):
                # part number
                part.partNum = num
            # create a measure in each part of the illustration
            measures = len(notes)
#            print('measures', measures)
            n = measures
#            while n > 0:
#                for part in illustration.parts:
#                    part.append(stream.Measure())
#                n += -1
#            print(illustration.parts[0].measures)
            # function to add note to the correct levels
            def addNoteToIllustration(note, illustration):
                lev = note.rule.level
                meas = note.index+1
                for part in illustration.parts:
#                    print('here: level, partNum, measure', lev, part.partNum, meas)
                    if lev == part.partNum:
#                        note.lyric = note.rule.name
#                        print('note offset', note.offset)
                        part.insert(note.offset, note)
#                        part.measure(str(meas)).append(note) # need to figure in the note offset
                    if lev < part.partNum:
 #                       note.lyric = None
                        part.insert(note.offset, note)
#                        part.measure(str(meas)).append(note) # need to figure in the note offset
            # populate the illustration parts
            for n in notes:
                addNoteToIllustration(n, illustration)
      
            illustration.show()   
            # exit after showing the first parse, for testing
            exit()
 
    def testGenerabilityFromLevels(parse):
        '''Given a parse in which rule levels have been assigned (perhaps by the student),
        determine whether the line is generable in that way.'''
        if parse.lineType == 'bass':
            pass
        if parse.lineType == 'primary':
            pass
        if parse.lineType == 'generic':
            pass
        pass
        
    def collectParses(self):
        '''collect all the attempted parses of a line from Parser (self.parses) 
        and discard any that have errors and thus failed'''
        failedParses = []
        for key in self.parseErrorsDict:
            if self.parseErrorsDict[key] != []:
                failedParses.append(key)
        
        # remove parses that have errors:
        self.parses = [parse for parse in self.parses if self.parseErrorsDict[parse.label] == []]
        
        # remove parses that have the same basic arc as another parse
        # because of creation order, preference given to inference methods 0-4
        arcBasicCandidates = []
        prunedParseSet = []
        for prs in self.parses:
#            print('basic arc', prs.arcBasic)
            if prs.arcBasic not in arcBasicCandidates:
                arcBasicCandidates.append(prs.arcBasic)
                prunedParseSet.append(prs)
        self.parses = prunedParseSet
#        for prs in self.parses:
#            print('new basic arc', prs.arcBasic)
        
        for parse in self.parses:
            if parse.lineType == 'primary': self.Pinterps.append(parse)    
            elif parse.lineType == 'bass': self.Binterps.append(parse)    
            elif parse.lineType == 'generic': self.Ginterps.append(parse)    
        if self.Pinterps: self.interpretations['primary'] = self.Pinterps
        if self.Binterps: self.interpretations['bass'] = self.Binterps
        if self.Ginterps: self.interpretations['generic'] = self.Ginterps

        # set generability properties
        if self.Pinterps:
            self.isPrimary = True
        else: self.isPrimary = False
        if self.Binterps:
            self.isBass = True
        else: self.isBass = False
        if self.Ginterps:
            self.isGeneric = True
        else: self.isGeneric = False
    
        # if all parses have failed, add a report to self.errors if there aren't errors already recorded
        if self.isPrimary == False and self.isBass == False and self.isGeneric == False and not self.errors:
            error = 'This line cannot be generated.'
            self.errors.append(error)

    def selectPreferredParses(self):
        '''input a list of successful interpretations from Parser (self.parses)
        and remove those that do not conform to cognitive preference rules'''

        # primary upper lines
        # find those that have the same scale degree for S2 
        threelines = [interp for interp in self.Pinterps if interp.S2Degree == '3']
        fivelines = [interp for interp in self.Pinterps if interp.S2Degree == '5']
        eightlines = [interp for interp in self.Pinterps if interp.S2Degree == '8']
        # get the indexes of that degree 
        threelineCands = [interp.arcBasic[0] for interp in threelines]
        fivelineCands = [interp.arcBasic[0] for interp in fivelines]
        eightlineCands = [interp.arcBasic[0] for interp in eightlines]
        # look for arcs that connect pairs of those indexes (as repetitions)
        ints = pairwise(fivelineCands)
        # create a list of interpretations that will be purged
        labelsToPurge = []

        # TODO Westergaard p. 112: prefer S notes onbeat (esp S2)
        # TODO implement Westergaard cognitive preferences, sections 4.2, 4.4, and 5.3
            # get local offset of each S pitch: prefer as many offset==0.0 as possible
        
        # just hang onto the earliest S2 candidates:
#        for pint in threelines: print(pint.label, pint.S2Index, pint.arcBasic)
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
        self.Pinterps = [interp for interp in self.Pinterps if interp.label not in labelsToPurge]

        # TODO are there options for the placement of S3? if so, coordinate with a bass line
        # redefine Pinterps after purging
        # TODO find the positions of the end of S3 (sd2) in upper lines
        S3PenultCands = [interp.arcBasic[-2] for interp in self.Pinterps] 
            
        # bass lines
        labelsToPurge = []
#        bassS3Degree = self.line.notes[interp.S3Index].csd.value
        lowfives = [interp for interp in self.Binterps if self.notes[interp.S3Index].csd.value == -3]
        highfives = [interp for interp in self.Binterps if self.notes[interp.S3Index].csd.value == 4]
        lowfiveCands = [interp.arcBasic[1] for interp in lowfives]
        highfiveCands = [interp.arcBasic[1] for interp in highfives]
        # choose an S3 that's integrated or immediately preceding
        # given two options, choose the later if there is a potential repetition of S2 between them
        # can this be negotiated earlier in the parse?

                # currently there is no preference where S3 occurs in a bass line
                # TODO: eventually this must be replaced by a preference for
                # consonant coordination with an S3 in the upper line: 
                # either simultaneous with or subsequent to sd2
                # TODO: using the reversed buffer is too radical, 
                # since it would prefer the second note of a repetition as S3
                # What about removing a candidate if it has the same sole dependent as an earlier candidate? NO

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
        self.Binterps = [interp for interp in self.Binterps if interp.label not in labelsToPurge]

        # if there are still several candidates for S3,
        # prefer ones in which S3 occurs on the beat 
        allfivesOnbeat = [five for five in self.Binterps if self.notes[five.S3Index].beat == 1.0]
        if len(self.Binterps) > len(allfivesOnbeat) and len(allfivesOnbeat) != 0:
            for interp in self.Binterps:
                if self.notes[interp.S3Index].beat != 1.0:
                    labelsToPurge.append(interp.label)        
        self.Binterps = [interp for interp in self.Binterps if interp.label not in labelsToPurge]
        
        # if there are two candidates for S3 and one can be an immediate repetition, prefer that one 
        preferredBassS3 = None
        labelsToPurge = []
        for interp in self.Binterps:
            for arc in interp.arcs:
                if arc == [interp.S3Index, interp.S3Index+1]:
                    preferredBassS3 = interp.S3Index
        if preferredBassS3 != None:
            for interp in self.Binterps:
                if interp.S3Index == preferredBassS3+1:
                    labelsToPurge.append(interp.label)
        self.Binterps = [interp for interp in self.Binterps if interp.label not in labelsToPurge]
                
        # update the list of parses and the dictionary of parses
        self.parses = self.Pinterps + self.Binterps + self.Ginterps
        self.interpretations['primary'] = self.Pinterps
        self.interpretations['bass'] = self.Binterps
        self.interpretations['generic'] = self.Ginterps

        return self

def pairwise(span):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = itertools.tee(span)
    next(b, None)
    zipped = zip(a, b)
    return list(zipped)
    
def shiftBuffer(stack, buffer):
    nextnote = buffer[0]
    buffer.pop(0)
    stack.append(nextnote)

def shiftStack(stack, buffer):
    lastnote = stack[-1]
    stack.pop(-1)
    buffer.insert(0, lastnote)

def isTriadMember(note, stufe, context=None):
    # determine whether a note belongs to a framing triad, given a note
    # stufe value can be used to check membership in a nontonic triad
    # e.g., using stufe = 4 will look for pitches in the dominant triad
    # will need to have a context reference (e.g., measure in 3rd species)
    if (note.csd.value - stufe) % 7 in {0, 2, 4}:
        return True
    else: return False

def isTriadicSet(pitchList):
    # tests whether a set of notes makes a major, minor or diminished triad
    isTriadicSet = False
    pairs = itertools.combinations(pitchList, 2) 
    for pair in pairs:
        int = interval.Interval(pair[0], pair[1]).simpleName
        rules = [int[-1] in ['2','7'],
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
        else: return False

def isSemiSimpleInterval(n1, n2):
        # input two notes with pitch
        lin_int = interval.Interval(n1, n2)
        if lin_int.semiSimpleNiceName == lin_int.niceName :
            return True
        else: return False

def isLinearUnison(n1, n2):
        # input two notes with pitch
        lin_int = interval.Interval(n1, n2)
        if lin_int.name in {'P1'}:
            return True
        else: return False

def isDiatonicStep(n1, n2):
        # input two notes with pitch
        lin_int = interval.Interval(n1, n2)
        if lin_int.name in {"m2", "M2"}:
            return True
        else: return False

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
        else: return False

def isNeighboring(arc, notes):
    # accepts an arcList of line indices and determines whether a valid N structure
    i = notes[arc[0]]
    j = notes[arc[1]]
    k = notes[arc[2]]
    rules1 = [len(arc) == 3,
#            isTriadMember(i) == True,
#            isTriadMember(k) == True,
            isDiatonicStep(i,j) == True,
            isDiatonicStep(j,k) == True,
            k.csd.value == i.csd.value]
    rules2 = [k.csd.direction == 'bidirectional',
            j.csd.value > k.csd.value and k.csd.direction == 'descending',
            j.csd.value < k.csd.value and k.csd.direction == 'ascending']
    if all(rules1) and any (rules2):
        # could add conditions to add label modifier: upper, lower
        return True
    else: return False

def isPassing(arc, notes):
    # accepts an arcList of line indices and determines whether a valid Pstructure
    # can probably assume that first and last pitches are in tonic triad, but
    span = len(arc)
    i = notes[arc[0]]
    j = notes[arc[1]]
    k = notes[arc[-1]]
    if i.csd.value > k.csd.value:
        passdir = 'falling'
    else: passdir = 'rising'
    ints = pairwise(arc)
    for int in ints:
        n1 = notes[int[0]]
        n2 = notes[int[1]]
        rules1 = [isDiatonicStep(n1, n2) == True]
        rules2 = [passdir == 'falling' and n1.csd.direction in ('bidirectional', 'descending'),
                passdir == 'rising' and n1.csd.direction in ('bidirectional', 'ascending')]
        rules3 = [passdir == 'falling' and n1.csd.value > n2.csd.value,
                passdir == 'rising' and n1.csd.value < n2.csd.value]
        if all(rules1) and any (rules2) and any(rules3):
            continue
        else:
#            print('This arc is not a passing motion')            
            return False
    return True

def isRepetition(arc, notes):
    # accepts an arcList of line indices and determines whether a valid R structure
    # can probably assume that first and last pitches are in tonic triad, but
    # label = 'repetition'
    i = notes[arc[0]]
    j = notes[arc[1]]
    rules1 = [#isTriadMember(i) == True,
            #isTriadMember(j) == True,
            j.csd.value == i.csd.value]
    if all(rules1):
        # could add conditions to add label modifier: upper, lower
        return True
    else: return False
    
def arcGenerateTransition(i, part, arcs, stack):
    # i is a note.index, the last transitional element before a righthead
    # assembles an arc after a righthead is detected
    # tests for arc type in self.line.notes
    # also assigns a label
        # after getting the elements, find the interval directions
    elements = []
    for elem in (part.flat.notes[i].dependency.lefthead, i, part.flat.notes[i].dependency.righthead): elements.append(elem)
    for d in part.flat.notes[i].dependency.dependents: # codependents
        if d < i and part.flat.notes[d].dependency.lefthead == part.flat.notes[i].dependency.lefthead:
            elements.append(d)
    thisArc = sorted(elements)
    arcs.append(thisArc)
    arcPurge(thisArc, stack)

def arcGenerateRepetition(j, part, arcs, stack):
    # j is a note.index of the repetition
    # assembles an arc after a repetition is detected
    # tests for arc type in self.line.notes
    elements = [elem for elem in (part.flat.notes[j].dependency.lefthead, j)]
    thisArc = elements
    arcs.append(thisArc)
    arcPurge(thisArc, stack)

def arcExtendTransition(notes, arc, extensions):
    # extentions is a list of notes
    # extends an arc, usually into the next timespan
    # clean out the old arc
    removeDependenciesFromArc(notes, arc)
    # add the extensions and put in ascending order
    arc = sorted(arc + extensions)
    # reset the dependencies in the extended arc
    addDependenciesFromArc(notes, arc)

def arcPurge(arc, stack):
    # purge stack elements in arc that have lefthead or lefthead and righthead
    if len(arc) >= 3:
        for trans in arc[1:-1]:
            for pos,note in enumerate(stack):
                if note.index == trans:
                    stack.pop(pos)
    if len(arc) == 2:
        trans = arc[1]
        for pos,note in enumerate(stack):
            if note.index == trans:
                stack.pop(pos)    
                
def pruneOpenHeads(notes, openheads):
    '''Prune direct repetitions from end of the list of open head indices'''
    print(openheads)
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
    '''checks to see whether a note at index i is the terminal of any nonbasic arc'''
    isTerminal = False
    for arc in arcs:
        if i == arc[0] or i == arc[-1]:
            isTerminal = True
    return isTerminal

def isEmbeddedInArc(i, arcs):
    '''checks to see whether a note at index i is embedded within any nonbasic arc'''
    isEmbedded = False
    for arc in arcs:
        if arc[0] < i < arc[-1]:
            isEmbedded = True
    return isEmbedded

def areArcTerminals(h, i, arcs):
    '''checks to see whether a head at index h and a note at index i are the terminals of any nonbasic arc'''
    areTerminals = False
    for arc in arcs:
        if h == arc[0] and i == arc[-1]:
            areTerminals = True
    return areTerminals
    
def arcLength(arc):
    '''returns the length of an arc measured as number of consecutions spanned'''
    length = arc[-1] - arc[0]
    return length
    

##########################################################################################
if __name__ == "__main__":
    pass
