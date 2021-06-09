from pathlib import Path
import subprocess
import re
import os

class BuildContext:
    Build_Contexts = {}
    _mm_regex = re.compile(r'([\w\/]+\.h)')

    def __init__(self, name, cmd_args=[], cpath=[], libs=[], libpath=[], sources=[],
                 cc=None, cxx=None, ar=None, objdir=None, replicate_structure=False, base_dir=None, env=None):
        self.name = name
        self.cmd_args = cmd_args
        self.cpath = cpath
        self.libs = libs
        self.libpath = libpath
        self.sources = sources
        self.cc = cc or "gcc"
        self.cxx = cxx or "g++"
        self.ar = ar or "ar"
        self.objdir = Path(str(objdir)) if objdir is not None else None
        self.replicate_structure = replicate_structure
        self.base_dir = base_dir or Path(".")
        self.env = env or os.environ.copy()

        BuildContext.Build_Contexts[self.name] = self
    
    def get_file(self, file):
        if not isinstance(file, BuildObject):
            file = BuildObject(str(file))
        
        return file
    
    def get_compiler(self, file):
        file = self.get_file(file)
        suffix = file.file.suffix
        compiler = {".cpp": self.cxx, ".c": self.cc,
                    ".cc": self.cxx}[suffix]
        return compiler
    
    def get_output_dir(self, file):
        file = self.get_file(file)
        if self.objdir is not None:
            if self.replicate_structure:
                return self.objdir / file.file.parent.relative_to(self.base_dir)
            else:
                return self.objdir
        else:
            return file.file.parent
    
    def get_output_file(self, file):
        file = self.get_file(file)
        dir = self.get_output_dir(file)
        file = dir / Path(file.file.name)
        return file.with_suffix(".o")
        
    def determine_deps(self, file):
        file = self.get_file(file)
        compiler = self.get_compiler(file)
        c_paths = list(set(self.cpath + file.cpath))
        mm = subprocess.check_output([compiler, '-MM', str(file)] + 
                                     ["-I" + s for s in c_paths], env=self.env).decode('utf-8')
        ret = BuildContext._mm_regex.findall(mm)
        return { 'file_dep': ret }
    
    def get_action(self, file, additional_args=[]):
        file = self.get_file(file)
        compiler = self.get_compiler(file)
        out_path = self.get_output_file(file)
        out_path.parent.mkdir(parents = True, exist_ok = True)
        c_paths = list(set(self.cpath + file.cpath))
        c_args = list(set(self.cmd_args + file.cmd_args + additional_args))
        action = f"{compiler} -c -o  {out_path} {' '.join(c_args)} {' '.join(['-I' + s for s in c_paths])} {file}"
        print(action)
        return action
    
    def compile_file(self, file):
        file = self.get_file(file)
        action = self.get_action(file)
        return subprocess.run(action, env=self.env, capture_output=True).returncode == 0
    
def task_determine_dependencies():
    """Determine dependencies for C/C++ build"""

    for ctxt in BuildContext.Build_Contexts.values():
        for file in ctxt.sources:
            yield {
                'name': f"{file}_{ctxt.name}",
                'actions': [(ctxt.determine_deps, [file])],
                'file_dep': [str(file)]
            }

class BuildObject:
    def __str__(self):
        return self.file.as_posix()

    def __init__(self, file, cpath=[], cmd_args=[]):
        self.file = Path(file)
        self.cmd_args = cmd_args
        self.cpath = cpath

main_sources = Path('src').glob("*.cpp")

srcs = [BuildObject(f, cmd_args=['-DOTHER_FILE', '-DYES', '-DMAIN']) for f in (list(Path('.').glob("*.cpp")) + list(Path('.').glob('src/*.cpp')))]

main_build = BuildContext("main", cmd_args=['-DMAIN'], objdir='obj/build/main', replicate_structure=True)
main_build.sources += srcs

def task_compile():
    """I'm gonna try and compile stuff hot stuff"""
    
    yield {
        'basename': 'compile_x',
        'name': None,
        'doc': 'builds file x'
    }

    for ctxt in BuildContext.Build_Contexts.values():
        for file in ctxt.sources:
            yield {
                'name'    : str(file),
                'actions' : [(ctxt.compile_file, [file])],
                'file_dep': [str(file)],
                'calc_dep': [f"determine_dependencies:{file}_{ctxt.name}"],
                'targets' : [ctxt.get_output_file(file)]
            }

if __name__ == '__main__':
    import doit
    doit.run(globals())