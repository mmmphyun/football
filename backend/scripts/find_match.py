from app.downloader import StatsBombDownloader

dl = StatsBombDownloader()
comps = dl.fetch_competitions()
wc = [c for c in comps if c.get("competition_name") == "FIFA World Cup" and c.get("season_name") == "2022"]
if wc:
    comp_id = wc[0]["competition_id"]
    season_id = wc[0]["season_id"]
    matches = dl.fetch_matches(comp_id, season_id)
    esp_crc = [m for m in matches if ("Spain" in m.get("home_team", {}).get("home_team_name", "") or "Spain" in m.get("away_team", {}).get("away_team_name", "")) and ("Costa Rica" in m.get("home_team", {}).get("home_team_name", "") or "Costa Rica" in m.get("away_team", {}).get("away_team_name", ""))]
    for m in esp_crc:
        print(f"Match ID: {m['match_id']}, {m.get('home_team', {}).get('home_team_name')} vs {m.get('away_team', {}).get('away_team_name')}, Score: {m.get('home_score')}-{m.get('away_score')}")
