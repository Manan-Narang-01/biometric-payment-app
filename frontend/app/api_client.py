"""HTTP client for communicating with the FastAPI backend."""
import requests
from flask import current_app, session


class APIClient:
    def __init__(self):
        self.base_url = None

    def _base(self) -> str:
        return current_app.config["API_BASE_URL"]

    def _headers(self, token: str | None = None) -> dict:
        headers = {"Content-Type": "application/json"}
        t = token or session.get("access_token")
        if t:
            headers["Authorization"] = f"Bearer {t}"
        return headers

    def get(self, path: str, params: dict = None, token: str = None) -> requests.Response:
        return requests.get(
            f"{self._base()}{path}",
            headers=self._headers(token),
            params=params,
            timeout=10,
        )

    def post(self, path: str, data: dict = None, token: str = None) -> requests.Response:
        return requests.post(
            f"{self._base()}{path}",
            headers=self._headers(token),
            json=data,
            timeout=10,
        )

    def put(self, path: str, data: dict = None, token: str = None) -> requests.Response:
        return requests.put(
            f"{self._base()}{path}",
            headers=self._headers(token),
            json=data,
            timeout=10,
        )

    def delete(self, path: str, token: str = None) -> requests.Response:
        return requests.delete(
            f"{self._base()}{path}",
            headers=self._headers(token),
            timeout=10,
        )


api = APIClient()
