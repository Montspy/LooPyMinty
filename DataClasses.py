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
    discount: int

class OffchainFee(TypedDict):
    gasPrice: str
    fees: 'list[Fee]'

class StorageId(TypedDict):
    orderId: int
    offchainId: int
