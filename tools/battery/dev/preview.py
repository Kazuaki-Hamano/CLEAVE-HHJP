import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)
import runpy
import tkinter as tk
from PIL import ImageGrab

original = tk.Tk
def preview():
    window = original()
    window.attributes('-topmost', True)
    window.geometry('+100+100')
    def capture():
        window.update()
        window.lift()
        box = (window.winfo_rootx(), window.winfo_rooty(),
               window.winfo_rootx() + window.winfo_width(),
               window.winfo_rooty() + window.winfo_height())
        ImageGrab.grab(bbox=box).save('output/battery/monitor-preview.png')
        window.destroy()
    window.after(1500, capture)
    return window
tk.Tk = preview
runpy.run_path('tools/battery/battery_monitor.py', run_name='__main__')
