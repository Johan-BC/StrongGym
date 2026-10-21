#!/usr/bin/env python3
"""
Selvstændig test af login mod goMember, uden om MCP-laget.
Kør denne FØR du sætter serveren op i Claude Code, så du ved credentials
og evt. client_id er korrekte.

Brug:
    python check_auth.py
(læser GOMEMBER_USERNAME / GOMEMBER_PASSWORD / GOMEMBER_CLIENT_ID fra miljøet,
 eller fra .env via python-dotenv, som står i requirements.txt)
"""
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from gomember_client import GoMemberClient, GoMemberAuthError

def main():
    try:
        client = GoMemberClient()
    except GoMemberAuthError as e:
        print(f"FEJL: {e}")
        sys.exit(1)

    print(f"Forsøger login mod {client.base_url}/auth/token som '{client.username}' ...")
    try:
        client._ensure_token()
    except GoMemberAuthError as e:
        print(f"Login FEJLEDE: {e}")
        print()
        print("Hvis fejlen nævner 'invalid_client' eller lignende: sæt GOMEMBER_CLIENT_ID i .env.")
        print("Hvis fejlen er 401/'invalid_grant': tjek brugernavn/password for det fiktive medlem.")
        sys.exit(1)

    print("Login OK - token modtaget.")
    print()
    print("Tester et harmløst GET-kald (liste over aktiviteter, side 1)...")
    try:
        result = client.get("/api/activity", query_params={"filter.pageSize": 5, "filter.currentPage": 1})
        print("GET-kald OK. Eksempel på svar (forkortet):")
        print(str(result)[:800])
    except Exception as e:
        print(f"GET-kaldet fejlede: {e}")
        print("Login virkede, men selve endpointet svarede med en fejl - tjek om det")
        print("fiktive medlem faktisk har fået rettigheder til Aktiviteter i goMember.")
        sys.exit(1)

    print()
    print("Alt ser rigtigt ud. Du kan nu bruge serveren fra Claude Code.")

if __name__ == "__main__":
    main()
