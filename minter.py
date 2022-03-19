#!/usr/bin/env python3
from os import path, makedirs, getenv
import sys
sys.path.insert(0, path.abspath(path.join(path.dirname(__file__), "hello_loopring")))

from dotenv import load_dotenv
import argparse
import asyncio
import json
from pprint import pprint
import base58

load_dotenv()

from DataClasses import *
from LoopringMintService import LoopringMintService, NFTDataEddsaSignHelper, NFTEddsaSignHelper

MINT_INFO_PATH = './'
cfg = {}
secret = {} # Split to avoid leaking keys to console or logs

# Verbose output
VERBOSE = False
def log(*objects, **kwds):
    if VERBOSE:
        print(*objects, **kwds)
def plog(object, **kwds):
    if VERBOSE:
        pprint(object, **kwds)

# Build config dictionnary
def setup(amount: int, cid: str):
    secret['loopringApiKey']     = getenv("LOOPRING_API_KEY")
    secret['loopringPrivateKey'] = getenv("LOOPRING_PRIVATE_KEY")
    cfg['ipfsCid']               = cid
    cfg['minterAddress']         = getenv("MINTER")
    cfg['accountId']             = int(getenv("ACCT_ID"))
    cfg['nftType']               = int(getenv("NFT_TYPE"))
    cfg['royaltyPercentage']     = int(getenv("ROYALTY_PERCENTAGE"))
    cfg['amount']                = amount
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
    assert cfg['amount'] is not None, "Missing amount"

    if secret['loopringPrivateKey'][:2] != "0x":
        secret['loopringPrivateKey'] = hex(int(secret['loopringPrivateKey']))

    log("config dump:")
    plog(cfg)

# Parse CLI arguments
def parse_args():
    # check for command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--amount", help="Specify the mint amount per NFT", type=int, default=1)
    parser.add_argument("-V", "--verbose", help="Verbose output", action='store_true')
    parser.add_argument("--noprompt", help="Skip all user prompts", action='store_true')

    single_group = parser.add_argument_group(title="Single mint", description="Use these options to mint a single NFT:")
    single_group.add_argument("-c", "--cid", help="Specify the CIDv0 hash for the metadata to mint", type=str)

    batch_group = parser.add_argument_group(title="Batch mint", description="Use these options to batch mint multiple NFTs:")
    batch_group.add_argument("-j", "--json", help="Specify a json file containing a list of CIDv0 hash to batch mint", type=str)
    batch_group.add_argument("-s", "--start", help="Specify the the starting ID to batch mint", type=int)
    batch_group.add_argument("-e", "--end", help="Specify the last ID to batch mint", type=int)
    args = parser.parse_args()

    if args.json is not None:
        assert path.exists(args.json), f"JSON file not found: {args.json}"
    
    if args.end is not None:
        assert args.start <= args.end, f"start cannot be greater than end: {args.start} > {args.end}"

    assert not (args.cid is None and args.json is None), f"Missing --cid or --json argument, please provide one"

    if args.cid is not None and (args.start or args.end):
        print("Ignoring start and end arguments with single CID minting")
    if args.start is None:
        args.start = 1

    global VERBOSE
    VERBOSE = args.verbose

    return args

# Estimate fees for a batch of NFTs from offchain fees
def estimate_batch_fees(off_chain_fee, count):
    fee = int(off_chain_fee['fees'][cfg['maxFeeTokenId']]['fee'])
    token_symbol = off_chain_fee['fees'][cfg['maxFeeTokenId']]['token']
    discount = off_chain_fee['fees'][cfg['maxFeeTokenId']]['discount']
    decimals = token_decimals[token_symbol]

    return count * fee * discount / (10 ** decimals), token_symbol

# Prompts the user to answer by yes or no
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

async def get_offchain_parameters(info: dict):
    async with LoopringMintService() as lms:
        # Getting the storage id
        storage_id = await lms.getNextStorageId(apiKey=secret['loopringApiKey'], accountId=cfg['accountId'], sellTokenId=cfg['maxFeeTokenId'])
        log(f"Storage id: {json.dumps(storage_id, indent=2)}")
        info['storage_id'] = storage_id
        if storage_id is None:
            sys.exit("Failed to obtain storage id")

        # Getting the token address
        counterfactual_nft_info = CounterFactualNftInfo(nftOwner=cfg['minterAddress'], nftFactory=cfg['nftFactory'], nftBaseUri="")
        counterfactual_nft = await lms.computeTokenAddress(apiKey=secret['loopringApiKey'], counterFactualNftInfo=counterfactual_nft_info)
        log(f"CounterFactualNFT Token Address: {json.dumps(counterfactual_nft, indent=2)}")
        info['counterfactual_nft_info'] = counterfactual_nft_info
        info['counterfactual_nft'] = counterfactual_nft
        if counterfactual_nft is None:
            sys.exit("Failed to obtain token address")

        # Getting the offchain fee
        off_chain_fee = await lms.getOffChainFee(apiKey=secret['loopringApiKey'], accountId=cfg['accountId'], requestType=9, tokenAddress=counterfactual_nft['tokenAddress'])
        log(f"Offchain fee:  {json.dumps(off_chain_fee['fees'][cfg['maxFeeTokenId']], indent=2)}")
        info['off_chain_fee'] = off_chain_fee
        if off_chain_fee is None:
            sys.exit("Failed to obtain offchain fee")

    return storage_id, counterfactual_nft, counterfactual_nft_info, off_chain_fee

