import time
from threading import Thread
from bisect import bisect
import json
import os


# Some default values
DEFAULT_CAP_DIR = r'C:\Users\tao\bxe400_traces'  # Also a FTP base dir
DEFAULT_SPLIT_INTERVAL = 120  # split trace every 2 minutes.
DEFAULT_FTP_LINK = r'ftp://100.96.38.40/'
DEFAULT_CAPTURE_THREAD_CHECK_INTERVAL = 0.1  # Check for new task interval
DEFAULT_HUMAN_READABLE_TIME_FORMAT = '%x %X'
DEFAULT_TASK_SAVE_PATH = r'C:\Users\tao\Documents\GitHub\SnifferWebInterface\capture_tasks.json'

def get_capture_filename_by_timestamp(start_time, stop_time):
  """Generate capture filename based on the specified timestamp."""
  filename = 'cap-%s-%s.btt' % (
    time.strftime('%y%m%d_%H%M%S', time.localtime(start_time)),
    time.strftime('%y%m%d_%H%M%S', time.localtime(stop_time)))
  return filename

class CaptureTask(object):
  """Data class for capture tasks"""
  def __init__(self, task_id, owner, host):
    self._task_id = task_id       # str, the id of this task
    self._start_timestamp = None  # Float, epoch time
    self._stop_timestamp = None   # Float, epoch time
    self._owner = owner           # str, the owner of this task
    self._host = host             # str, from which host the task come
    self._trace_list = []         # str list, the capture traces of this task.
    self._trace_pending = False   # bool, True if capture is pending.

  def start(self):
    self._start_timestamp = time.time()
    self._trace_pending = True

  def stop(self):
    self._stop_timestamp = time.time()

  def is_started(self):
    return self._start_timestamp is not None

  def is_stopped(self):
    return self._stop_timestamp is not None

  def is_trace_pending(self):
    return self._trace_pending

  def add_trace(self, trace_path, more_trace=True):
    self._trace_list.append(trace_path)
    self._trace_pending = more_trace

  def to_dict(self, time_format_string=DEFAULT_HUMAN_READABLE_TIME_FORMAT):
    """Convert task to dict for easy serialization."""
    res = {}
    res['id'] = self._task_id
    if self._start_timestamp:
      res['start_time'] = time.strftime(
          time_format_string, time.localtime(self._start_timestamp))
    else:
      res['start_time'] = ''
    if self._stop_timestamp:
      res['stop_time'] = time.strftime(
          time_format_string, time.localtime(self._stop_timestamp))
    else:
      res['stop_time'] = ''
    res['owner'] = self._owner
    res['host'] = self._host
    tmp = []
    for p in self._trace_list:
      tmp.append(p if DEFAULT_FTP_LINK in p else DEFAULT_FTP_LINK + p)
    res['trace_list'] = tmp
    res['status'] = self.status
    return res

  @classmethod
  def from_dict(cls, task_dict,
                time_format_string=DEFAULT_HUMAN_READABLE_TIME_FORMAT):
    """Convert a dict to task."""
    try:
      task_id = task_dict['id']
      owner = task_dict['owner']
      host = task_dict['host']
      # Read the string to epoch time.
      start_timestamp = time.mktime(
          time.strptime(task_dict['start_time'], time_format_string))
      stop_timestamp = time.mktime(
          time.strptime(task_dict['stop_time'], time_format_string))
      if isinstance(task_dict['trace_list'], list):
        trace_list = task_dict['trace_list']
      else:
        raise CaptureTaskException('Invalid trace list.')
      pending = False
      if task_dict['status'] in ['Running', 'Pending']:
        pending = True

      task = CaptureTask(task_id, owner, host)
      task._start_timestamp = start_timestamp
      task._stop_timestamp = stop_timestamp
      task._trace_list = trace_list
      task._trace_pending = pending
      return task
    except KeyError as ex:
      msg = 'Failed to load task from dict, missing %s' % ex
      raise CaptureTaskException(msg)
    except ValueError as ex:
      msg = 'Failed to parse time: %s.' % ex
      raise CaptureTaskException(msg)

  @property
  def status(self):
    """Returns task status as str.

    There are 5 possible status:
    - Not started: no start time set
    - Running: started and not stopped.
    - Pending: stopped, waiting for last capture to finish.
    - Finished: stopped and all capture is done.
    """
    if self._start_timestamp is None:
      st = 'Not Started'
    elif self._stop_timestamp is None:
      st = 'Running'
    elif self._trace_pending:
      st = 'Pending'
    else:
      st = 'Finished'
    return st

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

  @property
  def trace_list(self):
    return self._trace_list

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
    self._running_tasks = []  # running capture task list
    self._pending_tasks = []  # stopped tasks waiting for last capture to finish.
    self._finished_tasks = []  # finished capture task list
    self._task_id_map = {}  # A dict of task id -> task for task lookup.
    # Sorted list of captured trace's (start epoch time, filename).
    self._trace_file_list = []

    # Start the capture thread
    self._capture_thread = Thread(target=self._capture_thread_func)
    self._capture_thread.daemon = True # thread dies with the program
    self._capture_thread.start()
    self._capture_start_time = 0

    # Load previous captures
    self._load_tasks_from_disk()

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
            print(time.strftime('CaptureThread: start capture @ %x %X.'))
          else:
            print('Capture thread: failed to start capture (%s).' %
                  self._controller.model)
        # split trace based on interval
        if self._should_split():
          self._split_capture()
          print(time.strftime('CaptureThread: split capture @ %x %X.'))
      else:
        # No running task, stop capture is necessary.
        if self._is_capturing:
          # state change: capture -> idle
          self._stop_capture()
          print(time.strftime('CaptureThread: stop capture @ %x %X.'))
      time.sleep(DEFAULT_CAPTURE_THREAD_CHECK_INTERVAL)

    # Capture thread will shutdown. Stop capture and close the controller.
    if self._is_capturing:
      # state change: capture -> shutdown
      self._stop_capture()
      time.strftime('CaptureThread: shutdown capture @ %x %X.')
    print('Capture thread shutdown.')

  def _stop_capture(self):
    """Stop the capture with necessary bookkeeping."""
    trace_path = get_capture_filename_by_timestamp(
        self._capture_start_time, time.time())
    real_path = os.path.join(DEFAULT_CAP_DIR, trace_path)
    print('CaptureManager: stopping capture, trace path %s' % real_path)
    trace_path = self._controller.stop_capture(real_path)
    trace_stop_time = time.time()
    trace_start_time = self._capture_start_time
    self._trace_file_list.append((trace_start_time,
                                  trace_stop_time,
                                  trace_path))
    self._previous_start_time = 0
    self._is_capturing = False
    self._add_trace_to_tasks(trace_path)

  def _split_capture(self):
    """Split capture"""
    trace_path = get_capture_filename_by_timestamp(
        self._capture_start_time, time.time())
    real_path = os.path.join(DEFAULT_CAP_DIR, trace_path)
    print('CaptureManager: spliting capture, trace path %s' % real_path)
    trace_path = self._controller.split_capture(real_path)
    trace_start_time = self._capture_start_time
    trace_stop_time = time.time()
    self._capture_start_time = trace_stop_time
    self._trace_file_list.append((trace_start_time,
                                  trace_stop_time,
                                  trace_path))
    self._add_trace_to_tasks(trace_path)

  def _add_trace_to_tasks(self, trace_path):
    """Add trace to running task and move finished task to the finished list."""
    finished_idx = []
    idx = 0
    for task in self._running_tasks:
      task.add_trace(trace_path)
    # Reverse the list so they are in time order.
    for task in reversed(self._pending_tasks):
      task.add_trace(trace_path, more_trace=False)
      print('CaptureManager: Task finished, ID %s' % task.id)
      self._finished_tasks.append(task)
    self._pending_tasks = []

  def _should_split(self):
    """Determine if we should split the file."""
    if self._split_interval > 0 and self._capture_start_time > 0:
      if time.time() - self._capture_start_time >= self._split_interval:
        return True
    return False

  def _has_running_tasks(self):
    return bool(self._running_tasks)

  def _find_trace_list_by_timestamps(self, start_time, stop_time):
    """Find the list of traces within the start/stop time period."""
    result = []
    # Find the first trace with start_time > task_start_time.
    idx = bisect(self._trace_file_list, (start_time, 0.0, ''))
    start_idx = idx - 1 if idx > 0 else 0
    # Then iterate from the start to end, add all traces within specified time.
    for trace_start_time, trace_stop_time, trace_path in \
            self._trace_file_list[start_idx:]:

      if trace_stop_time <= start_time:
        continue
      elif trace_start_time >= stop_time:
        break
      else:
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
    print('CaptureManager: Start task, ID %s' % task_id)

  def stop_task(self, task_id):
    """Stop the task with specified task id."""
    task = self.get_task_by_id(task_id)
    if task is None:
      raise TaskNotFoundError('Cannot find task with ID %s' % task_id)
    if task.is_stopped():
      raise TaskStoppedError('Task already stopped.')
    # Stopped task will be moved to pending list. Task in pending list will be
    # moved to finished on the next capture split/stop.
    task.stop()
    try:
      self._running_tasks.remove(task)
    except ValueError:
      raise TaskNotFoundError('Cannot find task in queue. ID %s' % task_id)
    self._pending_tasks.append(task)
    print('CaptureManager: Stop task (wait for last capture), ID %s' % task_id)

  def get_finished_tasks(self):
    return self._finished_tasks

  def get_running_tasks(self):
    return self._running_tasks

  def get_pending_tasks(self):
    return self._pending_tasks

  def get_task_by_id(self, task_id):
    return self._task_id_map.get(task_id, None)

  def shutdown(self):
    """Shutdown the capture thread."""
    for task in self._running_tasks:
      task.stop()
    self._shutdown = True
    self._capture_thread.join()
    self._controller.close()
    self._save_tasks_to_disk()

  def get_controller_model(self):
    return self._controller.model

  def get_capture_config(self):
    """Get capture config as dict."""
    # Capture config is controller's config + split setting.
    # TODO: should be converted to a generic config method.
    config = {'Capture Split Interval': '%s seconds' % self._split_interval}
    config.update(self._controller.get_capture_config())
    return config

  def _save_tasks_to_disk(self):
    """Save the tasks to persistent storage."""
    res = []
    for task in self._finished_tasks:
      res.append(task.to_dict())
    try:
      with open(DEFAULT_TASK_SAVE_PATH, 'wb') as f:
        json.dump(res, f, indent=1)
        print('%d tasks saved to %s.' % (len(res), DEFAULT_TASK_SAVE_PATH))
    except IOError as ex:
      print('Failed to save task: %s' % ex)

  def _load_tasks_from_disk(self):
    """Load the task from disk"""
    res = []
    try:
      with open(DEFAULT_TASK_SAVE_PATH, 'rb') as f:
        res = json.load(f)
    except IOError:
      print 'No saved task, starting fresh.'
    for t in res:
      task = CaptureTask.from_dict(t)
      self._finished_tasks.append(task)
      self._task_id_map[task.id] = task


class CaptureTaskException(Exception):
  pass


class DuplicateTaskError(CaptureTaskException):
  pass


class TaskNotFoundError(CaptureTaskException):
  pass


class TaskStoppedError(CaptureTaskException):
  pass
