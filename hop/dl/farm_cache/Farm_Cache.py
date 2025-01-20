#!/usr/bin/env python3
from Deadline.Plugins import DeadlinePlugin
import os


def GetDeadlinePlugin():
    return Farm_Cache()


def CleanupDeadlinePlugin(deadlinePlugin):
    deadlinePlugin.clean_up()


class Farm_Cache(DeadlinePlugin):
    def __init__(self):
        self.InitializeProcessCallback += self.init_process
        self.RenderExecutableCallback += self.get_executable
        self.RenderArgumentCallback += self.get_args

    def init_process(self):
        self.StdoutHandling = True
        self.SingleFramesOnly = not self.GetBooleanConfigEntry("simulation")

        self.stdout_handler = self.AddStdoutHandlerCallback(r"ALF_PROGRESS (\d+)%")
        self.stdout_handler.HandleCallback += self.handle_progress

        self.error_handler_renderer = self.AddStdoutHandlerCallback(
            r"Couldn't find renderer: (.*)"
        )
        self.error_handler_renderer.HandleCallback += self.handle_renderer_error

    def get_executable(self):
        executable_path = os.path.normpath(self.GetConfigEntry("hbatch"))
        if not executable_path or not os.path.exists(executable_path):
            self.FailRender(f"Executable not found: {executable_path}")
        return executable_path

    def get_args(self):
        hip_path = self.GetPluginInfoEntry("hip_file")
        node = self.GetPluginInfoEntry("node_path")

        if not hip_path or not os.path.exists(hip_path):
            self.FailRender(f"Hip file path is invalid or does not exist: {hip_path}")

        return f"{hip_path} -c 'render -Va -f {self.GetStartFrame()} {self.GetEndFrame()} {node}; quit'"

    def clean_up(self):
        handlers = [
            "InitializeProcessCallback",
            "RenderExecutableCallback",
            "RenderArgumentCallback",
            "stdout_handler",
            "error_handler_renderer",
        ]
        for handler in handlers:
            if hasattr(self, handler):
                delattr(self, handler)

    def handle_progress(self):
        match = self.GetRegexMatch(1)
        if match:
            progress = int(match)
            self.SetProgress(progress)
            self.LogInfo(f"Cache progress: {progress}%")

    def handle_renderer_error(self):
        error_message = self.GetRegexMatch(1)
        self.FailRender(
            f"Error: Renderer node not found: {error_message}. Please verify the node path."
        )
