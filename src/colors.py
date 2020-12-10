# --- Color System Definitions --- #
from enum import Enum

class Color(Enum):# (R, Y, B)
    RED =           (4, 0, 0)
    RED_ORANGE =    (3, 1, 0)
    ORANGE =        (2, 2, 0)
    YELLOW_ORANGE = (1, 3, 0)
    YELLOW =        (0, 4, 0)
    YELLOW_GREEN =  (0, 3, 1)
    GREEN =         (0, 2, 2)
    BLUE_GREEN =    (0, 1, 3)
    BLUE =          (0, 0, 4)
    BLUE_VIOLET =   (1, 0, 3)
    VIOLET =        (2, 0, 2)
    RED_VIOLET =    (3, 0, 1)
    BROWN =         (1, 1, 1)
    
    def adjacent(self, other):
        diff = sum(abs(c1 - c2) for c1, c2 in zip(self.value, other.value))
        return diff <= 2

    def __add__(self, other):
        # if addends contain all three components, make brown
        if all(c1 + c2 > 0 for c1, c2 in zip(self.value, other.value)):
            return Color.BROWN
        
        if self.adjacent(other):    # return the tertiary one
            return self if 1 in self.value else other
        else:                       # average RYB components
            return Color(tuple(
                (c1 + c2) // 2 for c1, c2 in zip(self.value, other.value)
            ))


assert(Color.RED + Color.YELLOW is Color.ORANGE)
assert(Color.RED + Color.GREEN is Color.BROWN)
for c in Color:
    assert(c + c is c)
assert(Color.RED_VIOLET + Color.VIOLET is Color.RED_VIOLET)
assert(Color.VIOLET + Color.RED_VIOLET is Color.RED_VIOLET)


# TODO in `main.py`, something like this:
# COLOR_RYB_RGB_MAP = {
#     Color.RED: (255, 0, 0),
#     ...
# }


