from music21 import *
import context
import vlChecker
import signal
import time
 

if __name__ == "__main__":
    # self_test code
    pass

#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard057a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard057b.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard057c.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard058a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard063a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard066a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard066b.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard067a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard068a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard068b.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard068c.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard068d.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard068e.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard068f.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard068g.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard068h.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard069a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard069b.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard070a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard070b.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard070c.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard070d.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard070e.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard070f.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard070g.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard072a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard072b.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard072c.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard072d.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard074a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard075a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard075b.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard081a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard081b.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard083a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard090a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard092a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard094a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard096a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard103a.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard103b.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard103c.musicxml'
#    source = 'WesterParseCorpora/WestergaardLineCorpus/Westergaard103d.musicxml'
    
    def tester(source, verify):
								if verify == 1: # tests for generability as any type of line
												context.evaluateLines(source, show=None)
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
								else:
												print('ERROR: No valid evaluation option selected.')
												
#    vltester(source, keynote='C', mode='major')
    tester(source, 16)
#    reporter(source, verify)
#    context.evaluateCounterpoint(source, keynote='B-', mode='major')
#    context.evaluateLines(source, show=None, partSelection=0, partLineType=None, keynote='B-', mode='major')
#    context.evaluateLines(source, show=None, partSelection=0, partLineType=None)
#    context.evaluateLines(source, show=None, partSelection=0, partLineType='generic')
#    context.evaluateLines(source, show=None, partSelection=0, partLineType='primary')
#    context.evaluateLines(source, show=None, partSelection=0, partLineType='bass')
