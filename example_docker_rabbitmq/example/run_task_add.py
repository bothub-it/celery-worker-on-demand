from time import time
from .tasks import add


if __name__ == '__main__':
    stated_at = time()
    r = add.apply_async(
        args=[2, 1],
        queue='add',
    )
    r.wait()
    print(r.get())
    print(time() - stated_at)
