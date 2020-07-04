from music21 import *
import context



#localCorpus = corpus.corpora.LocalCorpus()
#aNewLocalCorpus = corpus.corpora.LocalCorpus('WesterCptCorp')
#aNewLocalCorpus.addPath('~/Dropbox/Documents in Dropbox/MusicComputing/WesterParse/WesterParseCorpora/WestergaardCounterpointCorpus')
#aNewLocalCorpus.save()
#corpus.cacheMetadata('WesterCptCorp')

#WesterParseCptCorpus = corpus.corpora.LocalCorpus('westergaard')
#WesterParseCptCorpus.delete()
#WesterParseCptCorpus.addPath('~/Dropbox/Documents in Dropbox/MusicComputing/WesterParse/WesterParseCorpora/WestergaardCounterpointCorpus')
#corpus.cacheMetadata()
#localCorpus.removePath('~/Desktop')

#WesterParseCptCorpus.save()
#print(corpus.manager.listLocalCorporaNames())

#WCC = corpus.corpora.LocalCorpus().search('WesterCptCorp')
#print(WCC)
#print(WCC[0].metadata.all())

WCCbundle = corpus.corpora.LocalCorpus('WesterCptCorp').metadataBundle
#WCCbundle.write()
#print(WCCbundle)

sources = corpus.corpora.LocalCorpus('WesterCptCorp')
sourcefiles = sources.search('Westergaard')
for s in sourcefiles:
    print(s)

if __name__ == "__main__":
    # self_test code


    def tester(source, verify):
								if verify == 1: # tests for generability as any type of line
												context.evaluateLines(source, show=None)
								elif verify == 2:
												context.evaluateCounterpoint(source, report=True)

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
								elif verify == 61:
												context.evaluateLines(source, show='show', partSelection=0, partLineType='primary')
								elif verify == 7:
												context.evaluateLines(source, show=None, partSelection=-1, partLineType='bass')
								elif verify == 71:
												context.evaluateLines(source, show='show', partSelection=-1, partLineType='bass')
								elif verify == 8:
												context.evaluateLines(source, show=None, partSelection=0, partLineType='generic')
								elif verify == 81:
												context.evaluateLines(source, show='show', partSelection=0, partLineType='generic')
								elif verify == 9:
												context.evaluateLines(source, show=None, partSelection=0, partLineType=None)
								elif verify == 91:
												context.evaluateLines(source, show='show', partSelection=0, partLineType=None)
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
    
    multiTester(sourcefiles, 1)


#    vltester(source, keynote='C', mode='major')
#    tester(source, 91)
#    reporter(source, verify)
#    context.evaluateCounterpoint(source, keynote='B-', mode='major')
#    context.evaluateLines(source, show=None, partSelection=0, partLineType=None, keynote='B-', mode='major')
#    context.evaluateLines(source, show=None, partSelection=0, partLineType=None)
#    context.evaluateLines(source, show=None, partSelection=0, partLineType='generic')
#    context.evaluateLines(source, show=None, partSelection=0, partLineType='primary')
#    context.evaluateLines(source, show=None, partSelection=0, partLineType='bass')
