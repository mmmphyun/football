# StatsBomb       —   
(  v2 +    )

---

##  
1. [Part 1.    (v2,  )](#part-1----v2--)
2. [Part 2.      ](#part-2------)
3. [Part 3.     ](#part-3-----)
4. [Part 4.    (Implementation Checklist)](#part-4----implementation-checklist)

---

# Part 1.    (v2,  )

## 1. 
StatsBomb Open Data · **(1)     ** **(2)     ()  **    .
  ** 1(360    )**,  **· **,  "" ** +  (360 )**,  **Docker Compose** .

## 2.   
- **StatsBomb Open Data** (GitHub statsbomb/open-data, **CC BY 4.0 —   **):
  - `competitions.json`
  - `matches/{competition_id}/{season_id}.json`
  - `events/{match_id}.json`
  - `lineups/{match_id}.json`
  - `three-sixty/{match_id}.json` (  )
- ****:  120×80 (x: 0~120, y: 0~80),  x=0/120.  `x,y`, `possession`(  id), `minute/second`, `type`, `shot_statsbomb_xg`, `play_pattern`( play_pattern=penalty )  .
- **360 **:   (·· )       .  /   +   .
- ****: Python (FastAPI + pandas/numpy) , React (Vite + TypeScript + Tailwind + D3 SVG) , SQLite ( ) +   ( JSON), Docker Compose (backend :8000, frontend :3000). Docker  `python:3.13-slim`,  matplotlib .

## 3.  
###   (CLI)
- `fetch` : `competitions.json`       **GitHub API `three-sixty/`    **, **  (≥30,   )  360     **    . `COMPETITION_ID`/`SEASON_ID`   .
-    ,   ** 3 ( )  **  /  .  JSON `data/raw/` .
- `process` :  ** **(  ,    , `--force` ).   `data/db.sqlite`   `has_360` .

###   (  )
- ****:     /    (360  ,    ).
- ** **:  **12×8 (10m )**  ·     (8×8, 16×12  ).
- ** **:   +   (=,  ),  15  +  (Δx).
- ** **: 360    ·, (>5.5m/s) ,    .
- ** **:  (/  ·3 ),  (   + PPDA),  (  → 8  / 3  ·  ).

###    + 
- ****: (··) + **xG ≥ 0.25** .
- **( )**:  =    **  **(:  30 ,  15 ),  = **   ( 4 )**.  / .            .
- ** **:     1 . 360 **  **    + ,    +  .    , **      **.

###   ( , 360 )
-      (  ) ,   **+2  ** : ( , 8m/s )  →    →      0.15/s  . · .
-  API ·    ** ()** . **360   **(   ).

### / ()
-   → **  **:  (, ,  ,  , , , ) +  .
- ** **:  (···xG) → (/,  0.5×/1×/2×,  ,  ) +  . ** 0    UI** .
- **(TacticalBoard)**: D3 SVG, 120×80 → 105×68   ,   =    ( ),  (·),   ,   . :  ,  , / .

### /
- Docker Compose: `backend`(uvicorn, 8000), `frontend`(nginx  , 3000), `data/`  . / `docker compose run --rm backend python -m app.cli fetch|process` .
-   (3000) ↔ (8000)   **CORS **(localhost:3000 ) .
- **README StatsBomb Open Data   CC BY 4.0  **  .

## 4. API 
- `GET /api/competitions` →    (, ,  , `has_360`)
- `GET /api/competitions/{id}/matches` →   (/, , , `has_360`,  )
- `GET /api/matches/{id}/summary` →  {formation(/  ), zones( ), pass_network(·), movement( ··), buildup, pressure(index·ppda), transitions}
- `GET /api/matches/{id}/highlights` → {id, team, type, minute, xg, window{start_event, end_event}}
- `GET /api/highlights/{id}/frames` → {players[{id,number,name,team}], frames[{event_index, t, ball, players[{id,x,y,vx,vy,max_speed}]}], grid_config}

## 5.  
- ** (pytest, )**:   1  `backend/tests/fixtures/`  →  ( ··  ),   ,   , (· ), API   .
- ** (Vitest)**: 120×80 →   ,    ,  ,   .
- ** **: `docker compose up` → `fetch`/`process`  → UI ·    ,        (360 )  .

## 6.  
- UI  ****,    . ·   (/).
-    360      ,    .
-    ,    , ML   v2  .
- `fetch`     `--force`  .

---

# Part 2.      

  (`backend/app/analysis/` )   /      .

### 2.1 StatsBomb 360 Open Data   (Critical)
* ****:
  - `formation.py`, `zones.py`, `movement.py` `ev.get("freeze_frame")` `p.get("player", {}).get("id")`  .
  -  StatsBomb  360  `three-sixty/{match_id}.json`   , freeze_frame   **`player_id`   **(`{"teammate": bool, "actor": bool, "keeper": bool, "location": [x, y]}`).
  -   `pid is None`   360   .
* ****:
  1. `events` `three-sixty`   `event["id"] == frame["event_uuid"]`   .
  2. `zones.py`:  ID  `teammate`     ID /     .
  3. `formation.py`: 360     /  ,     ID    (Pass/Carry/Tackle/Shot )    .
  4. `movement.py`:   360     , **      **     (`actor`)  / .

### 2.2    `attack_direction` 
* ****:
  - `common.py`, `buildup.py`, `transitions.py`    (-1  1)    .
  - StatsBomb   **    x=0 → x=120 (  ) ** .
* ****:
  -  `attack_direction`    x (0:  ~ 120: ) .
  -  /: `end[0] - start[0] >= `.
  - 3 :   (`x < 40`),   (`40 <= x < 80`), /  (`x >= 80`).

### 2.3 PPDA     
* ****:
  - `common.event_time()` `(period - 1) * 3600`   90  `duration_min` 150     .
  - PPDA  (0~120)  /       .
* ****:
  - `duration_min`:   `minute`   period      ( 90~100).
  - PPDA: **   (StatsBomb  `x >= 40`)**        (Pressure, Tackle, Interception, Block, Clearance)   .
    $$\text{PPDA} = \frac{\text{Opponent Passes in } x \ge 40}{\text{Defensive Actions in } x \ge 40}$$

### 2.4   (Thirds)  
* ****:
  - `buildup.py` `team == team_id`   `seen_possessions`          .
* ****:
  - `ev.get("possession_team", {}).get("id") == team_id`        (`location`)  //    .

### 2.5    
* ****:
  - GitHub Contents API(`downloader.py`)    60/ Rate Limit  360    .
  - `storage.py` `upsert_competition` `match_count` , `list_matches` `season_id`  .
* ****:
  - `downloader.py`: Contents API   graceful fallback    (`data/raw/`)  .
  - `storage.py`:      .

---

# Part 3.     

```

                    Frontend (React 18 + Vite)               
  - TacticalBoard (D3 SVG 120x80 Grid / Tokens / Ghosts)    
  - MatchView (Tactical Summary: Formation, Zones, Passes)   
  - HighlightView (Player Controller + Ghost Extrapolation)  

                                HTTP (:3000 -> :8000/api)

                    Backend (FastAPI)                        
  - main.py: CORS, REST API 5 Routes                         
  - highlights.py & frames.py: Clip Window & Frame Builder   
  - analysis/*.py: 8 Tactical Engine Modules                 
  - storage.py: SQLite (data/db.sqlite)                      
  - downloader.py: GitHub StatsBomb Open Data Fetcher        
  - cli.py: `fetch` & `process` CLI Commands                 

                                File System

                    Data Storage Layer                       
  - data/raw/{competitions,matches,events,lineups,360}.json   
  - data/db.sqlite (Processed Summaries & Frames)             

```

## 3.1    
- `app/config.py`:  ,  ,  .
- `app/downloader.py`: StatsBomb GitHub     `data/raw/`  .
- `app/storage.py`: SQLite     CRUD .
- `app/analysis/`:
  - `common.py`:  ,   ,  .
  - `formation.py`: /    .
  - `zones.py`: 12×8 (8×8, 16×12)    .
  - `passes.py`:   /   .
  - `movement.py`: /  , ,  .
  - `pressure.py`:  (x ≥ 40) PPDA    .
  - `buildup.py`:  /    (3).
  - `transitions.py`:    8  /   .
  - `predict.py`:  +   +     (+2).
- `app/highlights.py`: , , xG ≥ 0.25     .
- `app/frames.py`:      /  .
- `app/processing.py`:  JSON  →   +  +    .
- `app/cli.py`: `fetch` (360   ), `process` ( ) CLI .
- `app/main.py`: FastAPI    CORS .

## 3.2     

### 1)    
```python
# :     (:   30 )
# :     (:   15 )
# :      (: 4 )
GOAL_CAP_SECONDS = 30
SHOT_CAP_SECONDS = 15
AFTER_EVENT_SECONDS = 4
HIGHLIGHT_XG_THRESHOLD = 0.25
```

### 2)     (Predict Extrapolation)
```python
def extrapolate(pos, vel, max_speed, anchor, t_sec=2.0, pull=0.15):
    # 1.   ( 8.0 m/s)
    speed = math.hypot(vel[0], vel[1])
    if speed > max_speed and speed > 0:
        vel = (vel[0] * max_speed / speed, vel[1] * max_speed / speed)
    # 2.  
    pred_x = pos[0] + vel[0] * t_sec
    pred_y = pos[1] + vel[1] * t_sec
    # 3.   (Anchor)  
    if anchor is not None:
        weight = min(1.0, pull * t_sec)
        pred_x += (anchor[0] - pred_x) * weight
        pred_y += (anchor[1] - pred_y) * weight
    # 4.    (0~120, 0~80)
    pred_x = max(0.0, min(120.0, pred_x))
    pred_y = max(0.0, min(80.0, pred_y))
    return (round(pred_x, 2), round(pred_y, 2))
```

---

# Part 4.    (Implementation Checklist)

###  Step 1:      
- [ ] `backend/app/analysis/common.py`:  `attack_direction` , `event_time`      .
- [ ] `backend/app/analysis/formation.py`: 360           .
- [ ] `backend/app/analysis/zones.py`: `three_sixty`     ID   (`teammate`)    .
- [ ] `backend/app/analysis/pressure.py`:  (x ≥ 40)  PPDA       `pressures_per_min` .
- [ ] `backend/app/analysis/buildup.py`: `possession_team`  3       .
- [ ] `backend/app/analysis/movement.py`:      dt  / .

###  Step 2: , ,  
- [ ] `backend/app/storage.py`: `match_count`, `season_id`    /    .
- [ ] `backend/app/downloader.py`: `fetch_three_sixty_index` Rate Limit   `data/raw/`  / .
- [ ] `backend/app/highlights.py`: //xG≥0.25  +      .
- [ ] `backend/app/frames.py`:   360 //   .
- [ ] `backend/app/processing.py`:      DB   .
- [ ] `backend/app/cli.py`: `fetch`, `process` CLI  .
- [ ] `backend/app/main.py`: FastAPI    REST  5 .

###  Step 3:   
- [ ] `backend/tests/fixtures/`:     (`events.json`, `lineups.json`, `three-sixty.json`, `matches.json`).
- [ ] `backend/tests/test_analysis.py`:  (, , PPDA, )   .
- [ ] `backend/tests/test_highlights.py`:       .
- [ ] `backend/tests/test_predict.py`:  /      .
- [ ] `backend/tests/test_api.py`: FastAPI   .

###  Step 4:    (`frontend/`)
- [ ] React 18 + Vite + TypeScript + Tailwind CSS .
- [ ] `frontend/Dockerfile` & `nginx.conf` (:3000 , :8000 API ).
- [ ] `src/lib/pitch.ts`: StatsBomb 120×80 ↔ SVG    .
- [ ] `src/lib/predict.ts` & `src/lib/interpolate.ts`:       .
- [ ] `src/components/TacticalBoard.tsx`: D3 SVG   ( , ,  ,  ).
- [ ] `src/components/MatchView.tsx`:        .
- [ ] `src/components/HighlightView.tsx`:  ,  (///),   UI.
- [ ] `src/App.tsx`: /      .
- [ ] Vitest   (`pitch.test.ts`, `predict.test.ts`).

###  Step 5:     
- [ ] `docker compose up --build -d`      .
- [ ] `docker compose run --rm backend python -m app.cli fetch`  `process`  .
- [ ]  UI(http://localhost:3000)       .
- [ ] README  UI  StatsBomb Open Data (CC BY 4.0)   .
