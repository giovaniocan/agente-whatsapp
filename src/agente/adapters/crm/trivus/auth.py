"""Auth de usuário de serviço (RN-64): login → JWT 7d, sem refresh; re-login no 401."""

import httpx

from agente.adapters.crm.trivus.dtos import TrivusLogin
from agente.adapters.crm.trivus.errors import TrivusError


class TrivusAuth:
    def __init__(self, client: httpx.AsyncClient, email: str, password: str) -> None:
        self._client = client
        self._email = email
        self._password = password
        self._token: str | None = None

    async def token(self) -> str:
        if self._token is None:
            resp = await self._client.post(
                "/auth/login", json={"email": self._email, "password": self._password}
            )
            if resp.status_code >= 400:
                raise TrivusError(f"login no trivus-api falhou ({resp.status_code})")
            self._token = TrivusLogin.model_validate(resp.json()).access_token
        return self._token

    def invalidate(self) -> None:
        self._token = None
