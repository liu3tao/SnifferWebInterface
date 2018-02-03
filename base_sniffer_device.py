"""A generic interface for sniffer devices."""

class BaseSnifferDevice(object):
  def __init__(self):
    super(BaseSnifferDevice, self).__init__()

  def start_capture(self):
    return True

  def stop_capture(self):
    return 'Capture'

  def split_capture(self):
    return 'Capture'

  def close(self):
    return True

  @property
  def model(self):
    return 'Base sniffer model'

  @property
  def is_capturing(self):
    return True

  @property
  def is_closed(self):
    return True