"""
Fælles, høfligt læselag oven på GoMemberClient til de automatiske kørsler.

- Alle kald går gennem GoMemberClient.get() - kun GET (se ../CLAUDE.md). Her
  findes ingen anden måde at kontakte goMember på.
- Maks 2 kald pr. sekund samlet (MIN_INTERVAL), timeout 30 s (i klienten).
- Et kald, der fejler med timeout, forbindelsesfejl, HTTP 429 eller 5xx,
  prøves igen højst 2 gange med pause imellem.
- Login prøves aldrig igen, hvis det fejler: en forkert adgangskode giver
  præcis ét mislykket login pr. kørsel (så kontoen ikke låses).
- Loft over antal kald pr. kørsel (loft=...).
- Fejlbeskeder er korte og på dansk og indeholder aldrig svarets indhold,
  tokens eller adgangskoder.
"""
import collections
import os
import sys
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from gomember_client import GoMemberClient, GoMemberAuthError  # noqa: E402  (kun get())

MIN_INTERVAL = 0.5          # sekunder mellem kald -> maks 2 kald/s
EKSTRA_FORSOEG = 2          # genforsøg pr. fejlet kald (ikke login)
PAUSER = (2.0, 6.0)         # pause før 1. og 2. genforsøg
MAKS_TOKENHENTNINGER = 3    # normalt 1; token kan fornys, hvis det udløber


class NetFejl(RuntimeError):
    """Fejl der skal stoppe kørslen. Teksten er kort, dansk og uden hemmeligheder."""


class LoftNaaet(NetFejl):
    pass


def har_login():
    return bool(os.environ.get("GOMEMBER_USERNAME") and os.environ.get("GOMEMBER_PASSWORD"))


class Hentning:
    def __init__(self, loft=600, anonym=None, base_url=None):
        self.anonym = (not har_login()) if anonym is None else anonym
        try:
            self.client = GoMemberClient(anonymous=self.anonym, base_url=base_url)
        except GoMemberAuthError:
            raise NetFejl("Login-oplysningerne (GOMEMBER_USERNAME/GOMEMBER_PASSWORD) mangler.") from None
        self.loft = loft
        self.n = 0                      # antal HTTP-forespørgsler (GET), inkl. genforsøg
        self.status = collections.Counter()
        self.genforsoeg = 0
        self.logins = 0
        self._login_fejlet = False
        self._last = 0.0
        # Tæl og begræns login-forsøg uden at ændre klientens adfærd.
        orig = self.client._fetch_token

        def _fetch_token_vagt():
            if self._login_fejlet:
                raise NetFejl("Login til goMember er allerede fejlet i denne kørsel; prøver ikke igen.")
            if self.logins >= MAKS_TOKENHENTNINGER:
                raise NetFejl("For mange login-forsøg i én kørsel; stopper for ikke at låse kontoen.")
            self._vent()
            self.logins += 1
            try:
                orig()
            except GoMemberAuthError:
                self._login_fejlet = True
                raise NetFejl("Login til goMember fejlede (forkert brugernavn/adgangskode, eller goMember "
                              "afviste login). Prøver ikke igen i denne kørsel.") from None
            except requests.Timeout:
                self._login_fejlet = True
                raise NetFejl("Login til goMember fik ikke svar inden for 30 s. Prøver ikke igen.") from None
            except requests.RequestException as e:
                self._login_fejlet = True
                raise NetFejl(f"Login til goMember mislykkedes ({type(e).__name__}: ingen forbindelse). "
                              "Prøver ikke igen.") from None
        self.client._fetch_token = _fetch_token_vagt

    @property
    def tilstand(self):
        return "anonym" if self.anonym else "login"

    def _vent(self):
        wait = MIN_INTERVAL - (time.time() - self._last)
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()

    def get(self, path, query=None, tilladt=(404,)):
        """GET path. Returnerer (status, data). 200 og statusser i `tilladt` returneres;
        alt andet stopper kørslen med NetFejl efter højst 2 genforsøg (kun ved 429/5xx/timeout)."""
        forsoeg = 0
        while True:
            if self.n >= self.loft:
                raise LoftNaaet(f"Loftet på {self.loft} kald pr. kørsel er nået; stopper.")
            self._vent()
            self.n += 1
            try:
                data = self.client.get(path, query_params=query)
                self.status[200] += 1
                return 200, data
            except NetFejl:
                raise
            except GoMemberAuthError:
                self.status["login"] += 1
                raise NetFejl("Login til goMember fejlede (forkert brugernavn/adgangskode, "
                              "eller goMember afviste login). Prøver ikke igen i denne kørsel.") from None
            except requests.HTTPError as e:
                st = e.response.status_code if e.response is not None else -1
                self.status[st] += 1
                if st in tilladt:
                    return st, None
                if st == 401 or st == 403:
                    raise NetFejl(f"goMember afviste adgang (HTTP {st}) til {path}.") from None
                kan_igen = st == 429 or st >= 500
                beskrivelse = f"HTTP {st}"
            except requests.Timeout:
                self.status["timeout"] += 1
                kan_igen, beskrivelse = True, "timeout (30 s)"
            except requests.ConnectionError:
                self.status["forbindelse"] += 1
                kan_igen, beskrivelse = True, "ingen forbindelse"
            except requests.RequestException as e:
                self.status["andet"] += 1
                kan_igen, beskrivelse = False, type(e).__name__
            if not kan_igen or forsoeg >= EKSTRA_FORSOEG:
                raise NetFejl(f"Kaldet til {path} fejlede ({beskrivelse})"
                              + (f" også efter {forsoeg} genforsøg." if forsoeg else ".")) from None
            time.sleep(PAUSER[forsoeg])
            forsoeg += 1
            self.genforsoeg += 1
