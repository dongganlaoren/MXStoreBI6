import multiprocessing as mp
import sys
import time

import pdfplumber


def worker(path: str, q: mp.Queue):
    t0 = time.time()
    try:
        with pdfplumber.open(path) as pdf:
            q.put(('opened', len(pdf.pages), time.time() - t0))
            p0 = pdf.pages[0]
            t1 = time.time()
            txt = p0.extract_text()
            q.put(('text', 0 if txt is None else len(txt), time.time() - t1, (txt or '')[:300]))
    except BaseException as e:
        q.put(('error', repr(e), time.time() - t0))


def main():
    path = sys.argv[1]
    q: mp.Queue = mp.Queue()
    p = mp.Process(target=worker, args=(path, q), daemon=True)
    p.start()

    deadline = time.time() + 8
    while time.time() < deadline:
        try:
            msg = q.get(timeout=0.5)
            print(msg)
            sys.stdout.flush()
        except Exception:
            pass
        if not p.is_alive():
            break

    if p.is_alive():
        p.terminate()
        p.join(1)
        print(('timeout', path))


if __name__ == '__main__':
    main()
