from pathlib import Path
import subprocess
import re
import os

class BuildContext:
    Build_Contexts = {}
    _mm_regex = re.compile(r'([\w\/]+\.h)')

    def __init__(self, name, sources=[], defines=[], path=[], libs=[], libpath=[],
                 cc=None, cxx=None, ar=None, objdir=None, replicate_structure=False, env=None):
        self.name = name
        self.sources = sources
        self.defines = defines
        self.path = path
        self.libs = libs
        self.libpath = libpath
        self.cc = cc or "gcc"
        self.cxx = cxx or "g++"
        self.ar = ar or "ar"
        self.objdir = objdir
        self.replicate_structure = replicate_structure
        self.env = env or os.environ.copy()

        BuildContext.Build_Contexts[self.name] = self
    
    def determine_deps(self, file):
        compiler = {"cpp": self.cxx, "c": self.cc}[Path(file).suffix]
        mm = subprocess.check_output([compiler, '-MM', file, '-Iother_includes'], env=env).decode('utf-8')
        ret = BuildContext._mm_regex.findall(mm)
        print("getting deps for " + file)
        return { 'file_dep': ret }

    def add_sources(self, *sources):
        for source in sources:
            if isinstance(source, BuildObject):
                self.sources += source
            else:
                self.sources += BuildObject(str(source))

class BuildObject:
    def __init__(self, *args, **kwargs):
        pass

def task_determine_dependencies():
    """Determine dependencies for C/C++ build"""

    for ctxt in BuildContext.Build_Contexts:
        for file in ctxt.sources:
            yield {
                'name': f"{file}_{ctxt.name}",
                'actions': [(determine_deps, [file])],
                'file_dep': [file]
            }

main_sources = Path('src').glob("*.cpp")

test = BuildObject()

main_build = BuildContext("main")
main_build.add_sources(main_sources)

print(main_build.sources)