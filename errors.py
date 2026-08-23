
class SourceUnavailableError(Exception):
    def __init__(self, source: str, reason: str):
        self.source = source
        self.reason = reason
        super().__init__(f"{source} unavailable: {reason}")