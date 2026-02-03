# students/rob/drive_cli.py
from students.rob.picarx_improved import Car
from students.rob.maneuvers import parallel_park_left, k_turn_left, drive_for

MENU = """
w: forward
s: backward
a: parallel park left
k: k-turn left
x: stop
0: quit
"""

def main():
    car = Car()
    print(MENU)

    while True:
        cmd = input("cmd> ").strip().lower()

        if cmd == "0":
            car.stop()
            break
        elif cmd == "w":
            drive_for(car, 0.8, +30, 0)
        elif cmd == "s":
            drive_for(car, 0.8, -30, 0)
        elif cmd == "a":
            parallel_park_left(car)
        elif cmd == "k":
            k_turn_left(car)
        elif cmd == "x":
            car.stop()
        else:
            print("unknown command")

if __name__ == "__main__":
    main()
