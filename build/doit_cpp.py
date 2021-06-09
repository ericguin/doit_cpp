from pathlib import Path
import subprocess
import re
import platform
import os

class BuildContext:
    Build_Contexts = {}
    _mm_regex = re.compile(r'([\w\/]+\.h)')

    def _get_output_suffix():
        if platform.system() == "Windows":
            return ".exe"
        else:
            return ""

    def __init__(self, name, output=None, cmd_args=None, cpath=None, libs=None, libpath=None, sources=None, link_args=None,
                 cc=None, cxx=None, ar=None, objdir=None, replicate_structure=False, base_dir=None, env=None):
        self.name = name
        self.output = output or name + BuildContext._get_output_suffix()
        self.cmd_args = cmd_args or list()
        self.link_args = link_args or list()
        self.cpath = cpath or list()
        self.libs = libs or list()
        self.libpath = libpath or list()
        self.sources = sources or list()
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

    def get_linker(self):
        if any(f.file.suffix == ".cpp" for f in self.sources):
            return self.cxx
        else:
            return self.cc
    
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
        action = f"{compiler} -c -o  {out_path} {' '.join(c_args).strip()} {' '.join(['-I' + s for s in c_paths]).strip()} {file}"
        print(action)
        return action
    
    def get_objects(self):
        for file in self.sources:
            file = self.get_file(file)
            yield self.get_output_file(file)
                
    def compile_file(self, file):
        file = self.get_file(file)
        
        action = self.get_action(file)
        return subprocess.run(action, env=self.env).returncode == 0
    
    def get_link_action(self):
        objects = ' '.join([str(o) for o in list(self.get_objects())]).strip()
        libpath = ' '.join(['-L' + l for l in self.libpath]).strip()
        libs = f"-Wl,--start-group {' '.join(['-l' + lib for lib in self.libs]).strip()} -Wl,--end-group" if any(self.libs) else ""
        link_args = ' '.join([arg for arg in self.link_args]).strip()
        linker = self.get_linker()
        action = f"{linker} -o {self.output} {objects} {libpath} {libs} {link_args}"
        print(action)
        return action

    def link(self):
        action = self.get_link_action()
        return subprocess.run(action, env=self.env).returncode == 0
    
def task_determine_dependencies():
    """Determine dependencies for C/C++ build"""

    for ctxt in BuildContext.Build_Contexts.values():
        for file in ctxt.sources:
            yield {
                'name': f"{file}@{ctxt.name}",
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


def task_compile():
    """I'm gonna try and compile stuff hot stuff"""
    
    yield {
        'basename': 'compile:x',
        'name': None,
        'doc': 'builds file x'
    }

    for ctxt in BuildContext.Build_Contexts.values():
        for file in ctxt.sources:
            yield {
                'name'    : f"{file}@{ctxt.name}",
                'actions' : [(ctxt.compile_file, [file])],
                'file_dep': [str(file)],
                'calc_dep': [f"determine_dependencies:{file}@{ctxt.name}"],
                'clean': True,
                'targets' : [ctxt.get_output_file(file)],
                'verbosity' : 2
            }

def task_link():
    """Links stuff yo"""

    yield {
        'basename': 'link:x',
        'name': None,
        'doc': 'links the context x'
    }
    
    for ctxt in BuildContext.Build_Contexts.values():
        yield {
            'name': f"{ctxt.name}",
            'actions': [ctxt.link],
            'task_dep': [f'compile:*@{ctxt.name}'],
            'file_dep': list(ctxt.get_objects()),
            'targets': [f"{ctxt.output}"],
            'clean': True,
            'verbosity': 2
        }
