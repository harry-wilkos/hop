import os


def set_env(vars: list):
    for index, var in enumerate(vars):
        value = os.environ[var]
        if os.path.exists(value):
            value = os.path.normpath(value)
        yield f"EnvironmentKeyValue{index}={var}={value}"
