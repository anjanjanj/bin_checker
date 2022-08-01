import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from bin_checker import BinChecker

# init logger
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(name)-12s "
                              "%(levelname)-8s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

# create checker
checker = BinChecker(days_from_now=1)

# create and configure scheduler
sched = BlockingScheduler()

sched.add_job(checker.run, "cron", coalesce=True, max_instances=1, hour="*/6")

# start scheduler
sched.start()
