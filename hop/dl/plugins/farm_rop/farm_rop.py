#!/usr/bin/env python3
from Deadline.Plugins import DeadlinePlugin, PluginType
from hop.dl import discord
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
        self.AddStdoutHandlerCallback(r"(\b\d+\.\d+)(?=%)").HandleCallback += (
            lambda: self.SetProgress(int(self.GetRegexMatch(1)))
        )
        self.AddStdoutHandlerCallback(
            r"(?i)(?<=Error:)(.|\n)*"
        ).HandleCallback += self.handle_error

    def get_executable(self):
        return self.GetConfigEntry("husk")

    def get_args(self):
        start_frame = self.GetStartFrame()
        file = self.GetPluginInfoEntry("usd_file")
        if not file or not os.path.exists(file):
            if self.GetBooleanPluginInfoEntry("discord"):
                job = self.GetJob()
                shot = job.JobName
                node = job.JobComment
                discord(
                    self,
                    f":red_circle: **{node}** in **{shot}** failed rendering :red_circle:",
                )
                discord(
                    self,
                    f":exclamation: USD file path is invalid or does not exist: {file} :exclamation:",
                )
            self.FailRender(f"USD file path is invalid or does not exist: {file}")
        return f"-V7 --make-output-path -f {start_frame} {file}"

    def handle_error(self):
        job = self.GetJob()
        shot = job.JobName
        node = job.JobComment
        if self.GetBooleanPluginInfoEntry("discord"):
            if not self.fail:
                discord(
                    self,
                    f":red_circle: **{node}** in **{shot}** failed rendering :red_circle:",
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

