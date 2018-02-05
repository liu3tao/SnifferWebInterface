import unittest
import time
from base_sniffer_device import BaseSnifferDevice
from capture_manager import CaptureManager

class MyTestCase(unittest.TestCase):
  def test_manager(self):
    sniffer = BaseSnifferDevice()
    manager = CaptureManager(controller=sniffer)
    time.sleep(1)
    for t in range(2):
      manager.start_new_task('test%d' % t, 'test owner', 'localhost')
      time.sleep(2)
      manager.stop_task('test%d' % t)

    for task in manager.get_finished_tasks():
      print('Finished: id %s, start %s, stop %s' % (task.id, task.start_time, task.stop_time))
      for trace in manager.get_trace_list_by_task_id(task.id):
        print('- T: %s' % trace)

    time.sleep(5)
    manager.shutdown()

if __name__ == '__main__':
  unittest.main()
