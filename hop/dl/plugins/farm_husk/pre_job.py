from hop.dl import discord


def __main__(*args):
    deadlinePlugin = args[0]
    job = deadlinePlugin.GetJob()
    shot = job.JobName
    holdout = job.JobComment
    message = (
        f":movie_camera: **{holdout}** for **{shot}** started rendering :movie_camera:"
    )
    discord(deadlinePlugin, message)

