#!/usr/bin/env python3
import sys
from os import path
from dotenv import load_dotenv

sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), "hello_loopring")))

import argparse
import asyncio
from aiohttp import ClientSession
import json
from pprint import pprint
import base58

from LoopringMintService import LoopringMintService, NFTDataEddsaSignHelper, NFTEddsaSignHelper
from CounterFactualNft import CounterFactualNftInfo

# check for command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("--cid", nargs=1, help="Specify the CIDv0 hash for metadata", type=str)
parser.add_argument("--count", nargs=1, help="Specify the amount of items to mint", type=int)
args = parser.parse_args()

# Set starting tokenId
if args.cid:
    cid = args.cid[0]
else:
    sys.exit("ERROR: Missing CID")

# Set starting tokenId
if args.count:
    count = args.count[0]
else:
    sys.exit("ERROR: Missing COUNT")

cfg = {}

def setup(cid):
    # Changes these variables to suit
    cfg['loopringApiKey']       = LOOPRING_API_KEY
    cfg['loopringPrivateKey']   = LOOPRING_PRIVATE_KEY
    cfg['ipfsCid']              = cid
    cfg['minterAddress']        = MINTER
    cfg['accountId']            = ACCT_ID
    cfg['nftType']              = NFT_TYPE
    cfg['creatorFeeBips']       = ROYALTY_PERCENTAGE
    cfg['amount']               = count
    cfg['validUntil']           = 1700000000
    cfg['maxFeeTokenId']        = FEE_TOKEN_ID
    cfg['nftFactory']           = "0xc852aC7aAe4b0f0a0Deb9e8A391ebA2047d80026"
    cfg['exchange']             = "0x0BABA1Ad5bE3a5C0a66E7ac838a129Bf948f1eA4"
    print("config dump:")
    pprint(cfg)

    assert cfg['loopringPrivateKey'] is not None and cfg['loopringPrivateKey'][:2] == "0x"
    assert cfg['loopringApiKey'] is not None

async def main(cid):
    # Initial Setup
    setup(cid)
    args = parse_args()

    # Get storage id, token address and offchain fee
    async with LoopringMintService() as lms:
        # Getting the storage id
        storage_id = await lms.getNextStorageId(apiKey=cfg['loopringApiKey'], accountId=cfg['accountId'], sellTokenId=cfg['maxFeeTokenId'])
        print(f"Storage id: {json.dumps(storage_id, sort_keys=True, indent=4)}")

        # Getting the token address
        counterfactual_ntf_info = CounterFactualNftInfo(nftOwner=cfg['minterAddress'], nftFactory=cfg['nftFactory'], nftBaseUri="")
        counterfactual_nft = await lms.computeTokenAddress(apiKey=cfg['loopringApiKey'], counterFactualNftInfo=counterfactual_ntf_info)
        print(f"CounterFactualNFT Token Address: {json.dumps(counterfactual_nft, sort_keys=True, indent=4)}")

        # Getting the offchain fee
        off_chain_fee = await lms.getOffChainFee(apiKey=cfg['loopringApiKey'], accountId=cfg['accountId'], requestType=9, tokenAddress=counterfactual_nft['tokenAddress'])
        print(f"Offchain fee:  {json.dumps(off_chain_fee, sort_keys=True, indent=4)}")

    # Generate Eddsa Signature
    # Generate the nft id here
    nft_id = "0x" + base58.b58decode(cfg['ipfsCid']).hex()[4:]    # Base58 to hex and drop first 2 bytes
    print(f"Generated NFT ID: {nft_id}")

    # Generate the poseidon hash for the nft data
    # https://github.com/Loopring/loopring_sdk/blob/692d372165b5ea0d760e33e177d9003cc0dfb0f7/src/api/sign/sign_tools.ts#L704
    ntf_id_hi = int(nft_id[2:34], 16)   # Skip "0x" prefix
    nft_id_lo = int(nft_id[34:66], 16)
    inputs = [
        int(cfg['minterAddress'], 16),
        cfg['nftType'],
        int(counterfactual_nft['tokenAddress'], 16),
        nft_id_lo,
        ntf_id_hi,
        cfg['creatorFeeBips']
    ]
    hasher = NFTDataEddsaSignHelper()
    nft_data_poseidon_hash = hasher.hash(inputs)
    # pprint(inputs)
    print(f"Hashed NFT data: {hex(nft_data_poseidon_hash)}")

    # Generate the poseidon hash for the remaining data
    # https://github.com/Loopring/loopring_sdk/blob/692d372165b5ea0d760e33e177d9003cc0dfb0f7/src/api/sign/sign_tools.ts#L899
    inputs = [
        int(cfg['exchange'], 16),
        cfg['accountId'],   # minterId
        cfg['accountId'],   # toAccountId
        nft_data_poseidon_hash,
        cfg['amount'],
        cfg['maxFeeTokenId'],
        int(off_chain_fee['fees'][cfg['maxFeeTokenId']]['fee']),
        cfg['validUntil'],
        storage_id['offchainId']
    ]
    hasher = NFTEddsaSignHelper(private_key=cfg['loopringPrivateKey'])
    nft_poseidon_hash = hasher.hash(inputs)
    # pprint(inputs)
    print(f"Hashed NFT payload: {hex(nft_poseidon_hash)}")

    eddsa_signature = hasher.sign(inputs)
    print(f"Signed NFT payload hash: {eddsa_signature}")

    # Submit the nft mint
    async with LoopringMintService() as lms:
        nft_mint_response = await lms.mintNft(
            apiKey=cfg['loopringApiKey'],
            exchange=cfg['exchange'],
            minterId=cfg['accountId'],
            minterAddress=cfg['minterAddress'],
            toAccountId=cfg['accountId'],
            toAddress=cfg['minterAddress'],
            nftType=cfg['nftType'],
            tokenAddress=counterfactual_nft['tokenAddress'],
            nftId=nft_id,
            amount=str(cfg['amount']),
            validUntil=cfg['validUntil'],
            creatorFeeBips=cfg['creatorFeeBips'],
            storageId=storage_id['offchainId'],
            maxFeeTokenId=cfg['maxFeeTokenId'],
            maxFeeAmount=off_chain_fee['fees'][cfg['maxFeeTokenId']]['fee'],
            forceToMint=False,
            counterFactualNftInfo=counterfactual_ntf_info,
            eddsaSignature=eddsa_signature
        )
        print(f"Nft Mint reponse: {json.dumps(nft_mint_response, sort_keys=True, indent=4)}")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())