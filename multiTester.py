from music21 import *
import context
import vlChecker
import signal
import time
 

if __name__ == "__main__":
    # self_test code
    pass

    sources = ['TestScoresXML/Bass01.musicxml', # Fux Dorian
        'TestScoresXML/Bass02.musicxml', # Krumhansl-Schmuckler gives wrong key
        'TestScoresXML/Bass03.musicxml',
        'TestScoresXML/Bass04.musicxml', # Krumhansl-Schmuckler gives wrong key
        'TestScoresXML/Bass05.musicxml',
        'TestScoresXML/Bass06.musicxml',

        'TestScoresXML/Primary01.musicxml', # Fux Ionian
        'TestScoresXML/Primary02.musicxml',
        'TestScoresXML/Primary03.musicxml',
        'TestScoresXML/Primary04.musicxml',
        'TestScoresXML/Primary05.musicxml',
        'TestScoresXML/Primary06.musicxml',

        'TestScoresXML/Generic01.musicxml',
        'TestScoresXML/Generic02.musicxml',

        'TestScoresXML/FirstSpecies01.musicxml',
        'TestScoresXML/FirstSpecies02.musicxml',
        'TestScoresXML/FirstSpecies03.musicxml',
        'TestScoresXML/FirstSpecies04.musicxml',
        'TestScoresXML/FirstSpecies05.musicxml',
        'TestScoresXML/FirstSpecies10.musicxml',

        'TestScoresXML/SecondSpecies01.musicxml',
        'TestScoresXML/SecondSpecies02.musicxml',

        'TestScoresXML/ThirdSpecies01.musicxml',    
        'TestScoresXML/ThirdSpecies02.musicxml',    
        'TestScoresXML/ThirdSpecies03.musicxml',    
        'TestScoresXML/ThirdSpecies04.musicxml',    
        'TestScoresXML/ThirdSpecies05.musicxml',    
        'TestScoresXML/ThirdSpecies06.musicxml',    
        'TestScoresXML/ThirdSpecies07.musicxml',    
#        'TestScoresXML/ThirdSpecies08.musicxml',    

        'TestScoresXML/FourthSpecies01.musicxml',
        'TestScoresXML/FourthSpecies02.musicxml',
        'TestScoresXML/FourthSpecies03.musicxml',
        'TestScoresXML/FourthSpecies04.musicxml',

        'TestScoresXML/Third_Species_Line_Test_0.musicxml'
    ]
    # allow user to select what kind of checking to do:
    # (1) just parse the lines
    # (2) just check the voice leading
    # (3) both

    verify = 1

    def tester(source, verify):
								if verify == 1: # tests for generability as any type of line
												context.evaluateLines(source, show=None)
								elif verify == 2:
												context.evaluateCounterpoint(source, report=True)
								
								elif verify == 10: # tests for generability as harmonic counterpoint
												context.evaluateLines(source, show=None, harmonicSpecies=True, offsetPredominant=36.0, offsetDominant=44.0, offsetClosingTonic=48.0, keynote='E', mode='major')

								elif verify == 3:
												context.evaluateLines(source, show=None)
												context.evaluateCounterpoint(source, report=True)
								elif verify == 4:
												context.evaluateLines(source, show='show')
												context.evaluateCounterpoint(source, report=True)
								elif verify == 41:
												context.evaluateLines(source, show='writeToLocal')
												context.evaluateCounterpoint(source, report=True)

								elif verify == 5:
												context.evaluateLines(source, show='show')
								elif verify == 51:
												context.evaluateLines(source, show='writeToLocal')

								elif verify == 6:
												context.evaluateLines(source, show=None, partSelection=0, partLineType='primary')
								elif verify == 16:
												context.evaluateLines(source, show='show', partSelection=0, partLineType='primary')
								elif verify == 7:
												context.evaluateLines(source, show=None, partSelection=-1, partLineType='bass')
								elif verify == 8:
												context.evaluateLines(source, show=None, partSelection=0, partLineType='generic')
								elif verify == 18:
												context.evaluateLines(source, show='show', partSelection=0, partLineType='generic')
								else:
												print('ERROR: No valid evaluation option selected.')
												
    def reporter(source, verify):
        print('Input:', source)
        cxt = context.makeGlobalContext(source)
        print('Inferred key:', cxt.key.nameString)
        for part in cxt.parts:
            print('Part', part.partNum, 'species:', part.species)
        tester(source, verify)
												
    def vltester(source, keynote, mode):
												context.evaluateCounterpoint(source, report=True, keynote=keynote, mode=mode, validateKey=False)
				
    def multiTester(sources, verify):
        for source in sources:
            print('filename:', source)
#            context.evaluateLines(source, show=None, partSelection=0, partLineType=None)
            tester(source, verify)

#    vltester(source, keynote='C', mode='major')
    multiTester(sources, 1)
#    reporter(source, verify)
#    context.evaluateCounterpoint(source, keynote='B-', mode='major')
#    context.evaluateLines(source, show=None, partSelection=0, partLineType=None, keynote='B-', mode='major')
#    context.evaluateLines(source, show=None, partSelection=0, partLineType=None)
#    context.evaluateLines(source, show=None, partSelection=0, partLineType='generic')
#    context.evaluateLines(source, show=None, partSelection=0, partLineType='primary')
#    context.evaluateLines(source, show=None, partSelection=0, partLineType='bass')
