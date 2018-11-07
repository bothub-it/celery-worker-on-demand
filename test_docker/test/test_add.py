from .tasks import add


if __name__ == '__main__':
    r = add.apply_async(
        args=[2, 1],
        queue='add',
    )
    r.wait()
    print(r.get())
