import inspect
from . import return_thread
from . import return_process
import subprocess
import os
import pickle
import sys
from pathlib import Path
import codecs
import re

def pre_process(args):
    if len(args) == 1 and type(args[0]) is list:
        values = args[0]
    else:
        values = list(args)

    for i in range(len(values)):
        if type(values[i]) is not list:
            values = [values]
            break

    return values


def thread(function, *args):
    args = pre_process(args)

    for c in range(len(args)):
        if len(args[c]) != len(inspect.getfullargspec(function)[0]):
            return "ERROR: Incorrect number of args passed"
        
    thread_d = {}
    for r, i in enumerate(args):
        thread = return_thread.return_thread(target=function, args=i)
        thread.start()
        thread_d[r] = thread

    return thread_d


def process(function, *args, hou = False, interpreter = None, module = None):
    args = pre_process(args)

    if interpreter is None and "python" in sys.executable or "hython" in sys.executable:
        interpreter = sys.executable
    elif  os.path.exists(interpreter) is False:
        return "ERROR: Cannot find python interpreter"

    if function is None:
        function = "main"

    if module is None:
        if inspect.isfunction(function):
            module = inspect.getmodule(function).__file__
            function = function.__name__
        else:
            return "ERROR: No function passed" 
    else:
        if os.path.exists(Path(module)) is True and type(function) is str:
            module = Path(module)        
        else:
            return "ERROR: No module passed"

    environmnet=os.environ
    if hou is True:
        try:
            environmnet["LD_PRELOAD"] = str(os.environ["HFS"]) + "/dsolib/libjemalloc.so"
        except KeyError:
            environmnet["HOUDINI_DISABLE_JEMALLOCTEST"] = "1"
        try:
            import hrpyc
            hrpyc.import_remote_module()
        except ModuleNotFoundError:
            return "ERROR: Cannot start server"
        except ConnectionRefusedError:
            hrpyc.start_server(use_thread=True, quiet=True)

    sub_p = subprocess.Popen([interpreter, "return_process.py", module, function, 
                            pickle.dumps(args).hex(), str(hou)], cwd=os.path.dirname(return_process.__file__), 
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                            env=environmnet)
    return sub_p


def retrieve(*threads_d):
    if type(threads_d[0]) is str and "ERROR" in threads_d[0]:
        return threads_d[0]
    else:
        collect = []
        if len(threads_d) != 1:
            for threads in threads_d:
                results = []
                if type(threads) is subprocess.Popen:
                    stdout = threads.communicate()[0].decode("utf-8").split("\n")[-3]
                    process = pickle.loads(codecs.decode(stdout.encode(), "base64"))
                    if type(process) is str:
                        collect = process
                    else:
                        for k in process:
                            results.append(process[k])
                        collect.append(results)
                else:
                    for i in threads:
                        results.append(threads[i].join())
                    collect.append(results)

        else:
            threads = threads_d[0]
            if type(threads) is not list:
                if type(threads) is not subprocess.Popen:
                    for i in threads:
                        collect.append(threads[i].join())
                else:
                    stdout = threads.communicate()[0].decode("utf-8")[::-1]
                    match = re.match(r"(?P<match>(\n|.)*)TRATS", stdout)
                    stdout = match.group("match")[::-1]
                    process = pickle.loads(codecs.decode(stdout.encode(), "base64"))
                    if type(process) is str:
                        collect = process
                    else:
                        for k in process:
                            collect.append(process[k])
            else:
                for __thread in threads:
                    results = []
                    for i in __thread:
                        results.append(__thread[i].join())
                    collect.append(results)
        if len(collect) == 1:
            collect = collect[0]
    return collect
