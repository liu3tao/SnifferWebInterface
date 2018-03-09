"""A generic interface for sniffer devices."""

import time


class BaseSnifferDevice(object):
  """A base sniffer device that can be used for test propose."""

  def __init__(self):
    super(BaseSnifferDevice, self).__init__()
    self._config = {}  # A dict of sniffer's config parameters.
    self._model_string = 'Base Sniffer'

  def set_capture_config(self, config):
    """Config the sniffer."""
    self._config.update(config)

  def get_capture_config(self):
    return self._config

  def start_capture(self):
    time.sleep(0.5)
    return True

  def stop_capture(self, capture_path):
    time.sleep(0.5)
    return 'Capture %s Stop @ %s' % (capture_path, time.time())

  def split_capture(self, capture_path):
    time.sleep(1)
    return 'Capture %s Split @ %s' % (capture_path, time.time())

  def close(self):
    return True

  @property
  def model(self):
    return self._model_string

  @property
  def is_capturing(self):
    return True

  @property
  def is_closed(self):
    return True
