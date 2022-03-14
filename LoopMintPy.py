#!/usr/bin/env python3
import sys
from os import path, getenv
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), "hello_loopring")))

import argparse
import asyncio
from aiohttp import ClientSession
import json
from pprint import pprint
import base58
from CIDGenerator import CIDGenerator

from LoopringMintService import LoopringMintService, NFTDataEddsaSignHelper, NFTEddsaSignHelper
from CounterFactualNft import CounterFactualNftInfo

cfg = {}

async def setup(args):
    # Changes these variables to suit
    cfg['loopringApiKey']       = getenv("LOOPRING_API_KEY")
    cfg['loopringPrivateKey']   = getenv("LOOPRING_PRIVATE_KEY")
    cfg['ipfsCid']              = ""
    cfg['minterAddress']        = getenv("MINTER")
    cfg['accountId']            = int(getenv("ACCT_ID"))
    cfg['nftType']              = int(getenv("NFT_TYPE"))
    cfg['creatorFeeBips']       = int(getenv("ROYALTY_PERCENTAGE"))
    cfg['amount']               = args.count
    cfg['validUntil']           = 1700000000
    cfg['maxFeeTokenId']        = int(getenv("FEE_TOKEN_ID"))
    cfg['nftFactory']           = "0xc852aC7aAe4b0f0a0Deb9e8A391ebA2047d80026"
    cfg['exchange']             = "0x0BABA1Ad5bE3a5C0a66E7ac838a129Bf948f1eA4"
    print("config dump:")
    pprint(cfg)

    assert cfg['loopringPrivateKey'] is not None and cfg['loopringPrivateKey'][:2] == "0x"
    assert cfg['loopringApiKey'] is not None

    # Generate CID if necessary
    if args.format == 'path':
        try:
            async with CIDGenerator() as generator:
                cfg['ipfsCid'] = await generator.get_cid_from_file(args.metadata)
        except Exception as err:
            sys.exit(f"Error with the CID Generator: {err}")
    else:
        cfg['ipfsCid'] = args.metadata

    # print("config dump:")
    # pprint(cfg)

def parse_args():
    # check for command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--format',          help="Specify the input format (CID or file path)", type=str, 
                                                   choices=['cid', 'path'], required=True)
    parser.add_argument('-m', '--metadata',        help="Specify the metadata.json file (CIDv0 hash or file path)", type=str, required=True)
    parser.add_argument('-c', '--count',           help="Specify the amount of items to mint (default: 1)", type=int, default=1)

    args = parser.parse_args()

    return args
    
async def main():
    # Initial Setup
    args = parse_args()
    await setup(args)

    # Get storage id, token address and offchain fee
    async with LoopringMintService() as lms:
        # Getting the storage id
        storage_id = await lms.getNextStorageId(apiKey=cfg['loopringApiKey'], accountId=cfg['accountId'], sellTokenId=cfg['maxFeeTokenId'])
        print("Storage id:")
        pprint(storage_id)

        # Getting the token address
        counterfactual_ntf_info = CounterFactualNftInfo(nftOwner=cfg['minterAddress'], nftFactory=cfg['nftFactory'], nftBaseUri="")
        counterfactual_nft = await lms.computeTokenAddress(apiKey=cfg['loopringApiKey'], counterFactualNftInfo=counterfactual_ntf_info)
        print("CounterFactualNFT Token Address:")
        pprint(counterfactual_nft)

        # Getting the offchain fee
        off_chain_fee = await lms.getOffChainFee(apiKey=cfg['loopringApiKey'], accountId=cfg['accountId'], requestType=9, tokenAddress=counterfactual_nft['tokenAddress'])
        print("Offchain fee:")
        pprint(off_chain_fee)
    
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
        print(f"Nft Mint reponse: {nft_mint_response}")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
