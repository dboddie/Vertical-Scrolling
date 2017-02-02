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
import UEFfile

version = "0.1"

def system(command):

    if os.system(command):
        sys.exit(1)

if __name__ == "__main__":

    if len(sys.argv) != 2:
    
        sys.stderr.write("Usage: %s <new UEF file>\n" % sys.argv[0])
        sys.exit(1)
    
    out_uef_file = sys.argv[1]
    
    # Memory map
    code_start = 0x0e00
    
    files = []
    
    # Assemble the files.
    assemble = [("vscroll2-ram.oph", "VSCROLL2"),
                ("vscroll-ram.oph", "VSCROLL"),
                ("vscroll.oph", "vscroll.rom"),
                ("vscroll1.oph", "vscroll1.rom"),
                ("vscrollpal1.oph", "vscrollpal1.rom"),
                ("vscroll2.oph", "vscroll2.rom")]
    
    code_data = {}
    
    for name, output in assemble:
        if name.endswith(".oph"):
            system("ophis " + name + " -o " + output)
            code = open(output).read()
        else:
            code = open(name).read().replace("\n", "\r")
        code_data[output] = code
    
    for src, obj in assemble:
        if not obj.endswith(".rom"):
            files.append((obj, code_start, code_start, code_data[obj]))
    
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
