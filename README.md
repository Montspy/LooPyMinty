# LoopMintPy

This is a Python3 adaptation of fudgey's [LoopMintSharp](https://github.com/fudgebucket27/LoopMintSharp).

## Install

Using local environment:

```shell
git clone --recurse-submodules https://github.com/sk33z3r/LoopMintPy.git
pip3 install -r hello_loopring/requirements.txt -r requirements.txt
python3 LoopMintPy.py --format cid --metadata QmVpLSoYak1N8pasuxLrNZLbnvrNvLTJmY8ncMBjNRPBtQ --count 100
```

Using Docker:

```shell
git clone --recurse-submodules https://github.com/sk33z3r/LoopMintPy.git
./docker.sh build
./docker.sh --format cid --metadata QmVpLSoYak1N8pasuxLrNZLbnvrNvLTJmY8ncMBjNRPBtQ --count 100
```

## dotenv

First you need to export your account to get the necessary details to fill in the dotenv file.

Go to loopring.io -> Security -> Export Account and copy the JSON provided into a safe space.

**DO NOT SHARE THIS INFO WITH ANYONE**

The output should look something like this:

```json
{
    "address": "0x000000000000000000000000000000000000000000000",
    "accountId": 12345,
    "level": "",
    "nonce": 1,
    "apiKey": "jKGjglkSlkdglksjdglkjsdgLHlhGksldjhgalHGLghlgg9dgHLGHSDgh",
    "publicX": "0x000000000000000000000000000000000000000000000",
    "publicY": "0x000000000000000000000000000000000000000000000",
    "privateKey": "0x000000000000000000000000000000000000000000000"
}
```

Copy `.env.example` and rename it to `.env`, then edit the fields to match your exported data.

| Variable             | Description                                  | Accepted Values         |
|----------------------|----------------------------------------------|-------------------------|
| LOOPRING_API_KEY     | `apiKey`                                     | See your account export |
| LOOPRING_PRIVATE_KEY | `privateKey`                                 | See your account export |
| MINTER               | `address`                                    | See your account export |
| ACCT_ID              | `accountId`                                  | See your account export |
| NFT_TYPE             | EIP1155 or EIP721                            | 0 (1155) or 1 (721)     |
| ROYALTY_PERCENTAGE   | Percentage for royalty payouts to the minter | 0 - 50                  |
| FEE_TOKEN_ID         | ETH or LRC                                   | 0 (ETH) or 1 (LRC)      |
| COUNT                | How many copies to mint                      | 1 - 10000               |

## Usage

```shell
usage: LoopMintPy.py [-h] -f {cid,path} -m METADATA [-c COUNT]

optional arguments:
  -h, --help            show this help message and exit
  -f {cid,path}, --format {cid,path}
                        Specify the input format (CID or file path)
  -m METADATA, --metadata METADATA
                        Specify the metadata.json file (CIDv0 hash or file path)
  -c COUNT, --count COUNT
                        Specify the amount of items to mint (default: 1)
```

### Examples:
* Mint an NFT from a local `metadata.json` file
```shell
python3 -f path -m /path/to/metadata.json
```
-- or --
```shell
./docker.sh -f path -m /path/to/metadata.json
```

* Mint 10 NFT from the CIDv0 hash of a `metadata.json` file uploaded to IPFS
```shell
python3 -f cid -m QmdmRoWVU4PV9ZCi1khprtX2YdAzV9UEFN5igZZGxPVAa4 -c 10
```
-- or --
```shell
./docker.sh -f cid -m QmdmRoWVU4PV9ZCi1khprtX2YdAzV9UEFN5igZZGxPVAa4 -c 10
```