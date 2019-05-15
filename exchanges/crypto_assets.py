class CryptoAssetInfo:
    def __init__(self, id, precision, exchange_info):
        self.id = id
        self.precision = precision
        self.exchange_info = exchange_info

class CryptoInstrumentInfo:
    def __init__(self, id, exchange, status, exchange_info):
        self.id = id
        self.exchange = exchange
        self.status = status
        self.exchange_info = exchange_info

class CryptoInstrumentPairInfo(CryptoInstrumentInfo):
    def __init__(self, id, exchange, base_asset, quote_asset, status, exchange_info):
        super().__init__(id, exchange, status, exchange_info)
        self.base_asset = base_asset
        self.quote_asset = quote_asset