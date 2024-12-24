import tempfile
from typing import Callable, Sequence, Union, Any
import inspect
import sys
import subprocess
import pickle
import os
import importlib
from concurrent.futures import ProcessPoolExecutor


class MultiProcess:
    def __init__(
        self,
        function: Callable,
        *args: Union[Any, Sequence[Any], Sequence[Sequence[Any]]],
        interpreter: str | None = None,
    ):
        self.function = function
        self.original_input = args
        self.args = self.process_args(args)
        self.interpreter = interpreter or sys.executable
        self.module_path = self.get_module()
        self.function_name = function.__name__
        self.process = None
        self.tempfile_path = None

    def get_module(self) -> str:
        module = inspect.getmodule(self.function)
        if module and module.__file__:
            return str(module.__file__)
        raise ImportError(
            f"Cannot determine module for function {self.function.__name__}"
        )

    def process_args(self, args: Sequence[Any]) -> list[Sequence[Any]]:
        """Chunk and validate arguments against the function's signature."""
        function_signature = inspect.signature(self.function)
        required_num_args = sum(
            param.default == inspect.Parameter.empty
            and param.kind
            in {
                inspect.Parameter.POSITIONAL_ONLY,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
            }
            for param in function_signature.parameters.values()
        )

        # Determine whether the input is already chunked
        if (
            len(args) == 1
            and isinstance(args[0], (list, tuple))
            and all(isinstance(item, (list, tuple)) for item in args[0])
        ):
            chunks = list(args[0])
        else:
            chunks = [
                args[i : i + required_num_args]
                for i in range(0, len(args), required_num_args)
            ]

        # Validate all chunks
        for chunk in chunks:
            try:
                function_signature.bind(*chunk)
            except TypeError as e:
                raise ValueError(f"Argument mismatch in chunk {chunk}: {e}")
        return chunks

    def execute(self) -> "MultiProcess":
        """Launch a subprocess to execute the function with prepared arguments."""
        script_file = str(__file__)
        if not script_file.endswith(".py"):
            script_file += ".py"

        env = os.environ.copy()
        env["PYTHONPATH"] = ":".join(sys.path)

        # Write arguments to a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.tempfile_path = temp_file.name
        with temp_file:
            pickle.dump(self.args, temp_file)

        # Pass the temp file path instead of serialized arguments
        self.process = subprocess.Popen(
            (
                self.interpreter,
                script_file,
                self.module_path,
                self.function_name,
                self.tempfile_path,
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        return self

    def retrieve(self, timeout: float | None = None) -> Any:
        """Retrieve and format the output from the subprocess with an optional timeout."""
        if self.process:
            try:
                stdout = self.process.communicate(timeout=timeout)[0]
            except subprocess.TimeoutExpired:
                self.process.kill()
                raise TimeoutError("Subprocess timed out.")
            finally:
                # Clean up the temporary file
                if self.tempfile_path:
                    os.unlink(self.tempfile_path)
                    self.tempfile_path = None

            output = stdout.decode()
            if "ERROR" in output:
                raise RuntimeError(output.split("ERROR", 1)[1].strip())
            if "RESULTS" in output:
                result_data = output.split("RESULTS", 1)[1].strip()
                flat_results = pickle.loads(bytes.fromhex(result_data))
                if len(self.original_input) == 1 and isinstance(
                    self.original_input[0], (list, tuple)
                ):
                    return [flat_results[idx] for idx in range(len(flat_results))]
                return flat_results
            raise ValueError("No results found in subprocess output.")
        raise RuntimeError("Subprocess has not been started.")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("ERROR: Incorrect arguments passed to subprocess")
        sys.exit(1)

    module_path, function_name, temp_file_path = sys.argv[1:]
    module_dir, module_file = os.path.split(module_path)
    module_name = os.path.splitext(module_file)[0]

    # Load the module dynamically
    sys.path.append(module_dir)
    try:
        module = importlib.import_module(module_name)
    except ImportError as e:
        print(f"ERROR: Failed to import module {module_name}: {e}")
        sys.exit(1)

    # Get the function
    try:
        function = getattr(module, function_name)
    except AttributeError:
        print(f"ERROR: Function {function_name} not found in module {module_name}")
        sys.exit(1)

    # Load arguments from the temporary file
    try:
        with open(temp_file_path, "rb") as temp_file:
            args = pickle.load(temp_file)
    except Exception as e:
        print(f"ERROR: Failed to load arguments from temporary file: {e}")
        sys.exit(1)

    # Execute function in parallel
    with ProcessPoolExecutor() as executor:
        futures = {
            executor.submit(function, *chunk): idx for idx, chunk in enumerate(args)
        }

        results = {}
        for future, idx in futures.items():
            try:
                results[idx] = future.result()
            except Exception as e:
                results[idx] = f"ERROR: {e}"

    # Return results to parent process
    print("RESULTS")
    print(pickle.dumps(results).hex())
    sys.exit(0)

