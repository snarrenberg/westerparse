#!/Users/snarrenberg/opt/anaconda3/envs/westerparse/bin/python
import os
import sys
sys.path.insert(0, os.path.abspath('../../westerparse'))
import glob
from pprint import pprint as pp
import itertools


from westerparse import westerparse
from music21 import *
if __name__ == "__main__":
    # self_test code
    pass

    # source = 'TestScoresXML/snarrenberg_cmin.musicxml'

    # source = 'TestScoresXML/Bass01.musicxml' # Fux Dorian
    # source = 'TestScoresXML/Bass02.musicxml' # Krumhansl-Schmuckler gives wrong key
    # source = 'TestScoresXML/Bass03.musicxml'
    # source = 'TestScoresXML/Bass04.musicxml' # Krumhansl-Schmuckler gives wrong key
    # source = 'TestScoresXML/Bass05.musicxml'
    # source = 'TestScoresXML/Bass06.musicxml'
    # source = 'TestScoresXML/Bass21.musicxml'

    # source = 'TestScoresXML/Primary01.musicxml' # Fux Ionian
    # source = 'TestScoresXML/Primary02.musicxml'
    # source = 'TestScoresXML/Primary03.musicxml'
    # source = 'TestScoresXML/Primary04.musicxml'
    # source = 'TestScoresXML/Primary05.musicxml'
    # source = 'TestScoresXML/Primary06.musicxml'
    # source = 'TestScoresXML/Primary16.musicxml'
    # source = 'TestScoresXML/Primary20.musicxml' # Krumhansl-Schmuckler gives wrong key
    # source = 'TestScoresXML/Primary21.musicxml' # line has no clear key

    # source = 'TestScoresXML/Generic01.musicxml'
    # source = 'TestScoresXML/Generic02.musicxml'

    # source = 'TestScoresXML/FirstSpecies01.musicxml'
    # source = 'TestScoresXML/FirstSpecies02.musicxml'
    # source = 'TestScoresXML/FirstSpecies03.musicxml'
    # source = 'TestScoresXML/FirstSpecies04.musicxml'
    # source = 'TestScoresXML/FirstSpecies05.musicxml'
    # source = 'TestScoresXML/FirstSpecies10a.musicxml'
    # source = 'TestScoresXML/FirstSpecies20.musicxml'
    # source = 'TestScoresXML/WP141.musicxml'

    # source = 'TestScoresXML/SecondSpecies01.musicxml'
    # source = 'TestScoresXML/SecondSpecies02.musicxml'
    # source = 'TestScoresXML/SecondSpecies03.musicxml' # not generable
    # source = 'TestScoresXML/SecondSpecies20.musicxml' # not generable
    # source = 'TestScoresXML/SecondSpecies21.musicxml' # not generable
    # source = 'TestScoresXML/SecondSpecies22.musicxml' # not generable

    # source = 'TestScoresXML/ThirdSpecies01.musicxml'    # vl errors
    # source = 'TestScoresXML/ThirdSpecies02.musicxml'
    # source = 'TestScoresXML/ThirdSpecies03.musicxml'
    # source = 'TestScoresXML/ThirdSpecies04.musicxml'    # vl error
    # source = 'TestScoresXML/ThirdSpecies05.musicxml'    # completion of Westergaard p. 136 exercise 4
    # source = 'TestScoresXML/ThirdSpecies06.musicxml'
    # source = 'TestScoresXML/ThirdSpecies07.musicxml'    # vl errors
    # source = 'TestScoresXML/ThirdSpecies08.musicxml'    # not currently generable
    # source = 'TestScoresXML/ThirdSpecies09.musicxml'
    # source = 'TestScoresXML/ThirdSpecies040.musicxml'
    # source = 'TestScoresXML/ThirdSpecies101.musicxml'

    #    source = 'TestScoresXML/FourthSpecies01.musicxml'
    # source = 'TestScoresXML/FourthSpecies02.musicxml'   # vl error
    # source = 'TestScoresXML/FourthSpecies03.musicxml'   # vl error
    # source = 'TestScoresXML/FourthSpecies04.musicxml'   # vl errors
    # source = 'TestScoresXML/FourthSpecies20.musicxml'
    # source = 'TestScoresXML/FourthSpecies21.musicxml'
    # source = 'TestScoresXML/FourthSpecies22.musicxml'

    # source = 'TestScoresXML/HarmonicSecondSpecies01.musicxml' # 10, 12
    # source = 'TestScoresXML/HarmonicSecondSpecies02.musicxml' # 8, 10
    # source = 'TestScoresXML/HarmonicSecondSpecies03.musicxml'  # 8, 14 initial tonic too short
    # source = 'TestScoresXML/harmonic_species1.musicxml' # 8, 10
    # source = 'TestScoresXML/harmonic_species2.musicxml'  # 11, 13
    # source = 'TestScoresXML/harmonic_species2_mistakes.musicxml'
    # source = 'TestScoresXML/harmonic_species3.musicxml'  #  7, 9
    # source = 'TestScoresXML/harmonic_species3_mistakes.musicxml'

    # source = 'TestScoresXML/CombinedSpecies1234.musicxml'

    # source = 'TestScoresXML/FourthSpeciesTripleMeterTest.musicxml'

    # source = 'TestScoresXML/Test200.musicxml'
    # source = 'TestScoresXML/Test201.musicxml'

    # source = 'TestScoresXML/Nursery01.musicxml'
    # source = 'TestScoresXML/Nursery02.musicxml'
    # source = 'TestScoresXML/Nursery03.musicxml'
    # source = 'TestScoresXML/Nursery04.musicxml'

    # source = 'TestScoresXML/chorale336.musicxml'
    # source = 'TestScoresXML/Christus, der ist mein Leben.musicxml'

    # source = 'TestScoresXML/BachKunst.musicxml'
    # source = 'TestScoresXML/WTC_I,_Fugue_in_C_Subject.musicxml'
    # source = 'TestScoresXML/WTC_I,_Fugue_in_d_sharp,_subject.musicxml' # fails K-S key assignment
    # source = 'TestScoresXML/WTC_I,_Fugue_in_F_sharp,_Subject.musicxml'

    # source = 'TestScoresXML/BeethovenOdeToJoy4thPhrase.musicxml'

    # source = 'TestScoresXML/2020_07_20T15_56_50_689Z.musicxml'
    # source = 'TestScoresXML/2020_07_20T17_15_38_905Z.musicxml'
    # source = 'TestScoresXML/2020_08_24T20_39_55_774Z.musicxml'
    # source = 'TestScoresXML/2020_09_11T14_43_44_987Z.musicxml'
    # source = 'TestScoresXML/2025_07_17_1114_31494.musicxml'
    # source = 'TestScoresXML/2020_08_26T17_50_33_151Z.musicxml'
    # source = 'TestScoresXML/2020_10_24T14_46_50_334Z.musicxml'
    # source = 'TestScoresXML/2020_09_11T14_43_44_987Z.musicxml'


    # source = 'TestScoresXML/Bass02.musicxml'
    # source = 'TestScoresXML/Westergaard057c.musicxml'
    # source = 'TestScoresXML/Westergaard070d.musicxml'
    # source = 'TestScoresXML/Westergaard100k.musicxml'
    # source = 'TestScoresXML/Westergaard111c.musicxml'
    # source = 'TestScoresXML/Westergaard111d.musicxml'
    # source = 'TestScoresXML/Westergaard105.musicxml'
    # source = 'TestScoresXML/Westergaard106f.musicxml'
    # source = 'TestScoresXML/Westergaard161a.musicxml'
    # source = 'TestScoresXML/Westergaard113k.musicxml'
    # source = 'TestScoresXML/Westergaard100k.musicxml'
    # source = 'TestScoresXML/Westergaard107a.musicxml'
    # source = 'TestScoresXML/Westergaard121a.musicxml'
    # source = 'TestScoresXML/2020_08_26T17_50_33_151Z.musicxml'
    # source = 'TestScoresXML/2020_10_11T20_10_52_188Z.musicxml'
    # source = 'TestScoresXML/2020_10_14T00_42_54_913Z.musicxml'
    # source = 'TestScoresXML/2020_10_14T16_31_54_122Z.musicxml'
    # source = 'TestScoresXML/2020_10_14T19_23_30_946Z.musicxml'
    # source = 'TestScoresXML/2020_10_24T14_46_50_334Z.musicxml'
    # source = 'TestScoresXML/2020_10_26T20_52_55_920Z.musicxml'
    # source = 'TestScoresXML/2020_10_24T04_03_18_019Z.musicxml'
    # source = 'TestScoresXML/2020_10_29T17_51_23_268Z.musicxml'
    # source = 'TestScoresXML/2021_01_19T17_58_09_439Z.musicxml'
    # source = 'TestScoresXML/2021_01_25T22_53_12_206Z.musicxml'
    # source = 'TestScoresXML/ChromaTest.musicxml'
    # source = 'TestScoresXML/2021_03_23T21_47_26_411Z.musicxml'
    # source = 'TestScoresXML/2021_10_13T03_12_23_557Z.musicxml'
    # source = 'TestScoresXML/2021_09_24T22_40_56_941Z.musicxml'
    # source = 'TestScoresXML/2021_10_14T03_07_52_916Z.musicxml'
    # source = 'TestScoresXML/2021_10_26T19_58_05_175Z.musicxml'

    # source = 'TestScoresXML/2022_02_15T19_11_33_693Z.musicxml'
    # source = 'TestScoresXML/WP14/1.musicxml'


    # source = 'TestScoresXML/chorale066.6.musicxml'
    # source = 'TestScoresXML/Christus_der_ist_mein_Leben.musicxml'

