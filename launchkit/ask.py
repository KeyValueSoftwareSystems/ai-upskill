"""Send one request of your own through an approach.

    python -m launchkit.ask --approach llm "Poster for the Tidal bottle on a beach"
    python -m launchkit.ask --approach graph --conv mine "Make the headline shorter"
    python -m launchkit.ask --approach graph --attach assets/tidal_photo.png "Use this photo"

Reuse --conv to stay in the same conversation.
"""
import argparse
import json

from .approaches import load_handle


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--approach", required=True, choices=["llm", "graph"])
    parser.add_argument("--workspace", default="harbor")
    parser.add_argument("--conv", default="playground")
    parser.add_argument("--attach", action="append", default=[])
    parser.add_argument("text")
    args = parser.parse_args()
    res = load_handle(args.approach)(args.text, workspace=args.workspace, conversation_id=args.conv, attachments=args.attach)
    if res.error:
        print("ERROR:", res.error)
    if res.spec:
        print(json.dumps(res.spec.to_dict(), indent=2))
    for path in res.images:
        print("image:", path)


if __name__ == "__main__":
    main()
