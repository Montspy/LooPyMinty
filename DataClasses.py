from typing import TypedDict

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

token_decimals = {'ETH': 18, 'LRC': 18, 'USDT': 6, 'DAI': 18, 'USDC': 6}