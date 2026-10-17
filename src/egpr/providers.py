"""Provider transport selection without changing prompts or model parameters."""
import atexit
import io
import json

from .api import ChatBackend, ENDPOINTS


class _BufferedHTTPResponse(io.BytesIO):
    def __init__(self, response):
        super().__init__(response.content)
        self.status = response.status_code
        self.headers = response.headers


class TogetherBackend(ChatBackend):
    """Use the official SDK transport; retain the common raw-response ledger.

    An initial urllib metadata request received HTTP 403. The official SDK's
    authenticated metadata request succeeded, so account access was not assumed
    broken. SDK retries are explicitly disabled, including on HTTP errors.
    """
    def __init__(self, credentials, tariff, *, timeout=45, client=None, status_errors=()):
        self.client = client
        self.status_errors = status_errors
        super().__init__(credentials, tariff, timeout=timeout, opener=self._open)

    def _open(self, request, *, context, timeout):
        if self.client is None:
            try:
                import httpx
                from together import Together, APIStatusError
            except ImportError:
                raise RuntimeError("Install the provider extra: uv sync --extra together") from None
            self.client = Together(api_key=self.credentials["TOGETHER_API_KEY"], max_retries=0,
                base_url=ENDPOINTS["together"].removesuffix("chat/completions"),
                http_client=httpx.Client(verify=context, timeout=timeout))
            self.status_errors = (APIStatusError,)
            atexit.register(self.client.close)
        try:
            raw = self.client.chat.completions.with_raw_response.create(**json.loads(request.data), timeout=timeout)
            response = raw.http_response
        except self.status_errors as exc:
            response = exc.response
        return _BufferedHTTPResponse(response)


def make_backend(provider, credentials, tariff):
    if provider == "together":
        return TogetherBackend(credentials, tariff)
    if provider == "openai":
        return ChatBackend(credentials, tariff)
    raise ValueError("Unconfigured provider")
