from tkinter import *
from tkinter import ttk
from PIL import Image, ImageTk

from music21 import *
from westerparse
#import context
import signal
import time
import os
import glob
import sys, io
#import strip_xml_metadata


def convertImage(image, *args):
    img = Image.open(image)
    width, height = img.size 
    left = 5
    top = 5
    right = width 
    bottom = height / 4
    img = img.crop((left, top, right, bottom)) 
    baseheight = 200
    wpercent = (baseheight/float(img.size[1]))
    vsize = int((float(img.size[0])*float(wpercent)))
    img = img.resize((vsize,baseheight), Image.ANTIALIAS)
    img_converted = ImageTk.PhotoImage(img)
    return img_converted

def convertMuseScorePng(image, *args):
    img = Image.open(image)
    width, height = img.size
    baseheight = 120
    wpercent = (baseheight/float(img.size[1]))
    vsize = int((float(img.size[0])*float(wpercent)))
    img = img.resize((vsize,baseheight), Image.ANTIALIAS)
    img_converted = ImageTk.PhotoImage(img)
    return img_converted
    
def onSelectFileSource(*args):
    idxs = fileList.curselection()
    if len(idxs) == 1:
        cleanUpCanvas()
        clearReportArea()
        displayFileSource()

def cleanUpCanvas():
    # clear the content of the display area
    music_canvas.delete('all')

def clearReportArea():
    # clear the report content
    reporttext.delete(1.0, END)

def displayFileSource(*args):
    idxs = fileList.curselection()
    if len(idxs) == 1:
        idx = int(idxs[0])
        WPfile = 'WesterParseCorpora/WesterParseLineCorpus/' + WPfilenames[idx] + '.musicxml'
        westerparse.displaySourceAsPng(WPfile)
        files = glob.glob('tempimages/*.png')
        if len(files) == 1:
            f_converted = convertMuseScorePng(files[0])
            music_canvas.create_image(20,20, image=f_converted, anchor='nw', tag='thumb0')
        cleanUpTempFiles()
        music_canvas.mainloop()

def clearMetadataFromTempFiles():
    files = glob.glob('tempimages/*.xml')
    for f in files:
        try:
            strip_xml_metadata(f)
        except OSError as e:
            print("Error: %s : %s" % (f, e.strerror))
            
def cleanUpTempFiles():
    # delete all the .xml files
    files = glob.glob('tempimages/*.xml')
    for f in files:
        try:
            os.unlink(f)
        except OSError as e:
            print("Error: %s : %s" % (f, e.strerror))
    # delete all the .png files
    files = glob.glob('tempimages/*.png')
    for f in files:
        try:
            os.unlink(f)
        except OSError as e:
            print("Error: %s : %s" % (f, e.strerror))

def evaluateSyntax(*args):
    clearReportArea()
    idxs = fileList.curselection()
    if len(idxs) == 1:
        # run WesterParse
        idx = int(idxs[0])
        WPfile = 'WesterParseCorpora/WesterParseLineCorpus/' + WPfilenames[idx] + '.musicxml'
        if linetype.get():
            lt = linetype.get()
        else:
            lt=None
        temp_out = io.StringIO()
        sys.stdout = temp_out 
        westerparse.evaluateLines(WPfile, show='writeToPng', partSelection=None, partLineType=lt, report=True)
        eval_report = sys.stdout.getvalue()
        temp_out.close()
        sys.stdout = sys.__stdout__
        # clear metadata from temp files
