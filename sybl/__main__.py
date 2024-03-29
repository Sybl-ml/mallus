import argparse
import sybl.authenticate


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    subparser = parser.add_subparsers(required=True, dest="authenticate")
    authentication_parser = subparser.add_parser("authenticate")

    authentication_parser.add_argument(
        "--email", "-e", type=str, help="Email for sybl client account", default=None
    )
    authentication_parser.add_argument(
        "--model-name", "-m", type=str, help="Name of your new model", default=None
    )
    authentication_parser.add_argument(
        "--ip", type=str, help="IP of the dcl to connect to", default="sybl.tech"
    )
    authentication_parser.add_argument(
        "--port", type=int, help="the port to connect to", default=7000
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    sybl.authenticate.main(args)
