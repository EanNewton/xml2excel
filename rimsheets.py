import sys

try:
    import Tkinter as tk
    import Tkinter.filedialog as filedialog
except ImportError:
    import tkinter as tk
    import tkinter.filedialog as filedialog

try:
    import ttk
    py3 = False
except ImportError:
    import tkinter.ttk as ttk
    py3 = True

import rimsheets_support


def vp_start_gui():
    '''Starting point when module is the main routine.'''
    global root
    root = tk.Tk()
    rimsheets_support.set_Tk_var()
    top = Toplevel1(root)
    rimsheets_support.init(root, top)
    root.mainloop()


def browseDirectory():
    rimsheets_support.directory_core.set(filedialog.askdirectory())


def browseModDirectory():
    rimsheets_support.directory_workshop.set(filedialog.askdirectory())


class CustomCheckbutton(tk.Checkbutton):
    def __init__(self, master, **kw):
        tk.Checkbutton.__init__(self, master=master, **kw)
        self.configure(background='#e6e6e6')
        self.configure(foreground='black')
        self.defaultBackground = self['background']
        self.configure(highlightbackground='#e6e6e6')
        self.configure(justify='left')

    def on_enter(self, e):
        self['background'] = self['activebackground']
    def on_leave(self, e):
        self['background'] = self.defaultBackground


