#!/usr/bin/env python3
from Deadline.Plugins import DeadlinePlugin, PluginType
import os
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
        self.SingleFramesOnly = not self.GetBooleanPluginInfoEntry("simulation")
        self.AddStdoutHandlerCallback(r"ALF_PROGRESS (\d+)%").HandleCallback += (
            lambda: self.SetProgress(int(self.GetRegexMatch(1)))
        )
        self.AddStdoutHandlerCallback(
            r"(?i)(?<=Error:)(.|\n)*"
        ).HandleCallback += self.handle_error

    def get_executable(self):
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
            name = self.GetJob().JobName
            discord(
                self,
                f":red_circle: **{node}** in **{name}** failed caching :red_circle:",
            )
            discord(
                self,
                f":exclamation: Hip file path is invalid or does not exist: {hip_path} :exclamation:",
            )
            self.FailRender(f"Hip file path is invalid or does not exist: {hip_path}")

        return f'-c "render -Va -f {start_frame} {end_frame} {node}; quit" {hip_path}'

    def handle_error(self):
        node = os.path.dirname(self.GetPluginInfoEntry("node_path"))
        name = self.GetJob().JobName
        if self.GetBooleanPluginInfoEntry("discord"):
            if not self.fail:
                discord(
                    self,
                    f":red_circle: **{node}** in **{name}** failed caching :red_circle:",
                )
                self.fail = True
            discord(
                self, f":exclamation: {self.GetRegexMatch(0).strip()} :exclamation:"
            )
        self.FailRender("Detected an error: " + self.GetRegexMatch(0).strip())

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
