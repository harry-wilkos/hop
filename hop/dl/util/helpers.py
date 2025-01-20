import os


def set_env(vars: list):
    for index, var in enumerate(vars):
        yield f"EnvironmentKeyValue{index}={var}={os.environ[var]}"
