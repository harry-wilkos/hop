from hop.dl import discord

def __main__(*args):
    deadlinePlugin = args[0]
    job = deadlinePlugin.GetJob()
    shot = job.JobName
    holdout = job.JobComment
    message = (
        f":frame_photo:  **{holdout}** for **{shot}** finished rendering :frame_photo:"
    )
    discord(deadlinePlugin, message)

