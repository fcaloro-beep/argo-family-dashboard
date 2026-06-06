from __future__ import annotations

import base64
from datetime import date, datetime, timedelta
import hashlib
import json
import secrets
import string
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from aiohttp import ClientError
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

CLIENT_ID = "72fd6dea-d0ab-4bb9-8eaa-3ac24c84886c"
APP_VERSION = "1.29.2"
API_BASE = "https://www.portaleargo.it/appfamiglia/api/rest"
REDIRECT_URI = "it.argosoft.didup.famiglia.new://login-callback"
MAX_ATTRIBUTE_ITEMS = 200


class ArgoFamilyError(Exception):
    """Errore durante la lettura dei dati Argo."""


class ArgoFamilyClient:
    def __init__(
        self,
        hass: HomeAssistant,
        data: dict[str, Any],
        options: dict[str, Any] | None = None,
    ) -> None:
        self.hass = hass
        self.session = async_get_clientsession(hass)
        self.school_code = data["school_code"]
        self.username = data["username"]
        self.password = data["password"]
        self.child_name = data.get("child_name") or data.get("name") or self.username
        self.options = options or {}
        self.token: dict[str, Any] | None = None
        self.login_data: dict[str, Any] | None = None
        self.profile: dict[str, Any] | None = None
        self.dashboard: dict[str, Any] | None = None

    async def async_get_dashboard(self) -> dict[str, Any]:
        try:
            await self._login()
            raw = self.dashboard or {}
            return self._build_home_assistant_data(raw)
        except ArgoFamilyError:
            raise
        except (ClientError, TimeoutError) as err:
            raise ArgoFamilyError(f"Errore rete Argo: {err}") from err
        except Exception as err:
            raise ArgoFamilyError(str(err)) from err

    async def _login(self) -> None:
        login_link = self._generate_login_link()
        code = await self._get_code(login_link)
        self.token = await self._get_token(login_link, code)
        self.login_data = await self._get_login_data()
        self.profile = await self._get_profile()
        self.dashboard = await self._get_dashboard()

    async def _get_code(self, login_link: dict[str, Any]) -> str:
        cookies: list[str] = []

        async with self.session.get(
            login_link["url"], allow_redirects=False
        ) as response:
            location = response.headers.get("location")
            cookies.extend(_cookies_from_response(response))
            if not location:
                text = await response.text()
                raise ArgoFamilyError(
                    f"Auth request senza redirect ({response.status}): {text[:200]}"
                )

        challenge = parse_qs(urlparse(location).query).get("login_challenge", [None])[0]
        if not challenge:
            raise ArgoFamilyError("Login challenge non trovato nel redirect Argo")

        form = {
            "challenge": challenge,
            "client_id": CLIENT_ID,
            "prefill": "false",
            "famiglia_customer_code": self.school_code,
            "username": self.username,
            "password": self.password,
            "login": "true",
        }
        async with self.session.post(
            "https://www.portaleargo.it/auth/sso/login",
            data=form,
            headers={"content-type": "application/x-www-form-urlencoded"},
            allow_redirects=False,
        ) as response:
            url1 = response.headers.get("location")
            if not url1:
                text = await response.text()
                raise ArgoFamilyError(
                    f"Login Argo senza redirect ({response.status}): {text[:200]}"
                )

        async with self.session.get(
            url1,
            headers={"cookie": "; ".join(cookies)},
            allow_redirects=False,
        ) as response:
            url2 = response.headers.get("location")
            cookies.extend(_cookies_from_response(response))
            if not url2:
                text = await response.text()
                raise ArgoFamilyError(
                    f"Primo redirect Argo non valido ({response.status}): {text[:200]}"
                )

        async with self.session.get(url2, allow_redirects=False) as response:
            url3 = response.headers.get("location")
            if not url3:
                text = await response.text()
                raise ArgoFamilyError(
                    f"Secondo redirect Argo non valido ({response.status}): {text[:200]}"
                )

        async with self.session.get(
            url3,
            headers={"cookie": "; ".join(cookies)},
            allow_redirects=False,
        ) as response:
            url4 = response.headers.get("location")
            if not url4:
                text = await response.text()
                raise ArgoFamilyError(
                    f"Ultimo redirect Argo non valido ({response.status}): {text[:200]}"
                )

        code = parse_qs(urlparse(url4).query).get("code", [None])[0]
        if not code:
            raise ArgoFamilyError(f"Codice OAuth non trovato nel redirect: {url4}")
        return code

    async def _get_token(self, login_link: dict[str, Any], code: str) -> dict[str, Any]:
        body = {
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": REDIRECT_URI,
            "code_verifier": login_link["code_verifier"],
            "client_id": CLIENT_ID,
        }
        async with self.session.post(
            "https://auth.portaleargo.it/oauth2/token",
            data=urlencode(body),
            headers={"content-type": "application/x-www-form-urlencoded"},
        ) as response:
            data = await response.json(content_type=None)
            if "error" in data:
                raise ArgoFamilyError(
                    f"{data.get('error')}: {data.get('error_description')}"
                )
            data["expire_date"] = (
                datetime.now() + timedelta(seconds=int(data.get("expires_in", 0)))
            ).isoformat()
            return data

    async def _api_request(
        self,
        path: str,
        *,
        method: str = "GET",
        body: Any = None,
    ) -> dict[str, Any]:
        headers = {
            "accept": "application/json",
            "argo-client-version": APP_VERSION,
            "authorization": f"Bearer {self.token.get('access_token') if self.token else ''}",
            "content-type": "application/json; charset=utf-8",
        }
        if self.login_data:
            headers["x-auth-token"] = str(self.login_data.get("token", ""))
            headers["x-cod-min"] = str(self.login_data.get("codMin", ""))
        if self.token and self.token.get("expire_date"):
            headers["x-date-exp-auth"] = _format_date(self.token["expire_date"])

        async with self.session.request(
            method,
            f"{API_BASE}/{path}",
            headers=headers,
            json=body if method == "POST" else None,
        ) as response:
            text = await response.text()
            try:
                data = json.loads(text)
            except json.JSONDecodeError as err:
                raise ArgoFamilyError(
                    f"{method} /{path} fallita ({response.status}): {text[:300]}"
                ) from err
            if isinstance(data, dict) and data.get("success") is False:
                raise ArgoFamilyError(data.get("msg") or f"Errore API /{path}")
            return data

    async def _get_login_data(self) -> dict[str, Any]:
        data = await self._api_request(
            "login",
            method="POST",
            body={
                "lista-opzioni-notifiche": "{}",
                "lista-x-auth-token": "[]",
                "clientID": _random_string(163),
            },
        )
        rows = data.get("data") or []
        if not rows:
            raise ArgoFamilyError("Login Argo riuscito ma nessun profilo trovato")
        return rows[0]

    async def _get_profile(self) -> dict[str, Any]:
        data = await self._api_request("profilo")
        return data.get("data") or {}

    async def _get_dashboard(self) -> dict[str, Any]:
        start_date = (
            _deep_get(self.profile, "anno", "dataInizio")
            or datetime.now().strftime("%Y-%m-%d 00:00:00.000")
        )
        options = self.login_data.get("opzioni", []) if self.login_data else []
        data = await self._api_request(
            "dashboard/dashboard",
            method="POST",
            body={
                "dataultimoaggiornamento": _format_date(start_date),
                "opzioni": json.dumps(
                    {item.get("chiave"): item.get("valore") for item in options}
                ),
            },
        )
        rows = _deep_get(data, "data", "dati") or []
        if not rows:
            raise ArgoFamilyError("Dashboard Argo vuota")

        dashboard = rows[0]
        for key in (
            "fuoriClasse",
            "promemoria",
            "bacheca",
            "voti",
            "bachecaAlunno",
            "registro",
            "appello",
        ):
            dashboard[key] = _handle_operation(dashboard.get(key) or [])
        dashboard["prenotazioniAlunni"] = _handle_operation(
            dashboard.get("prenotazioniAlunni") or [],
            pk_fn=lambda item: _deep_get(item, "prenotazione", "pk"),
        )
        return dashboard

    def _build_home_assistant_data(self, raw: dict[str, Any]) -> dict[str, Any]:
        grades = [_grade_to_ha(item) for item in raw.get("voti") or []]
        grades.sort(key=lambda item: item.get("data") or "", reverse=True)

        register = [_register_to_ha(item) for item in raw.get("registro") or []]
        register.sort(key=lambda item: item.get("data") or "", reverse=True)

        assignments = [
            homework
            for entry in register
            for homework in entry.get("compiti", [])
        ]
        assignments.sort(key=lambda item: item.get("data_consegna") or "")
        pending_assignments = [
            item for item in assignments if _date_sort_key(item.get("data_consegna")) >= _today_key()
        ]
        assigned_assignments = [
            item for item in assignments if _date_sort_key(item.get("data_consegna")) < _today_key()
        ]

        subjects = self._build_subjects(raw, grades)
        average = _number_or_none(raw.get("mediaGenerale"))
        activities = [
            item for item in register if item.get("attivita")
        ]
        lessons = register
        memos = [_memo_to_ha(item) for item in raw.get("promemoria") or []]
        class_board = [_board_to_ha(item) for item in raw.get("bacheca") or []]
        student_board = [_student_board_to_ha(item) for item in raw.get("bachecaAlunno") or []]
        attendance = _attendance_summary(raw.get("appello") or [], raw.get("fuoriClasse") or [])
        updates = _build_updates(grades, class_board, student_board, raw.get("appello") or [], raw.get("fuoriClasse") or [])
        upcoming = _build_upcoming(pending_assignments, activities, memos)

        return {
            "student": self.login_data or {},
            "profile": self.profile or {},
            "school_code": self.school_code,
            "school_name": _first_value(
                self.profile or {},
                self.login_data or {},
                keys=(
                    "desScuola",
                    "denominazioneScuola",
                    "scuola",
                    "nomeScuola",
                    "istituto",
                    "desIstituto",
                ),
            ),
            "class_name": _first_value(
                self.profile or {},
                self.login_data or {},
                keys=("classe", "desClasse", "classeDescrizione", "sezione", "annoCorso"),
            ),
            "student_name": self.child_name,
            "status": "ok",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "average": average,
            "subjects": subjects,
            "grades": grades,
            "latest_grade": grades[0] if grades else None,
            "grades_by_subject": _group_by(grades, "materia"),
            "upcoming": upcoming,
            "updates": updates,
            "attendance": attendance,
            "lessons": lessons[:MAX_ATTRIBUTE_ITEMS],
            "assignments": assignments,
            "pending_assignments": pending_assignments,
            "assigned_assignments": assigned_assignments,
            "activities": activities[:MAX_ATTRIBUTE_ITEMS],
            "absences": raw.get("appello") or [],
            "communications": class_board,
            "student_communications": student_board,
            "notes": raw.get("noteDisciplinari") or [],
            "schedule": raw.get("orario") or [],
            "register": register[:MAX_ATTRIBUTE_ITEMS],
            "memos": memos,
            "raw": raw,
        }

    @staticmethod
    def _build_subjects(raw: dict[str, Any], grades: list[dict[str, Any]]) -> list[dict[str, Any]]:
        media_materie = raw.get("mediaMaterie") or {}
        lista_materie = raw.get("listaMaterie") or []
        by_pk = {str(item.get("pk")): item.get("materia") for item in lista_materie}
        subjects = []

        for pk, item in media_materie.items():
            if not isinstance(item, dict) or "mediaMateria" not in item:
                continue
            subjects.append(
                {
                    "materia": by_pk.get(str(pk)) or str(pk),
                    "pk": pk,
                    "media": _number_or_none(item.get("mediaMateria")),
                    "voti": item.get("numVoti", 0),
                }
            )

        if subjects:
            return sorted(subjects, key=lambda item: str(item.get("materia")))

        grouped: dict[str, list[float]] = {}
        counts: dict[str, int] = {}
        for grade in grades:
            subject = grade.get("materia") or "Materia"
            counts[subject] = counts.get(subject, 0) + 1
            value = _number_or_none(grade.get("valore"))
            if value is not None:
                grouped.setdefault(subject, []).append(value)

        return [
            {
                "materia": subject,
                "media": _average(grouped.get(subject, [])),
                "voti": counts[subject],
            }
            for subject in sorted(counts)
        ]

    def _generate_login_link(self) -> dict[str, Any]:
        code_verifier = _random_string(43)
        challenge = _code_challenge(code_verifier)
        state = _random_string(22)
        nonce = _random_string(22)
        scopes = ["openid", "offline", "profile", "user.roles", "argo"]
        query = urlencode(
            {
                "redirect_uri": REDIRECT_URI,
                "client_id": CLIENT_ID,
                "response_type": "code",
                "prompt": "login",
                "state": state,
                "nonce": nonce,
                "scope": " ".join(scopes),
                "code_challenge": challenge,
                "code_challenge_method": "S256",
            }
        )
        return {
            "url": f"https://auth.portaleargo.it/oauth2/auth?{query}",
            "redirect_uri": REDIRECT_URI,
            "scopes": scopes,
            "code_verifier": code_verifier,
            "challenge": challenge,
            "client_id": CLIENT_ID,
            "state": state,
            "nonce": nonce,
        }


