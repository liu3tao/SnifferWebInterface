import time
from datetime import datetime
from threading import Thread
from bisect import bisect


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

  def is_started(self):
    return self._start_timestamp is not None

  def is_stopped(self):
    return self._stop_timestamp is not None

  @property
  def start_time(self):
    return self._start_timestamp

  @property
  def stop_time(self):
    return self._stop_timestamp

  @property
  def owner(self):
    return self._owner

  @property
  def host(self):
    return self._host

  @property
  def id(self):
    return self._task_id

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
    self._split_interval = split_interval  # for temporary override
    self._running_tasks = list()  # running capture task list
    self._finished_tasks = list()  # finished capture task list
    self._task_id_map = dict()  # A dict of task id -> task for task lookup.
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
      if self._has_running_tasks():
        # state change: idle -> capture
        if not self._is_capturing:
          if self._controller.start_capture():
            self._is_capturing = True
            self._capture_start_time = time.time()
            time.strftime('CaptureManager: start capture @ %x %X.')
          else:
            print('Capture thread: failed to start capture (%s).' %
                  self._controller.model)
        # split trace based on interval
        if self._should_split():
          trace_path = self._controller.split_capture()
          trace_stop_time = time.time()
          trace_start_time = self._capture_start_time
          self._capture_start_time = time.time()
          self._trace_file_list.append((trace_start_time,
                                        trace_stop_time,
                                        trace_path))
          time.strftime('CaptureManager: split capture @ %x %X.')
      else:
        # No running task, stop capture is necessary.
        if self._is_capturing:
          # state change: capture -> idle
          trace_path = self._controller.stop_capture()
          trace_stop_time = time.time()
          trace_start_time = self._capture_start_time
          self._trace_file_list.append((trace_start_time,
                                        trace_stop_time,
                                        trace_path))
          self._previous_start_time = 0
          self._is_capturing = False
          time.strftime('CaptureManager: stop capture @ %x %X.')
      time.sleep(0.5)  # check every 0.5 seconds.

    # Capture thread will shutdown. Stop capture and close the controller.
    if self._is_capturing:
      # state change: capture -> shutdown
      trace_path = self._controller.stop_capture()
      trace_stop_time = time.time()
      trace_start_time = self._capture_start_time
      self._trace_file_list.append((trace_start_time,
                                    trace_stop_time,
                                    trace_path))
      self._previous_start_time = 0
      self._is_capturing = False
      time.strftime('CaptureManager: stop capture @ %x %X.')
      self._controller.close()

    print('Capture thread shutdown.')

  def _should_split(self):
    """Determine if we should split the file."""
    if self._split_interval > 0 and self._capture_start_time > 0:
      if time.time() - self._capture_start_time >= self._split_interval:
        return True
    return False

  def _has_running_tasks(self):
    return not self._running_tasks

  def _find_trace_list_by_timestamps(self, start_time, stop_time):
    """Find the list of traces within the start/stop time period."""
    result = list()
    # Find the first trace with start_time > task_start_time.
    idx = bisect(self._trace_file_list, (start_time, 0.0, ''))
    start_idx = idx - 1 if idx > 0 else 0
    # Then iterate from the start to end, add all traces within specified time.
    for trace_start_time, trace_stop_time, trace_path in \
            self._trace_file_list[start_idx:]:
      if trace_stop_time < stop_time:
        result.append(trace_path)
    return result

  def start_new_task(self, task_id, task_owner, task_host):
    """Start a new capture task."""
    # Every new task must has unique ID.
    if self.get_task_by_id(task_id):
      raise DuplicateTaskError('Duplicate task ID %s' % task_id)
    task = CaptureTask(task_id, task_owner, task_host)
    self._running_tasks.append(task)
    self._task_id_map[task_id] = task
    task.start()
    print('Start task, ID %s' % task_id)

  def stop_task(self, task_id):
    """Stop the task with specified task id."""
    task = self.get_task_by_id(task_id)
    if task is None:
      raise TaskNotFoundError('Cannot find task with ID %s' % task_id)
    if task.is_stopped():
      raise TaskStoppedError('Task already stopped.')
    # Now stop task and move it from running queue to finished queue.
    task.stop()
    try:
      self._running_tasks.remove(task)
    except ValueError:
      # We cannot find the task in the running queue? Something is wrong.
      raise CaptureTaskException('Running task not found in queue')
    finally:
      self._finished_tasks.append(task)
      print('Stop task, ID %s' % task_id)

  def get_finished_tasks(self):
    return self._finished_tasks

  def get_running_tasks(self):
    return self._running_tasks

  def get_task_by_id(self, task_id):
    return self._task_id_map.get(task_id, None)

  def get_trace_list_by_task_id(self, task_id):
    """Find the list of traces file URL of a capture task."""
    task = self.get_task_by_id(task_id)
    if task is None:
      raise TaskNotFoundError('Cannot find task with ID %s' % task_id)

    start_time = task.start_time
    stop_time = task.stop_time
    if start_time is None:
      return []
    if stop_time is None:
      stop_time = time.time()
    return self._find_trace_list_by_timestamps(start_time, stop_time)

  def shutdown(self):
    """Shutdown the capture thread."""
    self._shutdown = True
    for task in self._running_tasks:
      task.stop()
      self._finished_tasks.append(task)


class CaptureTaskException(Exception):
  pass


class DuplicateTaskError(CaptureTaskException):
  pass


class TaskNotFoundError(CaptureTaskException):
  pass


class TaskStoppedError(CaptureTaskException):
  pass

