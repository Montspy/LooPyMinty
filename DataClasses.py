from typing import TypedDict

class MintResponseData(TypedDict):
    hash: str
    nftTokenId: int
    nftData: str
    status: str
    isIdempotent: bool
    accountId: int
    storageId: int

class CounterFactualNft(TypedDict):
    tokenAddress: str

class CounterFactualNftInfo(TypedDict):
    nftOwner: str
    nftFactory: str
    nftBaseUri: str

class Fee(TypedDict):
    token: str
    fee: str
    discount: float

class OffchainFee(TypedDict):
    gasPrice: str
    fees: 'list[Fee]'

class StorageId(TypedDict):
    orderId: int
    offchainId: int

class NftData(TypedDict):
    nftData: str
    minter: str
    nftType: str
    tokenAddress: str
    nftId: str
    creatorFeeBips: int
    royaltyPercentage: int
    status: bool
    nftFactory: str
    nftOwner: str
    nftBaseUri: str
    royaltyAddress: str
    originalMinter: str

token_decimals = {'ETH': 18, 'LRC': 18, 'USDT': 6, 'DAI': 18, 'USDC': 6}