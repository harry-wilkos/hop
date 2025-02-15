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
        self.SingleFramesOnly = True
        self.AddStdoutHandlerCallback(r"(\d+)%").HandleCallback += (
            lambda: self.SetProgress(int(self.GetRegexMatch(1)))
        )
        self.AddStdoutHandlerCallback(
            r"(?i)(?<=Error:)(.|\n)*"
        ).HandleCallback += self.handle_error

    def get_executable(self):
        return self.GetConfigEntry("nuke")

    def get_args(self):
        start_frame = self.GetStartFrame()
        file = self.GetPluginInfoEntry("nk_file")
        use_discord = self.GetBooleanPluginInfoEntry("discord")
        node = self.GetPluginInfoEntry("node_path")
        proxy = "-f" if self.GetBooleanPluginInfoEntry("proxy") else ""
        if not file or not os.path.exists(file):
            if use_discord:
                name = self.GetJob().JobName
                discord(
                    self,
                    f":pouring_liquid: **{node}** in **{name}** failed rendering :pouring_liquid:",
                )
                discord(
                    self,
                    f":exclamation: Nuke file path is invalid or does not exist: {file} :exclamation:",
                )

            self.FailRender(f"Nuke file path is invalid or does not exist: {file}")
        return f"-X {node} -F {start_frame} -V 2 --topdown {proxy} {file}"

    def handle_error(self):
        if self.GetBooleanPluginInfoEntry("discord"):
            if not self.fail:
                name = self.GetJob().JobName
                node = self.GetPluginInfoEntry("node_path")
                discord(
                    self,
                    f":pouring_liquid: **{node}** in **{name}** failed rendering :pouring_liquid:",
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
