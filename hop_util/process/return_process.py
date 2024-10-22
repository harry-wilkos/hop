import sys
import os
import importlib
import pickle
import inspect
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import codecs

def enableHouModule():
    import sys, os
    sys.path.append(os.getenv('HHP'))
    if hasattr(sys, "setdlopenflags"):
        old_dlopen_flags = sys.getdlopenflags()
        sys.setdlopenflags(old_dlopen_flags | os.RTLD_GLOBAL)
    if sys.platform == "win32" and hasattr(os, "add_dll_directory"):
        os.add_dll_directory("{}/bin".format(os.getenv("HFS")))
    try:
        import hou
    except (ImportError, ModuleNotFoundError):
        sys.path.append(os.getenv('HHP'))
        import hou
    finally:
        if hasattr(sys, "setdlopenflags"):
            sys.setdlopenflags(old_dlopen_flags)

if __name__ == "__main__":
    if sys.argv[4] == "True":
        try:
            enableHouModule()
        except Exception as e:
            print("START")
            print(codecs.encode(pickle.dumps(f"ERROR: Couldn't import HOU: {e}"), "base64").decode())
            exit()
    module_path, module_file = os.path.split(Path(sys.argv[1]))
    module_name = os.path.splitext(module_file)[0]
    sys.path.append(module_path)
    module = importlib.import_module(module_name)

    function = getattr(module, sys.argv[2])
    args = pickle.loads(bytes.fromhex(sys.argv[3]))
    for c in range(len(args)):
        if len(args[c]) != len(inspect.getfullargspec(function)[0]):
            print("START")
            print(codecs.encode(pickle.dumps("ERROR: Incorrect number of args passed"), "base64").decode())
            exit()
    
    thread_d = {}
    with ProcessPoolExecutor() as exe:
        for r, i in enumerate(args):
            thread = exe.submit(function, *i)
            try:
                result = thread.result()
            except:
                result = thread.exception()
            thread_d[r] = result

    print("START")
    print(codecs.encode(pickle.dumps(thread_d), "base64").decode())