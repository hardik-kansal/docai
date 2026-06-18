# from contextlib import contextmanager
def contextmanager(func):
    print("before wrapper")

    class wrapper:
        def __init__(self, *args):
            print("init")
            self.args = args
            self.g = func(*self.args)

        def __enter__(self):
            print("enter")
            return next(self.g)

        def __exit__(self, *args):
            print("exit")
            next(self.g)
            return True

    return wrapper


@contextmanager
def test(name):
    print("before try")
    try:
        yield 1
        print("after yield")
    finally:
        print("bye")
        yield


with test("Sam") as f:
    print("hi..")
    print(f)
