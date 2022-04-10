#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "hello_loopring")))

from dotenv import load_dotenv
from pprint import pprint
import argparse
import asyncio
import json

from DataClasses import *
from LoopringMintService import LoopringMintService, NFTTransferEddsaSignHelper

# Verbose output
VERBOSE = False
def log(*objects, **kwds):
    if VERBOSE:
        print(*objects, **kwds)
def plog(object, **kwds):
    if VERBOSE:
        pprint(object, **kwds)

async def get_account_info(account: str):
    async with LoopringMintService() as lms:
        account = str(account).strip()
        if account[:2] == "0x":
            address = account
            id = await lms.getAccountId(address)
        elif account[-4:] == ".eth":
            address = await lms.resolveENS(account)
            id = await lms.getAccountId(address)
        else:
            id = int(account)
            address = await lms.getAccountAddress(id)
    return id, address

async def retry_async(coro, *args, timeout: float=3, retries: int=3, **kwds):
    for attempts in range(retries):
        try:
            return await asyncio.wait_for(coro(*args, **kwds), timeout=timeout)
        except asyncio.TimeoutError:
            print("Retrying... " + str(attempts))

async def eternity(s: float):
    await asyncio.sleep(s)

# Build config dictionnary
async def load_config(args, paths: Struct):
    cfg = Struct()
    secret = Struct()   # Split to avoid leaking keys to console or logs

    secret.loopringPrivateKey = os.getenv("LOOPRING_PRIVATE_KEY")
    cfg.fromAddress           = os.getenv("FROM")
    cfg.maxFeeTokenId         = int(os.getenv("FEE_TOKEN_ID"))

    cfg.validUntil            = 1700000000
    cfg.nftFactory            = "0xc852aC7aAe4b0f0a0Deb9e8A391ebA2047d80026"
    cfg.exchange              = "0x0BABA1Ad5bE3a5C0a66E7ac838a129Bf948f1eA4"
    
    # Resolve ENS, get account_id and ETH address
    cfg.fromAccount, cfg.fromAddress = await retry_async(get_account_info, cfg.fromAddress, retries=3)
    assert cfg.fromAddress and cfg.fromAccount, f"Invalid from address: {cfg.fromAddress} (account ID {cfg.fromAccount})"

    assert secret.loopringPrivateKey, "Missing private key (LOOPRING_PRIVATE_KEY)"
    assert cfg.maxFeeTokenId in range(len(token_decimals)), f"Missing or invalid fee token ID (FEE_TOKEN_ID): {cfg.maxFeeTokenId}"

    if secret.loopringPrivateKey[:2] != "0x":
        secret.loopringPrivateKey = "0x{0:0{1}x}".format(int(secret.loopringPrivateKey), 64)
    
    return cfg, secret

# Parse CLI arguments
def parse_args():
    # check for command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-n", "--amount", help="Specify the transfer amount per to address", type=int)
    parser.add_argument("--test", help="Skips the transfer step", action='store_true')
    parser.add_argument("-V", "--verbose", help="Verbose output", action='store_true')
    parser.add_argument("--noprompt", help="Skip all user prompts", action='store_true')
    parser.add_argument("--name", help=argparse.SUPPRESS, type=str)
    parser.add_argument("--nft", help="NFT ID (hex string) to transfer", type=str)
    # parser.add_argument("--memo", help="Transfer memo", default="")
    
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument("--to", help="L2 address (hex string) to transfer to", type=str)
    source_group.add_argument("--tofile", help="Path to a file of L2 address (hex string) to transfer to", type=str)

    args = parser.parse_args()

    # NFT id
    assert args.nft, "Missing NFT ID (use --nft)"
    
    # Transfer amount
    if not args.amount:
        args.amount = int(os.getenv("AMOUNT") or 1)

    # Test mode
    if args.test:
        print('Test mode enabled: Transfers will be skipped and no fees will incur.')
    
    args.memo = ''

    global VERBOSE
    VERBOSE = args.verbose

    return args

# Estimate fees for a batch of NFTs from offchain fees
def estimate_batch_fees(cfg, off_chain_fee, count):
    fee = int(off_chain_fee['fees'][cfg.maxFeeTokenId]['fee'])
    token_symbol = off_chain_fee['fees'][cfg.maxFeeTokenId]['token']
    discount = off_chain_fee['fees'][cfg.maxFeeTokenId]['discount']
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

async def get_user_api_key(cfg, secret):
    async with LoopringMintService() as lms:
        # Getting the user api key
        api_key_resp = await lms.getUserApiKey(accountId=cfg.fromAccount, privateKey=secret.loopringPrivateKey)
        # log(f"User API key: {json.dumps(api_key_resp, indent=2)}")   # DO NOT LOG
        if api_key_resp is None:
            sys.exit("Failed to obtain user api key")

    secret.loopringApiKey = api_key_resp['apiKey']

