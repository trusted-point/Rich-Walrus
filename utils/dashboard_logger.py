import logging
from collections import deque

class RichPanelLogHandler(logging.Handler):
    def __init__(self, max_logs=8):
        super().__init__()
        self.log_lines = deque(maxlen=max_logs)

    def emit(self, record):
        log_entry = self.format(record).strip()
        self.log_lines.append(log_entry)

    def get_logs(self):
        return "\n".join(self.log_lines)