#    source = 'TestScoresXML/'

    # source = 'TestScoresXML/Third_Species_Line_Test_0.musicxml'

#    source = 'TestScoresXML/HarmonicSecondSpecies01.musicxml'

    # source = '../examples/corpus/Westergaard100k.musicxml'
    # source = '../examples/corpus/WP205.musicxml'
    # source = 'TestScoresXML/SecondSpecies33.musicxml'
    # source = '../examples/corpus/WP002.musicxml'
    # source = '../examples/corpus/WP008.musicxml'
    # source = '../examples/corpus/Westergaard075a.musicxml'
    # source = '../examples/corpus/WP000.musicxml'
    # source = '../examples/corpus/WP022.musicxml'
    # source = '../examples/corpus/WP309.musicxml'
    # source = '../examples/corpus/WP405.musicxml'
    # source = '../examples/corpus/WP001.musicxml'

    # source = '../examples/corpus/WPH200.musicxml' # 10, 12
    # source = '../examples/corpus/WPH201.musicxml' # 8, 10
    # source = '../examples/corpus/WPH202.musicxml' # ERRORS
    # source = '../examples/corpus/WPH203.musicxml' # 8, 10
    # source = '../examples/corpus/WPH204.musicxml' # 11, 13
    # source = '../examples/corpus/WPH205.musicxml' # 7, 9
    # source = '../examples/corpus/WPH206.musicxml' #
    # source = '../examples/corpus/WPH207.musicxml' #
    # source = '../examples/corpus/WPH208.musicxml' #
    # source = '../examples/corpus/WPH209.musicxml' # 6, 8?

    # source = 'TestScoresXML/2021_09_26T19_30_23_572Z.musicxml'
    # source = 'TestScoresXML/2021_09_24T22_40_56_941Z.musicxml' # FIXED
    # source = 'TestScoresXML/2020_07_27T22_03_17_936Z.musicxml'
    # source = 'TestScoresXML/2020_07_31T21_35_42_273Z.musicxml'
    # source = 'TestScoresXML/2020_08_11T16_59_58_638Z.musicxml'
    # source = 'TestScoresXML/2021_10_02T16_27_59_954Z.musicxml' # NEEDS A SOLUTION!!??
    # source = 'TestScoresXML/2022_05_30T10_08_19_918Z.musicxml'
    # source = 'TestScoresXML/2022_05_30T10_19_29_433Z.musicxml'
    # source = 'TestScoresXML/2022_05_31T18_56_28_644Z.musicxml'
    # source = 'TestScoresXML/2022_06_02T09_19_48_464Z.musicxml'
    # source = 'TestScoresXML/2022_06_07T17_52_57_966Z.musicxml'
    # source = 'TestScoresXML/2025_08_06_1046_19243.musicxml'
    # source = 'TestScoresXML/2025_08_08_1203_41679.musicxml'
    # source = 'TestScoresXML/2025_08_20_1047_37654.musicxml'
    # source = 'TestScoresXML/2025_09_04_1911_50853.musicxml'
    source = 'TestScoresXML/2025_10_30_0859_46322.musicxml'



    def tester(source, verify):
        if verify == 1: # tests for generability as any type of line
            # print(source)
            westerparse.evaluateLines(source, show='html')
        elif verify == 2:
            westerparse.evaluateCounterpoint(source, report='html')
        elif verify == 21:
            westerparse.evaluateCounterpoint(source)

        elif verify == 1111:  # tests for generability as any type of line
            return westerparse.evaluateLines(source, show='html')

        elif verify == 2222:
            return westerparse.evaluateCounterpoint(source, report='html')

        elif verify == 100: # tests for generability as harmonic counterpoint
            westerparse.evaluateLines(source, show='show',
                                      harmonicSpecies=True,
                                      startPredominant=10,
                                      startDominant=12)
        elif verify == 101:
            westerparse.evaluateLines(source, show=None,
                                      harmonicSpecies=True,
                                      startPredominant=10,
                                      startDominant=12)
        elif verify == 110:
            westerparse.evaluateLines(source, show='show',
                                      partSelection=0,
                                      partLineType = 'primary',
                                      harmonicSpecies=True,
                                      startDominant=6)
        elif verify == 111:
            westerparse.evaluateLines(source, show='show',
                                      partSelection=0,
                                      partLineType='primary',
                                      harmonicSpecies=True,
                                      startPredominant=7,
                                      startDominant=9)

        elif verify == 3:
            westerparse.evaluateLines(source, show=None)
            westerparse.evaluateCounterpoint(source, report=True)
        elif verify == 31:
            westerparse.evaluateLines(source, show='show')
            westerparse.evaluateCounterpoint(source, report=True)
        elif verify == 32:
            westerparse.evaluateLines(source, show='writeToLocal')
            westerparse.evaluateCounterpoint(source, report=True)

        elif verify == 5:
            westerparse.evaluateLines(source, show='show')
        elif verify == 51:
            westerparse.evaluateLines(source, show='writeToLocal')
        elif verify == 52:
            westerparse.evaluateLines(source, show='writeToPng')
        elif verify == 53:
            westerparse.evaluateLines(source, show=None)

        elif verify == 6:
            westerparse.evaluateLines(source, show=None,
                                      partSelection=0,
                                      partLineType='primary')
        elif verify == 61:
            westerparse.evaluateLines(source, show='show',
                                      partSelection=0,
                                      partLineType='primary')
        elif verify == 62:
            westerparse.evaluateLines(source, show='showWestergaardParse',
                                  partSelection=0,
                                  partLineType='primary')
        elif verify == 63:
            westerparse.evaluateLines(source, show=None,
                                      partSelection=0,
                                      partLineType='primary',
                                      keynote='A',
                                      mode='major')

        elif verify == 7:
            westerparse.evaluateLines(source, show=None,
                                      partSelection=-1,
                                      partLineType='bass')
        elif verify == 71:
            westerparse.evaluateLines(source, show='show',
                                      partSelection=-1,
                                      partLineType='bass')
        elif verify == 72:
            westerparse.evaluateLines(source, show=None,
                                      partSelection=-1,
                                      partLineType='bass',
                                      keynote='A',
                                      mode='minor')
        elif verify == 8:
            westerparse.evaluateLines(source, show=None,
                                      partSelection=0,
                                      partLineType='generic')
        elif verify == 81:
            westerparse.evaluateLines(source, show='show',
                                      partSelection=0,
                                      partLineType='generic')
        elif verify == 9:
            westerparse.evaluateLines(source, show=None,
                                      partSelection=0, partLineType=None)
        elif verify == 91:
            westerparse.evaluateLines(source, show='show',
                                      partSelection=0, partLineType=None)
        elif verify == 92:
            westerparse.evaluateLines(source, show='show',
                                      partSelection=1, partLineType='generic')
        elif verify == 93:
            westerparse.evaluateLines(source, show=None,
                                      partSelection=1, partLineType='generic')
        elif verify == 94:
            westerparse.evaluateLines(source, show=None,
                                      partSelection=0, partLineType='generic')
        elif verify == 95:
            westerparse.evaluateLines(source, show=None,
                                      partSelection=1, partLineType=None)

        elif verify == 201:
            westerparse.evaluateLines(source, show='parsedata')

        else:
            print('ERROR: No valid evaluation option selected.')

    def reporter(source, verify):
        print('Input:', source)
        cxt = westerparse.makeGlobalContext(source)
        print('Inferred key:', cxt.key.nameString)
        print('Number of parts:', len(cxt.parts))
        for part in cxt.parts:
            print('Part', part.partNum, 'species:', part.species)
        tester(source, verify)

    def vltester(source, keynote, mode):
            westerparse.evaluateCounterpoint(source, report=True,
                                             keynote=keynote, mode=mode,
                                             validateKey=False)

    def unit_tests(test):        # UNIT TESTS for HTML reporting
        if test == 1:
            # no notes in line
            source = 'TestScoresXML/WP_Test01.musicxml'
            rpt = westerparse.evaluateLines(source, show='html')
        if test == 2:
            # invalid key from user
            source = 'TestScoresXML/WP_Test02.musicxml'
            rpt = westerparse.evaluateLines(source, show='html', keynote='D$', mode='manor')
        if test == 3:
            # no inferrable key
            source = 'TestScoresXML/WP_Test02.musicxml'
            rpt = westerparse.evaluateLines(source, show='html', keynote='D', mode='minor')
        if test == 4:
            # no inferrable key
            source = 'TestScoresXML/WP_Test04.musicxml'
            rpt = westerparse.evaluateLines(source, show='html')
        if test == 5:
            # invalid part selection
            source = 'TestScoresXML/WP_Test02.musicxml'
            rpt = westerparse.evaluateLines(source, show='html', partSelection=2)
        if test == 6:
            # part selection not permitted
            source = 'TestScoresXML/WP_Test06.musicxml'
            rpt = westerparse.evaluateLines(source, show='html', partLineType='generic')
        if test == 7:
            # valid and parsable
            source = 'TestScoresXML/WP_Test06.musicxml'
            rpt = westerparse.evaluateLines(source, show='html')
        if test == 8:
            # parser errors in upper and lower lines
            source = 'TestScoresXML/WP_Test08.musicxml'
            rpt = westerparse.evaluateLines(source, show='html')
        if test == 9:
            # valid and parsable as bass line
            source = 'TestScoresXML/WP_Test02.musicxml'
            rpt = westerparse.evaluateLines(source, show='html', partLineType='bass')
        if test == 10:
            # valid and parsable as upper line
            source = 'TestScoresXML/WP_Test02.musicxml'
            rpt = westerparse.evaluateLines(source, show='html', partLineType='primary')
        if test == 11:
            # incomplete parts
            source = 'TestScoresXML/WP_Test07.musicxml'
            rpt = westerparse.evaluateLines(source, show='html')
        if test == 12:
            # too many notes in final bar
            source = 'TestScoresXML/WP_Test09.musicxml'
            rpt = westerparse.evaluateLines(source, show='html')
        if test == 13:
            # rests in bar other than first
            source = 'TestScoresXML/WP_Test10.musicxml'
            rpt = westerparse.evaluateLines(source, show='html')
        if test == 14:
            # misplaced rest in first bar
            source = 'TestScoresXML/WP_Test11.musicxml'
            rpt = westerparse.evaluateLines(source, show='html')
        if test == 15:
            #
            source = 'TestScoresXML/WP_Test12.musicxml'
            rpt = westerparse.evaluateLines(source, show='html')
        if test == 16:
            # unresolved local insertion
            source = 'TestScoresXML/WP_Test13.musicxml'
            rpt = westerparse.evaluateLines(source, show='html')
        if test == 17:
            # keyFinder error
            source = 'TestScoresXML/WP_Test14.musicxml'
            rpt = westerparse.evaluateLines(source, show='html', partSelection=1)
        if test == 18:
            # parser error, NTT w/o lefthead
            source = 'TestScoresXML/WP_Test15.musicxml'
            rpt = westerparse.evaluateLines(source, show='html')
        if test == 51:
            # no notes in line
            source = 'TestScoresXML/WP_Test01.musicxml'
            rpt = westerparse.evaluateCounterpoint(source, report='html')
        if test == 52:
            # invalid key from user
            source = 'TestScoresXML/WP_Test02.musicxml'
            rpt = westerparse.evaluateCounterpoint(source, report='html', keynote='D$', mode='manor')
        if test == 53:
            # no inferrable key
            source = 'TestScoresXML/WP_Test04.musicxml'
            rpt = westerparse.evaluateCounterpoint(source, report='html')
        if test == 54:
            # not contrapuntal
            source = 'TestScoresXML/WP_Test02.musicxml'
            rpt = westerparse.evaluateCounterpoint(source, report='html')
        if test == 55:
            # improper harmonic segmentation
            source = 'TestScoresXML/WP_Test05.musicxml'
            rpt = westerparse.evaluateCounterpoint(source,
                                                   report='html',
                                                   harmonicSpecies=True,
                                                   startPredominant=8,
                                                   startDominant=14)
        if test == 56:
            # voice-leading errors
            source = 'TestScoresXML/WP_Test16.musicxml'
            rpt = westerparse.evaluateCounterpoint(source, report='html')
        return rpt

    # testno = 4
    # rpt = unit_tests(testno)
    # print(f'TEST CASE {testno}\n{rpt}')


    # Test no. 5 not working, 2025-08-18

    # unit_test_ids = [1, 2, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 51, 52, 53, 54, 55, 56]
    # for id in unit_test_ids:
    #     rpt = unit_tests(id)
    #     print(f'TEST CASE {id}\n{rpt}\n')


    def data_extractor(sources):
        for data_source in sources:
            # print('File:', data_source)
            westerparse.evaluateLines(data_source, show='parsedata')
            pass

    # sources = glob.glob('parse_corpus/*')
    # data_extractor(sources)

    # vltester(source, keynote='D$', mode='manor')
    # reporter(source, 1)


    html = tester(source, 1)
    print(html)
    
    # tester(source, 1)

    # from westerparse import vlChecker

    # cxt = westerparse.makeGlobalContext(source)
    # duets = cxt.makeTwoPartContexts()
    # tsTree = duets[2].asTimespans(classList=(note.Note,))
    # klangs = vlChecker.getGenericKlangs(cxt.score)
    # print(klangs)
    # print(offsetList)
    # obis = vlChecker.getOnbeatIntervals(duets[2])
    # print([obi.simpleName for obi in obis])
    # contentDict = vlChecker.getAllVerticalitiesContentDictionary(cxt)


    # vs = contentDict[0.0][1].isNote
    # print(vs)
    # westerparse.evaluateLines(source, show=None)

#    westerparse.evaluateLines(source, show=None, partSelection=0, partLineType='primary')
    
#    context.evaluateLines(source, show='show', partSelection=None, partLineType=None)



