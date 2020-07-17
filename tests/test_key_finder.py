import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import westerparse
import keyFinder

#source = 'TestScoresXML/Bass01.musicxml'
source = 'TestScoresXML/2020_07_17T19_22_29_948Z.musicxml'
#    source = 'TestScoresXML/Bass02.musicxml' # Krumhansl-Schmuckler gives wrong key
#    source = 'TestScoresXML/Bass03.musicxml'
#    source = 'TestScoresXML/Bass04.musicxml' # Krumhansl-Schmuckler gives wrong key
#    source = 'TestScoresXML/Bass05.musicxml'
#    source = 'TestScoresXML/Bass06.musicxml'
#    source = 'TestScoresXML/Bass21.musicxml'
#    source = 'TestScoresXML/Bass02.musicxml'
#    source = 'TestScoresXML/Primary01.musicxml'
#    source = 'TestScoresXML/Primary04.musicxml'
#    source = 'TestScoresXML/Primary20.musicxml' # Krumhansl-Schmuckler gives wrong key
#    source = 'TestScoresXML/Primary21.musicxml' # Krumhansl-Schmuckler gives wrong key
#    source = 'TestScoresXML/FirstSpecies01.musicxml'
#    source = 'TestScoresXML/FirstSpecies04.musicxml'
#    source = 'TestScoresXML/SecondSpecies22.musicxml'
#    source = 'TestScoresXML/ThirdSpecies02.musicxml'
#    source = 'TestScoresXML/FourthSpecies20.musicxml'
#    source = 'TestScoresXML/HarmonicSecondSpecies01.musicxml'
#    source = 'TestScoresXML/WTC_I,_Fugue_in_d_sharp,_subject.musicxml' # fails K-S key assignment
#    source = 'TestScoresXML/BeethovenOdeToJoy4thPhrase.musicxml'
#    source = 'TestScoresXML/2020_04_24T16_22_17_785Z.musicxml'
#    source = 'TestScoresXML/2020_04_25T22_03_04_858Z.musicxml'
#    source = 'TestScoresXML/2020_04_27T16_06_46_776Z.musicxml'
#    source = 'TestScoresXML/2020_04_27T18_21_12_217Z.musicxml'
#    source = 'TestScoresXML/2020_04_29T19_28_50_357Z.musicxml'
#    source = 'TestScoresXML/2020_05_22T14_39_18_497Z.musicxml'

gxt = westerparse.makeGlobalContext(source)

k = keyFinder.inferKey(gxt)
print(k)
