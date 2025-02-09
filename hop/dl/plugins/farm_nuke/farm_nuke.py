#!/usr/bin/env python3
from Deadline.Plugins import DeadlinePlugin, PluginType
import os


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
        return self.GetConfigEntry("nuke")

    def get_args(self):
        start_frame = self.GetStartFrame()
        file = self.GetPluginInfoEntry("nk_file")
        use_discord = self.GetBooleanPluginInfoEntry("discord")
        node = self.GetPluginInfoEntry("node_path")
        if not file or not os.path.exists(file):
            if use_discord:
                # send message to discord
                pass

            self.FailRender(f"Nuke file path is invalid or does not exist: {file}")
        return f"-x -t {file} -X {node} -F {start_frame} -V 2"

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
