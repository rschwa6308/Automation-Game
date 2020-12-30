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
            midpoint = [
                (c1 + c2) // 2 for c1, c2 in zip(self.value, other.value)
            ]
            if sum(midpoint) < 4:   # colors do not have a perfect midpoint; shift towards tertiary
                midpoint[max([0, 1, 2], key=lambda i: midpoint[i])] += 1
            return Color(tuple(midpoint))



# RGB values taken from https://en.wikipedia.org/wiki/Tertiary_color#/media/File:Color_star-en_(tertiary_names).svg
# names do not match up exactly (e.g. "violet")
COLOR_RBG_MAP = {
    Color.RED:              (254, 39, 18),
    Color.RED_ORANGE:       (253, 83, 8),
    Color.ORANGE:           (251, 153, 2),
    Color.YELLOW_ORANGE:    (250, 188, 2),
    Color.YELLOW:           (254, 254, 51),
    Color.YELLOW_GREEN:     (208, 234, 43),
    Color.GREEN:            (102, 176, 50),
    Color.BLUE_GREEN:       (3, 146, 206),
    Color.BLUE:             (2, 71, 254),
    Color.BLUE_VIOLET:      (6, 1, 164),
    Color.VIOLET:           (134, 1, 175),
    Color.RED_VIOLET:       (167, 25, 75),
    Color.BROWN:            (139, 69, 19),      # "saddlebrown" (https://www.rapidtables.com/web/color/brown-color.html)
}



if __name__ == "__main__":
    assert(Color.RED + Color.BLUE is Color.VIOLET)
    assert(Color.RED + Color.RED_ORANGE is Color.RED_ORANGE)
    assert(Color.RED + Color.YELLOW is Color.ORANGE)
    assert(Color.RED + Color.GREEN is Color.BROWN)
    assert(Color.RED_VIOLET + Color.VIOLET is Color.RED_VIOLET)
    assert(Color.VIOLET + Color.RED_VIOLET is Color.RED_VIOLET)
    assert(Color.BLUE + Color.YELLOW_GREEN is Color.BLUE_GREEN)

    for c in Color:
        assert(c + c is c)

    for c1 in Color:
        for c2 in Color:
            # print(f"{c1} + {c2} = {c1 + c2}")
            assert(c1 + c2 in Color)        # closed
            assert(c1 + c2 is c2 + c1)      # commutative


# TODO in `main.py`, something like this:
# COLOR_RYB_RGB_MAP = {
#     Color.RED: (255, 0, 0),
#     ...
# }


