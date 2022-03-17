#!/usr/bin/env python3
import sys
from os import path, makedirs, getenv
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), "hello_loopring")))

import argparse
import asyncio
from aiohttp import ClientSession
import json
from pprint import pprint
import base58

from DataClasses import *
from LoopringMintService import LoopringMintService, NFTDataEddsaSignHelper, NFTEddsaSignHelper

MINT_INFO_PATH = './'
cfg = {}
secret = {} # Split to avoid leaking keys to console or logs

def setup(count: int, cid: str):
    secret['loopringApiKey']     = getenv("LOOPRING_API_KEY")
    secret['loopringPrivateKey'] = getenv("LOOPRING_PRIVATE_KEY")
    cfg['ipfsCid']               = cid
    cfg['minterAddress']         = getenv("MINTER")
    cfg['accountId']             = int(getenv("ACCT_ID"))
    cfg['nftType']               = int(getenv("NFT_TYPE"))
    cfg['royaltyPercentage']     = int(getenv("ROYALTY_PERCENTAGE"))
    cfg['amount']                = count
    cfg['validUntil']            = 1700000000
    cfg['maxFeeTokenId']         = int(getenv("FEE_TOKEN_ID"))
    cfg['nftFactory']            = "0xc852aC7aAe4b0f0a0Deb9e8A391ebA2047d80026"
    cfg['exchange']              = "0x0BABA1Ad5bE3a5C0a66E7ac838a129Bf948f1eA4"

    assert secret['loopringPrivateKey'] is not None, "Invalid private key (LOOPRING_PRIVATE_KEY)"
    assert secret['loopringApiKey'] is not None, "Missing API key (LOOPRING_API_KEY)"
    assert cfg['minterAddress'] is not None, "Missing minter address (MINTER)"
    assert cfg['accountId'] is not None, "Missing account ID (ACCT_ID)"
    assert cfg['nftType'] in [0, 1], f"Incorrect NFT type (NFT_TYPE): {cfg['nftType']}"
    assert cfg['royaltyPercentage'] in range(0, 11), f"Incorrect royalty percentage [0-10] (ROYALTY_PERCENTAGE): {cfg['royaltyPercentage']}"
    assert cfg['maxFeeTokenId'] is not None, "Missing fee token ID (FEE_TOKEN_ID)"
    assert cfg['ipfsCid'] is not None and cfg['ipfsCid'][:2] == "Qm", f"Invalid cid: {cfg['ipfsCid']}"
    assert cfg['amount'] is not None, "Missing count"

    if secret['loopringPrivateKey'][:2] != "0x":
        secret['loopringPrivateKey'] = hex(int(secret['loopringPrivateKey']))

    print("config dump:")
    pprint(cfg)

def parse_args():
    # check for command line arguments
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-c", "--cid", help="Specify the CIDv0 hash for the metadata to mint", type=str)
    group.add_argument("-j", "--json", help="Specify a json file containing a list of CIDv0 hash to mint", type=str)
    parser.add_argument("-n", "--count", help="Specify the amount of items to mint", type=int, default=1)
    parser.add_argument("--noprompt", help="Skip all user prompts", action='store_true')
    args = parser.parse_args()

    if args.json is not None:
        assert path.exists(args.json), f"JSON file not found: {args.json}"

    return args

def estimate_batch_fees(off_chain_fee, count):
    fee = int(off_chain_fee['fees'][cfg['maxFeeTokenId']]['fee'])
    token_symbol = off_chain_fee['fees'][cfg['maxFeeTokenId']]['token']
    discount = off_chain_fee['fees'][cfg['maxFeeTokenId']]['discount']
    decimals = token_decimals[token_symbol]

    return count * fee * discount / (10 ** decimals), token_symbol

def prompt_yes_no(prompt: str, default: str=None):
    if default is None:
        indicator = "[y/n]"
    elif default == "yes":
        indicator = "[Y/n]"
    elif default == "no":
        indicator = "[y/N]"
    else:
        raise ValueError(f"Invalid default string yes/no/None but is {default}")
    
    while True:
        print(f"{prompt} {indicator}: ", end='')
        s = input().lower()
        if s[:1] == 'y':
            return True
        elif s[:1] == 'n':
            return False
        elif s == "" and default is not None:
            if default == "yes":
                return True
            elif default == "no":
                return False

