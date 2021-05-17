from requests.adapters import HTTPAdapter, DEFAULT_POOLBLOCK


class FingerprintAdapter(HTTPAdapter):
    __attrs__ = HTTPAdapter.__attrs__ + ['fingerprint']

    def __init__(self, fingerprint, **kwargs):
        self.fingerprint = fingerprint

        super(FingerprintAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=DEFAULT_POOLBLOCK, **pool_kwargs):
        super().init_poolmanager(connections, maxsize, block, **pool_kwargs, assert_fingerprint=self.fingerprint)

    def proxy_manager_for(self, proxy, **proxy_kwargs):
        return super().proxy_manager_for(proxy, **proxy_kwargs, assert_fingerprint=self.fingerprint)
