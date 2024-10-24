import sys
import os
import importlib
import pickle
import inspect
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import codecs
from ..import_hou import import_hou

if __name__ == "__main__":
    if sys.argv[4] == "True":
        try:
            import_hou()
        except Exception as e:
            print("START")
            print(
                codecs.encode(
                    pickle.dumps(f"ERROR: Couldn't import HOU: {e}"), "base64"
                ).decode()
            )
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
            print(
                codecs.encode(
                    pickle.dumps("ERROR: Incorrect number of args passed"), "base64"
                ).decode()
            )
            exit()

    thread_d = {}
    with ProcessPoolExecutor() as exe:
        for r, i in enumerate(args):
            thread = exe.submit(function, *i)
            try:
                result = thread.result()
            except Exception:
                result = thread.exception()
            thread_d[r] = result

    print("START")
    print(codecs.encode(pickle.dumps(thread_d), "base64").decode())