async def main():
    # Initial Setup
    args = parse_args()

    # Parse cids from JSON or command line
    if args.json is not None:
        with open(args.json, 'r') as f:
            cids = json.load(f)
    elif args.cid is not None:
        cids = [args.cid]

    if not path.exists(MINT_INFO_PATH):
        makedirs(MINT_INFO_PATH)
    mint_info = []

    approved_fees_prompt = args.noprompt

    try:
        for current_cid in cids:
            info = {'cid': current_cid, 'count': args.count}
            mint_info.append(info)
            setup(args.count, current_cid)

            # Get storage id, token address and offchain fee
            async with LoopringMintService() as lms:
                # Getting the storage id
                storage_id = await lms.getNextStorageId(apiKey=secret['loopringApiKey'], accountId=cfg['accountId'], sellTokenId=cfg['maxFeeTokenId'])
                print(f"Storage id: {json.dumps(storage_id, indent=2)}")
                info['storage_id'] = storage_id

                # Getting the token address
                counterfactual_ntf_info = CounterFactualNftInfo(nftOwner=cfg['minterAddress'], nftFactory=cfg['nftFactory'], nftBaseUri="")
                counterfactual_nft = await lms.computeTokenAddress(apiKey=secret['loopringApiKey'], counterFactualNftInfo=counterfactual_ntf_info)
                print(f"CounterFactualNFT Token Address: {json.dumps(counterfactual_nft, indent=2)}")
                info['counterfactual_ntf_info'] = counterfactual_ntf_info
                info['counterfactual_nft'] = counterfactual_nft

                # Getting the offchain fee
                off_chain_fee = await lms.getOffChainFee(apiKey=secret['loopringApiKey'], accountId=cfg['accountId'], requestType=9, tokenAddress=counterfactual_nft['tokenAddress'])
                print(f"Offchain fee:  {json.dumps(off_chain_fee['fees'][cfg['maxFeeTokenId']], indent=2)}")
                info['off_chain_fee'] = off_chain_fee

            if not approved_fees_prompt:
                batch_fees, fees_symbol = estimate_batch_fees(off_chain_fee, len(cids))
                print("--------")
                approved_fees_prompt = prompt_yes_no(f"Estimated fees for minting {len(cids)} NFTs: {batch_fees}{fees_symbol}, continue?", default="no")
                info['approved_fees'] = {'approval': approved_fees_prompt, 'fee': batch_fees, 'token': fees_symbol}
                if not approved_fees_prompt: 
                    sys.exit("Aborted by user")

            # Generate Eddsa Signature
            # Generate the nft id here
            nft_id = "0x" + base58.b58decode(cfg['ipfsCid']).hex()[4:]    # Base58 to hex and drop first 2 bytes
            print(f"Generated NFT ID: {nft_id}")
            info['nft_id'] = nft_id

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
                cfg['royaltyPercentage']
            ]
            hasher = NFTDataEddsaSignHelper()
            nft_data_poseidon_hash = hasher.hash(inputs)
            # pprint(inputs)
            print(f"Hashed NFT data: {hex(nft_data_poseidon_hash)}")
            info['nft_data_poseidon_hash'] = hex(nft_data_poseidon_hash)

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
            hasher = NFTEddsaSignHelper(private_key=secret['loopringPrivateKey'])
            nft_poseidon_hash = hasher.hash(inputs)
            # pprint(inputs)
            print(f"Hashed NFT payload: {hex(nft_poseidon_hash)}")
            info['nft_poseidon_hash'] = hex(nft_poseidon_hash)

            eddsa_signature = hasher.sign(inputs)
            print(f"Signed NFT payload hash: {eddsa_signature}")
            info['eddsa_signature'] = eddsa_signature

            # Submit the nft mint
            async with LoopringMintService() as lms:
                nft_mint_response = await lms.mintNft(
                    apiKey=secret['loopringApiKey'],
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
                    royaltyPercentage=cfg['royaltyPercentage'],
                    storageId=storage_id['offchainId'],
                    maxFeeTokenId=cfg['maxFeeTokenId'],
                    maxFeeAmount=off_chain_fee['fees'][cfg['maxFeeTokenId']]['fee'],
                    forceToMint=False,
                    counterFactualNftInfo=counterfactual_ntf_info,
                    eddsaSignature=eddsa_signature
                )
                print(f"Nft Mint reponse: {nft_mint_response}")
                info['nft_mint_response'] = nft_mint_response
    finally:
        with open(path.join(MINT_INFO_PATH, 'mint-info.json'), 'w+') as f:
            json.dump(mint_info, f, indent=4)

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