#        clearMetadataFromTempFiles()

        # select files to display
        files = glob.glob('tempimages/*.png')
        if len(files) < 5:
            display_number = len(files)
        else:
            display_number = 4
        displaymsg = 'Displaying ' + str(display_number) + ' of ' + str(len(files)) + ' possible parses.'
        # display up to 4 parses
        imgcounter = 0
        if len(files) == 0:
            reporttext.insert(INSERT, eval_report)
            cleanUpCanvas()
            displayFileSource()
        elif len(files) > 0:
            # clear out the previous thumbnails and report
            cleanUpCanvas()
            reporttext.insert(INSERT, eval_report)
            reporttext.insert(INSERT, '\n')
            reporttext.insert(INSERT, '\n')
            reporttext.insert(INSERT, displaymsg)
        if len(files) >= 1:
            f0_converted = convertMuseScorePng(files[0])
            vertoffset = (imgcounter*150)+20
            music_canvas.create_image(20,vertoffset, image=f0_converted, anchor='nw', tag='thumb0')
            imgcounter += 1
        if len(files) >= 2:
            f1_converted = convertMuseScorePng(files[1])
            vertoffset = (imgcounter*150)+20
            music_canvas.create_image(20,vertoffset, image=f1_converted, anchor='nw', tag='thumb1')
            imgcounter += 1
        if len(files) >= 3:
            f2_converted = convertMuseScorePng(files[2])
            vertoffset = (imgcounter*150)+20
            music_canvas.create_image(20,vertoffset, image=f2_converted, anchor='nw', tag='thumb2')
            imgcounter += 1
        if len(files) >= 4:
            f3_converted = convertMuseScorePng(files[3])
            vertoffset = (imgcounter*150)+20
            music_canvas.create_image(20,vertoffset, image=f3_converted, anchor='nw', tag='thumb3')
        
#        for f in files[0:4]:
#            try:
#                f_converted = convertMuseScorePng(f)
#                thumbtag = 'thumb' + str(imgcounter)
#                vertoffset = imgcounter*150
#                music_canvas.create_image(0,vertoffset, image=f_converted, anchor='nw', tag=thumbtag)
#                music_canvas.itemconfig(thumbtag, image=f_converted)
#            except OSError as e:
#                print("Error: %s : %s" % (f, e.strerror))
#            imgcounter += 1
        cleanUpTempFiles()
        music_canvas.mainloop()
        
def evaluateCounterpoint(*args):
    clearReportArea()
    idxs = fileList.curselection()
    if len(idxs) == 1:
        idx = int(idxs[0])
        WPfile = 'WesterParseCorpora/WesterParseLineCorpus/' + WPfilenames[idx] + '.musicxml'
        temp_out = io.StringIO()
        sys.stdout = temp_out
        # run the vl checker
        westerparse.evaluateCounterpoint(WPfile, report=True)
        eval_report = sys.stdout.getvalue()
        temp_out.close()
        sys.stdout = sys.__stdout__
        reporttext.insert(INSERT, eval_report)
        cleanUpCanvas()
        displayFileSource()

def playMIDI(*args):
    clearReportArea()
    idxs = fileList.curselection()
    if len(idxs) == 1:
        # run WesterParse
        idx = int(idxs[0])
        WPfile = 'WesterParseCorpora/WesterParseLineCorpus/' + WPfilenames[idx] + '.musicxml'
        WP21 = converter.parse(WPfile)
        mf = midi.translate.streamToMidiFile(WP21)
        mf.open('WesterParseCorpora/WesterParseLineCorpus/midi.mid', 'wb')
        mf.write()
        mf.close()
        os.system('open -a /Applications/MIDIPlayer\ X.app WesterParseCorpora/WesterParseLineCorpus/midi.mid')
        WP21.show('midi')



root = Tk()
root.title('WesterParse Corpus Tester')


WPfilenames = tuple(open('WesterParseCorpora/WPfilenameList.txt').read().split('\n'))
WPfiles = StringVar(value=WPfilenames)


mainframe = ttk.Frame(root)
mainframe.grid(column=0, row=0, sticky=(N, W, E, S))

root.columnconfigure(0, weight=1)
root.rowconfigure(0, weight=1)


# APP LOGO
logoframe = ttk.Frame(mainframe)
logoframe.grid(column=1, row=1, sticky=(W))
logo = Image.open('WesterParseLogo.jpg')
baseheight = 120
wpercent = (baseheight/float(logo.size[1]))
vsize = int((float(logo.size[0])*float(wpercent)))
logo_resized = logo.resize((vsize,baseheight), Image.ANTIALIAS)
logo_canvas = Canvas(logoframe, width=vsize, height=baseheight)
logo_converted = ImageTk.PhotoImage(logo_resized)
logo_canvas.create_image(0,0, image=logo_converted, anchor=NW, tag='thumb0')
logo_canvas.grid(column=1, row=1)

