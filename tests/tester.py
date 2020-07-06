from music21 import *
import westerparse
import signal
import time
import os
import glob 

if __name__ == "__main__":
    # self_test code
    pass

#    source = 'TestScoresXML/snarrenberg_cmin.musicxml'

    # user inputs
    # accept a source file (score) from the user
#    source = 'TestScoresXML/Bass01.musicxml' # Fux Dorian
#    source = 'TestScoresXML/Bass02.musicxml' # Krumhansl-Schmuckler gives wrong key
#    source = 'TestScoresXML/Bass03.musicxml'
#    source = 'TestScoresXML/Bass04.musicxml' # Krumhansl-Schmuckler gives wrong key
#    source = 'TestScoresXML/Bass05.musicxml'
#    source = 'TestScoresXML/Bass06.musicxml'
#    source = 'TestScoresXML/Bass21.musicxml'

#    source = 'TestScoresXML/Primary01.musicxml' # Fux Ionian
#    source = 'TestScoresXML/Primary02.musicxml'
#    source = 'TestScoresXML/Primary03.musicxml'
#    source = 'TestScoresXML/Primary04.musicxml'
#    source = 'TestScoresXML/Primary05.musicxml'
#    source = 'TestScoresXML/Primary06.musicxml'
#    source = 'TestScoresXML/Primary20.musicxml' # Krumhansl-Schmuckler gives wrong key
#    source = 'TestScoresXML/Primary21.musicxml' # line has no clear key

#    source = 'TestScoresXML/Generic01.musicxml'
#    source = 'TestScoresXML/Generic02.musicxml'

#    source = 'TestScoresXML/FirstSpecies01.musicxml'
#    source = 'TestScoresXML/FirstSpecies02.musicxml'
    source = 'TestScoresXML/FirstSpecies03.musicxml'
#    source = 'TestScoresXML/FirstSpecies04.musicxml'
#    source = 'TestScoresXML/FirstSpecies05.musicxml'
#    source = 'TestScoresXML/FirstSpecies10a.musicxml'
#    source = 'TestScoresXML/FirstSpecies20.musicxml'
#    source = 'TestScoresXML/WP141.musicxml'

#    source = 'TestScoresXML/SecondSpecies01.musicxml'
#    source = 'TestScoresXML/SecondSpecies02.musicxml'
#    source = 'TestScoresXML/SecondSpecies03.musicxml' # not generable
#    source = 'TestScoresXML/SecondSpecies20.musicxml' # not generable
#    source = 'TestScoresXML/SecondSpecies21.musicxml' # not generable
#    source = 'TestScoresXML/SecondSpecies22.musicxml' # not generable

#    source = 'TestScoresXML/ThirdSpecies01.musicxml'    # vl errors
#    source = 'TestScoresXML/ThirdSpecies02.musicxml'    
#    source = 'TestScoresXML/ThirdSpecies03.musicxml'    
#    source = 'TestScoresXML/ThirdSpecies04.musicxml'    # vl error
#    source = 'TestScoresXML/ThirdSpecies05.musicxml'    # completion of Westergaard p. 136 exercise 4
#    source = 'TestScoresXML/ThirdSpecies06.musicxml'    
#    source = 'TestScoresXML/ThirdSpecies07.musicxml'    # vl errors
#    source = 'TestScoresXML/ThirdSpecies08.musicxml'    # not currently generable
#    source = 'TestScoresXML/ThirdSpecies09.musicxml'    

#    source = 'TestScoresXML/FourthSpecies01.musicxml'
#    source = 'TestScoresXML/FourthSpecies02.musicxml'   # vl error
#    source = 'TestScoresXML/FourthSpecies03.musicxml'   # vl error
#    source = 'TestScoresXML/FourthSpecies04.musicxml'   # vl errors
#    source = 'TestScoresXML/FourthSpecies20.musicxml'
#    source = 'TestScoresXML/FourthSpecies21.musicxml'
#    source = 'TestScoresXML/FourthSpecies22.musicxml'

#    source = 'TestScoresXML/HarmonicSecondSpecies01.musicxml'

#    source = 'TestScoresXML/CombinedSpecies1234.musicxml'

#    source = 'TestScoresXML/FourthSpeciesTripleMeterTest.musicxml'

#    source = 'TestScoresXML/Test200.musicxml'
#    source = 'TestScoresXML/Test201.musicxml'

#    source = 'TestScoresXML/Nursery01.musicxml'
#    source = 'TestScoresXML/Nursery02.musicxml'
#    source = 'TestScoresXML/Nursery03.musicxml'
#    source = 'TestScoresXML/Nursery04.musicxml'

#    source = 'TestScoresXML/chorale336.musicxml'
#    source = 'TestScoresXML/Christus, der ist mein Leben.musicxml'

#    source = 'TestScoresXML/BachKunst.musicxml'
#    source = 'TestScoresXML/WTC_I,_Fugue_in_C_Subject.musicxml'
#    source = 'TestScoresXML/WTC_I,_Fugue_in_d_sharp,_subject.musicxml' # fails K-S key assignment
#    source = 'TestScoresXML/WTC_I,_Fugue_in_F_sharp,_Subject.musicxml'

