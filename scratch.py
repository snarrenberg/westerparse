from music21 import *
import theoryAnalyzerRS
import theoryResultRS



if __name__ == "__main__":
	# self_test code
	pass


#	source = 'TestScoresXML/WTC_I,_Fugue_in_C_Subject.musicxml'
#	source = 'TestScoresXML/SyncopationTest.musicxml'
	source = 'TestScoresXML/CombinedSpecies1234.musicxml'
#	source = 'TestScoresXML/SecondSpecies10.musicxml'
	
	sc = converter.parse(source)

	ns = sc.parts[0].flat.notes
	
	thism = ns[10].getContextByClass('Measure')
	
	print([n for n in thism.flat.notes])
	
	thismns = [note for note in sc.flat.notes if note.measureNumber == 5]
	print(thismns[1].getContextByClass('Measure'))


	# VLContext goes from one downbeat through the end of the next bar
	
	# examine verts in vertList
	
	# if vert falls on downbeat, store vert for later reference in the VLContext
	
		print(vert.getLongestDuration())
		print(vert.getObjectsByPart(1, classFilterList=None))
		print(vert.getShortestDuration())
		# Verticality.contentDict
		
		
	assuming flattened score, I think
	vert.offset(leftAlign=False) produces the offset of the rightmost object in the verticality
	vert.objects[n].offset produces the offset of the object in the score
	vert.objects[n].quarterLength produces the duration of the object in the score	
	
	vert.contentDict.items() will get a list of objects in each part
	in species, each list has one note
	

shortcut for vlq evaluation:
	if motion is oblique: just check for voice crossing with bass
	else:



give a onbeat verticality, determine 
	for all voice pairs
		assign a species code
		assemble the set of relevant paired verticalities in this and in some case the next bar
		
	for all voice pairs that include the bass:
		assemble the set of relevant paired verticalities (if any) and check for voice crossing

coding for VLQs

ij, where i = top voice and j = lower voice

vlq.code[0], vlq.code[2]

11 = first-first

12 = first-second
21 = second-first

13
31

14
41

22
33
44

32
23

24
42

43
34


15
51
