# StatsBomb       —    v3
(StatsBomb Open Data       )

---

##  
1. [    ](#1-----)
2. [StatsBomb     ](#2-statsbomb-----)
3. [  (Downloader & Storage)](#3---downloader--storage)
4. [  8   (Analysis Engine)](#4---8---analysis-engine)
5. [ &   ](#5-----)
6. [REST API  (Backend Endpoints)](#6-rest-api--backend-endpoints)
7. [   (TacticalBoard & UI)](#7----tacticalboard--ui)
8. [   (Implementation Checklist)](#8----implementation-checklist)

---

# 1.     

## 1.1 
StatsBomb Open Data(GitHub `statsbomb/open-data`, CC BY 4.0) ·:
1. **    ** (, 12×8  ,  ,  , ,  )
2. **    (D3 SVG)  ** (360  ,   ,  , +2   , 22    )
    .

## 1.2   
```

                 Frontend (React 18 + TypeScript + Vite)      
  - TacticalBoard.tsx (D3 SVG 120x80 / Zones / Tokens / Ghost)
  - MatchView.tsx (8     &  ) 
  - HighlightView.tsx ( , , )  

                                HTTP (:3000 -> :8000/api)

                 Backend (FastAPI / Python 3.13+)            
  - main.py: CORS, REST API 5 Routes                         
  - highlights.py & frames.py:   &        
  - analysis/*.py: 8                       
  - processing.py:                
  - storage.py: SQLite (data/db.sqlite) CRUD                 
  - downloader.py: GitHub Raw  & data/raw/    
  - cli.py: `fetch` & `process` CLI                    

                                File System

                    Data Storage Layer                       
  - data/raw/{competitions,matches,events,lineups,360}.json   
  - data/db.sqlite (  ,  , ) 

```

---

# 2. StatsBomb     

## 2.1    ($x=0 	o 120$)
* ** **:  $120.0\text{m} \times$  $80.0\text{m}$
* **  **: StatsBomb  /, /   **     ($x=0$) ($x=120$) **  .
* **[]**  $-1$  `attack_direction`      .
  -   (Defensive Third): $0.0 \le x < 40.0$
  -   (Middle Third): $40.0 \le x < 80.0$
  - /  (Final Third): $80.0 \le x \le 120.0$

## 2.2 360     
* 360  `three-sixty/{match_id}.json`   , `event_uuid` `events.json` `event["id"]` 1:1 .
* 360     `player_id`  ** **:
  ```json
  { "teammate": true, "actor": false, "keeper": false, "location": [61.0, 40.1] }
  ```
* **     **:
  1. `actor: true` $\to$   `event["player"]["id"]` 100%  / .
  2. `keeper: true` $\to$    GK .
  3. `teammate: true/false` $\to$ /    12×8    .
  4. `visible_area`  $\to$      .
  5.     $\to$    (Anchor)     ( ).

## 2.3    
* `minute` `second`  1/1    .
* `(period - 1) * 3600`   , `duration_min = max(event.minute)`   period    90~100 .

---

# 3.   (Downloader & Storage)

## 3.1 `app/downloader.py`
* **360    **:
  - `competitions.json` `match_available_360`  `null`  `MIN_MATCHES`($\ge 30$)     . (GitHub API Rate limit  )
  - `COMPETITION_ID`/`SEASON_ID`      .
* **   (`data/raw/`)**:
  -   `data/raw/...`     .
  -    GitHub Raw     JSON .
  -     3 .

## 3.2 `app/storage.py` (SQLite Schema)
* `competitions`: `competition_id`, `season_id`, `name`, `season_name`, `country`, `match_count`, `has_360`, `processed_at`
* `matches`: `match_id`, `competition_id`, `season_id`, `home_team`, `away_team`, `home_team_id`, `away_team_id`, `home_score`, `away_score`, `match_date`, `has_360`, `status`
* `match_summaries`: `match_id`, `summary_json`
* `highlights`: `id`, `match_id`, `team_id`, `team_name`, `type`, `minute`, `second`, `xg`, `start_event`, `end_event`, `event_index`
* `highlight_frames`: `id`, `match_id`, `frames_json`, `players_json`, `has_360`

---

# 4.   8   (Analysis Engine)

### 1) `app/analysis/common.py`
* `event_time(ev)`: `minute * 60 + second`     .
* `is_completed_pass(ev)`: `type == 'Pass'` and `pass.outcome is None` ( 'Complete').
* `build_lineup_maps(lineups)`: / , , , GK  .
* `team_ids(events)` & `opponent_of(team_id, team_ids_list)`.

### 2) `app/analysis/formation.py`
* **/ (`possession`, `out_of_possession`)   **:
  -     (Pass, Carry, Shot, Tackle, Pressure, Receipt )     $(x, y)$ .
  - 360       .

### 3) `app/analysis/zones.py`
* **12×8    ($10\text{m} \times 10\text{m}$ )**:
  - 360   :     `teammate`   /    .
  - -360 :   (`location`, `pass.end_location`, `carry.end_location`)  .
  -     ($0.0 \sim 1.0$) .

### 4) `app/analysis/passes.py`
* **  (Pass Network)**:
  -    Passer $\to$ Recipient    ( 15).
  -       $(x, y)$  .
  -     $\Delta x$ .

### 5) `app/analysis/pressure.py`
* **  &   PPDA**:
  -   (`duration_min`)    (`pressures_per_min`).
  - PPDA:    ($x \ge 40$)     $\div$    (`Pressure`, `Tackle`, `Interception`, `Block`, `Clearance`) .
    $$\text{PPDA} = \frac{\text{Opponent Passes in } x \ge 40}{\text{Defensive Actions in } x \ge 40}$$

### 6) `app/analysis/buildup.py`
* **  & 3  **:
  -  : $(end[0] - start[0]) \ge 10.0\text{m}$
  -  : $(end[0] - start[0]) \ge 5.0\text{m}$
  -   : `possession_team == team_id`      ($x < 40$), ($40 \le x < 80$), ($x \ge 80$)    .

### 7) `app/analysis/transitions.py`
* **     **:
  -  (`Ball Recovery`, `Interception`)    8     ($x \ge 80$)      .

### 8) `app/analysis/predict.py`
* **   (+2)**:
  -   $\to$    ($8.0\text{m/s}$) $\to$    ($0 \le x \le 120, 0 \le y \le 80$) $\to$      ($0.15/\text{s}$) .

---

# 5.  &   

## 5.1    (`app/highlights.py`)
* ** **:
  1.  (Goal: ,  , )
  2.   ($xG \ge 0.25$)
* **    **:
  - ** **:    (`possession`)    (:   30 ,   15 ).
  - ** **:      (:  4 ).

## 5.2    (`app/frames.py`)
*        :
  - `event_index`, `timestamp`, `minute`, `second`, `ball_location`
  - `visible_area`:     (360 )
  - `players`: 
    - 360      (`is_teammate`, `is_actor`, `is_keeper`, `location: [x, y]`)
    -        $(v_x, v_y)$  $+2$    $(pred_x, pred_y)$
    - -360 :     

---

# 6. REST API  (Backend Endpoints)

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/competitions` |     (`competition_id`, `season_id`, `name`, `match_count`, `has_360`) |
| `GET` | `/api/competitions/{comp_id}/matches?season_id={season_id}` |     (/ , , , 360 ,  ) |
| `GET` | `/api/matches/{match_id}/summary` | 8     (,  ,  , /PPDA, , ) |
| `GET` | `/api/matches/{match_id}/highlights` |     (`id`, `team`, `type`, `minute`, `xg`, `window`) |
| `GET` | `/api/highlights/{highlight_id}/frames` |     ( ,  ,  ,  ) |

---

# 7.    (TacticalBoard & UI)

## 7.1  
* **React 18 + TypeScript + Vite + Tailwind CSS + D3.js (SVG  )**

## 7.2   
1. **`TacticalBoard.tsx`**:
   - $120 \times 80$  $\to$ SVG   .
   - 12×8    &    .
   -    (`visible_area`)  .
   -    &  .
   -    ( , ,  ).
   -      (Ghost Vector).
   - **[] 22    **:          .
2. **`MatchView.tsx`**:
   -      (,   ,  , PPDA ,  3 ).
3. **`HighlightView.tsx`**:
   -      .
   - /,   ($0.5\times / 1\times / 2\times$),  ,  (Interpolation).

---

# 8.    (Implementation Checklist)

###  Step 1:   &   
- [ ] `backend/app/config.py`:     .
- [ ] `backend/app/downloader.py`: `competitions.json`  360     `data/raw/`   .
- [ ] `backend/app/storage.py`: SQLite      CRUD .

###  Step 2:   8  & 
- [ ] `backend/app/analysis/common.py`:   , `attack_direction`  ,  `event_time`  .
- [ ] `backend/app/analysis/formation.py`:       .
- [ ] `backend/app/analysis/zones.py`: `three-sixty`    12×8   .
- [ ] `backend/app/analysis/passes.py`:        .
- [ ] `backend/app/analysis/pressure.py`:  ($x \ge 40$) PPDA       .
- [ ] `backend/app/analysis/buildup.py`: `possession_team`  3     .
- [ ] `backend/app/analysis/transitions.py`:    8    .
- [ ] `backend/app/analysis/predict.py`: /      .

###  Step 3: ,   & 
- [ ] `backend/app/highlights.py`:   $xG \ge 0.25$   +     .
- [ ] `backend/app/frames.py`: 360 ///   .
- [ ] `backend/app/processing.py`:     DB   .
- [ ] `backend/app/cli.py`: `fetch`, `process` CLI  .
- [ ] `backend/app/main.py`: FastAPI REST API  5  CORS .

###  Step 4:  / 
- [ ] `backend/tests/fixtures/`:    .
- [ ] `backend/tests/test_analysis.py`: 8    .
- [ ] `backend/tests/test_highlights.py`:      .
- [ ] `backend/tests/test_api.py`: FastAPI   .

###  Step 5:    (`frontend/`)
- [ ] React 18 + Vite + TypeScript + Tailwind CSS .
- [ ] `src/lib/pitch.ts`: $120 \times 80 \leftrightarrow$ SVG   .
- [ ] `src/lib/interpolate.ts` & `src/lib/predict.ts`:       .
- [ ] `src/components/TacticalBoard.tsx`: D3 SVG  ,  , , .
- [ ] `src/components/MatchView.tsx`:        .
- [ ] `src/components/HighlightView.tsx`:  , ,   UI.
- [ ] `src/App.tsx`: /     .

###  Step 6:     
- [ ] `fetch` & `process`      .
- [ ]      / .
