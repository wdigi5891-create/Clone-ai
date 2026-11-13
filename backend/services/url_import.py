"""Import par lien, uniquement par des mécanismes autorisés.

- Lien direct vers un fichier vidéo public (MP4/MOV/WEBM) : téléchargement HTTP simple.
- TikTok : le lien est vérifié via l'API officielle oEmbed, mais TikTok ne fournit
  aucun téléchargement autorisé pour les applications tierces ; on n'essaie donc PAS
  de contourner ses protections et l'utilisateur est invité à importer son fichier.
- Autres plateformes (YouTube, Instagram, ...) : même politique.
"""
import ipaddress
import socket
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

from core.config import get_settings

PLATFORMS = {
    "tiktok.com": "TikTok", "youtube.com": "YouTube", "youtu.be": "YouTube",
    "instagram.com": "Instagram", "facebook.com": "Facebook", "fb.watch": "Facebook",
    "x.com": "X", "twitter.com": "X", "snapchat.com": "Snapchat", "vimeo.com": "Vimeo",
    "dailymotion.com": "Dailymotion",
}
CONTENT_TYPES = {"video/mp4": "mp4", "video/quicktime": "mov", "video/webm": "webm"}
UA = "AIVideoCloner/1.0 (+import par lien direct)"


class UrlImportError(Exception):
    def __init__(self, message: str, code: str = "invalid", info: dict | None = None):
        super().__init__(message)
        self.code, self.info = code, info or {}


def _platform(host: str) -> str | None:
    host = host.lower()
    return next((name for dom, name in PLATFORMS.items() if host == dom or host.endswith("." + dom)), None)


def _assert_public(host: str) -> None:
    """Protection SSRF : refuse les adresses privées, locales ou réservées."""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        raise UrlImportError("Nom de domaine introuvable. Vérifiez le lien.")
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise UrlImportError("Ce lien pointe vers une adresse non publique et ne peut pas être importé.")


def validate(url: str) -> dict:
    """Valide le lien et indique s'il est importable. Lève UrlImportError sinon."""
    url = (url or "").strip()
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise UrlImportError("Lien invalide : collez une adresse complète commençant par https://")
    host = parsed.hostname
    platform = _platform(host)
    if platform == "TikTok":
        info = {"platform": platform}
        try:
            r = httpx.get("https://www.tiktok.com/oembed", params={"url": url}, timeout=10,
                          headers={"User-Agent": UA})
            if r.status_code == 200:
                data = r.json()
                info.update(title=data.get("title", ""), author=data.get("author_name", ""))
            elif r.status_code in (400, 404):
                raise UrlImportError("Ce lien TikTok est introuvable ou la vidéo n'est pas publique.", "not_found", info)
        except httpx.HTTPError:
            pass
        raise UrlImportError(
            "Lien TikTok reconnu, mais TikTok n'autorise pas le téléchargement des vidéos par des "
            "applications tierces. Téléchargez votre vidéo depuis l'application TikTok (Partager → "
            "Enregistrer la vidéo, si le créateur l'autorise) puis importez le fichier ici.",
            "platform_restricted", info)
    if platform:
        raise UrlImportError(
            f"{platform} n'autorise pas le téléchargement direct de ses vidéos. Importez le fichier "
            "original (MP4, MOV ou WEBM) dont vous détenez les droits.", "platform_restricted",
            {"platform": platform})
    allowed = [h.strip().lower() for h in get_settings().url_import_allowed_hosts.split(",") if h.strip()]
    if allowed and host.lower() not in allowed:
        raise UrlImportError("Ce domaine n'est pas autorisé pour l'import par lien.", "host_not_allowed")
    _assert_public(host)
    return {"url": url, "platform": None, "importable": True}


def download(url: str, dest_dir: str) -> tuple[str, str]:
    """Télécharge un lien direct. Retourne (chemin local, nom de fichier)."""
    s = get_settings()
    validate(url)
    max_bytes = s.max_upload_mb * 1024 * 1024
    current = url
    with httpx.Client(timeout=httpx.Timeout(30, read=120), headers={"User-Agent": UA}) as client:
        for _ in range(4):
            with client.stream("GET", current) as r:
                if r.status_code in (301, 302, 303, 307, 308) and r.headers.get("location"):
                    current = urljoin(current, r.headers["location"])
                    validate(current)  # chaque redirection est revalidée
                    continue
                if r.status_code in (401, 403):
                    raise UrlImportError("Cette vidéo est protégée ou privée : accès refusé par le site. "
                                         "Importez plutôt le fichier original.", "forbidden")
                if r.status_code != 200:
                    raise UrlImportError(f"La vidéo n'est pas accessible (réponse {r.status_code}). "
                                         "Importez plutôt le fichier original.", "unreachable")
                ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
                ext = CONTENT_TYPES.get(ctype) or Path(urlparse(current).path).suffix.lstrip(".").lower()
                if ext not in s.allowed_ext_set or (ctype and not ctype.startswith(("video/", "application/octet-stream"))):
                    raise UrlImportError("Ce lien ne pointe pas directement vers un fichier vidéo MP4, MOV ou WEBM. "
                                         "Importez plutôt le fichier original.", "not_video")
                if int(r.headers.get("content-length") or 0) > max_bytes:
                    raise UrlImportError(f"Vidéo trop volumineuse (limite {s.max_upload_mb} Mo).", "too_large")
                name = Path(urlparse(current).path).name or f"video.{ext}"
                dest = Path(dest_dir) / f"download.{ext}"
                size = 0
                with open(dest, "wb") as f:
                    for chunk in r.iter_bytes(1024 * 256):
                        size += len(chunk)
                        if size > max_bytes:
                            raise UrlImportError(f"Vidéo trop volumineuse (limite {s.max_upload_mb} Mo).", "too_large")
                        f.write(chunk)
                return str(dest), name
    raise UrlImportError("Trop de redirections pour ce lien.", "unreachable")