class Toplevel1:
    def __init__(self, top=None):
        '''This class configures and populates the toplevel window.
           top is the toplevel containing window.'''

        _bgcolor = '#e6e6e6'  # X11 color: 'gray85'
        _fgcolor = '#000000'  # X11 color: 'black'
        _compcolor = '#e6e6e6' # X11 color: 'gray85'
        _ana1color = '#e6e6e6' # X11 color: 'gray85'
        _ana2color = '#e6e6e6' # Closest X11 color: 'gray92'

        self.style = ttk.Style()
        if sys.platform == "win32":
            self.style.theme_use('winnative')
        self.style.configure('.',background=_bgcolor)
        self.style.configure('.',foreground=_fgcolor)
        self.style.configure('.',font="TkDefaultFont")
        self.style.map('.',background=
            [('selected', _compcolor), ('active',_ana2color)])

        top.geometry("640x640+551+424")
        top.minsize(1, 1)
        top.maxsize(2545, 1570)
        top.resizable(1, 1)
        top.configure(background='#e6e6e6')
        top.title("RimSheets Generator")

        #General GUI Decorator Layout
        self.Label1 = tk.Label(top)
        self.Label1.place(relx=0.095, rely=0.043, height=32, width=92)
        self.Label1.configure(foreground='black')
        self.Label1.configure(background='#e6e6e6')
        self.Label1.configure(text='''Files to Scan''')

        self.Label2 = tk.Label(top)
        self.Label2.place(relx=0.565, rely=0.043, height=32, width=87)
        self.Label2.configure(foreground='black')
        self.Label2.configure(background='#e6e6e6')
        self.Label2.configure(text='''Options''')

        #Dividers
        self.TSeparator1 = ttk.Separator(top)
        self.TSeparator1.place(relx=0.0, rely=0.134, relwidth=1.017)

        self.TSeparator2 = ttk.Separator(top)
        self.TSeparator2.place(relx=0.367, rely=0.0, relheight=0.556)
        self.TSeparator2.configure(orient="vertical")

        self.TSeparator3 = ttk.Separator(top)
        self.TSeparator3.place(relx=0.0, rely=0.556, relwidth=0.992)

        #Timeout entry
        self.Label3 = tk.Label(top)
        self.Label3.place(relx=0.433, rely=0.179, height=21, width=138)
        self.Label3.configure(foreground='black')
        self.Label3.configure(background='#e6e6e6')
        self.Label3.configure(text='''Timeout (0 = none):''')

        self.Entry1 = tk.Entry(top)
        self.Entry1.place(relx=0.717, rely=0.179,height=23, relwidth=0.137)
        self.Entry1.configure(font="TkFixedFont")
        self.Entry1.configure(foreground='black')
        self.Entry1.configure(background='white')
        self.Entry1.insert(0, '0')
        self.Entry1.configure(textvariable=rimsheets_support.eb_timeout)

        #Output entry
        self.Label3 = tk.Label(top)
        self.Label3.place(relx=0.433, rely=0.279, height=21, width=138)
        self.Label3.configure(foreground='black')
        self.Label3.configure(background='#e6e6e6')
        self.Label3.configure(text='''Save as:''')

        self.Entry2 = tk.Entry(top)
        self.Entry2.place(relx=0.717, rely=0.279,height=23, relwidth=0.137)
        self.Entry2.configure(font="TkFixedFont")
        self.Entry2.configure(foreground='black')
        self.Entry2.configure(background='white')
        self.Entry2.insert(0, 'RimSheets')
        self.Entry2.configure(textvariable=rimsheets_support.eb_outputName)

        #Basic Options and Location Selection
        self.Frame1 = tk.Frame(top)
        self.Frame1.place(relx=0.0, rely=0.137, relwidth=0.36, relheight=0.35)
        self.Frame1.configure(background='#e6e6e6')

        self.Checkbutton1 = CustomCheckbutton(self.Frame1)
        self.Checkbutton1.grid(column=0, row=0, sticky=tk.N+tk.S+tk.W+tk.E)
        self.Checkbutton1.configure(text='''Core''')
        self.Checkbutton1.configure(variable=rimsheets_support.cb_enableCore)

        self.Checkbutton2 = CustomCheckbutton(self.Frame1)
        self.Checkbutton2.grid(column=0, row=1, sticky=tk.N+tk.S+tk.W+tk.E)
        self.Checkbutton2.configure(text='''Royal''')
        self.Checkbutton2.configure(variable=rimsheets_support.cb_enableRoyal)

        self.Checkbutton3 = CustomCheckbutton(self.Frame1)
        self.Checkbutton3.grid(column=0, row=2, sticky=tk.N+tk.S+tk.W+tk.E)
        self.Checkbutton3.configure(text='''Steam Workshop''')
        self.Checkbutton3.configure(variable=rimsheets_support.cb_enableWorkshop)

        self.Checkbutton4 = CustomCheckbutton(self.Frame1)
        self.Checkbutton4.grid(column=0, row=3, sticky=tk.N+tk.S+tk.W+tk.E)
        self.Checkbutton4.configure(text='''Output as single file?''')
        self.Checkbutton4.configure(variable=rimsheets_support.cb_singleFile)

        self.Checkbutton5 = CustomCheckbutton(self.Frame1)
        self.Checkbutton5.grid(column=0, row=4, sticky=tk.N+tk.S+tk.W+tk.E)
        self.Checkbutton5.configure(text='''Enable logging?''')
        self.Checkbutton5.configure(variable=rimsheets_support.cb_logging)

        #Lower message box
        self.Message2 = tk.Message(top)
        self.Message2.place(relx=0.1, rely=0.67, relheight=0.2, relwidth=0.8)
        self.Message2.configure(text='''Message''')
        self.Message2.configure(justify='center')
        self.Message2.configure(textvariable=rimsheets_support.msg_progressStage)
        self.Message2.configure(width=500) 
        
        #Upper message box
        self.Message1 = tk.Message(top)
        self.Message1.place(relx=0.1, rely=0.6, relheight=0.1, relwidth=0.8)
        self.Message1.configure(text='''Message''')
        self.Message1.configure(justify='center')
        self.Message1.configure(textvariable=rimsheets_support.msg_output)
        self.Message1.configure(width=500) 

        #Overall Progress bar
        self.TProgressbar1 = ttk.Progressbar(top, mode='determinate', maximum=100, value=0)
        self.TProgressbar1.place(relx=0.032, rely=0.9, relwidth=0.937, relheight=0.0, height=19)
        self.TProgressbar1.configure(length="600")
        self.TProgressbar1.configure(variable=rimsheets_support.progressBar)

        #Sub Progress bar
        self.TProgressbar2 = ttk.Progressbar(top, mode='determinate', maximum=100, value=0)
        self.TProgressbar2.place(relx=0.032, rely=0.95, relwidth=0.937, relheight=0.0, height=19)
        self.TProgressbar2.configure(length="600")
        self.TProgressbar2.configure(variable=rimsheets_support.progressSubBar)

        #TODO find out if this is needed or not
        self.menubar = tk.Menu(top,font="TkMenuFont",bg=_bgcolor,fg=_fgcolor)
        top.configure(menu = self.menubar)
 
        #Buttons and Context Menus
        self.Button1 = tk.Button(self.Frame1)
        self.Button1.place(relx=0.4, rely=0.8, height=31, width=60)
        self.Button1.configure(command=rimsheets_support.run)
        self.Button1.configure(text='''Start''')

        self.Button2 = tk.Button(top)
        self.Button2.place(relx=0.533, rely=0.35, height=31, width=200)
        self.Button2.configure(command=browseDirectory)
        self.Button2.configure(text='''Change RimWorld Directory''')

        self.Button3 = tk.Button(top)
        self.Button3.place(relx=0.555, rely=0.45, height=31, width=170)
        self.Button3.configure(command=browseModDirectory)
        self.Button3.configure(text='''Change Mod Directory''')

if __name__ == '__main__':
    vp_start_gui()





