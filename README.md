# LoopMintPy

This is a Python3 adaptation of fudgey's [LoopMintSharp](https://github.com/fudgebucket27/LoopMintSharp).

This fork of [LoopMintPy](https://github.com/Montspy/LoopMintPy.git) is meant to be used in conjunction with the batch minting scripts.

## Install

Using local environment:

```shell
git clone --recurse-submodules https://github.com/sk33z3r/LoopMintPy.git
pip3 install -r hello_loopring/requirements.txt -r requirements.txt
python LoopMintPy.py --cid QmVpLSoYak1N8pasuxLrNZLbnvrNvLTJmY8ncMBjNRPBtQ
```

Using Docker:

```shell
git clone --recurse-submodules https://github.com/sk33z3r/LoopMintPy.git
./docker.sh build
./docker.sh --cid QmVpLSoYak1N8pasuxLrNZLbnvrNvLTJmY8ncMBjNRPBtQ
```

## dotenv

First you need to export your account to get the necessary details to fill in the dotenv file.

Go to loopring.io -> Security -> Export Account and copy the JSON provided into a safe space.

**DO NOT SHARE THIS INFO WITH ANYONE**

The output should look something like this:

```json
{
    "Nonce":1,
    "PublicKeyY":"123456789012345678901234567890123456789012345678901234567890",
    "AccountId":12345,
    "ApiKey":"hdajkshHFkfahfLKFH9384hFHLIfa9hfHf8faofhq3rhkfha98fj",
    "PublicKeyX":"123456789012345678901234567890123456789012345678901234567890",
    "PrivateKey":"123456789012345678901234567890123456789012345678901234567890",
    "Address":"0x0000000000000000000000000000000000000000"
}
```

Copy `.env.example` and rename it to `.env`, then edit the fields to match your exported data.

| Variable             | Description                                  | Accepted Values         |
|----------------------|----------------------------------------------|-------------------------|
| LOOPRING_API_KEY     | `ApiKey`                                     | See your account export |
| LOOPRING_PRIVATE_KEY | `PrivateKey`                                 | See your account export |
| MINTER               | `Address`                                    | See your account export |
| ACCT_ID              | `AccountId`                                  | See your account export |
| NFT_TYPE             | EIP1155 or EIP721                            | 0 (1155) or 1 (721)     |
| ROYALTY_PERCENTAGE   | Percentage for royalty payouts to the minter | 0 - 50                  |
| FEE_TOKEN_ID         | ETH or LRC                                   | 0 (ETH) or 1 (LRC)      |
| COUNT                | How many copies to mint                      | 1 - 10000               |
