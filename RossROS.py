"""
RossROS (lightweight local version)

The ROB515 manual suggests fetching RossROS.py from rossros.org. To keep your
repo self-contained, this file re-implements the subset needed for:
- threaded line following (sensor -> interpreter -> controller)
- threaded obstacle detection with ultrasonic

API exposed:
- Bus
- Producer
- ConsumerProducer
- Consumer
- Timer
"""
from students.rob.line_following.concurrent.bus import Bus, HardwareLock
from students.rob.line_following.concurrent.tasks import Producer, ConsumerProducer, Consumer, Timer

__all__ = [
    "Bus",
    "HardwareLock",
    "Producer",
    "ConsumerProducer",
    "Consumer",
    "Timer",
]