def _cookies_from_response(response: Any) -> list[str]:
    values = response.headers.getall("set-cookie", [])
    cookies = []
    for value in values:
        cookie = value.split(";", 1)[0]
        if cookie:
            cookies.append(cookie)
    return cookies


def _random_string(length: int) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def _code_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def _format_date(value: Any) -> str:
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            try:
                dt = datetime.strptime(value[:10], "%Y-%m-%d")
            except ValueError:
                dt = datetime.now()
    elif isinstance(value, datetime):
        dt = value
    elif isinstance(value, date):
        dt = datetime(value.year, value.month, value.day)
    else:
        dt = datetime.now()
    return dt.strftime("%Y-%m-%d %H:%M:%S.") + f"{dt.microsecond // 1000:03d}"


def _handle_operation(items: list[dict[str, Any]], pk_fn=None) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    deleted: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            continue
        pk = str(item.get("pk") or (pk_fn(item) if pk_fn else ""))
        if item.get("operazione") == "D":
            deleted.add(pk)
            continue
        clean = {key: value for key, value in item.items() if key != "operazione"}
        existing = next((row for row in result if str(row.get("pk")) == pk), None)
        if existing:
            existing.update(clean)
        else:
            result.append(clean)
    return [item for item in result if str(item.get("pk")) not in deleted]


