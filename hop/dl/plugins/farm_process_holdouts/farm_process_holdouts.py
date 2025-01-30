#!/usr/bin/env python3
from Deadline.Plugins import DeadlinePlugin, PluginType
import os
from shutil import which


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
        self.AddStdoutHandlerCallback(r"(?i)(?<=Error:)(.|\n)*").HandleCallback += (
            lambda: self.FailRender(
                "Detected an error: " + self.GetRegexMatch(0).strip()
            )
        )

    def get_executable(self):
        return (
            os.path.normpath(magick)
            if (magick := which("magick.exe")) is not None
            else self.FailRender("Cannot find Image Magick")
        )

    def get_args(self):
        start_frame = f"{self.GetStartFrame():04d}"
        run = self.GetPluginInfoEntry("back_plate").replace("$F", start_frame)
        output_path = self.GetPluginInfoEntry("output")
        exrs = [
            os.path.join(path, f"{start_frame}.exr")
            for path in self.GetPluginInfoEntry("exrs").split(";")
        ]

        for count, exr in enumerate(exrs):
            exr = rf" ( {exr} -resize 1280x720 ) "
            if not count and not run:
                run += exr
                continue
            run += f"{exr} -compose Over -composite"

        output = os.path.normpath(os.path.join(output_path, f"{start_frame}.png"))
        return f"{run} -resize 1280x720 {output}"

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
