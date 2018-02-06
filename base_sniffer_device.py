"""A generic interface for sniffer devices."""

import time

class BaseSnifferDevice(object):
  def __init__(self):
    super(BaseSnifferDevice, self).__init__()

  def start_capture(self):
    time.sleep(0.5)
    return True

  def stop_capture(self):
    time.sleep(0.5)
    return 'Capture Stop @ %s' % time.time()

  def split_capture(self):
    time.sleep(1)
    return 'Capture Split @ %s' % time.time()

  def close(self):
    return True

  @property
  def model(self):
    return 'Base Sniffer'

  @property
  def is_capturing(self):
    return True

  @property
  def is_closed(self):
    return True