def _grade_to_ha(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "data": _date_only(item.get("datGiorno") or item.get("datEvento")),
        "materia": item.get("desMateria") or item.get("materia") or item.get("materiaLight", {}).get("codMateria"),
        "valore": item.get("valore") or item.get("codCodice"),
        "descrizione": item.get("descrizioneVoto"),
        "prova": item.get("descrizioneProva"),
        "docente": item.get("docente"),
        "raw": item,
    }


def _register_to_ha(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "data": _date_only(item.get("datGiorno")),
        "ora": item.get("ora"),
        "materia": item.get("materia"),
        "docente": item.get("docente"),
        "attivita": _clean(item.get("attivita")),
        "compiti": [
            {
                "data_assegnazione": _date_only(item.get("datGiorno")),
                "data_consegna": _date_only(homework.get("dataConsegna")),
                "materia": item.get("materia"),
                "docente": item.get("docente"),
                "ora": item.get("ora"),
                "testo": _clean(homework.get("compito")),
            }
            for homework in item.get("compiti") or []
        ],
        "raw": item,
    }


def _memo_to_ha(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "data": _date_only(item.get("datGiorno")),
        "docente": item.get("docente"),
        "testo": _clean(item.get("desAnnotazioni")),
        "ora_inizio": item.get("oraInizio"),
        "ora_fine": item.get("oraFine"),
        "raw": item,
    }