async def get_offchain_parameters(cfg, secret, nftTokenId):
    async with LoopringMintService() as lms:
        parameters = {}
        # Getting the storage id
        storage_id = await lms.getNextStorageId(apiKey=secret.loopringApiKey, accountId=cfg.fromAccount, sellTokenId=nftTokenId)
        log(f"Storage id: {json.dumps(storage_id, indent=2)}")
        if storage_id is None:
            sys.exit("Failed to obtain storage id")
        
        parameters['storage_id'] = storage_id

        # Getting the token address
        counterfactual_nft_info = CounterFactualNftInfo(nftOwner=cfg.fromAddress, nftFactory=cfg.nftFactory, nftBaseUri="")
        counterfactual_nft = await lms.computeTokenAddress(apiKey=secret.loopringApiKey, counterFactualNftInfo=counterfactual_nft_info)
        log(f"CounterFactualNFT Token Address: {json.dumps(counterfactual_nft, indent=2)}")
        if counterfactual_nft is None:
            sys.exit("Failed to obtain token address")
            
        parameters['counterfactual_nft_info'] = counterfactual_nft_info
        parameters['counterfactual_nft'] = counterfactual_nft

        # Getting the offchain fee (requestType=11 is NFT_TRANSFER)
        off_chain_fee = await lms.getOffChainFee(apiKey=secret.loopringApiKey, accountId=cfg.fromAccount, requestType=11, tokenAddress=counterfactual_nft['tokenAddress'])
        log(f"Offchain fee:  {json.dumps(off_chain_fee['fees'][cfg.maxFeeTokenId], indent=2)}")
        if off_chain_fee is None:
            sys.exit("Failed to obtain offchain fee")
            
        parameters['off_chain_fee'] = off_chain_fee

    return parameters

async def get_nft_info(cfg, secret, args) -> NftInfo:
    async with LoopringMintService() as lms:
        info = {}
        # Getting the NFT balance
        nft_balance = await lms.getUserNftBalance(apiKey=secret.loopringApiKey, accountId=cfg.fromAccount)
        log(f"NFT balance: {json.dumps(nft_balance, indent=2)}")
        if nft_balance is None:
            sys.exit("Failed to obtain nft balance")
        
    nft_info = [nft for nft in nft_balance['data'] if nft['nftId'].lower() == args.nft.lower()]
    nft_info.append(None)

    return nft_info[0]

# https://github.com/Loopring/loopring_sdk/blob/692d372165b5ea0d760e33e177d9003cc0dfb0f7/src/api/sign/sign_tools.ts#L1020
async def get_hashes_and_sign(cfg, secret, tokenId: int, amount: int, toAddress: str, toAccount: int, offchain_parameters: dict, info: dict):
    # Generate the poseidon hash for the remaining data
    # https://github.com/Loopring/loopring_sdk/blob/692d372165b5ea0d760e33e177d9003cc0dfb0f7/src/api/sign/sign_tools.ts#L899
    inputs = [
        int(cfg.exchange, 16),
        cfg.fromAccount,  # fromAccountId
        toAccount,        # toAccountId
        tokenId,
        amount,
        cfg.maxFeeTokenId,
        int(offchain_parameters['off_chain_fee']['fees'][cfg.maxFeeTokenId]['fee']),
        int(toAddress, 16),
        0,
        0,
        cfg.validUntil,
        offchain_parameters['storage_id']['offchainId']
    ]
    hasher = NFTTransferEddsaSignHelper(private_key=secret.loopringPrivateKey)
    nft_poseidon_hash = hasher.hash(inputs)
    plog(inputs)
    log("Hashed NFT transfer payload: 0x{0:0{1}x}".format(nft_poseidon_hash, 64))
    info['nft_poseidon_hash'] = "0x{0:0{1}x}".format(nft_poseidon_hash, 64)

    eddsa_signature = hasher.sign(inputs)
    log(f"Signed NFT payload hash: {eddsa_signature}")
    info['eddsa_signature'] = eddsa_signature

    return eddsa_signature

async def transfer_nft(cfg, secret,  amount: int, toAccount: int, toAddress: str, nftInfo: NftInfo, eddsa_signature: str, offchain_parameters: dict, test_mode: bool, info: dict):
    async with LoopringMintService() as lms:
        if test_mode:
            return TransferResult.TESTMODE, None
        
        nft_transfer_response = await lms.transferNft(
            apiKey=secret.loopringApiKey,
            privateKey=secret.loopringPrivateKey,
            exchange=cfg.exchange,
            fromAccountId=cfg.fromAccount,
            fromAddress=cfg.fromAddress,
            toAccountId=toAccount,
            toAddress=toAddress,
            amount=amount,
            validUntil=cfg.validUntil,
            storageId=offchain_parameters['storage_id']['offchainId'],
            maxFeeTokenId=cfg.maxFeeTokenId,
            maxFeeAmount=offchain_parameters['off_chain_fee']['fees'][cfg.maxFeeTokenId]['fee'],
            memo=cfg.memo,
            nftInfo=nftInfo,
            counterFactualNftInfo=offchain_parameters['counterfactual_nft_info'],
            eddsaSignature=eddsa_signature
        )
        log(f"Nft Transfer reponse: {nft_transfer_response}")
        info['nft_transfer_response'] = nft_transfer_response

        if nft_transfer_response is not None and lms.last_status == 200:
            return TransferResult.SUCCESS, nft_transfer_response
        else:
            return TransferResult.FAILED, nft_transfer_response

