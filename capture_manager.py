import time
from Queue import Queue
from datetime import datetime
from threading import Thread


# Some default values
DEFAULT_CAP_DIR = r'C:\Users\tao\bxe400_traces'  # Also a FTP base dir
DEFAULT_SPLIT_INTERVAL = 120  # split trace every 2 minutes.
DEFAULT_FTP_LINK = r'ftp://100.96.38.40/'


class CaptureTask(object):
  """Data class for capture tasks"""
  def __init__(self, task_id, owner, host):
    self._task_id = task_id       # str, the id of this task
    self._start_timestamp = None  # Float, epoch time
    self._stop_timestamp = None   # Float, epoch time
    self._owner = owner           # str, the owner of this task
    self._host = host             # str, from which host the task come

  def start(self):
    self._start_timestamp = time.time()

  def stop(self):
    self._stop_timestamp = time.time()

  @property
  def started(self):
    return self._start_timestamp is not None

  @property
  def stopped(self):
    return self._stop_timestamp is not None

  @property
  def start_time(self):
    if self._start_timestamp:
      return datetime.fromtimestamp(self._start_timestamp)
    return None

  @property
  def stop_time(self):
    if self._stop_timestamp:
      return datetime.fromtimestamp(self._stop_timestamp)
    return None

  @property
  def owner(self):
    return self._owner

  @property
  def host(self):
    return self._host


class CaptureManager(object):
  def __init__(self, controller,
               capture_dir=DEFAULT_CAP_DIR,
               split_interval=DEFAULT_SPLIT_INTERVAL):
    """Maintain the capture thread.

      Args:
        controller: sniffer controller.
        capture_dir: str, the capture directory
        split_interval: float, the time interval before each split
    """
    self._controller = controller
    self._is_capturing = False
    self._shutdown = False
    self._capture_dir = capture_dir
    self._split_interval = split_interval
    self._running_tasks = Queue()  # Queues of capture tasks.
    self._finished_tasks = Queue()
    # Sorted list of captured trace's (start epoch time, filename).
    self._trace_file_list = []

    # Start the capture thread
    self._capture_thread = Thread(target=self._capture_thread_func)
    self._capture_thread.daemon = True # thread dies with the program
    self._capture_thread.start()
    self._capture_start_time = 0

  def _capture_thread_func(self):
    """Thread function for capture management."""
    print('Capture thread started.')

    while not self._shutdown:
      # Running state change
      if self._has_pending_tasks():
        # state change: idle -> capture
        if not self._is_capturing:
          if self._controller.start_capture():
            self._is_capturing = True
            self._capture_start_time = time.time()
          else:
            print('Capture thread: failed to start capture (%s).' %
                  self._controller.model)
        # split trace based on interval
        if self._should_split():
          trace_path = self._controller.split_capture()
          trace_start_time = self._capture_start_time
          self._capture_start_time = time.time()
          self._trace_file_list.append((trace_start_time, trace_path))
      else:
        # No running task, stop capture is necessary.
        if self._is_capturing:
          # state change: capture -> idle
          trace_path = self._controller.stop_capture()
          trace_start_time = self._capture_start_time
          self._trace_file_list.append((trace_start_time, trace_path))
          self._previous_start_time = 0
          self._is_capturing = False
      time.sleep(0.5)  # check every 0.5 seconds.

    # Capture thread will shutdown. Stop capture and close the controller.
    if self._is_capturing:
      # state change: capture -> shutdown
      trace_path = self._controller.stop_capture()
      trace_start_time = self._capture_start_time
      self._trace_file_list.append((trace_start_time, trace_path))
      self._previous_start_time = 0
      self._is_capturing = False
      self._controller.close()

    print('Capture thread shutdown.')

  def _should_split(self):
    """Determine if we should split the file."""
    if self._split_interval > 0 and self._capture_start_time > 0:
      if time.time() - self._capture_start_time >= self._split_interval:
        return True
    return False

  def _has_pending_tasks(self):
    return not self._running_tasks.empty()

  def add_task(self, task, exclusive=False, split_interval_override=0):
    self._running_tasks.put(task)
    task.start()

  def get_finished_tasks(self):
    return (t for t in self._finished_tasks.queue)

  def get_task(self, task_uuid):
    pass