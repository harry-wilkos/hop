#!/usr/bin/env python3
from Deadline.Plugins import DeadlinePlugin, PluginType
import os
from hop.dl.util import discord


def GetDeadlinePlugin():
    return Farm_Cache()


def CleanupDeadlinePlugin(deadlinePlugin):
    deadlinePlugin.clean_up()


class Farm_Cache(DeadlinePlugin):
    def __init__(self):
        super().__init__()
        self.InitializeProcessCallback += self.init_process
        self.RenderExecutableCallback += self.get_executable
        self.RenderArgumentCallback += self.get_args

    def init_process(self):
        self.PluginType = PluginType.Simple
        self.StdoutHandling = True
        self.AddStdoutHandlerCallback(r"ALF_PROGRESS (\d+)%").HandleCallback += (
            lambda: self.SetProgress(int(self.GetRegexMatch(1)))
        )
        self.AddStdoutHandlerCallback("ERROR:(.*)").HandleCallback += self.handle_error

    def get_executable(self):
        self.SingleFramesOnly = not self.GetBooleanPluginInfoEntry("simulation")
        return self.GetConfigEntry("hbatch")

    def get_args(self):
        hip_path = self.GetPluginInfoEntry("hip_file")
        node = self.GetPluginInfoEntry("node_path")
        start_frame = self.GetStartFrame()
        end_frame = self.GetEndFrame()

        if not self.GetBooleanPluginInfoEntry("simulation"):
            substep = self.GetFloatPluginInfoEntry("substep")
            end_frame += 1 - substep

        if not hip_path or not os.path.exists(hip_path):
            self.FailRender(f"Hip file path is invalid or does not exist: {hip_path}")

        return f'-c "render -Va -f {start_frame} {end_frame} {node}; quit" {hip_path}'

    def handle_error(self):
        hip_path = self.GetPluginInfoEntry("hip_file")
        node = self.GetPluginInfoEntry("node_path")
        discord(self, "test")
        self.FailRender("Detected an error: " + self.GetRegexMatch(1))

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