async def main():
    load_dotenv()

    # check for command line arguments
    try:
        args = parse_args()
    except Exception as err:
        sys.exit(f"Failed to initialize the transfers: {err}")
    
    # Generate paths
    paths = Struct()
    paths.transfer_info = os.path.join(os.path.dirname(__file__), "transfer-info.json")
    paths.config = "./config.json"

    # Parse all cids from JSON or command line
    if args.tofile:
        with open(args.tofile, 'r') as f:
            all_tos = [line.strip() for line in f]
    elif args.to:
        all_tos = [args.to]

    if not os.path.exists(os.path.dirname(paths.transfer_info)):
        os.makedirs(os.path.dirname(paths.transfer_info))

    transfer_info = []
    transfer_info.append({'args': vars(args)})

    approved_fees_prompt = args.noprompt

    try:
        cfg, secret = await load_config(args, paths)
        log("config dump:")
        plog(cfg)
        transfer_info.append({'cfg': cfg})

        # Filter tos
        filtered_tos = []
        for to in all_tos:
            info = {'to': to, 'amount': args.amount, 'skipped': True}

            valid_to = False

            # L2 address in hex string
            if not valid_to and str(to)[:2] == '0x':
                try:
                    int(to, 16)
                    valid_to = True
                except ValueError as err:
                    pass
            # .eth ENS (or .loopring.eth)
            if not valid_to and str(to)[-4:] == '.eth':
                valid_to = True
            # Account ID in decimal
            if not valid_to:
                try:
                    if str(int(str(to), 10)) == str(to):
                        valid_to = True
                except ValueError as err:
                    pass

            if not valid_to:
                transfer_info.append(info)
                print(f"Skipping invalid to address: {to}")
                continue

            filtered_tos.append(to)
            info['skipped'] = False

            transfer_info.append(info)

        if len(filtered_tos) == 0:
            print(f"No valid to address found, no one to transfer to...")
            sys.exit(0)

        # Get user API key
        print("Getting user API key... ", end='')
        await get_user_api_key(cfg, secret)
        print("done!")

        # Get nft balance
        print("Getting nft info... ", end='')
        nft_info = await get_nft_info(cfg, secret, args)
        transfer_info.append({'nft_info': nft_info})
        print("done!")

        # Get storage id, token address and offchain fee
        print("Getting offchain parameters... ", end='')
        offchain_parameters = await get_offchain_parameters(cfg, secret, nft_info['tokenId'])
        transfer_info.append({'offchain_parameters': offchain_parameters})
        print("done!")

        # Estimate fees and get user approval
        if not approved_fees_prompt:
            batch_fees, fees_symbol = estimate_batch_fees(cfg, offchain_parameters['off_chain_fee'], len(filtered_tos))
            log("--------")
            approved_fees_prompt = prompt_yes_no(f"Estimated L2 fees for transfering {args.amount} copies of NFTs to {len(filtered_tos)} addresses: {batch_fees}{fees_symbol}, continue?", default="no")
            transfer_info.append({'fee_approval': approved_fees_prompt, 'fee': batch_fees, 'token': fees_symbol})
            if not approved_fees_prompt: 
                sys.exit("Aborted by user")
        
        # NFT transfer sequence
        for i, to in enumerate(filtered_tos):

            info = {'to': to, 'amount': args.amount}
            
            # Resolve ENS, get account_id and ETH address
            toAccount, toAddress = await retry_async(get_account_info, to, retries=3)
            assert toAddress and toAccount, f"Invalid to address: {toAddress} (account ID {toAccount})"
            info['toAddress'] = toAddress
            info['toAccount'] = toAccount

            # Generate Eddsa Signature
            eddsa_signature = await get_hashes_and_sign(cfg, secret, nft_info['tokenId'], args.amount, toAddress, toAccount, offchain_parameters=offchain_parameters, info=info)

            # Submit the nft transfer
            transfer_result, response = await transfer_nft(cfg,
                                                           secret,
                                                           amount=args.amount,
                                                           toAccount=toAccount,
                                                           toAddress=toAddress,
                                                           nftInfo=nft_info,
                                                           eddsa_signature=eddsa_signature,
                                                           offchain_parameters=offchain_parameters,
                                                           test_mode=args.test,
                                                           info=info)
            
            if transfer_result == TransferResult.SUCCESS:
                print(f"{i+1}/{len(filtered_tos)} {i+1}: Successful Transfer! (tx hash: {response['hash']})")
                offchain_parameters['storage_id']['offchainId'] += 2
            elif transfer_result ==  TransferResult.FAILED:
                print(f"{i+1}/{len(filtered_tos)} {i+1}: Transfer FAILED... (to: {to})")
            elif transfer_result ==  TransferResult.TESTMODE:
                print(f"{i+1}/{len(filtered_tos)} {i+1}: Skipping transfer (test mode) (to: {to})")

            transfer_info.append(info)
    finally:
        with open(paths.transfer_info, 'w+') as f:
            json.dump(transfer_info, f, indent=4)

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main())
