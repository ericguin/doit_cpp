from build.doit_cpp import *
from pathlib import Path

srcs = [BuildObject(f, cmd_args=['-DOTHER_FILE', '-DYES', '-DMAIN']) for f in (list(Path('.').glob("*.cpp")) + list(Path('.').glob('src/*.cpp')))]

main_build = BuildContext("main", cmd_args=['-DMAIN'], objdir='obj/build/main')
main_build.sources.extend(srcs)
print(main_build.sources)

ut_build = BuildContext("ut", cmd_args=['-DUT'], objdir='obj/build/ut')
ut_build.sources.extend(srcs)
ut_build.sources.extend([BuildObject("ut/ut.cpp")])
print(main_build.sources)

if __name__ == '__main__':
    import doit
    doit.run(globals())