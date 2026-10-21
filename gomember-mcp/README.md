# goMember read-only MCP-server

En MCP-server der udelukkende eksponerer **GET**-endpoints fra goMember/MemberLink
API'et (Strong Gyms swagger-fil), afgrænset til Aktiviteter, Events, Bookinger og
Hold/Etiketter (tags). 49 værktøjer i alt.

## Hvorfor det er read-only, konkret

- `gomember_client.py` implementerer kun `get()`. Der findes ingen `post()`,
  `put()`, `patch()` eller `delete()`-metode i klassen - så der er ingen
  kodevej der kan skrive eller slette data i goMember, uanset hvad nogen
  (inklusive Claude Code) beder om.
- `server.py` er auto-genereret af `generate.py` direkte fra swagger-filens
  GET-operationer inden for det aftalte scope. Ret aldrig i `server.py` i
  hånden - ret i `generate.py` og kør den igen, ellers forsvinder ændringen
  næste gang filen genereres.
- Kontoen (det fiktive goMember-medlem) er et andet, svagere lag - se README-
  historikken i chatten. Kodelaget her er det lag du reelt kan stole på.

## Opsætning

```powershell
cd gomember-mcp
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

På macOS/Linux hedder de tre sidste trin `source .venv/bin/activate`,
samme `pip install`, og `cp .env.example .env`. Resten af kommandoerne i
denne fil skrives med `python`; på et system hvor `python` peger på
Python 2, brug `python3` i stedet.

Udfyld `.env` med login for det fiktive read-only medlem:

```
GOMEMBER_USERNAME=dit-fiktive-medlems-login
GOMEMBER_PASSWORD=...
```

## Test login og API-adgang FØR du kobler den til Claude Code

```powershell
python check_auth.py
```

(`python-dotenv` står i `requirements.txt`, så `check_auth.py` læser `.env`
automatisk efter `pip install -r requirements.txt`.)

Scriptet logger ind, henter et token, og laver ét harmløst GET-kald
(`/api/activity`) for at bekræfte at det fiktive medlem rent faktisk har
adgang. Hvis login fejler med noget i stil med `invalid_client`, sæt
`GOMEMBER_CLIENT_ID` i `.env` - swagger-filen dokumenterer desværre ikke om
token-endpointet kræver det.

**Vigtigt:** dette script tester kun at login og læsning virker. Det tester
IKKE om goMember rent faktisk afviser skrivekald fra denne konto - det API'et
her aldrig kalder, netop fordi write-metoderne ikke eksisterer i koden.

## Registrér i Claude Code

Fra terminalen i dit Strong Gym-projekt:

```bash
claude mcp add gomember-readonly \
  --env GOMEMBER_USERNAME=dit-fiktive-medlems-login \
  --env GOMEMBER_PASSWORD=... \
  -- /absolut/sti/til/gomember-mcp/.venv/Scripts/python /absolut/sti/til/gomember-mcp/server.py
```

Eller manuelt i `.mcp.json` i projektet:

```json
{
  "mcpServers": {
    "gomember-readonly": {
      "command": "/absolut/sti/til/gomember-mcp/.venv/Scripts/python",
      "args": ["/absolut/sti/til/gomember-mcp/server.py"],
      "env": {
        "GOMEMBER_USERNAME": "dit-fiktive-medlems-login",
        "GOMEMBER_PASSWORD": "..."
      }
    }
  }
}
```

Genstart Claude Code, og de 49 værktøjer bliver tilgængelige (fx
`list_activities`, `list_events_for_activity`, `get_events_for_calendar_v3`,
`list_tags`, `get_tags_in_category`).

## Hvis du senere får brug for flere endpoints

Åbn `generate.py`, tilføj det aftalte tag til `SCOPED_TAGS` (eller tilføj det
specifikke path til `NAME_MAP` og udvid `SCOPED_TAGS`-filteret), kør
`python generate.py SGSwagger.json` igen. Kun GET-operationer bliver
nogensinde inkluderet, uanset hvad du tilføjer til scope - det er hårdkodet i
`build_ops()`, som filtrerer på `path_item.get("get")` og aldrig kigger på de
andre HTTP-metoder i swagger-filen.

## Filer

| Fil | Formål |
|---|---|
| `SGSwagger.json` | Swagger-specifikationen du sendte |
| `generate.py` | Genererer `server.py` ud fra swagger-filen |
| `gomember_client.py` | HTTP/auth-klient - kun `get()` findes |
| `server.py` | Den genererede MCP-server (49 read-only værktøjer) |
| `check_auth.py` | Selvstændig test af login + ét GET-kald |
| `.env.example` | Skabelon til credentials |