def _board_to_ha(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "data": _date_only(item.get("data") or item.get("datEvento")),
        "autore": item.get("autore"),
        "categoria": item.get("categoria"),
        "titolo": item.get("oggetto") or item.get("categoria"),
        "testo": _clean(item.get("messaggio")),
        "allegati": item.get("listaAllegati") or [],
        "raw": item,
    }


def _student_board_to_ha(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "data": _date_only(item.get("data") or item.get("datEvento")),
        "titolo": item.get("messaggio") or item.get("nomeFile"),
        "testo": item.get("nomeFile"),
        "raw": item,
    }


def _attendance_summary(appello: list[dict[str, Any]], fuori_classe: list[dict[str, Any]]) -> dict[str, Any]:
    summary = {
        "assenze": 0,
        "ritardi": 0,
        "uscite": 0,
        "fuori_classe": len(fuori_classe),
        "eventi": appello,
    }
    for item in appello:
        code = str(item.get("codEvento") or item.get("codice") or "").upper()
        description = str(item.get("descrizione") or item.get("desEvento") or "").lower()
        if code == "A" or "assen" in description:
            summary["assenze"] += 1
        elif code == "R" or "ritard" in description:
            summary["ritardi"] += 1
        elif code == "U" or "uscit" in description:
            summary["uscite"] += 1
    return summary


