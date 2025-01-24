def __main__(deadlinePlugin):
    job = deadlinePlugin.GetJob()
    deadlinePlugin.LogInfo("JobName_HOP: %s" % job.JobName)
    deadlinePlugin.LogInfo("JobId_HOP: %s" % job.JobId)
    deadlinePlugin.LogInfo("discord_HOP: %s" % job.discord) 
