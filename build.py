#!/usr/bin/env python

"""
Copyright (C) 2016 David Boddie <david@boddie.org.uk>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os, stat, struct, sys
import Image

from palette import get_entries, black, red, green, yellow, blue, magenta, \
                    cyan, white
import UEFfile

version = "0.1"

def system(command):

    if os.system(command):
        sys.exit(1)

palette = {"\x00\x00\x00": 0,
           "\xff\x00\x00": 1,
           "\xff\xff\x00": 2,
           "\xff\xff\xff": 3}

def read_png(path):

    im = Image.open(path).convert("RGB")
    s = im.tostring()
    
    data = []
    a = 0
    
    i = 0
    while i < im.size[1]:
    
        line = []
        
        j = 0
        while j < im.size[0]:
        
            line.append(palette[s[a:a+3]])
            a += 3
            j += 1
        
        i += 1
        data.append(line)
    
    return data

def read_sprite(lines):

    data = ""
    
    # Read 8 rows at a time.
    for row in range(0, len(lines), 8):
    
        width = len(lines[0])
        
        # Read 4 columns at a time.
        for column in range(0, width, 4):
        
            # Read the rows.
            for line in lines[row:row + 8]:
            
                shift = 3
                byte = 0
                for pixel in line[column:column + 4]:
                
                    if pixel == 1:
                        byte = byte | (0x01 << shift)
                    elif pixel == 2:
                        byte = byte | (0x10 << shift)
                    elif pixel == 3:
                        byte = byte | (0x11 << shift)
                    
                    shift -= 1
                
                data += chr(byte)
    
    return data

rainbow_colours = [red, yellow, green, cyan, blue, magenta]

def rainbow(i):

    # Each physical colour is used in two adjacent rows.
    c1 = rainbow_colours[(i/4) % 6]
    c2 = rainbow_colours[(((i+2)/4) + 1) % 6]
    return [black, c1, c2, white]

if __name__ == "__main__":

    if len(sys.argv) != 2:
    
        sys.stderr.write("Usage: %s <new UEF file>\n" % sys.argv[0])
        sys.exit(1)
    
    out_uef_file = sys.argv[1]
    
    # Special MGC title palette processing
    
    fe08_f = open("data/fe08.dat", "w")
    fe09_f = open("data/fe09.dat", "w")
    fe08_f.write(".byte ")
    fe09_f.write(".byte ")
    
    blank = get_entries(4, [black, black, black, black])
    standard = get_entries(4, [black, red, yellow, white])
    
    for i in range(256):
    
        if i >= 128 + 68:
            fe08, fe09 = get_entries(4, rainbow(i))
        elif i >= 128 + 48:
            fe08, fe09 = get_entries(4, [black, yellow, green, cyan])
        elif i > 128:
            fe08, fe09 = get_entries(4, [black, blue, cyan, white])
        else:
            fe08, fe09 = standard
        
        fe08_f.write("$%02x" % fe08)
        fe09_f.write("$%02x" % fe09)
        if i != 255:
            fe08_f.write(",")
            fe09_f.write(",")
    
    fe08_f.close()
    fe09_f.close()
    
    # Memory map
    code_start = 0x0e00
    
    files = []
    
    # Assemble the files.
    assemble = [("vscroll2-ram.oph", "VSCROLL2"),
                ("vscroll-ram.oph", "VSCROLL"),
                ("images/mgctitle.png", "MGCTITLE"),
                ("vscroll.oph", "vscroll.rom"),
                ("vscroll1.oph", "vscroll1.rom"),
                ("vscrollpal1.oph", "vscrollpal1.rom"),
                ("vscroll2.oph", "vscroll2.rom"),
                ("mgctitle.oph", "mgctitle.rom")]
    
    code_data = {}
    
    for name, output in assemble:
        if name.endswith(".oph"):
            system("ophis " + name + " -o " + output)
            code = open(output).read()
        elif name.endswith(".dat"):
            code = open(name).read()
        elif name.endswith(".png"):
            code = read_sprite(read_png(name))
        else:
            code = open(name).read().replace("\n", "\r")
        
        code_data[output] = code
    
    # Special MGC title image processing
    
    mgctitle = open("mgctitle.rom").read()
    mgctitle += code_data["MGCTITLE"]
    open("mgctitle.rom", "w").write(mgctitle)
    
    # General ROM processing
    
    for src, obj in assemble:
        if not obj.endswith(".rom"):
            files.append((obj, code_start, code_start, code_data[obj]))
    
    # General UEF processing
    
    u = UEFfile.UEFfile(creator = 'build.py '+version)
    u.minor = 6
    u.target_machine = "Electron"
    
    u.import_files(0, files, gap = True)
    
    # Write the new UEF file.
    try:
        u.write(out_uef_file, write_emulator_info = False)
    except UEFfile.UEFfile_error:
        sys.stderr.write("Couldn't write the new executable to %s.\n" % out_uef_file)
        sys.exit(1)
    
    # Remove the executable files.
    for name, output in assemble:
        if name.endswith(".oph") and os.path.exists(output):
            if not output.endswith(".rom"):
                os.remove(output)
    
    # Exit
    sys.exit()
