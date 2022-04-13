import base58
import argparse

# Parse CLI arguments
def parse_args():
    # check for command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--cid", help="Specify the CIDv0 hash for the conversion", type=str)
    args = parser.parse_args()

    # CID sources
    assert args.cid, "Missing --cid, please provide one"

    if args.cid:
        assert args.cid[:2] == "Qm", f"Invalid cid: {args.cid}" # Support CIDv0 only

    return args

def main():
    # check for command line arguments
    try:
        args = parse_args()
    except Exception as err:
        sys.exit(f"Failed to initialize the converter: {err}")

    nftId = '0x' + bytes.hex(base58.b58decode(args.cid))[4:]

    print(nftId)

if __name__ == '__main__':
    main()