#    source = 'TestScoresXML/BeethovenOdeToJoy4thPhrase.musicxml'

#    source = 'TestScoresXML/2019_12_10T15_37_10_018Z.musicxml'


#    source = 'WesterParseCorpora/WesterParseLineCorpus/Westergaard070c.musicxml'
#    source = 'TestScoresXML/Westergaard100k.musicxml'
#    source = 'TestScoresXML/WestergaardP111c.musicxml'
#    source = 'TestScoresXML/WestergaardP111d.musicxml'
#    source = 'TestScoresXML/Westergaard105.musicxml'
#    source = 'TestScoresXML/Westergaard106f.musicxml'
#    source = 'TestScoresXML/Westergaard115i.musicxml'
#    source = 'TestScoresXML/Westergaard143.musicxml'
#    source = 'TestScoresXML/Westergaard161a.musicxml'
#    source = 'TestScoresXML/Westergaard113k.musicxml'
#    source = 'TestScoresXML/Westergaard100k.musicxml'
#    source = 'TestScoresXML/Westergaard107a.musicxml'
#    source = 'TestScoresXML/Westergaard121a.musicxml'

#    source = 'TestScoresXML/ChromaTest.musicxml'

#    source = 'TestScoresXML/chorale066.6.musicxml'

#    source = 'TestScoresXML/'
    
#    source = 'TestScoresXML/Third_Species_Line_Test_0.musicxml'

#    source = 'WesterParseCorpora/WesterParseLineCorpus/WP017.musicxml'


#    source = '/Library/Frameworks/Python.framework/Versions/3.6/lib/python3.6/site-packages/music21/corpus/essenFolksong/zuccal0.abc'

    # allow user to select what kind of checking to do:
    # (1) just parse the lines
    # (2) just check the voice leading
    # (3) both

    verify = 1

    def tester(source, verify):
								if verify == 1: # tests for generability as any type of line
												westerparse.evaluateLines(source, show=None)
								elif verify == 2:
												westerparse.evaluateCounterpoint(source, report=True)
								
								elif verify == 10: # tests for generability as harmonic counterpoint
												westerparse.evaluateLines(source, show=None, harmonicSpecies=True, offsetPredominant=36.0, offsetDominant=44.0, offsetClosingTonic=48.0, keynote='E', mode='major')

								elif verify == 3:
												westerparse.evaluateLines(source, show=None)
												westerparse.evaluateCounterpoint(source, report=True)
								elif verify == 4:
												westerparse.evaluateLines(source, show='show')
												westerparse.evaluateCounterpoint(source, report=True)
								elif verify == 41:
												westerparse.evaluateLines(source, show='writeToLocal')
												westerparse.evaluateCounterpoint(source, report=True)

								elif verify == 5:
												westerparse.evaluateLines(source, show='show')
								elif verify == 51:
												context.evaluateLines(source, show='writeToLocal')
								elif verify == 52:
												context.evaluateLines(source, show='writeToPng')

								elif verify == 6:
												context.evaluateLines(source, show=None, partSelection=0, partLineType='primary')
								elif verify == 16:
												context.evaluateLines(source, show='show', partSelection=0, partLineType='primary')
								elif verify == 7:
												context.evaluateLines(source, show=None, partSelection=-1, partLineType='bass')
								elif verify == 17:
												context.evaluateLines(source, show='show', partSelection=-1, partLineType='bass')
								elif verify == 8:
												context.evaluateLines(source, show=None, partSelection=0, partLineType='generic')
								elif verify == 18:
												context.evaluateLines(source, show='show', partSelection=0, partLineType='generic')
								elif verify == 9:
												context.evaluateLines(source, show=None, partSelection=0, partLineType=None)
								elif verify == 19:
												context.evaluateLines(source, show='show', partSelection=0, partLineType=None)
								elif verify == 28:
												context.evaluateLines(source, show='show', partSelection=1, partLineType='generic')
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

#     exx = converter.parse(source)
#     mf = midi.translate.streamToMidiFile(exx)
#     mf.open('WesterParseCorpora/WesterParseLineCorpus/midi.mid', 'wb')
#     mf.write()
#     mf.close()
#     os.system("open -a /Applications/MIDIPlayer\ X.app WesterParseCorpora/WesterParseLineCorpus/midi.mid")

#    vltester(source, keynote='C', mode='major')
    tester(source, 1)
#    context.evaluateLines(source, show=None, report=True)
    
#    context.evaluateLines(source, show='show', partSelection=None, partLineType=None)
    
#    reporter(source, verify)
#    context.evaluateCounterpoint(source, keynote='B-', mode='major')
#    context.evaluateLines(source, show=None, partSelection=0, partLineType=None, keynote='B-', mode='major')
#    context.evaluateLines(source, show=None, partSelection=0, partLineType=None)
#    context.evaluateLines(source, show=None, partSelection=0, partLineType='generic')
#    context.evaluateLines(source, show=None, partSelection=0, partLineType='primary')
#    context.evaluateLines(source, show=None, partSelection=0, partLineType='bass')