# APP DESCRIPTION 
apptext = Text(mainframe, width=50, height=9, wrap='word', relief='sunken')#, state='disabled')
apptext.grid(column=2, row=1, sticky=(W))
apptext.insert(INSERT, 'WesterParse Corpus Tester')
apptext.insert(END, '\n\nWesterParse is a transition-based dependency parser for simple tonal melodies.')
apptext.insert(END, '\n\nWesterParse is a core component of the Westergaardian Species Counterpoint Online Project, developed by Robert Snarrenberg at Washington University in St. Louis.')

# FILE LIST 
listframe = ttk.Frame(mainframe)
listframe.grid(column=3, row=1, sticky=(E))
# instruction
listlabel = ttk.Label(listframe, text='Select file name: ')
listlabel.grid(column=1, row=1)
# file list
fileList = Listbox(listframe, height=5, listvariable=WPfiles)
fileList.grid(column=1, row=2)
fileList.bind('<<ListboxSelect>>', onSelectFileSource)
#fileList.bind('<Double-1>', evaluateSyntax)
s = ttk.Scrollbar(listframe, orient=VERTICAL, command=fileList.yview)
s.grid(column=2, row=2, sticky=(N,S))
fileList.configure(yscrollcommand=s.set)

# EVALUATE BUTTONS
evaluateLine = ttk.Button(listframe, text='Display Linear Syntax', command=evaluateSyntax)
evaluateLine.grid(column=1, row=3, stick=(S, W, E))
evaluateCpt = ttk.Button(listframe, text='Evaluate Counterpoint', command=evaluateCounterpoint)
evaluateCpt.grid(column=1, row=4, stick=(S, W, E))
playMIDI = ttk.Button(listframe, text='Play MIDI file', command=playMIDI)
playMIDI.grid(column=1, row=5, stick=(S, W, E))

# LINETYPE SELECTION
linetype = StringVar()
linetype.set('any')
selectframe = ttk.Frame(mainframe)
selectframe.grid(column=4, row=1, sticky=(W))
rad1 = Radiobutton(selectframe,text='primary', value='primary', variable=linetype)
rad2 = Radiobutton(selectframe,text='bass', value='bass', variable=linetype)
rad3 = Radiobutton(selectframe,text='generic', value='generic', variable=linetype)
rad4 = Radiobutton(selectframe,text='any', value='any', variable=linetype)
rad1.grid(column=0, row=0, sticky=(W))
rad2.grid(column=0, row=1, sticky=(W))
rad3.grid(column=0, row=2, sticky=(W))
rad4.grid(column=0, row=3, sticky=(W))

# REPORT AREA
#parse_report = StringVar()
reporttext = Text(mainframe, width=114, height=10, wrap='word')
reporttext.grid(column=1, row=3, columnspan=4)


# DISPLAY AREA
musicframe = ttk.Frame(mainframe, padding='0 0 0 0', borderwidth='2')
musicframe.grid(column=1, row=4, columnspan=4)
# intro image
imageSelected = 'WesterParseCorpora/FuxDorian.png'
music_canvas = Canvas(musicframe, width=800, height=800)
music_converted = convertImage(imageSelected)
music_canvas.create_image(0,0, image=music_converted, anchor='nw', tag='thumb0')
music_canvas.create_image(0,150, image=None, anchor='nw', tag='thumb1')
music_canvas.create_image(0,300, image=None, anchor='nw', tag='thumb2')
music_canvas.create_image(0,450, image=None, anchor='nw', tag='thumb3')
music_canvas.pack()
music_canvas.mainloop()

#displaymsg = StringVar()
#displaymsg.set('blank')
#displaylabel = ttk.Label(listframe, text=displaymsg)
#displaylabel.grid(column=3, row=4)



root.mainloop()