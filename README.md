# LoopMintPy

This is a Python3 adaptation of fudgey's [LoopMintSharp](https://github.com/fudgebucket27/LoopMintSharp).

## Install

Using local environment:

```shell
git clone --recurse-submodules https://github.com/Montspy/LoopMintPy.git
pip3 install -r hello_loopring/requirements.txt -r requirements.txt
```

Using Docker:

```shell
./docker.sh build
./docker.sh --cid QmVpLSoYak1N8pasuxLrNZLbnvrNvLTJmY8ncMBjNRPBtQ
```

## dotenv

First you need to export your account to get the necessary details to fill in the dotenv file. The values below match to fields in the export.

Go to loopring.io -> Security -> Export Account and copy the JSON provided into a safe space.

**DO NOT SHARE THIS INFO WITH ANYONE**

Create a local file in the top level name `.env` and populate it with this info

```conf
LOOPRING_API_KEY=ApiKey
LOOPRING_PRIVATE_KEY=PrivateKey
MINTER=Address
ACCT_ID=AccountId
NFT_TYPE=0 (ERC1155) or 1 (ERC721)
ROYALTY_PERCENTAGE=0 - 50
FEE_TOKEN_ID=0 (ETH) or 1 (LRC)
BATCH_COUNT=1000
START_ID=0
```
