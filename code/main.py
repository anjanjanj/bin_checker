import logging
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

checker.run()
