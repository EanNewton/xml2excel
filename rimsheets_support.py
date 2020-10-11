import sys
import os
import parserXML
import tracemalloc
from platform import system as psys
from pathlib import Path

try:
    import Tkinter as tk
    import Tkinter.messagebox as messagebox
except ImportError:
    import tkinter as tk
    import tkinter.messagebox as messagebox

try:
    import ttk
    py3 = False
except ImportError:
    import tkinter.ttk as ttk
    py3 = True

def set_Tk_var():
    global cb_singleFile
    cb_singleFile = tk.IntVar()

    global cb_enableCore
    cb_enableCore = tk.IntVar()
    
    global cb_enableRoyal
    cb_enableRoyal = tk.IntVar()
    
    global cb_enableWorkshop
    cb_enableWorkshop = tk.IntVar()

    global cb_logging
    cb_logging = tk.IntVar()
    
    global eb_timeout
    eb_timeout = tk.StringVar()
    
    global eb_outputName
    eb_outputName = tk.StringVar()
    
    global msg_output
    msg_output = tk.StringVar()
    msg_output.set('')
    
    global progressBar
    progressBar = tk.IntVar()
    
    global progressSubBar
    progressSubBar = tk.IntVar()
    
    global msg_progressStage
    msg_progressStage = tk.StringVar() 

    global directory_core
    directory_core = tk.StringVar()

    global directory_workshop
    directory_workshop = tk.StringVar()

def init(top, gui, *args, **kwargs):
    global w, top_level, root
    w = gui
    top_level = top
    root = top
    dirsFound = autoDetectSteam()
    msg_output.set('\nAuto detected RimWorld at:\n{}'.format(dirsFound[0]))
    msg_progressStage.set('Auto detected mods at:\n{}'.format(dirsFound[1]))


def autoDetectSteam():
    if psys() == 'Windows':
        path_core = 'C:\\Program Files\\Steam\\steamapps\\common\\RimWorld'
        path_workshop = 'C:\\Program Files\\Steam\\steamapps\\workshop\\content\\294100'
    elif psys() in  {'Linux', 'Darwin'}:
        path_core = '{}/.local/share/Steam/steamapps/common/RimWorld'.format(Path.home())
        path_workshop = '{}/.local/share/Steam/steamapps/workshop/content/294100'.format(Path.home())

    flags = [None, None]
    if os.path.exists(path_core):
        directory_core.set(path_core)
        flags[0] = path_core
    else:
        flags[0] = 'Please set RimWorld directory.\nCommonly found in /Steam/steamapps/common/Rimworld'
    if os.path.isdir(path_workshop):
        directory_workshop.set(path_workshop)
        flags[1] = path_workshop
    else:
        flags[1] = 'Please set RimWorld mods directory.\nCommonly found in /Steam/steamapps/workshop/content/294100'
    
    return flags


def setProgress(message, progress):
    msg_output.set(message)
    progressBar.set(progress)
    top_level.update()

def setSubProgress(message, progress):
    msg_progressStage.set(message)
    progressSubBar.set(progress)
    top_level.update()

def run():
    if str(eb_timeout.get()).isnumeric():
        parserXML.TIMEOUT_VAL = int(eb_timeout.get())

    if str(eb_outputName.get()):
        parserXML.OUTPUT_NAME = str(eb_outputName.get())
    else:
        parserXML.OUTPUT_NAME = 'RimSheets'

    if cb_enableCore.get():
        if directory_core.get():
            parserXML.DEFS.append(["{}/Data/Core/Defs".format(directory_core.get()), 'Core'])
        else:
            messagebox.showerror(title='Error', message='Could not find RimWorld directory.')
            return
    if cb_enableRoyal.get():
        if directory_core.get():
            parserXML.DEFS.append(["{}/Data/Royalty/Defs".format(directory_core.get()), 'Royalty'])
        else:
            messagebox.showerror(title='Error', message='Could not find RimWorld directory.')
            return
    if cb_enableWorkshop.get():
        if directory_workshop.get():
            parserXML.DEFS.append(['{}'.format(directory_workshop.get()), 'Workshop'])
        else:
            messagebox.showerror(title='Error', message='Could not find RimWorld Workshop directory.')
            return
    
    parserXML.SINGLE_FILE = True if cb_singleFile.get() else False
    parserXML.LOGGING = True if cb_logging.get() else False
    
    parserXML.run()
    parserXML.DEFS.clear()
    sys.stdout.flush()

if __name__ == '__main__':
    import rimsheets
    rimsheets.vp_start_gui()