def _build_updates(
    grades: list[dict[str, Any]],
    class_board: list[dict[str, Any]],
    student_board: list[dict[str, Any]],
    appello: list[dict[str, Any]],
    fuori_classe: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    updates: list[dict[str, Any]] = []
    for grade in grades:
        updates.append(
            {
                "tipo": "Voto",
                "data": grade.get("data"),
                "titolo": grade.get("materia"),
                "testo": f"{grade.get('valore') or ''} {grade.get('descrizione') or ''}".strip(),
            }
        )
    for item in class_board:
        updates.append({"tipo": "Bacheca", **item})
    for item in student_board:
        updates.append({"tipo": "Bacheca alunno", **item})
    for item in appello:
        updates.append(
            {
                "tipo": "Appello",
                "data": _date_only(item.get("data") or item.get("datEvento")),
                "titolo": item.get("descrizione") or item.get("desEvento"),
                "testo": _clean(item.get("nota") or item.get("commentoGiustificazione")),
                "raw": item,
            }
        )
    for item in fuori_classe:
        updates.append(
            {
                "tipo": "Fuori classe",
                "data": _date_only(item.get("data") or item.get("datEvento")),
                "titolo": item.get("descrizione"),
                "testo": _clean(item.get("nota")),
                "raw": item,
            }
        )
    updates.sort(key=lambda item: item.get("data") or "", reverse=True)
    return updates[:MAX_ATTRIBUTE_ITEMS]


def _build_upcoming(
    pending_assignments: list[dict[str, Any]],
    activities: list[dict[str, Any]],
    memos: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    today = _today_key()
    for item in pending_assignments:
        items.append({"tipo": "Compito", **item})
    for item in activities:
        if _date_sort_key(item.get("data")) >= today:
            items.append({"tipo": "Attivita", **item})
    for item in memos:
        if _date_sort_key(item.get("data")) >= today:
            items.append({"tipo": "Promemoria", **item})
    items.sort(key=lambda item: item.get("data_consegna") or item.get("data") or "")
    return items[:MAX_ATTRIBUTE_ITEMS]


def _group_by(items: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        group = str(item.get(key) or "Altro")
        result.setdefault(group, []).append(item)
    return result


def _today_key() -> str:
    return date.today().isoformat()


def _date_sort_key(value: Any) -> str:
    return _date_only(value) or "0000-00-00"


def _date_only(value: Any) -> str | None:
    if not value:
        return None
    return str(value)[:10]


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\n", " ").split())


def _number_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(str(value).replace(",", ".")), 2)
    except ValueError:
        return None


def _average(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _deep_get(value: Any, *keys: str) -> Any:
    current = value
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _first_value(*sources: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for source in sources:
        found = _find_first_key(source, keys)
        if found not in (None, ""):
            return found
    return None


def _find_first_key(value: Any, keys: tuple[str, ...]) -> Any:
    if isinstance(value, dict):
        for key in keys:
            if key in value and value[key] not in (None, ""):
                return value[key]
        for item in value.values():
            found = _find_first_key(item, keys)
            if found not in (None, ""):
                return found
    elif isinstance(value, list):
        for item in value:
            found = _find_first_key(item, keys)
            if found not in (None, ""):
                return found
    return None
