# LoopMintPy

This is a **Python3** adaptation of fudgey's [LoopMintSharp](https://github.com/fudgebucket27/LoopMintSharp).
Now with batch minting!

## Install

Using local environment:

```shell
git clone --recurse-submodules https://github.com/Montspy/LooPyMinty.git
pip3 install -r hello_loopring/requirements.txt -r requirements.txt
```

Some additional depencies include: `python-dev`, `gcc`, `libc-dev` and may need ot be install with your package manager if pip3 install fails.

Using Docker:

```shell
git clone --recurse-submodules https://github.com/Montspy/LooPyMinty.git
./docker.sh build
```

## dotenv

First you need to export your account to get the necessary details to fill in the dotenv file.

Go to loopring.io -> Security -> Export Account and copy the JSON provided into a safe space.

**⚠️ DO NOT SHARE THIS INFO WITH ANYONE ⚠️**

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
| ROYALTY_PERCENTAGE   | Percentage for royalty payouts to the minter | 0 - 10                  |
| FEE_TOKEN_ID         | ETH or LRC                                   | 0 (ETH) or 1 (LRC)      |
| COUNT                | How many copies to mint                      | 1 - 10000               |

## Usage

```shell
> python3 LooPyMinty.py -h
usage: LooPyMinty.py [-h] (-c CID | -j JSON) [-n AMOUNT] [-s START] [-e END] [--noprompt] [-V]

options:
  -h, --help            show this help message and exit
  -c CID, --cid CID     Specify the CIDv0 hash for the metadata to mint
  -j JSON, --json JSON  Specify a json file containing a list of CIDv0 hash to mint
  -n AMOUNT, --amount AMOUNT
                        Specify the mint amount per NFT
  -s START, --start START
                        Specify the the starting ID to mint
  -e END, --end END     Specify the last ID to mint
  --noprompt            Skip all user prompts
  -V, --verbose         Verbose output
```

### Mint a single NFT

```shell
python3 LoopMintPy.py --cid QmdmRoWVU4PV9ZCi1khprtX2YdAzV9UEFN5igZZGxPVAa4 --count 100
# or
./docker.sh --cid QmdmRoWVU4PV9ZCi1khprtX2YdAzV9UEFN5igZZGxPVAa4 --count 100
```

### Batch mint NFTs

```shell
python3 LoopMintPy.py --json ./metadata-cids.json --count 1
# or
./docker.sh --json ./metadata-cids.json --count 1
```

### Content of `metadata-cids.json`
`metadata-cids.json` should be an array of dict with ID and CID:
```json
[
    {
        "ID": 1,
        "CID": "Qmau1Sx2hLTkLmXsu2dD28yMZtL3Pzs2uKqP2MeHZPm93V"
    },
    {
        "ID": 2,
        "CID": "QmSyhgNxWWEQSVTjgxzd4F6xHJ2LLDFzaTdX6wV5qFzenX"
    },
    {
        "ID": 3,
        "CID": "QmYETprnpLtVXxydrzgCSrz6uC1swmS31rqupazdPWenE6"
    }
]
```