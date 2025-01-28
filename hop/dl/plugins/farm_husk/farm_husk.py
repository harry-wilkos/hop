#!/usr/bin/env python3
from Deadline.Plugins import DeadlinePlugin, PluginType
from hop.dl import discord


def GetDeadlinePlugin():
    return Farm_Cache()


def CleanupDeadlinePlugin(deadlinePlugin):
    deadlinePlugin.clean_up()


class Farm_Cache(DeadlinePlugin):
    def __init__(self):
        super().__init__()
        self.fail = False
        self.InitializeProcessCallback += self.init_process
        self.RenderExecutableCallback += self.get_executable
        self.RenderArgumentCallback += self.get_args

    def init_process(self):
        self.PluginType = PluginType.Simple
        self.StdoutHandling = True
        self.SingleFramesOnly = True

    def get_executable(self):
        return self.GetConfigEntry("husk")

    def get_args(self):
        start_frame = self.GetStartFrame()
        file = self.GetPluginInfoEntry("usd_file")
        return f"-V7 --make-output-path -f {start_frame} {file}"

    def handle_error(self):
        pass

    def clean_up(self):
        handlers = [
            "InitializeProcessCallback",
            "RenderExecutableCallback",
            "RenderArgumentCallback",
        ]
        for handler in handlers:
            if hasattr(self, handler):
                delattr(self, handler)

        for stdoutHandler in self.StdoutHandlers:
            del stdoutHandler.HandleCallback

