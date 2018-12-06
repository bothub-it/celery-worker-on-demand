from .tasks import diff


if __name__ == '__main__':
    r = diff.apply_async(
        args=[4, 2],
        queue='diff',
    )
    r.wait()
    print(r.get())
