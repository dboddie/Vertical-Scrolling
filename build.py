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

from compressors.distance_pair import compress
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

def rainbow(i, colours, s):

    # Each physical colour is used in two adjacent rows.
    c1 = colours[(i/s) % len(colours)]
    c2 = colours[(((i+1)/s) + 1) % len(colours)]
    return [black, c1, c2, white]

def format_data(data):

    s = ""
    i = 0
    while i < len(data):
        s += ".byte " + ",".join(map(lambda c: "$%02x" % ord(c), data[i:i+24])) + "\n"
        i += 24
    
    return s

def mgc_palette(full = True):

    # Special MGC title palette processing
    
    fe08_data = []
    fe09_data = []
    
    blank = get_entries(4, [black, black, black, black])
    standard = get_entries(4, [black, red, yellow, white])
    
    if full:
        s1, s2 = 111, 65
    else:
        s1, s2 = 43, 3
    
    for i in range(256):
    
        if i >= 128 + s1:
            fe08, fe09 = get_entries(4, rainbow(i - 239, [yellow, cyan, white, green, cyan], 3))
        elif i >= 128 + s2:
            fe08, fe09 = get_entries(4, rainbow(i, rainbow_colours, 3))
        elif full and i >= 128 + 46:
            fe08, fe09 = get_entries(4, rainbow(i, [white, cyan, green, yellow], 3))
        elif full and i > 128:
            fe08, fe09 = get_entries(4, [black, blue, cyan, white])
        else:
            fe08, fe09 = standard
        
        fe08_data.append(fe08)
        fe09_data.append(fe09)
    
    return fe08_data, fe09_data


if __name__ == "__main__":

    if len(sys.argv) != 2:
    
        sys.stderr.write("Usage: %s <new UEF file>\n" % sys.argv[0])
        sys.exit(1)
    
    out_uef_file = sys.argv[1]
    
    # Memory map
    code_start = 0x0e00
    
    files = []
    
    # Special MGC title image and code processing
    
    # Convert the PNG to screen data and compress it with the palette data.
    mgctitle_sprite = read_sprite(read_png("images/mgctitle.png"))
    fe08_data, fe09_data = mgc_palette(full = True)
    mgcdata_list = "".join(map(chr, compress(fe08_data + fe09_data + map(ord, mgctitle_sprite))))
    
    mgctitle_small_sprite = read_sprite(read_png("images/mgctitle-trimmed.png"))
    fe08_data, fe09_data = mgc_palette(full = False)
    mgcdata_small_list = "".join(map(chr, compress(fe08_data + fe09_data + map(ord, mgctitle_small_sprite))))
    
    # Read the code and append the formatted title data to it.
    mgccode_temp = open("mgccode-full.oph").read()
    mgccode_temp = mgccode_temp.replace('.include "mgccode.oph"\n',
                                        open("mgccode.oph").read())
    mgccode_temp += "\n" + "title_data:\n" + format_data(mgcdata_list)
    
    mgccode_small_temp = open("mgccode-small.oph").read()
    mgccode_small_temp = mgccode_small_temp.replace('.include "mgccode.oph"\n',
                         open("mgccode.oph").read())
    mgccode_small_temp += "\n" + "title_data:\n" + format_data(mgcdata_small_list)
    
    # Write "temporary" files containing the code and compressed title data.
    # The mgctitle.oph file will include the decompression code.
    # This file can be included in a UEF2ROM project that provides its own
    # decompression code, or the dp_decode.oph sources can be appended to it.
    open("mgccode-temp.oph", "w").write(mgccode_temp)
    open("mgccode-small-temp.oph", "w").write(mgccode_small_temp)
    
    # Assemble the files.
    assemble = [("vscroll2-ram.oph", "VSCROLL2"),
                ("vscroll-ram.oph", "VSCROLL"),
                ("images/mgctitle-trimmed.png", "MGCTITLE"),
                ("vscroll.oph", "vscroll.rom"),
                ("vscroll1.oph", "vscroll1.rom"),
                ("vscrollpal1.oph", "vscrollpal1.rom"),
                ("vscroll2.oph", "vscroll2.rom"),
                ("mgctitle.oph", "mgctitle.rom"),
                ("mgctitle-trimmed.oph", "MGCTRIMMED"),
                ("mgccode-trimmed.oph", "MGCCODE")]
    
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
    
    # Create a full MGC title ROM.
    mgctitle = open("mgctitle.rom").read()
    padding = 16384 - len(mgctitle)
    if padding > 0:
        mgctitle += "\x00" * padding
    
    open("mgctitle.rom", "w").write(mgctitle)
    
    # Create a ROM that uses the trimmed title image.
    
    code_start = 0x3910
    mgctrimmed = open("MGCTRIMMED").read()
    
    # Pad out the space between the ROM code and the title code.
    mgctrimmed += "\x00" * (code_start - len(mgctrimmed))
    
    # Create the palette data for the trimmed image.
    fe08_data, fe09_data = mgc_palette(full = False)
    mgccode_and_data = open("MGCCODE").read()
    mgccode_and_data += "".join(map(chr, compress(fe08_data + fe09_data + map(ord, code_data["MGCTITLE"]))))
    
    if len(mgccode_and_data) > 0x4000 - code_start:
        print "*" * 77
        print "Code and data exceeds allocated space."
        print "Change the start address from $%x to $%x in mgccode-trimmed.oph" % (
            0x8000 + code_start, 0xc000 - len(mgccode_and_data))
        print "and mgctitle-trimmed.oph."
        print "*" * 77
    
    # Write the code to a file for use with other ROMs.
    open("mgccode", "w").write(mgccode_and_data)
    
    # Finish writing the ROM.
    mgctrimmed += mgccode_and_data
    padding = 16384 - len(mgctrimmed)
    if padding > 0:
        mgctrimmed += "\x00" * padding

    open("mgctrimmed.rom", "w").write(mgctrimmed)
    
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
    keep = ["mgccode"]
    
    for name, output in assemble:
        if name.endswith(".oph") and os.path.exists(output):
            if not output.endswith(".rom") and output not in keep:
                os.remove(output)
    
    # Exit
    sys.exit()
