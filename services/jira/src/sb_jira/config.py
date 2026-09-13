"""Configuration for sb-jira. All paths are env-overridable for testing."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SB_JIRA_", extra="ignore")

    # Repo layout
    code_home: Path = Path("/Users/praspr/Documents/code_home")

    # Local mirror
    tickets_dir: Path = Path(
        "/Users/praspr/Documents/code_home/ciq/docs/jira/tickets"
    )
    readme_path: Path = Path(
        "/Users/praspr/Documents/code_home/ciq/docs/jira/README.md"
    )
    tickethistory_path: Path = Path(
        "/Users/praspr/Documents/code_home/ciq/docs/jira/tickethistory.md"
    )

    # Atlassian
    atlassian_site: str = "https://cisco-cxe.atlassian.net"
    atlassian_email: str = "praspr@cisco.com"
    atlassian_jql: str = 'assignee = "praspr@cisco.com" ORDER BY updated DESC'

    # keyring
    keyring_service: str = "sb"
    keyring_username: str = "jira.token"

    # CORS
    web_app_origin: str = "http://localhost:5173"

    # server
    host: str = "127.0.0.1"
    port: int = 8789

    @property
    def relative_tickets_prefix(self) -> str:
        """Relative path prefix used in JiraTicket.file_path, e.g. 'ciq/docs/jira/tickets'."""
        try:
            rel = self.tickets_dir.relative_to(self.code_home)
            return str(rel)
        except ValueError:
            return str(self.tickets_dir)


settings = Settings()
