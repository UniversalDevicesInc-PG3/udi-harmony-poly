#!/usr/bin/env python3
#

import logging
from pyharmony import discovery as harmony_discovery

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=10,
    format='%(levelname)s:\t%(name)s\t%(message)s'
)
logger.setLevel(logging.DEBUG)
harmony_discovery.logger = logger
res = harmony_discovery.discover(scan_attempts=10,scan_interval=1)
harmony_discovery.discover.listen_socket.close()
print(res)