async def get_hashes_and_sign(storage_id: StorageId, off_chain_fee: OffchainFee, counterfactual_nft: CounterFactualNft, info: dict):
    # Generate the nft id here
    nft_id = "0x" + base58.b58decode(cfg['ipfsCid']).hex()[4:]    # Base58 to hex and drop first 2 bytes
    log(f"Generated NFT ID: {nft_id}")
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
    # plog(inputs)
    log(f"Hashed NFT data: {hex(nft_data_poseidon_hash)}")
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
    # plog(inputs)
    log(f"Hashed NFT payload: {hex(nft_poseidon_hash)}")
    info['nft_poseidon_hash'] = hex(nft_poseidon_hash)

    eddsa_signature = hasher.sign(inputs)
    log(f"Signed NFT payload hash: {eddsa_signature}")
    info['eddsa_signature'] = eddsa_signature

    return nft_id, nft_data_poseidon_hash, eddsa_signature

async def mint_nft(nft_data_poseidon_hash: str, nft_id: str, eddsa_signature: str,
                   storage_id: StorageId, off_chain_fee: OffchainFee,
                   counterfactual_nft: CounterFactualNft, counterfactual_nft_info: CounterFactualNftInfo, info: dict):
    async with LoopringMintService() as lms:
        # Check if NFT exists (get the token nft data)
        nft_data = await lms.getNftData(nftDatas=hex(nft_data_poseidon_hash))
        log(f"Nft data: {json.dumps(nft_data, indent=2)}")
        info['nft_data'] = nft_data
        nft_exists = (lms.last_status == 200) and (nft_data is not None) and (len(nft_data) > 0)

        if nft_exists:
            return MintResult.EXISTS
        
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
            counterFactualNftInfo=counterfactual_nft_info,
            eddsaSignature=eddsa_signature
        )
        log(f"Nft Mint reponse: {nft_mint_response}")
        info['nft_mint_response'] = nft_mint_response

        if nft_mint_response is not None and lms.last_status == 200:
            return MintResult.SUCCESS
        else:
            return MintResult.FAILED

async def main():
    # Initial Setup
    try:
        args = parse_args()

        # Parse cids from JSON or command line
        if args.json is not None:
            with open(args.json, 'r') as f:
                cids = json.load(f)
        elif args.cid is not None:
            cids = [{"ID": 1, "CID": args.cid}]

        if not path.exists(MINT_INFO_PATH):
            makedirs(MINT_INFO_PATH)
    except Exception as err:
        sys.exit(f"Failed to initialize the minter: {err}")

    mint_info = []
    approved_fees_prompt = args.noprompt

    try:
        for cid_info in cids:
            id = int(cid_info.pop("ID"))
            current_cid = cid_info.pop("CID")

            info = {'id': id, 'cid': current_cid, 'amount': args.amount}

            if id < args.start or (args.end is not None and id > args.end):
                continue

            mint_info.append(info)
            setup(args.amount, current_cid)
            
            # Get storage id, token address and offchain fee
            storage_id, counterfactual_nft, counterfactual_nft_info, off_chain_fee = await get_offchain_parameters(info)

            # Estimate fees and get user approval
            if not approved_fees_prompt:
                batch_fees, fees_symbol = estimate_batch_fees(off_chain_fee, len(cids))
                log("--------")
                approved_fees_prompt = prompt_yes_no(f"Estimated fees for minting {len(cids)} NFTs: {batch_fees}{fees_symbol}, continue?", default="no")
                info['approved_fees'] = {'approval': approved_fees_prompt, 'fee': batch_fees, 'token': fees_symbol}
                if not approved_fees_prompt: 
                    sys.exit("Aborted by user")

            # Generate Eddsa Signature
            nft_id, nft_data_poseidon_hash, eddsa_signature = await get_hashes_and_sign(storage_id=storage_id,off_chain_fee=off_chain_fee, counterfactual_nft=counterfactual_nft, info=info)
            
            # Submit the nft mint
            mint_result = await mint_nft(nft_data_poseidon_hash=nft_data_poseidon_hash,
                                         nft_id=nft_id,
                                         eddsa_signature=eddsa_signature,
                                         storage_id=storage_id,
                                         off_chain_fee=off_chain_fee,
                                         counterfactual_nft=counterfactual_nft,
                                         counterfactual_nft_info=counterfactual_nft_info,
                                         info=info)
            
            if mint_result == MintResult.SUCCESS:
                print(f"NFT {id}: Successful Mint! ({current_cid})")
            elif mint_result ==  MintResult.FAILED:
                print(f"NFT {id}: Mint FAILED... ({current_cid})")
            elif mint_result ==  MintResult.EXISTS:
                print(f"NFT {id}: Skipping mint (nft already exists) ({current_cid})")
    finally:
        with open(path.join(MINT_INFO_PATH, 'mint-info.json'), 'w+') as f:
            json.dump(mint_info, f, indent=4)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
