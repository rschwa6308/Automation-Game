from typing import Callable, Sequence, Tuple

# EXPERIMENTAL
class Animation:
    """easily-constructible asynchronous animations"""
    def __init__(self, runner, steps: Sequence[Tuple[Callable, int]]):
        self.runner = runner
        self.steps = steps
        self.curr = 0
        self.length = sum(s[1] for s in steps)
        self.done = False

    def get_nth_step(self, n):
        i = 0
        tally = self.steps[0][1]
        while tally <= n:
            tally += self.steps[i + 1][1]
            i += 1

        return self.steps[i][0]

    def step(self):
        if self.done:
            raise RuntimeError("Animation has no more steps.")

        next_step = self.get_nth_step(self.curr)
        next_step(self.runner)

        self.curr += 1
        if self.curr >= self.length:
            self.done = True


if __name__ == "__main__":
    test_anim = Animation(None, [
        (lambda r: print("A"), 3),
        (lambda r: print("B"), 6),
    ])

    for _ in range(9):
        test_anim.step()
