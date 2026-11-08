#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nástroj pro vytváření a čtení souborů .vlcr z příkazové řádky.

  python vlcr_tool.py encode "Ahoj světe" -o zprava.vlcr
  python vlcr_tool.py encode -i zprava.txt -o zprava.vlcr
  python vlcr_tool.py decode zprava.vlcr
"""
import argparse
import sys

import vlcr_codec


def main():
    p = argparse.ArgumentParser(description="Nástroj pro soubory .vlcr")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("encode", help="vytvoří .vlcr ze zprávy")
    e.add_argument("message", nargs="?", help="text zprávy (nebo použijte -i)")
    e.add_argument("-i", "--input", help="načíst zprávu z textového souboru")
    e.add_argument("-o", "--output", help="výstupní soubor .vlcr (jinak stdout)")

    d = sub.add_parser("decode", help="vypíše zprávu ze souboru .vlcr")
    d.add_argument("file")

    a = p.parse_args()
    if a.cmd == "encode":
        if a.input:
            with open(a.input, encoding="utf-8") as f:
                msg = f.read()
        elif a.message is not None:
            msg = a.message
        else:
            msg = sys.stdin.read()
        out = vlcr_codec.encode(msg)
        if a.output:
            with open(a.output, "w", encoding="utf-8") as f:
                f.write(out)
            print("Hotovo:", a.output)
        else:
            sys.stdout.write(out)
    else:
        with open(a.file, encoding="utf-8", errors="replace") as f:
            try:
                print(vlcr_codec.decode(f.read()))
            except ValueError as ex:
                sys.exit(str(ex))


if __name__ == "__main__":
    main()
